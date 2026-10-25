"""Strict acceptance of GC callback observations; released survivors remain observations."""
import re

def one(text,pattern):
 rows=re.findall(pattern,text,re.M)
 if len(rows)!=1:raise ValueError('Missing/duplicate record: '+pattern)
 return rows[0]

def parse_player(text,mode):
 if mode not in ('handle','stack','stress'):raise ValueError('Unknown mode')
 env=one(text,r'^GCP_ENV mode=(\w+) unity=(\S+) incremental=(\w+) gcMode=(\w+)\s*$')
 if env!=(mode,'2022.3.62f3','True','Enabled'):raise ValueError('Environment mismatch')
 size,assembly,pointer,context=one(text,r'^GCP_LOAD bytes=(\d+) assembly=(\w+) pointer=(\d+) context=(\d+)\s*$')
 if assembly!='HotUpdate' or min(int(size),int(pointer))<=0 or (int(context)==0)!=(mode=='stack'):raise ValueError('Callback/context mismatch')
 main=dict(zip(('managed','native'),map(int,one(text,r'^GCP_MAIN managed=(\d+) native=(\d+)\s*$'))))
 held=re.findall(r'^GCP_HELD stage=(\w+) alive=(\w+) full=(\d+)\s*$',text,re.M)
 if held!=([('before','True','3'),('after','True','3')] if mode!='stack' else []):raise ValueError('Held control lost')
 checkpoints=re.findall(r'^GCP_CHECK seq=(\d+) alive=(\w+) full=(\d+) slices=(\d+) more=(\d+)\s*$',text,re.M)
 n={'handle':2,'stack':1,'stress':1024}[mode]
 expected=list(range(32,1025,32)) if mode=='stress' else [n]
 if [int(c[0]) for c in checkpoints]!=expected:raise ValueError('Checkpoint sequence mismatch')
 for seq,alive,full,slices,more in checkpoints:
  if alive!='True' or (int(full),int(slices))!=((0,4) if mode=='stress' else (3,0)) or not 0<=int(more)<=int(slices):raise ValueError('Collection/control record invalid')
 if one(text,r'^GCP_STOP joinedBefore=(\w+) requested=(\d+)\s*$')!=('False','1'):raise ValueError('In-flight stop invalid')
 before,after,delta=map(int,one(text,r'^GCP_GC before=(\d+) after=(\d+) delta=(-?\d+)\s*$'))
 if delta<0 or after-before!=delta or mode!='stress' and delta<3:raise ValueError('Collection counter mismatch')
 count,checksum,errors,native,joined=one(text,r'^GCP_JOIN count=(\d+) checksum=(-?\d+) errors=(\d+) native=(\d+) joined=(\w+)\s*$')
 if int(count)!=n or int(checksum)!={'handle':149,'stack':257,'stress':786944}[mode] or errors!='0' or joined!='True' or int(native)==main['native'] or int(native)<=0:raise ValueError('Callback outcome invalid')
 frees=re.findall(r'^GCP_HANDLE_FREE afterJoin=(\w+)\s*$',text,re.M)
 if frees!=(['True'] if mode!='stack' else []):raise ValueError('Handle lifetime mismatch')
 alive,full=one(text,r'^GCP_RELEASED alive=(\w+) full=(\d+)\s*$')
 if alive not in ('True','False') or full!='3':raise ValueError('Released observation invalid')
 if one(text,r'^GCP_DELEGATE_RELEASE afterJoin=(\w+)\s*$')!='True' or one(text,r'^GCP_DONE mode=(\w+) failures=(\d+)\s*$')!=(mode,'0'):raise ValueError('Shutdown incomplete')
 markers=['GCP_ENV ','GCP_LOAD ','GCP_MAIN ']+(['GCP_HELD stage=before'] if mode!='stack' else [])+['GCP_CHECK seq='+str(seq)+' ' for seq in expected]+['GCP_STOP ','GCP_GC ','GCP_JOIN ']+(['GCP_HELD stage=after','GCP_HANDLE_FREE '] if mode!='stack' else [])+['GCP_RELEASED ','GCP_DELEGATE_RELEASE ','GCP_DONE ']
 positions=[text.index(x) for x in markers]
 if positions!=sorted(positions):raise ValueError('Lifetime order mismatch')
 return dict(mode=mode,gc_before=before,gc_after=after,gc_delta=delta,pointer=int(pointer),context=int(context),main=main,native=int(native),count=int(count),checksum=int(checksum),released_alive=alive=='True',checkpoints=[dict(seq=int(x[0]),full=int(x[2]),slices=int(x[3]),more=int(x[4])) for x in checkpoints],payload_bytes=8388608 if mode=='stress' else 0)


