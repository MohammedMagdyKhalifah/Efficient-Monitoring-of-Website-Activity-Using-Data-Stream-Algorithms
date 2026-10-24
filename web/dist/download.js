// A standards-compliant stored ZIP, built locally from the project's static files.
// Gzip inputs are already compressed, so storing them avoids a duplicate hosted ZIP.
const encoder = new TextEncoder();
const crcTable = Uint32Array.from({length:256},(_,n)=>{
  let c=n;for(let k=0;k<8;k++)c=c&1?0xedb88320^(c>>>1):c>>>1;return c>>>0;
});
export function crc32(bytes){let c=0xffffffff;for(const b of bytes)c=crcTable[(c^b)&255]^(c>>>8);return (c^0xffffffff)>>>0;}
export function zipFiles(files){
  const locals=[],central=[];let offset=0,centralLength=0;
  const stamp=new Date(),time=(stamp.getHours()<<11)|(stamp.getMinutes()<<5)|(stamp.getSeconds()>>>1);
  const date=((stamp.getFullYear()-1980)<<9)|((stamp.getMonth()+1)<<5)|stamp.getDate();
  for(const file of files){
    const name=encoder.encode(file.name),data=file.data,crc=crc32(data);
    const header=new Uint8Array(30+name.length),v=new DataView(header.buffer);
    v.setUint32(0,0x04034b50,true);v.setUint16(4,20,true);v.setUint16(6,0x800,true);
    v.setUint16(10,time,true);v.setUint16(12,date,true);v.setUint32(14,crc,true);
    v.setUint32(18,data.length,true);v.setUint32(22,data.length,true);v.setUint16(26,name.length,true);header.set(name,30);
    locals.push(header,data);
    const entry=new Uint8Array(46+name.length),c=new DataView(entry.buffer);
    c.setUint32(0,0x02014b50,true);c.setUint16(4,20,true);c.setUint16(6,20,true);c.setUint16(8,0x800,true);
    c.setUint16(12,time,true);c.setUint16(14,date,true);c.setUint32(16,crc,true);c.setUint32(20,data.length,true);c.setUint32(24,data.length,true);
    c.setUint16(28,name.length,true);c.setUint32(42,offset,true);entry.set(name,46);
    central.push(entry);centralLength+=entry.length;offset+=header.length+data.length;
  }
  const end=new Uint8Array(22),v=new DataView(end.buffer);v.setUint32(0,0x06054b50,true);
  v.setUint16(8,files.length,true);v.setUint16(10,files.length,true);v.setUint32(12,centralLength,true);v.setUint32(16,offset,true);
  return new Blob([...locals,...central,end],{type:'application/zip'});
}
export async function downloadProject(progress=()=>{}){
  const r=await fetch('./data/project-files.json');if(!r.ok)throw Error('Project file index is unavailable');
  const list=await r.json(),files=[];
  for(let i=0;i<list.length;i++){
    if(i%10===0)progress(`Collecting project files: ${i+1} / ${list.length}…`);
    if('content' in list[i]){
      files.push({name:`481013386_MohammedKhalifah_5113_Assignment_2/${list[i].name}`,data:encoder.encode(list[i].content)});
      continue;
    }
    const response=await fetch(list[i].url);if(!response.ok)throw Error(`Missing file: ${list[i].name}`);
    files.push({name:`481013386_MohammedKhalifah_5113_Assignment_2/${list[i].name}`,data:new Uint8Array(await response.arrayBuffer())});
  }
  const blob=zipFiles(files),url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download='481013386_MohammedKhalifah_5113_Assignment_2.zip';a.click();
  setTimeout(()=>URL.revokeObjectURL(url),60000);
}
