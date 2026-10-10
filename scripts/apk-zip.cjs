const fs=require('node:fs'),assert=require('node:assert/strict'),{inflateRawSync}=require('node:zlib');
// Read APK entries in memory. Never extract untrusted paths to the filesystem.
function apkZip(file){
  const bytes=fs.readFileSync(file);let end=-1;
  for(let at=bytes.length-22;at>=Math.max(0,bytes.length-65557);at--)if(bytes.readUInt32LE(at)===0x06054b50&&at+22+bytes.readUInt16LE(at+20)===bytes.length){end=at;break;}
  assert.ok(end>=0,'ZIP end record missing');assert.equal(bytes.readUInt16LE(end+4),0,'Multi-disk ZIP unsupported');
  let at=bytes.readUInt32LE(end+16);const entries=[];
  for(let index=0;index<bytes.readUInt16LE(end+10);index++){
    assert.equal(bytes.readUInt32LE(at),0x02014b50);const nameLength=bytes.readUInt16LE(at+28),extraLength=bytes.readUInt16LE(at+30),commentLength=bytes.readUInt16LE(at+32);
    entries.push({name:bytes.subarray(at+46,at+46+nameLength).toString('utf8'),method:bytes.readUInt16LE(at+10),size:bytes.readUInt32LE(at+24),compressedSize:bytes.readUInt32LE(at+20),offset:bytes.readUInt32LE(at+42)});at+=46+nameLength+extraLength+commentLength;
  }
  return {entries,read(name){const entry=entries.find(item=>item.name===name);assert.ok(entry,`ZIP entry missing: ${name}`);const start=entry.offset;assert.equal(bytes.readUInt32LE(start),0x04034b50);const dataOffset=start+30+bytes.readUInt16LE(start+26)+bytes.readUInt16LE(start+28);const compressed=bytes.subarray(dataOffset,dataOffset+entry.compressedSize);const data=entry.method===0?compressed:entry.method===8?inflateRawSync(compressed):null;assert.ok(data,'Unsupported ZIP compression');assert.equal(data.length,entry.size);return data;}};
}
module.exports={apkZip};
