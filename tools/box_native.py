"""Validate final native receiver identities, method tokens and selected paths."""
import re

def parse_native(text,route,mode,metadata,md):
 def check(v,msg):
  if not v:raise ValueError(msg)
 check('private pdb symbols' in text and 'CBN_LAYOUT objectSize=16' in text,'Private symbols/layout missing')
 check(not any(e in text for e in ('Syntax error','Numeric expression missing','Memory access error','Type information missing')),'Debugger expression failure')
 methods=[];receivers=[];boxes=[];returns=[];native=[];body=[];last=None
 for l in text.splitlines():
  m=re.fullmatch(r'CBN_METHOD kind=(\w+) method=([0-9a-f]+) name=(.*?) token=([0-9a-f]+) class=(.*?) ns=(.*?) image=(.*?) interp=([0-9a-f]+)',l)
  if m:
   x=m.groups();last=dict(kind=x[0],method=x[1],name=x[2],token=int(x[3],16),type=x[4],namespace=x[5],image=x[6],interp=x[7]);methods.append(last);continue
  m=re.fullmatch(r'CBN_RECEIVER kind=(\w+) this=([0-9a-f]+) first=(-?\d+) header16=(-?\d+)',l)
  if m:
   check(last is not None and last['kind']==m[1],'Receiver pairing');receivers.append(dict(method=last,receiver=m[2],value=int(m[3])));continue
  m=re.fullmatch(r'CBN_BOX name=(.*?) ns=(.*?) data=([0-9a-f]+) value=(-?\d+)',l)
  if m:boxes.append(dict(type=m[1],namespace=m[2],source=m[3],value=int(m[4])));continue
  m=re.fullmatch(r'CBN_BOX_RETURN object=([0-9a-f]+) payload=([0-9a-f]+) value=(-?\d+)',l)
  if m:returns.append(dict(object=m[1],payload=m[2],value=int(m[3])));continue
  m=re.fullmatch(r'CBN_BODY image=([0-9a-f]+) token=([0-9a-f]+) assembly=(.*?)',l)
  if m:body.append(dict(image=m[1],token=int(m[2],16),assembly=m[3]));continue
  m=re.fullmatch(r'CBN_NATIVE name=(.*?) symbol=(.*?) method=([0-9a-f]+) token=([0-9a-f]+)',l)
  if m:native.append(dict(name=m[1],symbol=m[2],method=m[3],token=int(m[4],16)))
 lookup={}
 for row in md:
  for t in row['types']:
   for method in t['methods']:lookup[(row['assembly']+'.dll',t['name'],method['name'])]=method['token']
 for x in methods:
  name=x['namespace']+'.'+x['type'];key=(x['image'],name,x['name'])
  check(key in lookup and lookup[key]==x['token'],'Native method/final DLL token mismatch')
 for x in native:
  key=('Probe.AOT.dll','.GenericCalls',x['name']);check(key in lookup and lookup[key]==x['token'],'Native generic token mismatch')
 check(len(boxes)==len(returns),'Box return count')
 for a,b in zip(boxes,returns):
  check(a['value']==b['value']==10 and int(b['payload'],16)==int(b['object'],16)+16 and b['payload']!=a['source'],'Box payload/initial copy')
 def target(name):return [x for x in receivers if x['method']['name']==name and x['method']['type']=='Counter']
 alias=False
 if mode=='box':
  check(len(boxes)==1 and boxes[0]['type']=='Counter','Expected one explicit receiver box')
  if route!='aot':
   hits=target('Increment');check(len(hits)==3 and [x['value'] for x in hits]==[10,11,12],'Box mutation entries')
   check(hits[0]['receiver']==hits[1]['receiver']==returns[0]['payload'] and hits[2]['receiver']!=returns[0]['payload'],'Box alias or unboxed-copy identity')
   check(len({x['method']['interp'] for x in hits})==1 and int(hits[0]['method']['interp'],16)!=0,'Box target cache')
   alias=True
 elif route=='hot' and mode=='text-fallback':
  check(len(boxes)==1 and boxes[0]['type']=='PlainCounter','Expected fallback boxing')
  hits=[x for x in receivers if x['method']['name']=='TextLocal'];check(len(hits)==1 and hits[0]['receiver']==boxes[0]['source'],'Fallback this pointer')
 else:
  check(not boxes,'Unexpected receiver boxing')
  if not (route=='cross' and mode=='value' and metadata=='off'):
   hits=target('ToString' if mode=='text-override' else 'Increment');check(len(hits)==1 and hits[0]['value']==10,'Target this input')
 if route=='hot' and mode=='text-override':
  local=[x for x in receivers if x['method']['name']=='TextLocal'];target_hits=target('ToString')
  check(len(local)==1 and local[0]['value']==10 and local[0]['receiver']==target_hits[0]['receiver'],'Override this pointer mismatch')
 if route=='cross':
  if mode=='ref':
   check(len(native)==1,'Unexpected native helper');hits=[x for x in native if x['name']=='ByRef'];check(len(hits)==1 and 'Il2CppFullySharedGenericAny' in hits[0]['symbol'],'Expected native ref helper')
   check(not any(x['type']=='GenericCalls' for x in methods),'Unexpected interpreted generic helper')
   if metadata=='off':check(not body,'Unexpected supplementary body read in off group')
   else:check(len(body)==1 and body[0]['assembly']=='Probe.AOT.dll' and body[0]['token']==lookup[('Probe.AOT.dll','.GenericCalls','ByValue')],'Expected transform-time ByValue lookup')
  elif mode=='value':
   check(not native,'Unexpected native generic ByValue execution')
   increment=target('Increment')
   if metadata=='off':check(not increment and not body,'Missing method did not stop before target')
   else:
    key=('Probe.AOT.dll','.GenericCalls','ByValue');check(any(x['assembly']=='Probe.AOT.dll' and x['token']==lookup[key] for x in body),'Missing supplementary ByValue body')
    check([x['kind'] for x in methods if x['type']=='GenericCalls' and x['name']=='ByValue']==['prepare','transform','frame'],'Expected one interpreted ByValue conversion/entry')
 if route!='cross':check(not native and not body,'Unexpected cross helper path')
 return dict(methods=methods,receivers=receivers,boxes=boxes,box_returns=returns,native_helpers=native,body_reads=body,box_alias_and_copy_verified=alias)
