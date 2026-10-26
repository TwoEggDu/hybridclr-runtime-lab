import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from incremental_results import validate_steps, parse_player, validate_native, validate_event_order

def good():return [dict(seq=n,more=True,starts=7,ends=6,write_starts=7,write_ends=6,kind=(n-1)%3,candidate=1000+n) for n in range(1,13)]
class IncrementalChecks(unittest.TestCase):
 def test_valid_cycle(self):self.assertEqual(validate_steps(good()),7)
 def test_no_remaining_work(self):
  rows=good();rows[2]['more']=False
  with self.assertRaises(ValueError):validate_steps(rows)
 def test_new_cycle(self):
  rows=good();rows[2]['starts']=8
  with self.assertRaises(ValueError):validate_steps(rows)
 def test_finished_before_write(self):
  rows=good();rows[2]['write_ends']=7
  with self.assertRaises(ValueError):validate_steps(rows)
 def test_missing_step(self):
  with self.assertRaises(ValueError):validate_steps(good()[:-1])
 def test_wrong_operation(self):
  rows=good();rows[2]['kind']=0
  with self.assertRaises(ValueError):validate_steps(rows)
 def test_wrong_candidate(self):
  rows=good();rows[2]['candidate']=999
  with self.assertRaises(ValueError):validate_steps(rows)
 def test_not_open(self):
  rows=good()
  for r in rows:r['ends']=7;r['write_ends']=7
  with self.assertRaises(ValueError):validate_steps(rows)
class PlayerChecks(unittest.TestCase):
 def raw(self):
  lines=['WBI_ENV writer=aot unity=2022.3.62f3 incremental=True mode=Manual heap=250000 budget=1000','WBI_BASE completed=1 starts=1 ends=1','WBI_BEGIN requested=True completed=1']
  for n in range(1,13):
   lines += [f'WBI_SLICE seq={n} more=True starts=1 ends=1 marks=2 markEnds=1 frame={n+1}',f'WBI_WRITE seq={n} kind={(n-1)%3} candidate={1000+n} starts=1 ends=1 markEnds=1']
  lines += ['WBI_END seq=844 more=False starts=1 ends=1 marks=4 markEnds=2 frame=14','WBI_GRAPH writes=12 checksum=12078 alive=12','WBI_EVENT index=0 event=0 starts=1 ends=0 phase=0 seq=0','WBI_EVENT index=1 event=1 starts=1 ends=0 phase=0 seq=0','WBI_EVENT index=2 event=2 starts=1 ends=0 phase=0 seq=0','WBI_EVENT index=3 event=5 starts=1 ends=1 phase=0 seq=0','WBI_EVENT index=4 event=1 starts=1 ends=1 phase=1 seq=0','WBI_EVENT index=5 event=1 starts=1 ends=1 phase=6 seq=12','WBI_EVENT index=6 event=1 starts=1 ends=1 phase=6 seq=12','WBI_EVENT index=7 event=2 starts=1 ends=1 phase=6 seq=12','WBI_RELEASE alive=0','WBI_DONE writer=aot probe=False failures=0']
  return '\n'.join(lines)
 def test_player(self):self.assertEqual(parse_player(self.raw(),'aot')['checksum'],12078)
 def test_false_slice(self):
  with self.assertRaises(ValueError):parse_player(self.raw().replace('seq=5 more=True','seq=5 more=False'),'aot')
 def test_extra_cycle(self):
  with self.assertRaises(ValueError):parse_player(self.raw().replace('marks=4 markEnds=2','marks=4 markEnds=3'),'aot')
 def test_event_completion_inside_write(self):
  with self.assertRaises(ValueError):parse_player(self.raw().replace('event=2 starts=1 ends=1 phase=6 seq=12','event=2 starts=1 ends=1 phase=6 seq=5'),'aot')
 def test_duplicate_step(self):
  with self.assertRaises(ValueError):parse_player(self.raw().replace('seq=6 more=True','seq=5 more=True'),'aot')
 def test_missing_done(self):
  with self.assertRaises(ValueError):parse_player(self.raw().replace('WBI_DONE','MISSING'),'aot')
 def test_corrupt_graph(self):
  with self.assertRaises(ValueError):parse_player(self.raw().replace('checksum=12078','checksum=12077'),'aot')
 def test_full_gc_intervened(self):
  with self.assertRaises(ValueError):parse_player(self.raw().replace('seq=2 more=True starts=1','seq=2 more=True starts=2'),'aot')
 def test_mode_mismatch(self):
  with self.assertRaises(ValueError):parse_player(self.raw(),'hot')
