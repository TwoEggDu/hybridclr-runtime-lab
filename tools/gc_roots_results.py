"""Strict decoder for self-authored debugger events, not a GC reachability oracle."""
import re

def parse_trace(text):
 live={};removed=[];samples=[];pending=None;sample=None;target=0
 def hx(s):return int(s.replace('`',''),16)
 def finish():
  nonlocal sample
  if sample is None:return
  expected=list(range(0,sample['bytes'],8))
  if [x[0] for x in sample['slots']]!=expected:raise ValueError('Missing, duplicate or out-of-range slot')
  sample['target_offsets']=[offset for offset,value in sample.pop('slots') if value==sample['target'] and value!=0]
  samples.append(sample);sample=None
 for line in text.splitlines():
  if not line.startswith('GR_'):continue
  event=line.split()[0];fields=dict(re.findall(r'(\w+)=(\S+)',line))
  if event!='GR_SLOT':finish()
  if event=='GR_ADD':
   state=fields['state'];
   if state in live:raise ValueError('Duplicate root registration')
   live[state]=hx(fields['tid'])
  elif event=='GR_REMOVE':
   state=fields['state']
   if state not in live or pending is not None:raise ValueError('Invalid root removal')
   if hx(fields['tid'])!=live[state]:raise ValueError('Root removed by a different owner thread')
   del live[state];removed.append(state)
  elif event=='GR_TARGET':target=hx(fields['object'])
  elif event=='GR_ENTRY':
   if pending is not None or fields['state'] not in live:raise ValueError('Unregistered or nested callback')
   pending=fields
  elif event=='GR_RETURN':
   if pending is None or fields['state']!=pending['state'] or fields['tid']!=pending['tid']:raise ValueError('Unpaired return')
   top=int(fields['top']);size=int(fields['bytes']);base=hx(fields['base'])
   if top<0 or top>4096 or int(pending['top'])!=top or size!=top*8:raise ValueError('Active length mismatch')
   if hx(fields['pair'])!=hx(pending['out']):raise ValueError('Result ABI mismatch')
   if base!=(hx(pending['expected']) if top else 0):raise ValueError('Active base mismatch')
   if hx(fields['target'])!=target:raise ValueError('Target changed without Track event')
   sample=dict(state=fields['state'],owner_tid=live[fields['state']],collector_tid=hx(fields['tid']),base=base,allocated_base=hx(pending['expected']),bytes=size,top=top,target=target,capacity=int(pending.get('capacity',top)),frames=int(pending.get('frames',0)),slots=[])
   if sample['capacity']<top:raise ValueError('Top outside allocated capacity')
   pending=None
  elif event=='GR_SLOT':
   if sample is None or fields['state']!=sample['state']:raise ValueError('Slot outside matching return')
   sample['slots'].append((int(fields['offset']),hx(fields['value'])))
  elif event not in ('GR_NATIVE','GR_COLLECT','GR_IDLE','GR_LAYOUT'):raise ValueError('Unknown event '+event)
 finish()
 if pending is not None or live or not samples:raise ValueError('Incomplete callback or lifecycle capture')
 return dict(samples=samples,removed=removed)


def validate_snapshot_matrix(mode,snapshots):
 stages=['before-native','active','joined-held','released'] if mode=='handle' else ['before-native','active','released']
 if set(snapshots)!=set(stages):raise ValueError('Snapshot stage mismatch')
 target=None
 for stage in stages:
  summary=snapshots[stage]['summary']
  if summary['format_version']!=[16] or summary['capture_flags']!=[1] or summary['vm_info']!=[[8,16,32,16,24,16]]:raise ValueError('Snapshot format/VM mismatch')
  if summary['unknown_handle_targets']!=0:raise ValueError('Unresolved handle target')
  targets=summary['hot_handle_targets']
  expected=1 if mode=='handle' and stage!='released' else 0
  if len(targets)!=expected:raise ValueError('Unexpected hot strong-handle targets')
  if expected:
   row=targets[0];context=row.get('context',{})
   if row['type']!='GcHot.Context' or context.get('tag')!=73 or context.get('head')!=0 or context.get('slots_type')!='GcHot.Node[]' or context.get('slots_length')!=64 or context.get('nonnull_slots')!=0:raise ValueError('Unexpected context graph')
   if target is not None and row['address']!=target:raise ValueError('Context identity changed')
   target=row['address']
 return target
