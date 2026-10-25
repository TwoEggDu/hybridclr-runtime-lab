"""Read a narrow subset of Unity queried-snapshot format; never infer liveness from heap bytes.
Format reference: Unity Memory Profiler 1.1.0 package, Reader/QueriedSnapshot.
This independent reader is limited to metadata, strong GC-handle targets and captured heap bytes.
"""
import struct
from pathlib import Path

class Snapshot:
 def __init__(self,path):
  self.data=Path(path).read_bytes()
  if len(self.data)<16 or self.unpack('I',0)[0]!=0xAEABCDCD or self.unpack('I',len(self.data)-4)[0]!=0xABCDCDAE:raise ValueError('Invalid snapshot signature')
  directory=self.unpack('Q',len(self.data)-12)[0]
  sig,version,blocks=self.unpack('IIQ',directory)
  if sig!=0xCDCDAEAB or version!=0x20170724 or self.unpack('I',blocks)[0]!=0x20170724:raise ValueError('Unsupported snapshot directory')
  count=self.unpack('I',directory+16)[0];nblocks=self.unpack('I',blocks+4)[0]
  if count>256 or nblocks>256:raise ValueError('Invalid directory counts')
  self.entries=self.unpack('Q'*count,directory+20);self.blocks=[]
  for address in self.unpack('Q'*nblocks,blocks+8):
   chunk,total=self.unpack('QQ',address)
   if chunk==0:raise ValueError('Invalid chunk size')
   n=(total+chunk-1)//chunk
   if n>len(self.data)//8 or total>len(self.data):raise ValueError('Invalid block bounds')
   offsets=self.unpack('Q'*n,address+16)
   parts=[self.read(off,min(chunk,total-i*chunk)) for i,off in enumerate(offsets)]
   self.blocks.append(b''.join(parts))
 def read(self,offset,size):
  if offset<0 or size<0 or offset+size>len(self.data):raise ValueError('Snapshot read out of bounds')
  return self.data[offset:offset+size]
 def unpack(self,fmt,offset):return struct.unpack('<'+fmt,self.read(offset,struct.calcsize('<'+fmt)))
 def entry(self,index):
  if index>=len(self.entries) or self.entries[index]==0:return []
  at=self.entries[index];kind,block,meta,extra=self.unpack('HIIQ',at)
  if block>=len(self.blocks):raise ValueError('Missing data block')
  data=self.blocks[block]
  if kind==1:offsets=[extra,extra+meta]
  elif kind==2:
   count=extra & 0xffffffff
   if count>len(data) or count*meta>len(data):raise ValueError('Constant array exceeds block')
   offsets=[i*meta for i in range(count+1)]
  elif kind==3:
   if meta>len(self.data)//8:raise ValueError('Dynamic array exceeds file')
   offsets=[extra,*self.unpack('Q'*meta,at+18)]
  elif kind==0:return []
  else:raise ValueError('Unsupported entry format')
  if any(a>b for a,b in zip(offsets,offsets[1:])) or (offsets and offsets[-1]>len(data)):raise ValueError('Invalid entry offsets')
  return [data[a:b] for a,b in zip(offsets,offsets[1:])]
 def numbers(self,index,fmt):return [struct.unpack('<'+fmt,x)[0] for x in self.entry(index)]
 def strings(self,index):return [x.decode('utf-8').rstrip('\0') for x in self.entry(index)]
 def summary(self):
  names=self.strings(23);types=self.numbers(29,'Q');lookup=dict(zip(types,names))
  starts=[x & 0x7fffffffffffffff for x in self.numbers(18,'Q')];heaps=self.entry(19)
  def read_heap(address,size):
   for start,data in zip(starts,heaps):
    offset=address-start
    if 0<=offset and offset+size<=len(data):return data[offset:offset+size]
   return None
  field_names=self.strings(33);field_offsets=self.numbers(31,'i');field_lists=self.entry(25)
  def fields_for(type_name):
   raw=field_lists[names.index(type_name)]
   ids=struct.unpack('<'+'i'*(len(raw)//4),raw)
   return {field_names[i]:field_offsets[i] for i in ids}
  handles=[]
  for address in self.numbers(15,'Q'):
   header=read_heap(address,8);klass=struct.unpack('<Q',header)[0] if header else 0
   row=dict(address=address,klass=klass,type=lookup.get(klass))
   if row['type']=='GcHot.Context':
    offsets=fields_for('GcHot.Context')
    def value(name,fmt):
     raw=read_heap(address+offsets[name],struct.calcsize('<'+fmt))
     if raw is None:raise ValueError('Context field outside captured heap')
     return struct.unpack('<'+fmt,raw)[0]
    slots=value('Slots','Q');array=read_heap(slots,32)
    if array is None:raise ValueError('Context array outside captured heap')
    array_type=lookup.get(struct.unpack_from('<Q',array,0)[0]);count=struct.unpack_from('<Q',array,24)[0]
    if count>1024:raise ValueError('Unexpected array size')
    payload=read_heap(slots+32,count*8)
    if payload is None:raise ValueError('Context slots outside captured heap')
    row['context']=dict(tag=value('Tag','i'),head=value('Head','Q'),slots=slots,slots_type=array_type,slots_length=count,nonnull_slots=sum(v[0]!=0 for v in struct.iter_unpack('<Q',payload)))
   handles.append(row)
  return dict(format_version=self.numbers(0,'I'),capture_flags=self.numbers(3,'I'),vm_info=[list(struct.unpack('<6I',x)) for x in self.entry(4)],type_count=len(names),heap_section_count=len(heaps),managed_stack_sections=len(self.entry(21)),gc_handle_count=len(handles),hot_types=[n for n in names if n.startswith('GcHot.')],hot_handle_targets=[h for h in handles if (h['type'] or '').startswith('GcHot.')],unknown_handle_targets=sum(h['type'] is None for h in handles))