def native_good():
 observations=[];barriers=[];dirty=[];returns=[];parked=[];final=[]
 for n in range(1,13):
  kind=(n-1)%3;target=0x10000+n*0x30;slots=[0x2010,0,0,0] if kind==0 else [0x3000+32+n*8,0,0,0] if kind==1 else [0x2020,0x2028,0x4000+32+n*24,0x4000+40+n*24]
  observations.append(dict(seq=n,kind=kind,tid=99,owner=0x2000,target=target,ownerMark=1,targetMark=0,gc=4,state=1,**dict(zip(('slotA','slotB','slotC','slotD'),slots))))
  for slot in ([slots[0],slots[2]] if kind==2 else [slots[0]]):
   barriers.append(dict(seq=n,kind=kind,slot=slot,value=target,gc=4,state=1,stack='WbState_Write Il2CppCodeGenWriteBarrier'))
   dirty.extend([dict(phase=phase,seq=n,kind=kind,slot=slot,bit=bit) for phase,bit in [('before',0),('after',1)]])
  returns.append(dict(seq=n,target=target,mark=0,gc=4,state=1));parked.append(dict(seq=n,tid=99,stackHits=0,gc=4,state=1));final.append(dict(seq=n,target=target,mark=1,gc=5,state=0))
 return dict(begin=[dict(gc=4,state=0)],end=[dict(gc=5,state=0)],observations=observations,barriers=barriers,dirty=dirty,returns=returns,parked=parked,final=final,rescans=[dict(seq=12,block=page,gc=4,state=1,stack='GC_push_next_marked_dirty') for page in (0x2000,0x3000,0x4000)],roots=[])
class NativeChecks(unittest.TestCase):
 def test_native(self):self.assertEqual(validate_native(native_good(),'aot')['barrier_count'],16)
 def test_native_cycle_changed(self):
  d=native_good();d['observations'][1]['gc']=5
  with self.assertRaises(ValueError):validate_native(d,'aot')
 def test_invalid_mark_decode(self):
  d=native_good();d['observations'][1]['ownerMark']=-1
  with self.assertRaises(ValueError):validate_native(d,'aot')
 def test_unmarked_owner(self):
  d=native_good();d['observations'][1]['ownerMark']=0
  with self.assertRaises(ValueError):validate_native(d,'aot')
 def test_missing_barrier(self):
  d=native_good();d['barriers'].pop()
  with self.assertRaises(ValueError):validate_native(d,'aot')
 def test_wrong_slot(self):
  d=native_good();d['barriers'][1]['slot']+=1
  with self.assertRaises(ValueError):validate_native(d,'aot')
 def test_dirty_not_set(self):
  d=native_good();d['dirty'][1]['bit']=0
  with self.assertRaises(ValueError):validate_native(d,'aot')
 def test_invalid_dirty_before(self):
  d=native_good();d['dirty'][0]['bit']=-1
  with self.assertRaises(ValueError):validate_native(d,'aot')
 def test_rescan_wrong_stage(self):
  d=native_good()
  for r in d['rescans']:r['seq']=0
  with self.assertRaises(ValueError):validate_native(d,'aot')
 def test_missing_rescan(self):
  d=native_good();d['rescans'].pop()
  with self.assertRaises(ValueError):validate_native(d,'aot')
 def test_final_wrong_cycle(self):
  d=native_good();d['final'][0]['gc']=6
  with self.assertRaises(ValueError):validate_native(d,'aot')
 def test_final_lost_mark(self):
  d=native_good();d['final'][0]['mark']=0
  with self.assertRaises(ValueError):validate_native(d,'aot')
 def hot(self):
  d=native_good()
  for b in d['barriers']:b['stack']='Interpreter::Execute'
  d['roots']=[dict(event='WBI_ROOT_ADD',tid=99,root=77)]+[dict(event='WBI_ROOT_QUERY',tid=1,root=77,top=0,frames=0) for _ in range(3)]+[dict(event='WBI_ROOT_REMOVE',tid=99,root=77)]
  return d
 def test_hot_roots(self):validate_native(self.hot(),'hot')
 def test_missing_root_remove(self):
  d=self.hot();d['roots'].pop()
  with self.assertRaises(ValueError):validate_native(d,'hot')
 def test_live_interpreter_slots(self):
  d=self.hot();d['roots'][1]['top']=1
  with self.assertRaises(ValueError):validate_native(d,'hot')
 def test_wrong_root_owner(self):
  d=self.hot();d['roots'][-1]['tid']=88
  with self.assertRaises(ValueError):validate_native(d,'hot')
 def test_parked_stale_target(self):
  d=native_good();d['parked'][0]['stackHits']=1
  with self.assertRaises(ValueError):validate_native(d,'aot')
