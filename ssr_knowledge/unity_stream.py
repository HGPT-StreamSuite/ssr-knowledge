"""Bounded read-only UnityFS 8 streams; no encryption or whole-bundle reads."""
import bisect
import collections
import io
import json
import struct
import sys
from pathlib import Path



def exact(file, count):
    value = file.read(count)
    if len(value) != count: raise ValueError("truncated resource")
    return value

def unpack(file, fmt): return struct.unpack(">" + fmt, exact(file, struct.calcsize(">" + fmt)))
def z(file, limit=1024):
    parts = bytearray()
    while len(parts) < limit:
        value = exact(file, 1)
        if value == b"\0": return parts.decode("utf-8", errors="strict")
        parts += value
    raise ValueError("overlong resource string")

def decode(data, size, mode):
    if size > 4 * 1024 * 1024: raise ValueError("block exceeds 4 MiB limit")
    if mode == 0: result = data
    elif mode in (2, 3):
        import lz4.block
        result = lz4.block.decompress(data, uncompressed_size=size)
    else: raise ValueError("unsupported compression; no custom decryption or fallback")
    if len(result) != size: raise ValueError("decompressed length mismatch")
    return result

class BoundedUnityFS:
    def __init__(self, path):
        self.path = path; self.file = path.open("rb")
        try:
            self._read_index(path)
        except BaseException:
            self.file.close()
            raise

    def _read_index(self, path):
        if z(self.file) != "UnityFS": raise ValueError("only UnityFS supported")
        self.version = unpack(self.file, "I")[0]; self.player = z(self.file); self.engine = z(self.file)
        length, comp, raw, self.flags = unpack(self.file, "QIII")
        self.index_compressed_bytes, self.index_uncompressed_bytes = comp, raw
        if self.version != 8 or not self.engine.startswith("6000."): raise ValueError("unexpected format/version")
        if self.flags & 0x1400 or self.flags & ~(0x3F | 0x40 | 0x80 | 0x100 | 0x200): raise ValueError("encrypted/unknown flags; stop")
        if length != path.stat().st_size or comp > 4*1024*1024: raise ValueError("invalid bundle/index size")
        self.file.seek((self.file.tell()+15)//16*16); start = self.file.tell()
        if self.flags & 0x80: self.file.seek(length - comp)
        index = io.BytesIO(decode(exact(self.file, comp), raw, self.flags & 0x3F))
        self.data_start = start if self.flags & 0x80 else self.file.tell()
        if self.flags & 0x200: self.data_start = (self.data_start + 15)//16*16
        exact(index, 16); count = unpack(index, "I")[0]
        if not 0 < count <= 100000: raise ValueError("invalid block count")
        self.blocks=[]; self.offsets=[]; physical=self.data_start; logical=0
        for _ in range(count):
            outsize, insize, flag = unpack(index, "IIH")
            if not 0 < outsize <= 4*1024*1024 or not 0 < insize <= 4*1024*1024 or flag & ~0x7F or flag & 0x3F not in (0,2,3): raise ValueError("unsupported/oversized block")
            self.offsets.append(logical); self.blocks.append((physical,insize,outsize,flag & 0x3F))
            logical+=outsize; physical+=insize
        if physical > length or logical > 20*1024**3: raise ValueError("invalid aggregate resource size")
        count = unpack(index, "I")[0]
        if count > 10000: raise ValueError("too many files")
        self.nodes=[]
        for _ in range(count):
            offset,size,flag=unpack(index,"QQI"); name=z(index)
            if offset+size>logical: raise ValueError("node outside data bounds")
            self.nodes.append({"name":name,"offset":offset,"size":size,"flags":flag})
        self.total=logical; self.cache=collections.OrderedDict(); self.cache_bytes=0
        self.read_bytes=0; self.decompressed_bytes=0; self.block_loads=0; self.max_cache=0
    def block(self, number):
        if number in self.cache:
            self.cache.move_to_end(number); return self.cache[number]
        start, size, outsize, mode=self.blocks[number]; self.file.seek(start)
        data=decode(exact(self.file,size),outsize,mode)
        while self.cache and self.cache_bytes+len(data)>32*1024*1024:
            _,old=self.cache.popitem(last=False); self.cache_bytes-=len(old)
        self.cache[number]=data; self.cache_bytes+=len(data); self.max_cache=max(self.max_cache,self.cache_bytes)
        self.read_bytes+=size; self.decompressed_bytes+=len(data); self.block_loads+=1
        return data
    def read(self, position, count):
        if count<0 or count>16*1024*1024 or position<0 or position+count>self.total: raise ValueError("bounded read rejected")
        output=[]
        while count:
            number=bisect.bisect_right(self.offsets,position)-1; data=self.block(number); within=position-self.offsets[number]
            part=data[within:within+count]
            if not part: raise ValueError("zero-progress read")
            output.append(part);position+=len(part);count-=len(part)
        return b"".join(output)

class BundleWindow(io.RawIOBase):
    def __init__(self,bundle,node): self.bundle=bundle;self.node=node;self.position=0
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.position
    def seek(self,offset,whence=0):
        position=offset if whence==0 else self.position+offset if whence==1 else self.node['size']+offset if whence==2 else -1
        if not 0<=position<=self.node['size']: raise ValueError("node seek out of bounds")
        self.position=position;return position
    def read(self,size=-1):
        if size<0: raise ValueError("whole-resource reads disabled")
        size=min(size,self.node['size']-self.position)
        data=self.bundle.read(self.node['offset']+self.position,size);self.position+=len(data);return data

