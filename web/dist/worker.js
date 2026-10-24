import {StreamEngine} from './algorithms.js';

let engine, config, streamReader, carry = new Uint8Array(), cursor = 0, block = null;
let running = false, ready = false, exhausted = false, generation = 0, busy = false;
let rate = 5000, offset = 0, computeMs = 0, timer = null, recordIndex = 0;
let history = [], feed = [], emitted = 0, abortController;

async function uncompressed(url, signal) {
  const response = await fetch(url,{signal});
  if(!response.ok) throw Error(`Cannot load dataset asset (${response.status})`);
  if(!('DecompressionStream' in self)) throw Error('This browser needs gzip stream support. Please use a current Chrome, Edge, Firefox or Safari.');
  return response.body.pipeThrough(new DecompressionStream('gzip'));
}

async function init(next) {
  const current = ++generation; running = ready = false; clearTimeout(timer);
  abortController?.abort(); abortController = new AbortController();
  try {
    if(streamReader) await streamReader.cancel().catch(()=>{});
    config = next; rate = next.rate; offset = 0; history = []; feed = []; computeMs = 0;
    carry = new Uint8Array(); cursor = 0; block = null; exhausted = false; recordIndex = 0; emitted = 0;
    postMessage({type:'loading',message:'Loading genuine NASA records and deterministic hash inputs…'});
    const hashStream = await uncompressed(`./data/hashes-${config.seed}.bin.gz`,abortController.signal);
    const hashBuffer = await new Response(hashStream).arrayBuffer();
    if(current!==generation) return;
    engine = new StreamEngine(config,hashBuffer);
    const input = await uncompressed('./data/events.bin.gz',abortController.signal);
    streamReader = input.getReader(); ready = true; busy = false;
    postMessage({type:'ready',snapshot:engine.snapshot(),config});
  } catch(error) { if(current===generation && error.name!=='AbortError') postMessage({type:'error',message:error.message}); }
}

async function nextRecord() {
  while(!block || cursor+20>block.byteLength) {
    const previous = block ? new Uint8Array(block.buffer,block.byteOffset+cursor,block.byteLength-cursor) : carry;
    const {done,value} = await streamReader.read();
    if(done) { if(previous.length) throw Error('The prepared stream ends with an incomplete record'); exhausted=true; return null; }
    const joined = new Uint8Array(previous.length+value.length); joined.set(previous); joined.set(value,previous.length);
    block = new DataView(joined.buffer); cursor = 0;
  }
  const row = Array.from({length:5},(_,i)=>block.getUint32(cursor+i*4,true)); cursor+=20; return row;
}

function emit(state='paused') {
  const snapshot = engine.snapshot(offset);
  postMessage({type:'update',snapshot,history:history.splice(0),feed:feed.slice(-12),state,
    computeMs,recordIndex,limit:config.limit});
  emitted = performance.now();
}

async function advance(amount, single=false) {
  if(!ready || busy) return;
  busy = true; const current = generation;
  try {
    for(let n=0;n<amount && engine.count<config.limit;n++) {
      const record = await nextRecord(); if(!record || current!==generation) break;
      const t = performance.now(); const event = engine.process(record); computeMs+=performance.now()-t;
      recordIndex++; feed.push(event); if(feed.length>12) feed.shift();
      if(engine.count%1000===0) {
        history.push({n:engine.count,exact:engine.seen.size,fm:engine.fm.estimate(),
          window:engine.dgim.estimate(),exactWindow:engine.exact.total,fpr:engine.falsePositives/engine.seen.size});
      }
    }
    if(current!==generation) return;
    if(exhausted || engine.count>=config.limit) {
      running=false;
      if(engine.count%1000) history.push({n:engine.count,exact:engine.seen.size,fm:engine.fm.estimate(),
        window:engine.dgim.estimate(),exactWindow:engine.exact.total,fpr:engine.falsePositives/engine.seen.size});
      emit('completed'); postMessage({type:'completed'});
    } else if(single || performance.now()-emitted>70 || !running) emit(running?'running':'paused');
  } catch(error) { running=false; postMessage({type:'error',message:error.message}); }
  finally { if(current===generation) busy=false; }
}

async function tick() {
  if(!running || !ready) return;
  const interval = rate < 20 ? 1000/rate : 50;
  const t = performance.now(); await advance(rate < 20 ? 1 : Math.max(1,Math.floor(rate/20)));
  if(running) timer=setTimeout(tick,Math.max(0,interval-(performance.now()-t)));
}

self.onmessage = async ({data}) => {
  if(data.type==='init') return init(data.config);
  if(data.type==='speed') { rate=data.rate; return; }
  if(data.type==='bits') { offset=data.offset; if(ready) emit(running?'running':'paused'); return; }
  if(!ready) return;
  if(data.type==='play') { if(running)return; running=true; tick(); }
  if(data.type==='pause') { running=false; clearTimeout(timer); if(!busy)emit('paused'); }
  if(data.type==='step') { running=false; clearTimeout(timer); await advance(1,true); }
};