class OrderChecks(unittest.TestCase):
 def good(self):
  d=native_good();lines=['WBI_NATIVE_BEGIN gc=4 state=0']
  def put(label,row):lines.append(label+' '+' '.join(f'{k}={v:x}' if k in ('slot','value','owner','target','tid','block') else f'{k}={v}' for k,v in row.items() if k!='stack'))
  for n in range(1,13):
   put('WBI_NATIVE_OBSERVE',d['observations'][n-1])
   for b in [r for r in d['barriers'] if r['seq']==n]:
    put('WBI_NATIVE_BARRIER',b)
    for dirty in [r for r in d['dirty'] if r['seq']==n and r['slot']==b['slot']]:put('WBI_NATIVE_DIRTY',dirty)
   put('WBI_NATIVE_RETURN',d['returns'][n-1]);put('WBI_NATIVE_PARK',d['parked'][n-1])
  for row in d['rescans']:put('WBI_NATIVE_RESCAN',row)
  lines.append('WBI_NATIVE_END gc=5 state=0')
  for row in d['final']:put('WBI_NATIVE_FINAL',row)
  return lines
 def test_valid_order(self):validate_event_order('\n'.join(self.good()))
 def test_rescan_before_write(self):
  lines=self.good();rescan=next(l for l in lines if l.startswith('WBI_NATIVE_RESCAN'));lines.remove(rescan);lines.insert(1,rescan)
  with self.assertRaises(ValueError):validate_event_order('\n'.join(lines))
 def test_park_before_tail(self):
  lines=self.good();park=next(l for l in lines if l.startswith('WBI_NATIVE_PARK'));lines.remove(park);lines.insert(2,park)
  with self.assertRaises(ValueError):validate_event_order('\n'.join(lines))
 def test_dirty_before_barrier(self):
  lines=self.good();dirty=next(l for l in lines if l.startswith('WBI_NATIVE_DIRTY'));lines.remove(dirty);lines.insert(2,dirty)
  with self.assertRaises(ValueError):validate_event_order('\n'.join(lines))
 def test_final_before_end(self):
  lines=self.good();final=next(l for l in lines if l.startswith('WBI_NATIVE_FINAL'));lines.remove(final);lines.insert(1,final)
  with self.assertRaises(ValueError):validate_event_order('\n'.join(lines))
if __name__=='__main__':unittest.main()
