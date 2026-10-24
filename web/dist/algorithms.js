// The browser updates these summaries from real requests, never from canned counters.
export class Bloom {
  constructor(bits = 1048576, hashes = 7) {
    if (![65536, 262144, 1048576].includes(bits) || ![2,4,7].includes(hashes)) throw Error('Invalid Bloom parameters');
    this.bits = bits; this.hashes = hashes; this.array = new Uint8Array(bits / 8); this.setBits = 0;
  }
  checkAndAdd(words) {
    let present = true; const positions = [];
    for (let i = 0; i < this.hashes; i++) {
      const p = words[i] % this.bits, mask = 1 << (p % 8), index = p >>> 3;
      positions.push(p);
      if (!(this.array[index] & mask)) { present = false; this.setBits++; }
      this.array[index] |= mask;
    }
    return { present, positions };
  }
  bit(index) { return Number(Boolean(this.array[index >>> 3] & (1 << (index % 8)))); }
}

export class FM {
  constructor(hashes = 16) {
    if (![1,16,64].includes(hashes)) throw Error('Invalid FM hash count');
    this.hashes = hashes; this.registers = new Uint8Array(hashes);
    this.groups = {1:1,16:4,64:8}[hashes]; this.empty = true;
  }
  add(zeros) {
    this.empty = false;
    for (let j = 0; j < this.hashes; j++) this.registers[j] = Math.max(this.registers[j], zeros[j]);
  }
  means() {
    const out = [], width = this.hashes / this.groups;
    for (let i = 0; i < this.hashes; i += width) {
      let sum = 0;
      for (let j = i; j < i + width; j++) sum += 2 ** this.registers[j];
      out.push(sum / width);
    }
    return out;
  }
  estimate() {
    if (this.empty) return 0;
    const a = this.means().sort((x,y)=>x-y), m = a.length >>> 1;
    return a.length % 2 ? a[m] : (a[m-1] + a[m])/2;
  }
}

export class DGIM {
  constructor(window = 10000) {
    if (!Number.isInteger(window) || window <= 0) throw Error('Invalid window');
    this.window = window; this.time = 0; this.buckets = [];
  }
  add(bit, trace = false) {
    if (bit !== 0 && bit !== 1) throw Error('Expected binary event');
    this.time++; const actions = [];
    while (this.buckets.length && this.buckets.at(-1)[1] <= this.time - this.window) {
      const b = this.buckets.pop(); if (trace) actions.push(`Expired bucket of ${b[0]} at #${b[1]}`);
    }
    if (!bit) return actions;
    this.buckets.unshift([1,this.time]);
    if (trace) actions.push('Created a size-1 bucket');
    let size = 1;
    while (true) {
      const indexes = [];
      this.buckets.forEach((b,i)=>{if(b[0]===size) indexes.push(i);});
      if (indexes.length <= 2) break;
      const newer = indexes.at(-2), older = indexes.at(-1);
      this.buckets[newer] = [size*2,this.buckets[newer][1]];
      this.buckets.splice(older,1);
      if(trace) actions.push(`Merged the two oldest ${size} buckets into ${size*2}`);
      size *= 2;
    }
    return actions;
  }
  estimate() {
    if(!this.buckets.length) return 0;
    const sum = this.buckets.reduce((s,b)=>s+b[0],0), oldest = this.buckets.at(-1)[0];
    return this.time <= this.window || oldest === 1 ? sum : sum - oldest/2;
  }
}

export class ExactWindow {
  constructor(window) { this.array = new Uint8Array(window); this.index = 0; this.total = 0; }
  add(bit) { this.total += bit-this.array[this.index]; this.array[this.index] = bit; this.index = (this.index+1)%this.array.length; }
}

export class StreamEngine {
  constructor(config, hashes) {
    this.config = config; this.hashes = new DataView(hashes); this.bloom = new Bloom(config.bits,config.k);
    this.fm = new FM(config.h); this.dgim = new DGIM(config.window); this.exact = new ExactWindow(config.window);
    this.seen = new Set(); this.count = 0; this.errors = 0; this.falsePositives = 0; this.falseNegatives = 0;
    this.repeats = 0; this.bytes = 0; this.unknownBytes = 0; this.statuses = {}; this.recentBits = [];
    this.last = null; this.actions = [];
  }
  process(record) {
    const [host,elapsed,request,status,bytes] = record, base = host*92;
    const words = Array.from({length:7},(_,j)=>this.hashes.getUint32(base+j*4,true));
    const zeros = new Uint8Array(this.hashes.buffer,base+28,64), prior = this.seen.has(host);
    const bloom = this.bloom.checkAndAdd(words);
    if (!prior && bloom.present) this.falsePositives++;
    if (prior && !bloom.present) this.falseNegatives++;
    if (prior) this.repeats++;
    this.seen.add(host); this.fm.add(zeros);
    const bit = Number(status>=400 && status<=599);
    const changes = this.dgim.add(bit,true); this.exact.add(bit);
    if(changes.length) this.actions = changes.map(text=>({event:this.count+1,text}));
    this.count++; this.errors += bit; this.statuses[status] = (this.statuses[status]||0)+1;
    if(bytes===0xFFFFFFFF) this.unknownBytes++; else this.bytes += bytes;
    this.recentBits.push(bit); if(this.recentBits.length>128) this.recentBits.shift();
    this.last = {event:this.count,host,elapsed,request,status,bytes,prior,
      bloomPresent:bloom.present,falsePositive:!prior&&bloom.present,positions:bloom.positions,
      hashWords:words,zeros:Array.from(zeros.slice(0,this.config.h)),bit};
    return this.last;
  }
  snapshot(offset=0) {
    const fm = this.fm.estimate(), window = this.dgim.estimate();
    return {count:this.count,unique:this.seen.size,repeats:this.repeats,errors:this.errors,bytes:this.bytes,
      unknownBytes:this.unknownBytes,falsePositives:this.falsePositives,falseNegatives:this.falseNegatives,
      fpr:this.seen.size?this.falsePositives/this.seen.size:0,fm,fmError:this.seen.size?Math.abs(fm-this.seen.size)/this.seen.size:0,
      window,exactWindow:this.exact.total,windowError:this.exact.total?Math.abs(window-this.exact.total)/this.exact.total:0,
      occupancy:this.bloom.setBits/this.bloom.bits,registers:Array.from(this.fm.registers),means:this.fm.means(),
      buckets:this.dgim.buckets.map(b=>[...b]),bits:Array.from({length:128},(_,i)=>this.bloom.bit(offset+i)),
      recentBits:[...this.recentBits],last:this.last,actions:this.actions,statuses:{...this.statuses}};
  }
}
