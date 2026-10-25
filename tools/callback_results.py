"""Acceptance of standalone native-callback Player observations."""
import re

def one(text,pattern):
 rows=re.findall(pattern,text,re.M)
 if len(rows)!=1:raise ValueError("Missing/duplicate record: "+pattern)
 return rows[0]

def parse_player(text,mode):
 env=one(text,r'^CB_ENV mode=(\w+) unity=(\S+) incremental=(\w+) gcMode=(\w+)\s*$')
 if env!=(mode,'2022.3.62f3','True','Enabled'):raise ValueError('Environment mismatch')
 size,assembly,pointer=one(text,r'^CB_LOAD bytes=(\d+) assembly=(\w+) pointer=(\d+)\s*$')
 if assembly!='HotUpdate' or min(int(size),int(pointer))<=0:raise ValueError('Hot load missing')
 main=dict(zip(['managed','native'],map(int,one(text,r'^CB_MAIN managed=(\d+) native=(\d+)\s*$'))))
 rows=re.findall(r'^CB_CALL index=(\d+) managed=(\d+) native=(\d+) a=(\d+) b=(\d+) result=(-?\d+)\s*$',text,re.M)
 expected=[(2,3,5),(7,8,15)]+([(11,12,23)] if mode=='raw' else [])
 if len(rows)!=len(expected):raise ValueError('Call count mismatch')
 calls=[dict(zip(['index','managed','native','a','b','result'],map(int,r))) for r in rows]
 for index,(c,args) in enumerate(zip(calls,expected)):
  if c['index']!=index or tuple(c[k] for k in ('a','b','result'))!=args or min(c['managed'],c['native'])<=0:raise ValueError('Call results mismatch')
  if c['native']==main['native'] or c['managed']==main['managed']:raise ValueError('Callback ran on main')
 if len({c['native'] for c in calls})!=1:raise ValueError('Worker OS identity mismatch')
 if mode=='registered':
  before,after,native,result,joined=one(text,r'^CB_OWNER before=(\d+) after=(\d+) native=(\d+) result=(\d+) joined=(\w+)\s*$')
  if before!=after or int(result)!=50015 or joined!='True' or any(c['managed']!=int(before) or c['native']!=int(native) for c in calls):raise ValueError('Existing registration lost')
 else:
  if one(text,r'^CB_STOP entered=(\w+) joinedBefore=(\w+) requested=(\d+)\s*$')!=('True','False','1'):raise ValueError('In-flight stop invalid')
  native,count,a,b,c,joined=one(text,r'^CB_RAW native=(\d+) count=(\d+) first=(-?\d+) second=(-?\d+) third=(-?\d+) joined=(\w+)\s*$')
  if (count,a,b,c,joined)!=('3','5','15','23','True') or int(native)!=calls[0]['native']:raise ValueError('Native completion mismatch')
 if one(text,r'^CB_RELEASE afterJoin=(\w+)\s*$')!='True' or one(text,r'^CB_DONE mode=(\w+) failures=(\d+)\s*$')!=(mode,'0'):raise ValueError('Incomplete shutdown')
 sequence=['CB_STOP ','CB_RAW ','CB_RELEASE ','CB_DONE '] if mode=='raw' else ['CB_OWNER ','CB_RELEASE ','CB_DONE ']
 positions=[text.index(x) for x in sequence]
 if positions!=sorted(positions):raise ValueError('Shutdown order mismatch')
 return dict(mode=mode,unity=env[1],incremental=True,gcMode='Enabled',bytes=int(size),pointer=int(pointer),main=main,calls=calls)


