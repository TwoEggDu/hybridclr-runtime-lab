"""Accept observations, without prescribing an OS scheduling order."""
import json
SIDES=('aot','hot');MODES=('cold','strict','failed','generic')
CELLS=[(s,m,n) for s in SIDES for m in MODES for n in (2,4)]+[('mixed','strict',n) for n in (2,4)]
def subjects(side,mode):
 ns='HotConcurrent' if side=='hot' else 'AotConcurrent'
 return [ns+'.'+s for s in {'cold':['Cold'],'strict':['Strict'],'failed':['Failed'],'generic':['Cache<System.Int32>','Cache<System.String>']}[mode]]
def parse_player(text,side,mode,n,build):
 def need(x,m):
  if not x:raise ValueError(m)
 need((side,mode,n) in CELLS,'unknown cell');need('CIP_FATAL' not in text,'fatal')
 r=[json.loads(x[4:]) for x in text.splitlines() if x.startswith('CIP ')]
 need(r and [x.get('seq') for x in r]==list(range(1,len(r)+1)),'sequence')
 def of(k):return [x for x in r if x['kind']==k]
 allowed={'env','meta','ready','gate','attempt','init_begin','init_end','body','result','caught','join','done'}
 need(all(x.get('kind') in allowed for x in r),'unknown event')
 need(len(of('env'))==1 and r[0]['kind']=='env','environment count')
 e=r[0];need(all(e.get(k)==v for k,v in dict(side=side,mode=mode,nworkers=n,build=build,unity='2022.3.62f3',hot_before=False).items()),'environment identity')
 main=(e.get('managed'),e.get('native'));need(all(isinstance(v,int) and v>0 for v in main),'main thread identity')
 subs=subjects(side,mode);meta=of('meta')
 need([x.get('subject') for x in meta]==subs and all(x.get('bfi') is (mode=='cold') and x.get('cctor') is (mode!='cold') for x in meta),'type metadata')
 ready=of('ready');need(sorted(x.get('worker') for x in ready)==list(range(n)),'ready count/worker')
 ids={x['worker']:(x.get('managed'),x.get('native')) for x in ready}
 need(len({v[0] for v in ids.values()})==n and len({v[1] for v in ids.values()})==n and all(a>0 and b>0 for a,b in ids.values()),'thread identity')
 need(all(a!=main[0] and b!=main[1] for a,b in ids.values()),'worker is main thread')
 gate=of('gate');need(len(gate)==1 and gate[0].get('phase')=='open','gate')
 g=gate[0]['seq'];need(all(x['seq']<g for x in ready+meta),'readiness order')
 attempts=of('attempt');need(sorted(x.get('worker') for x in attempts)==list(range(n)) and all(x['seq']>g for x in attempts),'attempt matrix/order')
 for x in attempts+of('result')+of('caught'):
  w=x.get('worker');need(isinstance(w,int),'worker field')
  if w<n:need(w>=0 and (x.get('managed'),x.get('native'))==ids[w],'worker changed thread')
 need(len(of('done'))==1 and r[-1]['kind']=='done' and r[-1].get('completed') is True,'completion')
 joins=of('join');need(sorted(x.get('worker') for x in joins)==list(range(n)) and all(x.get('joined') is True for x in joins),'joins')
 outcomes=of('caught') if mode=='failed' else of('result')
 need(not of('result' if mode=='failed' else 'caught'),'wrong outcome kind')
 need(len(outcomes)==n*len(subs)+(2 if mode=='failed' else 0),'outcome count')
 begins=of('init_begin');ends=of('init_end');bodies=of('body')
 need(len(begins)==(0 if mode=='cold' else len(subs)),'initializer count')
 need(len(ends)==(0 if mode in ('cold','failed') else len(subs)),'initializer completion count')
 need(len(bodies)==(0 if mode=='failed' else n*len(subs)),'body count')
 for x in begins+ends+bodies+outcomes:need(x.get('subject') in subs and x['seq']>g,'subject or early execution')
 summaries=[]
 for s in subs:
  oo=[x for x in outcomes if x['subject']==s]
  need(sorted(x['worker'] for x in oo)==list(range(n+(2 if mode=='failed' else 0))),'outcome workers')
  begin=[x for x in begins if x['subject']==s];end=[x for x in ends if x['subject']==s]
  if mode!='cold':
   need(len(begin)==1 and (begin[0].get('managed'),begin[0].get('native')) in ids.values(),'initializer owner')
   need(any(x['seq']<begin[0]['seq'] and ids[x['worker']][0]==begin[0]['managed'] for x in attempts),'initializer before owner attempt')
  if mode not in ('cold','failed'):
   need(len(end)==1 and begin[0]['seq']<end[0]['seq'] and (end[0].get('managed'),end[0].get('native'))==(begin[0]['managed'],begin[0]['native']),'initializer end/owner')
  value=7 if mode=='cold' else 81123 if 'String' in s else 41083
  sb=[x for x in bodies if x['subject']==s]
  need(len(sb)==(0 if mode=='failed' else n),'body per type')
  if mode!='failed':
   need(sorted((x.get('managed'),x.get('native')) for x in sb)==sorted(ids.values()),'body threads')
   need(all(x.get('value')==value for x in sb+oo),'published field state')
   for x in oo:
    need(any(b['managed']==x['managed'] and b['seq']<x['seq'] for b in sb),'body/result order')
   if end:need(all(x['seq']>end[0]['seq'] for x in sb+oo),'partial publication')
  else:
   need(all(x.get('detail')=='System.Reflection.TargetInvocationException>System.TypeInitializationException>System.InvalidOperationException' and x.get('message')=='concurrent-init-failed:'+s and x['seq']>begin[0]['seq'] for x in oo),'exact failure/cause')
   retries=[x for x in oo if x['worker']>=n]
   need([x['worker'] for x in retries]==[n,n+1],'retry order')
   need(all((x.get('managed'),x.get('native'))==main and x['seq']>max(j['seq'] for j in joins) for x in retries),'retry must follow all joins on main')
  for w in range(n):
   a=next(x for x in attempts if x['worker']==w);o=next(x for x in oo if x['worker']==w);j=next(x for x in joins if x['worker']==w)
   need(a['seq']<o['seq']<j['seq'],'worker lifecycle')
  overlap=0 if not end else sum(begin[0]['seq']<x['seq']<end[0]['seq'] for x in attempts)
  summaries.append(dict(subject=s,initializers=len(begin),owner=begin[0]['managed'] if begin else None,attempts_during_initializer=overlap,value=None if mode=='failed' else value))
 return dict(side=side,mode=mode,workers=n,subjects=summaries,outcomes=len(outcomes),joined=n,events=r)