def parse_native(text,player):
 if player['mode'] not in ('handle','stack'):raise ValueError('Focused retention traces only')
 for module in ('GameAssembly','NativeProbe'):
  if not re.search(module+r' C \(private pdb symbols\)',text):raise ValueError('Private symbols missing')
 matches=list(re.finditer(r'^GCP_NATIVE_(\w+) tid=([0-9a-f]+)([^\r\n]*)$',text,re.M|re.I));events=[]
 for i,m in enumerate(matches):events.append(dict(kind=m[1],tid=int(m[2],16),fields=dict(re.findall(r'(\w+)=([^ ]+)',m[3])),pos=m.start(),detail=text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)]))
 def group(items,kind):return [e for e in items if e['kind']==kind]
 def single(items,kind):
  values=group(items,kind)
  if len(values)!=1:raise ValueError('Missing/duplicate '+kind)
  return values[0]
 def num(e,key):return int(e['fields'][key],16)
 own=[e for e in events if e['tid']==player['native']];n=player['count']
 enters=[e for e in own if e['kind']=='PLUGIN' and e['fields'].get('phase')=='1']
 exits=[e for e in own if e['kind']=='PLUGIN' and e['fields'].get('phase')=='2']
 if len(enters)!=n or len(exits)!=n:raise ValueError('Native count mismatch')
 active_collections=0;methods=[];caches=[];states=[]
 for index,(enter,exit) in enumerate(zip(enters,exits),1):
  if enter['pos']>=exit['pos'] or int(enter['fields']['seq'])!=index or int(exit['fields']['seq'])!=index or int(exit['fields']['value'])!=(index+73 if player['mode']=='handle' else 257):raise ValueError('Native outcome mismatch')
  span=[e for e in own if enter['pos']<e['pos']<exit['pos']]
  wrapper=single(span,'WRAPPER');scope=single(span,'SCOPE_ENTER');leave=single(span,'SCOPE_LEAVE');attach=single(span,'ATTACH')
  if num(wrapper,'wrapper')!=player['pointer'] or num(wrapper,'context')!=player['context'] or int(wrapper['fields']['seq'])!=index or int(wrapper['fields']['mode'])!=(0 if player['mode']=='handle' else 1):raise ValueError('ABI identity mismatch')
  execute=single([e for e in span if re.search(r'name\s*:\s*0x[0-9a-f`]+\s+"Call"',e['detail'],re.I)],'EXECUTE')
  if 'GameAssembly!__ReversePInvokeMethod_0+' not in execute['detail']:raise ValueError('Wrapper stack missing')
  methods.append(num(execute,'method'));cache=re.search(r'interpData\s*:\s*0x([0-9a-f`]+)',execute['detail'],re.I)
  if cache is None and not re.search(r'interpData\s*:\s*\(null\)',execute['detail']):raise ValueError('Cache field missing')
  caches.append(int(cache[1].replace('`',''),16) if cache else 0)
  create=single(span,'CREATE');add=single(span,'ROOT_ADD');free=single(span,'FREE');destroy=single(span,'DESTROY');remove=single(span,'ROOT_REMOVE');detaches=group(span,'DETACH');state=num(create,'state')
  if not state or num(add,'root')!=state or num(destroy,'state')!=state or num(remove,'root')!=state or num(scope,'helper')!=num(leave,'helper') or not num(leave,'owned') or not detaches or any(num(d,'thread')!=num(leave,'owned') for d in detaches):raise ValueError('State/ownership mismatch')
  sequence=[wrapper,scope,attach,execute,create,add,leave,detaches[0],free,destroy,remove]
  if [e['pos'] for e in sequence]!=sorted(e['pos'] for e in sequence):raise ValueError('Lifecycle order mismatch')
  states.append(create['fields']['state'])
  collects=[e for e in events if e['kind']=='COLLECT' and enter['pos']<e['pos']<exit['pos']]
  if index==n:
   if len(collects)!=3 or any(e['tid']!=player['main']['native'] or not add['pos']<e['pos']<leave['pos'] for e in collects):raise ValueError('Active collection evidence missing')
   active_collections=len(collects)
  elif collects:raise ValueError('Unexpected collection in initial callback')
 if len(set(methods))!=1 or caches[0]!=0 or any(c==0 for c in caches[1:]):raise ValueError('Method/cache mismatch')
 # Transform can also prepare constructors and validators; isolate the callback method.
 transforms=[e for e in own if e['kind']=='TRANSFORM' and num(e,'method')==methods[0]]
 if len(transforms)!=1 or not enters[0]['pos']<transforms[0]['pos']<exits[0]['pos']:raise ValueError('Callback conversion mismatch')
 plugins=[e for e in events if e['kind']=='PLUGIN'];phase={}
 for value in ('3','4','5','6'):
  found=[e for e in plugins if e['fields'].get('phase')==value]
  if len(found)!=1:raise ValueError('Stop/start/end/join missing')
  phase[value]=found[0]
 if phase['3']['tid']!=player['main']['native'] or phase['4']['tid']!=player['main']['native'] or phase['5']['tid']!=player['native'] or phase['6']['tid']!=player['native'] or not phase['5']['pos']<enters[0]['pos']<phase['3']['pos']<exits[-1]['pos']<phase['6']['pos']<phase['4']['pos']:raise ValueError('Stop/join order mismatch')
 context_free=group(events,'CONTEXT_FREE')
 if player['mode']=='handle':
  if len(context_free)!=1 or context_free[0]['pos']<phase['4']['pos']:raise ValueError('Context released before join')
 elif context_free:raise ValueError('Stack group unexpectedly used a handle')
 return dict(mode=player['mode'],native=player['native'],callback_count=n,method=f'{methods[0]:016x}',interpData=[f'{v:016x}' for v in caches],states=states,active_full_collects=active_collections,attach_count=len(group(own,'ATTACH')),detach_entry_count=len(group(own,'DETACH')),root_remove_count=len(group(own,'ROOT_REMOVE')),context_free_count=len(context_free))
