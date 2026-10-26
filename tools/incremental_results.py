"""Acceptance gates require an unchanged unfinished cycle across all12 mutations."""
def validate_steps(rows):
 if len(rows)!=12:raise ValueError('Incomplete mutation matrix')
 cycle=rows[0]['starts'];ends=rows[0]['ends']
 if cycle!=ends+1:raise ValueError('Cycle not open')
 for n,row in enumerate(rows,1):
  if row['seq']!=n or row['kind']!=(n-1)%3 or row['candidate']!=1000+n:raise ValueError('Mutation order/identity')
  if row['more'] is not True:raise ValueError('No work remains')
  if row['starts']!=cycle or row['write_starts']!=cycle or row['ends']!=ends or row['write_ends']!=ends:raise ValueError('Cycle changed across write')
 return cycle

import re

def records(text,prefix):
 rows=[]
 for line in text.splitlines():
  if line.startswith(prefix+' '):
   row={}
   for key,value in re.findall(r'(\w+)=([^ ]+)',line):
    row[key]=True if value=='True' else False if value=='False' else int(value) if re.fullmatch(r'-?\d+',value) else value
   rows.append(row)
 return rows

def one(text,prefix):
 rows=records(text,prefix)
 if len(rows)!=1:raise ValueError('Missing/duplicate '+prefix)
 return rows[0]

def parse_player(text,mode):
 if 'Exception:' in text:raise ValueError('Player exception')
 env=one(text,'WBI_ENV');base=one(text,'WBI_BASE');begin=one(text,'WBI_BEGIN');end=one(text,'WBI_END');graph=one(text,'WBI_GRAPH');done=one(text,'WBI_DONE');release=one(text,'WBI_RELEASE')
 if env['writer']!=mode or done!={'writer':mode,'probe':False,'failures':0} or env['incremental'] is not True or env['mode']!='Manual':raise ValueError('Environment/mode mismatch')
 if begin!={'requested':True,'completed':base['completed']}:raise ValueError('Cycle completed at start')
 slices=records(text,'WBI_SLICE');writes=records(text,'WBI_WRITE');rows=[]
 if len(slices)!=12 or len(writes)!=12:raise ValueError('Incomplete matrix')
 for n,(sl,wr) in enumerate(zip(slices,writes),1):
  if sl['seq']!=n or wr['seq']!=n:raise ValueError('Sequence')
  if any(r[k]!=base[k] for r in (sl,wr) for k in ('starts','ends')):raise ValueError('Unexpected full collection')
  if sl['markEnds']!=base['completed'] or wr['markEnds']!=base['completed']:raise ValueError('Marking cycle changed')
  if n>1 and sl['frame']!=slices[n-2]['frame']+1:raise ValueError('Not consecutive frames')
  rows.append(dict(seq=n,more=sl['more'],starts=base['completed']+1,ends=sl['markEnds'],write_starts=base['completed']+1,write_ends=wr['markEnds'],kind=wr['kind'],candidate=wr['candidate']))
 cycle=validate_steps(rows)
 order=[line.split(' ')[0]+':'+str(row['seq']) for line in text.splitlines() if line.startswith(('WBI_SLICE ','WBI_WRITE ')) for row in [dict(re.findall(r'(seq)=(\d+)',line))]]
 if order!=[f'{label}:{n}' for n in range(1,13) for label in ('WBI_SLICE','WBI_WRITE')]:raise ValueError('Interleaving')
 if end['more'] is not False or end['markEnds']!=cycle or end['starts']!=base['starts'] or end['ends']!=base['ends'] or end['seq']<=12:raise ValueError('Completion boundary')
 if graph!={'writes':12,'checksum':12078,'alive':12}:raise ValueError('Graph integrity')
 events=records(text,'WBI_EVENT')
 if not events or [r['index'] for r in events]!=list(range(len(events))):raise ValueError('Event buffer sequence')
 # START/END wrap full collections; MARK_END, not MARK_START, counts completed marking cycles.
 during=[r for r in events if r['phase'] in (1,2,3,4,6)]
 completed=[r for r in during if r['event']==2]
 if len(completed)!=1 or completed[0]['phase']!=6 or completed[0]['seq']!=12:raise ValueError('Mark-end event boundary')
 if any(r['event'] in (0,5) for r in during) or not any(r['event']==1 and r['phase']==1 for r in during):raise ValueError('Unexpected full collection or missing marking attempt')
 return dict(writer=mode,cycle=cycle,steps=rows,frames=[r['frame'] for r in slices],drain_calls=end['seq']-12,mark_attempts=end['marks']-slices[0]['marks']+1,checksum=graph['checksum'],retained=graph['alive'],released_alive=release['alive'],events=events)


