"""Validate native method identities against final own DLL metadata."""
import re

def parse_native(text,metadata):
 def check(v,msg):
  if not v:raise ValueError(msg)
 check('private pdb symbols' in text,'No private PDB')
 check(not any(x in text for x in ['Syntax error','Numeric expression missing','Type information missing','Memory access error']), 'Debugger expression failure')
 pattern=r'^AUTN (prepare|transform|execute|inline) method=([0-9a-f]+) name=(.*?) token=([0-9a-f]+) class=(.*?) ns=(.*?) image=(.*?) interp=([0-9a-f]+)$'
 methods=[dict(kind=m[0],method=m[1],name=m[2],token=int(m[3],16),type=m[4],namespace=m[5],image=m[6],interp=m[7]) for m in re.findall(pattern,text,re.M)]
 check(not any(m['image']=='UniTask.dll' for m in methods),'Unexpected interpreted UniTask builder path')
 own=[m for m in methods if m['image']=='HotUpdate.dll']
 def rows(name,kind):return [x for x in own if x['name']==name and x['kind']==kind]
 for name in ['Work','MoveNext']:
  expected=[m['token'] for t in metadata['types'] for m in t['methods'] if m['name']==name]
  check(len(expected)==1,'Ambiguous final method token')
  group=[m for m in own if m['name']==name]
  check(group and all(m['token']==expected[0] for m in group),'Wrong method token')
  check(len({m['method'] for m in group})==1,'Method identity changed')
  check(len(rows(name,'transform'))==1,'Wrong conversion count')
 check(len(rows('Work','execute'))==1,'Work count')
 move=rows('MoveNext','execute');check(len(move)==3,'Need initial entry plus two resumptions')
 check(int(move[-1]['interp'],16)!=0 and move[-2]['interp']==move[-1]['interp'],'Resume cache missing/changed')
 pattern=r'^AUTN_NATIVE kind=(start|await) symbol=(.*?) method=([0-9a-f]+) token=([0-9a-f]+) name=(.*?) class=(.*?) image=(.*?) full=(\d+)$'
 native=[dict(kind=m[0],symbol=m[1],method=m[2],token=int(m[3],16),name=m[4],type=m[5],image=m[6],method_flag=int(m[7])) for m in re.findall(pattern,text,re.M)]
 check([x['kind'] for x in native]==['start','await','await'],'Need one native Start and two native await registrations')
 check(all(x['image']=='UniTask.dll' and x['type']=='AsyncUniTaskMethodBuilder`1' for x in native),'Wrong native builder identity')
 check(native[0]['name']=='Start' and all(x['name']=='AwaitUnsafeOnCompleted' for x in native[1:]),'Wrong native builder members')
 any_route=all('Il2CppFullySharedGenericAny' in x['symbol'] for x in native)
 ref_route=all('RuntimeObject' in x['symbol'] for x in native)
 check(any_route or ref_route,'Mixed/unknown native builder route')
 body=re.findall(r'^AUTN_BODY image=([0-9a-f]+) token=([0-9a-f]+) assembly=(.*?)$',text,re.M)
 check(not any(x[2]=='UniTask.dll' for x in body),'Unexpected supplementary UniTask method body read')
 return dict(move_next_execute_count=3,work_execute_count=1,own_transform_count=2,resume_cache_reused=True,builder_route='native-any' if any_route else 'native-reference',native_builder=native,interpreter_methods=methods,homologous_body_reads=[dict(image=x[0],token=int(x[1],16),assembly=x[2]) for x in body])
