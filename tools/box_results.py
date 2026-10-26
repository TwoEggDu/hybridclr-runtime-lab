"""Own constrained/boxing event acceptance; missing implementation is not semantics passed."""
import json
ROUTES=('aot','hot','cross');MODES=('value','ref','box','text-override','text-fallback','reference')
def parse_player(text,route,mode,metadata,build_id):
 def check(v,msg):
  if not v:raise ValueError(msg)
 check('CBX_FATAL' not in text,'Driver failure')
 events=[json.loads(l.split('CBX ',1)[1]) for l in text.splitlines() if 'CBX ' in l]
 check(bool(events),'No own events');check([x['seq'] for x in events]==list(range(1,len(events)+1)),'Sequence')
 def rows(k):return [x for x in events if x['kind']==k]
 def one(k):
  r=rows(k);check(len(r)==1,'Expected one '+k);return r[0]
 env=one('env');check(events[0]==env and (env['route'],env['mode'],env['metadata'],env['build'])==(route,mode,metadata,build_id),'Identity')
 check(not env['hot_before'],'Hot preloaded');check(events[-1]==one('done') and one('done')['value']==0,'Completion')
 begin=one('begin');check(begin['value']==10,'Initial value')
 check(all(e['kind'] in ('env','metadata','begin','body','target','result','error','done') for e in events),'Unknown event')
 mr=rows('metadata');check(len(mr)==(1 if metadata=='on' else 0),'Metadata count')
 if mr:check(mr[0]['value']==0 and mr[0]['label']=='Probe.AOT' and mr[0]['detail']=='Superset','Metadata rejected')
 if rows('error'):
  error=one('error');check(route=='cross' and metadata=='off' and mode=='value' and error['type']=='System.MissingMethodException','Unexpected failure')
  check(not rows('result') and error['seq']>begin['seq'],'Failure phase')
  expected='AOT generic method not instantiated in aot. assembly:Probe.AOT.dll, method:System.Int32 GenericCalls::ByValue<HotBox.Counter>(HotBox.Counter)'
  check(error.get('detail')==expected and not rows('body') and not rows('target'),'Wrong missing method identity/phase')
  return dict(classification='missing_method',events=events,error=error)
 r=one('result');check(r['seq']>begin['seq'],'Result order')
 expected={'value':(10,11,0),'ref':(11,11,0),'box':(10,12,13),'reference':(12,11,12),'text-override':(10,0,0),'text-fallback':(10,0,0)}[mode]
 check(tuple(r[k] for k in ('a','b','c'))==expected,'Wrong state/return')
 check(r['flag']==(mode in ('box','reference')),'Object identity')
 if mode=='text-override':check(r['text']=='counter:10','Override result')
 elif mode=='text-fallback':check(r['text']==('AotBox' if route=='aot' else 'HotBox')+'.PlainCounter','Fallback type name')
 else:check(not r['text'],'Unexpected text')
 targets=rows('target');values=[x['value'] for x in targets]
 check(values=={'value':[11],'ref':[11],'box':[11,12,13],'reference':[11,12],'text-override':[10],'text-fallback':[]}[mode],'Target executions')
 return dict(classification='completed',events=events,result=r)