def validate_native(data,mode):
 for key in ('observations','returns','parked','final'):
  if [r['seq'] for r in data[key]]!=list(range(1,13)):raise ValueError('Incomplete native '+key)
 if len(data['begin'])!=1 or len(data['end'])!=1:raise ValueError('Native boundary')
 gc=data['begin'][0]['gc'];end=data['end'][0]
 if data['begin'][0]['state']!=0 or end!={'gc':gc+1,'state':0}:raise ValueError('Native collection identity')
 owners={r['owner'] for r in data['observations']};tids={r['tid'] for r in data['observations']}
 if len(owners)!=1 or len(tids)!=1:raise ValueError('Owner/thread changed')
 pages=set();pairs=0
 for n,(ob,ret,park,final) in enumerate(zip(data['observations'],data['returns'],data['parked'],data['final']),1):
  kind=(n-1)%3
  if ob['kind']!=kind or ob['ownerMark']!=1 or ob['targetMark']!=0:raise ValueError('Unexpected pre-write marks/kind')
  if any(r['gc']!=gc or r['state']==0 for r in (ob,ret,park)):raise ValueError('Native cycle advanced during mutation')
  if ret['target']!=ob['target'] or ret['mark']!=0:raise ValueError('Return target/mark')
  if park['tid']!=ob['tid'] or park['stackHits']!=0:raise ValueError('Current target remains on scrubbed worker stack')
  if final['target']!=ob['target'] or final['mark']!=1 or final['gc']!=gc+1 or final['state']!=0:raise ValueError('Final target identity/mark/cycle')
  slots=[ob['slotA'],ob['slotC']] if kind==2 else [ob['slotA']]
  for slot in slots:
   pages.add(slot&~4095)
   barriers=[r for r in data['barriers'] if r['seq']==n and r['slot']==slot and r['value']==ob['target'] and r['gc']==gc and r['state']!=0]
   if not barriers or not any(('Interpreter::Execute' in r['stack'] if mode=='hot' else 'WbState_Write' in r['stack']) for r in barriers):raise ValueError('Missing target store/barrier path')
   dirty=[r for r in data['dirty'] if r['seq']==n and r['slot']==slot]
   if [r['phase'] for r in dirty]!=['before','after'] or any(r['bit'] not in (0,1) or r['kind']!=kind for r in dirty) or dirty[1]['bit']!=1:raise ValueError('Dirty page effect missing')
   if dirty[0]['bit']==0:pairs+=1
  if kind==0 and ob['slotA']!=ob['owner']+16:raise ValueError('Field layout')
  if kind==2 and (ob['slotA']!=ob['owner']+32 or ob['slotB']!=ob['owner']+40 or ob['slotD']!=ob['slotC']+8):raise ValueError('Struct layout')
 rescanned={r['block'] for r in data['rescans'] if r['seq']==12 and r['gc']==gc and r['state']!=0 and 'GC_push_next_marked_dirty' in r['stack']}
 if not pages.issubset(rescanned):raise ValueError('Expected destination page rescan missing')
 queries=[r for r in data['roots'] if r['event']=='WBI_ROOT_QUERY']
 if mode=='hot':
  adds=[r for r in data['roots'] if r['event']=='WBI_ROOT_ADD'];removes=[r for r in data['roots'] if r['event']=='WBI_ROOT_REMOVE']
  if len(adds)!=1 or len(removes)!=1 or len(queries)<3 or data['roots'][0]!=adds[0] or data['roots'][-1]!=removes[0]:raise ValueError('Root lifetime matrix')
  if adds[0]['tid'] not in tids or removes[0]['tid']!=adds[0]['tid'] or any(r['root']!=adds[0]['root'] for r in data['roots']):raise ValueError('Root owner mismatch')
  if any(r['top']!=0 or r['frames']!=0 for r in queries):raise ValueError('Expected idle interpreter state')
 elif data['roots']:raise ValueError('Unexpected interpreted roots in AOT control')
 return dict(root_queries=len(queries),gc_before=gc,gc_after=gc+1,owner_marks=sorted({r['ownerMark'] for r in data['observations']}),target_marks_before=sorted({r['targetMark'] for r in data['observations']}),target_marks_after=sorted({r['mark'] for r in data['final']}),barrier_count=len(data['barriers']),dirty_transitions_0_to_1=pairs,rescanned_destination_pages=len(pages),worker_stack_hits=[r['stackHits'] for r in data['parked']])

