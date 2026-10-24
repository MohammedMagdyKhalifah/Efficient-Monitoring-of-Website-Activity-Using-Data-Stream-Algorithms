// Node bridge for testing the actual browser worker with real local gzip inputs.
import {parentPort} from 'node:worker_threads';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const dist=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../dist');
globalThis.self=globalThis;
globalThis.postMessage=value=>parentPort.postMessage(value);
globalThis.fetch=async url=>{
  const file=path.resolve(dist,String(url));
  if(!file.startsWith(dist+path.sep))throw Error('Invalid fixture path');
  return new Response(fs.readFileSync(file));
};
await import('../dist/worker.js');
parentPort.on('message',data=>self.onmessage({data}));