def parse_native(text,player):
 for module in ('GameAssembly','NativeProbe'):
  if not re.search(module+r' C \(private pdb symbols\)',text):raise ValueError('Private PDB missing: '+module)
 matches=list(re.finditer(r'^CB_NATIVE_(\w+) tid=([0-9a-f]+)([^\r\n]*)$',text,re.M|re.I));events=[]
 for i,m in enumerate(matches):
  fields=dict(re.findall(r'(\w+)=([^ ]+)',m[3]))
  events.append(dict(kind=m[1],tid=int(m[2],16),fields=fields,pos=m.start(),detail=text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)]))
 tid=player['calls'][0]['native'];own=[e for e in events if e['tid']==tid]
 def group(items,kind):return [e for e in items if e['kind']==kind]
 def single(items,kind):
  found=group(items,kind)
  if len(found)!=1:raise ValueError('Missing/duplicate '+kind)
  return found[0]
 def number(e,key):return int(e['fields'][key],16)
 enters=[e for e in own if e['kind']=='PLUGIN' and e['fields'].get('phase')=='1']
 exits=[e for e in own if e['kind']=='PLUGIN' and e['fields'].get('phase')=='2']
 if len(enters)!=len(player['calls']) or len(exits)!=len(enters):raise ValueError('Native callback count mismatch')
 methods=[];caches=[];scopes=[];states=[]
 for c,enter,exit in zip(player['calls'],enters,exits):
  if enter['pos']>=exit['pos'] or any(int(e['fields'][key])!=c[key] for e in (enter,exit) for key in ('a','b')) or int(exit['fields']['value'])!=c['result']:raise ValueError('Native callback result mismatch')
  span=[e for e in own if enter['pos']<e['pos']<exit['pos']]
  wrap=single(span,'WRAPPER');start=single(span,'SCOPE_ENTER');end=single(span,'SCOPE_LEAVE');execute=single(span,'EXECUTE')
  if number(wrap,'wrapper')!=player['pointer'] or [int(wrap['fields'][k]) for k in ('a','b')]!=[c['a'],c['b']]:raise ValueError('Wrapper identity mismatch')
  if not wrap['pos']<start['pos']<execute['pos']<end['pos'] or number(start,'helper')!=number(end,'helper'):raise ValueError('Scope ordering mismatch')
  if not re.search(r'name\s*:\s*0x[0-9a-f`]+\s+"Call"',execute['detail'],re.I) or 'GameAssembly!__ReversePInvokeMethod_0+' not in execute['detail']:raise ValueError('Hot callback stack missing')
  methods.append(number(execute,'method'))
  cache=re.search(r'interpData\s*:\s*0x([0-9a-f`]+)',execute['detail'],re.I)
  if cache is None and not re.search(r'interpData\s*:\s*\(null\)',execute['detail']):raise ValueError('Cache field missing')
  caches.append(int(cache[1].replace('`',''),16) if cache else 0)
  scopes.append(number(end,'owned'))
  if player['mode']=='raw':
   attach=single(span,'ATTACH');create=single(span,'CREATE');add=single(span,'ROOT_ADD');free=single(span,'FREE');destroy=single(span,'DESTROY');remove=single(span,'ROOT_REMOVE');detach=group(span,'DETACH')
   state=number(create,'state');states.append(create['fields']['state'])
   if not scopes[-1] or not detach or any(number(e,'thread')!=scopes[-1] for e in detach):raise ValueError('Owned registration mismatch')
   if not start['pos']<attach['pos']<execute['pos']<create['pos']<add['pos']<end['pos']<detach[0]['pos']<free['pos']<destroy['pos']<remove['pos']<exit['pos']:raise ValueError('Raw lifecycle order mismatch')
   if not state or number(add,'root')!=state or number(destroy,'state')!=state or number(remove,'root')!=state:raise ValueError('Raw state/root mismatch')
  elif scopes[-1]!=0 or group(span,'ATTACH') or group(span,'DETACH'):raise ValueError('Existing registration incorrectly owned')
 if len(set(methods))!=1 or not methods[0] or caches[0]!=0 or any(x==0 for x in caches[1:]) or len(set(caches[1:]))!=1:raise ValueError('Method or first/later cache mismatch')
 transform=single(own,'TRANSFORM')
 if number(transform,'method')!=methods[0] or not enters[0]['pos']<transform['pos']<exits[0]['pos']:raise ValueError('First conversion mismatch')
 if player['mode']=='registered':
  create=single(own,'CREATE');add=single(own,'ROOT_ADD');free=single(own,'FREE');destroy=single(own,'DESTROY');remove=single(own,'ROOT_REMOVE')
  state=number(create,'state');states.append(create['fields']['state'])
  if not enters[0]['pos']<create['pos']<add['pos']<exits[0]['pos']<enters[1]['pos']<exits[1]['pos']<free['pos']<destroy['pos']<remove['pos']:raise ValueError('Registered cleanup order mismatch')
  if not state or number(add,'root')!=state or number(destroy,'state')!=state or number(remove,'root')!=state or group(own,'DETACH'):raise ValueError('Registered state/root mismatch')
 else:
  plugins=[e for e in events if e['kind']=='PLUGIN']
  phases={k:[e for e in plugins if e['fields'].get('phase')==k] for k in ('3','4','5','6')}
  if any(len(x)!=1 for x in phases.values()):raise ValueError('Stop/start/end/join records missing')
  stop,join,start,end=[phases[k][0] for k in ('3','4','5','6')]
  if stop['tid']!=player['main']['native'] or join['tid']!=player['main']['native'] or start['tid']!=tid or end['tid']!=tid or not start['pos']<enters[0]['pos']<enters[2]['pos']<stop['pos']<exits[2]['pos']<end['pos']<join['pos']:raise ValueError('In-flight stop ordering mismatch')
 return dict(mode=player['mode'],native=tid,callback_count=len(enters),method=f'{methods[0]:016x}',interpData=[f'{x:016x}' for x in caches],transform_count=1,owned_threads=[f'{x:016x}' for x in scopes],states=states,attach_count=len(group(own,'ATTACH')),detach_entry_count=len(group(own,'DETACH')),state_create_count=len(group(own,'CREATE')),root_remove_count=len(group(own,'ROOT_REMOVE')))