def parse_trace(text,mode):
 if any(x in text for x in ('Syntax error','Unable to resolve','Command file execution failed','offset expression evaluation failed','Numeric expression missing','Memory access error','Symbol GameAssembly!WbBox')):raise ValueError('Debugger command/ABI failed')
 if 'private pdb symbols' not in text:raise ValueError('Matching private PDB missing')
 expected={'_all_nils':'0a8','_dirty_pages':'462e0','_grungy_pages':'62e0','_top_index':'29e2e0','hb_marks':'040','___Field':'010','___Slots':'018','___Pair':'020','___Pairs':'038','___Left':'000','___Right':'008','___Tag':'010'}
 for name,off in expected.items():
  if not re.search(r'\+0x'+off+r'\s+'+name+r'[^ ]*\s+:',text):raise ValueError('PDB field mismatch '+name)
 start=re.search(r'^GameAssembly!GC_dirty_inner:\r?\n([0-9a-f`]+)',text,re.M)
 returns=re.findall(r'^([0-9a-f`]+)\s+c3\s+ret\s*$',text,re.M)
 number=lambda s:int(s.replace('`',''),16)
 if not start or len(returns)!=1 or number(returns[0])-number(start[1])!=0x5e:raise ValueError('Dirty return offset mismatch')
 names={'WBI_NATIVE_BEGIN':'begin','WBI_NATIVE_END':'end','WBI_NATIVE_OBSERVE':'observations','WBI_NATIVE_BARRIER':'barriers','WBI_NATIVE_DIRTY':'dirty','WBI_NATIVE_RETURN':'returns','WBI_NATIVE_PARK':'parked','WBI_NATIVE_FINAL':'final','WBI_NATIVE_RESCAN':'rescans'}
 data={v:[] for v in names.values()};data['roots']=[]
 hexkeys={'tid','owner','target','slotA','slotB','slotC','slotD','slot','value','block','root'}
 lines=text.splitlines()
 for i,line in enumerate(lines):
  label=line.split(' ')[0]
  if label not in names and not label.startswith('WBI_ROOT_'):continue
  row={k:(int(v.replace('`',''),16) if k in hexkeys else int(v) if re.fullmatch(r'-?\d+',v) else v) for k,v in re.findall(r'(\w+)=([^ ]+)',line)}
  if label in ('WBI_NATIVE_BARRIER','WBI_NATIVE_RESCAN'):
   tail=[]
   for l in lines[i+1:]:
    if l.startswith('WBI_'):break
    tail.append(l)
   row['stack']='\n'.join(tail)
  if label.startswith('WBI_ROOT_'):row['event']=label;data['roots'].append(row)
  else:data[names[label]].append(row)
 windows=validate_event_order(text)
 data['summary']=validate_native(data,mode)
 data['summary']['root_query_windows']=windows
 return data


def validate_event_order(text):
 events=[]
 for line in text.splitlines():
  if line.startswith(('WBI_NATIVE_','WBI_ROOT_')):
   events.append((line.split(' ')[0],dict(re.findall(r'(\w+)=([^ ]+)',line))))
 def positions(label,seq=None,slot=None):return [i for i,(name,row) in enumerate(events) if name==label and (seq is None or row.get('seq')==str(seq)) and (slot is None or row.get('slot')==slot)]
 def exactly(label,seq=None):
  rows=positions(label,seq)
  if len(rows)!=1:raise ValueError('Event boundary '+label)
  return rows[0]
 begin=exactly('WBI_NATIVE_BEGIN');end=exactly('WBI_NATIVE_END');last=begin
 for n in range(1,13):
  ob=exactly('WBI_NATIVE_OBSERVE',n);tail=exactly('WBI_NATIVE_RETURN',n);park=exactly('WBI_NATIVE_PARK',n);final=exactly('WBI_NATIVE_FINAL',n)
  if not last<ob<tail<park<end<final:raise ValueError('Write/tail/park/completion order')
  barriers=positions('WBI_NATIVE_BARRIER',n);dirty=positions('WBI_NATIVE_DIRTY',n)
  if not barriers or not dirty or any(not ob<i<tail for i in barriers+dirty):raise ValueError('Store event outside writer window')
  slots={events[i][1]['slot'] for i in barriers}
  if slots!={events[i][1]['slot'] for i in dirty}:raise ValueError('Barrier/dirty address set')
  for slot in slots:
   bs=positions('WBI_NATIVE_BARRIER',n,slot);ds=positions('WBI_NATIVE_DIRTY',n,slot)
   if len(ds)!=2 or events[ds[0]][1]['phase']!='before' or events[ds[1]][1]['phase']!='after' or not max(bs)<ds[0]<ds[1]:raise ValueError('Barrier/dirty event order')
  last=park
 rescans=positions('WBI_NATIVE_RESCAN')
 if not rescans or any(not last<i<end or events[i][1].get('seq')!='12' for i in rescans):raise ValueError('Rescan must follow last write and precede completion')
 windows={'baseline':0,'cycle':0,'after_cycle':0}
 for i in positions('WBI_ROOT_QUERY'):windows['baseline' if i<begin else 'cycle' if i<end else 'after_cycle']+=1
 return windows
