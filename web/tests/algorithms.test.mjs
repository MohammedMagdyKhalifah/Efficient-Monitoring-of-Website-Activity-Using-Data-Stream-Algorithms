import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Bloom,FM,DGIM,ExactWindow,StreamEngine} from '../dist/algorithms.js';
import {zipFiles,crc32} from '../dist/download.js';
import {Worker} from 'node:worker_threads';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../dist/data');
const config={bits:1048576,k:7,h:16,window:10000,seed:42};

test('Bloom queries before inserting and never loses an inserted host',()=>{
  const b=new Bloom(65536,7),words=[1,2,3,4,5,6,7];
  assert.equal(b.checkAndAdd(words).present,false);
  assert.equal(b.checkAndAdd(words).present,true);
  assert.equal(b.setBits,7);
});
test('FM duplicate invariance, empty stream and group arithmetic',()=>{
  const f=new FM(16);assert.equal(f.estimate(),0);
  f.add(new Uint8Array(64).fill(3));assert.equal(f.estimate(),8);
  f.add(new Uint8Array(64).fill(1));assert.equal(f.estimate(),8);
  assert.deepEqual(f.means(),[8,8,8,8]);
});
test('DGIM exhaustively matches its positive-count bound and exact zero case',()=>{
  for(const window of [1,2,3,5,8,16])for(let sequence=0;sequence<512;sequence++){
    const d=new DGIM(window),exact=new ExactWindow(window),history=[];
    for(let i=0;i<9;i++){
      const bit=(sequence>>i)&1;history.push(bit);d.add(bit);exact.add(bit);
      const truth=history.slice(-window).reduce((a,b)=>a+b,0);
      assert.equal(exact.total,truth);assert.ok(Math.abs(d.estimate()-truth)<=truth*.5);
      const sizes=d.buckets.map(b=>b[0]);assert.ok(sizes.every(s=>sizes.filter(v=>v===s).length<=2));
      assert.ok(d.buckets.every(b=>b[1]>d.time-window));
    }
  }
});
test('Invalid configurations are rejected',()=>{
  assert.throws(()=>new Bloom(13,2));assert.throws(()=>new FM(3));assert.throws(()=>new DGIM(0));
  assert.throws(()=>new DGIM().add(2));
});
test('ZIP creation emits standard signatures, Unicode names and a valid CRC',async()=>{
  assert.equal(crc32(new TextEncoder().encode('123456789')),0xcbf43926);
  const zip=zipFiles([{name:'project/real.txt',data:new TextEncoder().encode('NASA')}]);
  const raw=new DataView(await zip.arrayBuffer());
  assert.equal(raw.getUint32(0,true),0x04034b50);
  assert.equal(raw.getUint32(raw.byteLength-22,true),0x06054b50);
});
test('All browser benchmark evidence is complete',()=>{
  const b=JSON.parse(fs.readFileSync(path.join(root,'benchmarks.json')));
  assert.equal(b.parameter_sweep.length,63);assert.equal(b.full_summary.length,3);assert.equal(b.scaling_summary.length,12);
});
test('Browser summaries reproduce the Python results on the complete real stream',()=>{
  const hash=zlib.gunzipSync(fs.readFileSync(path.join(root,'hashes-42.bin.gz')));
  const buffer=hash.buffer.slice(hash.byteOffset,hash.byteOffset+hash.byteLength);
  const engine=new StreamEngine(config,buffer);
  const records=zlib.gunzipSync(fs.readFileSync(path.join(root,'events.bin.gz')));
  assert.equal(records.length,1891714*20);
  for(let i=0;i<records.length;i+=20){
    const record=Array.from({length:5},(_,j)=>records.readUInt32LE(i+j*4));engine.process(record);
    if(engine.count===10000){assert.equal(engine.seen.size,936);assert.equal(engine.fm.estimate(),2528);assert.equal(engine.dgim.estimate(),48);}
    if(engine.count===100000){assert.equal(engine.seen.size,7752);assert.equal(engine.fm.estimate(),25088);}
  }
  const actual=engine.snapshot();assert.equal(actual.count,1891714);assert.equal(actual.unique,81982);
  assert.equal(actual.falsePositives,27);assert.equal(actual.falseNegatives,0);assert.equal(actual.fm,442368);
  assert.equal(actual.window,28);assert.equal(actual.exactWindow,30);assert.equal(actual.errors,10980);
});

test('The actual worker supports init, one step, real playback and one-per-second pacing',async()=>{
  const worker=new Worker(new URL('./worker-harness.mjs',import.meta.url));
  const messages=[],waiters=[];
  worker.on('message',data=>{
    const index=waiters.findIndex(w=>w.predicate(data));
    if(index>=0){const w=waiters.splice(index,1)[0];clearTimeout(w.timer);w.resolve(data);}
    else messages.push(data);
  });
  function next(predicate){
    const index=messages.findIndex(predicate);
    if(index>=0)return Promise.resolve(messages.splice(index,1)[0]);
    return new Promise((resolve,reject)=>{
      const waiter={predicate,resolve,timer:setTimeout(()=>reject(Error('Worker did not respond')),5000)};
      waiters.push(waiter);
    });
  }
  try{
    worker.postMessage({type:'init',config:{...config,limit:10000,rate:100000}});
    await next(d=>d.type==='ready');worker.postMessage({type:'step'});
    const single=await next(d=>d.type==='update');assert.equal(single.snapshot.count,1);
    assert.equal(single.snapshot.last.elapsed,0);assert.equal(single.snapshot.last.status,200);
    worker.postMessage({type:'play'});
    const done=await next(d=>d.type==='update'&&d.state==='completed');
    assert.equal(done.snapshot.count,10000);assert.equal(done.snapshot.unique,936);
    assert.equal(done.snapshot.fm,2528);assert.equal(done.snapshot.window,48);
    worker.postMessage({type:'init',config:{...config,limit:100000,rate:1}});
    await next(d=>d.type==='ready');messages.length=0;worker.postMessage({type:'play'});
    await new Promise(resolve=>setTimeout(resolve,170));worker.postMessage({type:'pause'});
    const paused=await next(d=>d.type==='update'&&d.state==='paused');assert.equal(paused.snapshot.count,1);
  }finally{await worker.terminate();for(const w of waiters)clearTimeout(w.timer);}
});
