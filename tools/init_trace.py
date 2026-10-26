"""Validate the fixed x64 PDB trace, not interpreter-internal call counts."""
import re
def parse_trace(text):
 def need(ok,msg):
  if not ok:raise ValueError(msg)
 need('private pdb symbols' in text,'missing private PDB');need(not any(x in text for x in ('Syntax error',"Couldn\'t resolve",'Unable to resolve')),'debugger error')
 rows=[]
 for block in re.split(r'^TIP_NATIVE_',text,flags=re.M)[1:]:
  h=re.match(r'(PREPARE|TRANSFORM|EXECUTE|END) method=([0-9a-f]+)',block)
  name=re.search(r'name\s*:\s*0x[0-9a-f`]+\s+"([^"\n]+)"',block)
  cache=re.search(r'interpData\s*:\s*(\(null\)|0x[0-9a-f`]+)',block)
  need(h and name and cache,'truncated MethodInfo event')
  rows.append(dict(kind=h[1],method=h[2],name=name[1],cache=cache[1],class_init='Runtime::ClassInit' in block))
 def pick(name,kind):return [r for r in rows if r['name']==name and r['kind']==kind]
 ctrans=pick('.cctor','TRANSFORM');cexec=pick('.cctor','EXECUTE');ptrans=pick('Ping','TRANSFORM');end=pick('Ping','END')
 need(len(ctrans)==len(cexec)==len(ptrans)==len(end)==1,'target event count')
 need(ctrans[0]['method']==cexec[0]['method'] and ptrans[0]['method']==end[0]['method'],'method identity changed')
 need(ctrans[0]['cache']==ptrans[0]['cache']=='(null)' and cexec[0]['cache']!='(null)' and end[0]['cache']!='(null)','cache state')
 need(cexec[0]['class_init'],'missing initialization stack')
 need(rows.index(ptrans[0])<rows.index(cexec[0])<rows.index(end[0]),'target preparation/initializer/end order')
 need(rows.index(ctrans[0])<rows.index(cexec[0]),'cctor executes before transformation')
 return dict(cctor_transforms=1,cctor_execute_entries=1,ping_transforms=1,ping_prepare_entries=len(pick('Ping','PREPARE')),ping_execute_function_entries=len(pick('Ping','EXECUTE')),same_method_identity=True,ping_cache_ready_at_end=True,ping_prepared_before_cctor=True,cctor_class_init_stack=True,limit='Execute native function entry count does not count interpreted internal calls; use own method events for body execution.')
