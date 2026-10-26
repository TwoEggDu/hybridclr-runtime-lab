"""Exception evidence validation; unexpected escapes remain observable failures."""
import json,re
ROUTES=('aa','hh','ha','ah');FAULTS=('body','manual','cctor','cctor-ret');VARIANTS=('baseline','counterfactual')
def parse_player(text,route,fault,variant,build_id):
 def need(ok,msg):
  if not ok:raise ValueError(msg)
 need(route in ROUTES and fault in FAULTS and variant in VARIANTS,'case identity');need('EHF_FATAL' not in text,'fatal')
 try:r=[json.loads(x[4:]) for x in text.splitlines() if x.startswith('EHF ')]
 except (TypeError,ValueError) as e:raise ValueError('bad JSON') from e
 need(bool(r),'empty evidence');need([x.get('seq') for x in r]==list(range(1,len(r)+1)),'event order')
 env=r[0];need(env.get('kind')=='env' and all(env.get(k)==v for k,v in dict(route=route,fault=fault,variant=variant,build=build_id,unity='2022.3.62f3',hot_before=False).items()),'wrong environment')
 need(r[-1].get('kind')=='done' and r[-1].get('completed') is True,'completion')
 need(sum(x['kind']=='env' for x in r)==1 and sum(x['kind']=='done' for x in r)==1,'envelope count')
 attempts=[i for i,x in enumerate(r) if x['kind']=='attempt'];need(len(attempts)==2 and [r[i].get('value') for i in attempts]==[1,2] and attempts[0]==1,'attempt count')
 caller='hot' if route[0]=='h' else 'aot';target='hot' if route[1]=='h' else 'aot';inits=[x for x in r if x['kind']=='init'];need(len(inits)==(1 if fault.startswith('cctor') else 0),'cctor count')
 if inits:need(inits[0].get('origin')==target and attempts[0]<r.index(inits[0])<attempts[1],'cctor identity/phase')
 etype='System.InvalidOperationException' if fault=='body' else 'System.TypeInitializationException';chain=etype+('>System.InvalidOperationException' if fault!='body' else '')
 out=[]
 for n,start in enumerate(attempts):
  end=attempts[n+1] if n==0 else len(r)-1;part=r[start+1:end];need(bool(part) and part[0]['kind']=='caller','caller missing')
  need(all(x.get('origin')==caller for x in part if x['kind'] in ('caller','caught','finally','after')),'caller identity')
  throws=[x for x in part if x['kind']=='throw'];need(len(throws)==(0 if fault.startswith('cctor') else 1),'throw count')
  need(all(x.get('origin')==target for x in throws),'target identity')
  core=[x['kind'] for x in part if x['kind'] not in ('throw','init')]
  handled=core==['caller','caught','finally','after','return'];escaped=core in (['caller','escape'],['caller','finally','escape'])
  need(handled or escaped,'catch/finally/return order')
  exc=[x for x in part if x['kind'] in ('caught','escape')];need(len(exc)==1 and exc[0].get('type')==etype and exc[0].get('detail')==chain,'exception identity')
  need(all(part.index(x)<part.index(exc[0]) for x in throws+[v for v in part if v['kind']=='init']),'effect after exception')
  out.append(dict(attempt=n+1,handled=handled,finally_count=sum(x['kind']=='finally' for x in part),type=exc[0]['type'],detail=exc[0]['detail']))
 classification='handled' if all(x['handled'] for x in out) else 'escaped' if not any(x['handled'] for x in out) else 'mixed'
 return dict(route=route,fault=fault,variant=variant,classification=classification,semantic_match=classification=='handled',cctor_count=len(inits),attempts=out,events=r)
def parse_context(text):
 if 'private pdb symbols' not in text or any(x in text for x in ('Syntax error',"Couldn\'t resolve",'Unable to resolve')):raise ValueError('PDB/debugger error')
 pattern=r'^EHF_VALUES imi=([0-9a-f]+) callerImi=([0-9a-f]+) activeEh=(\d+) callerEh=(\d+) offset=(-?\d+) baseMatchesCaller=([01])'
 matches=list(re.finditer(pattern,text,re.M));out=[]
 if not matches:raise ValueError('no context')
 for i,m in enumerate(matches):
  part=text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)]
  regions=[dict(begin=int(a),end=int(b)) for a,b in re.findall(r'^EHF_REGION begin=(-?\d+) end=(-?\d+)',part,re.M)]
  active,caller=int(m[1],16),int(m[2],16);ae,ce,offset=int(m[3]),int(m[4]),int(m[5])
  if not active or not caller or m[6]!='1' or ce<1 or len(regions)!=ce or any(x['end']<=x['begin'] for x in regions):raise ValueError('incomplete caller context')
  methods=re.findall(r'^EHF_METHOD name=(\w+) token=([0-9a-f]+)',part,re.M);callees=re.findall(r'^EHF_CALLEE ready=([01]) activeMatches=([01])',part,re.M)
  if len(methods)!=1 or methods[0][0]!='RunOwn' or int(methods[0][1],16)>>24!=6 or len(callees)!=1 or callees[0][0]!='1':raise ValueError('Native method/callee identity')
  mismatch=active!=caller
  if (active==caller and ae!=ce) or (callees[0][1]=='1')!=mismatch:raise ValueError('Inconsistent active/caller/callee state')
  out.append(dict(method='RunOwn',method_token=int(methods[0][1],16),callee_cache_ready=True,active_matches_callee=callees[0][1]=='1',mismatch=active!=caller,active_eh=ae,caller_eh=ce,offset=offset,ip_base_matches_caller=True,regions=regions,inside_caller_region=any(x['begin']<=offset<x['end'] for x in regions)))
 return out

def compare_runs(a,b):
 expected=[(r,f,n) for r in ROUTES for f in FAULTS for n in (1,2,3)]
 for v,rows in [('baseline',a),('counterfactual',b)]:
  if [(x['route'],x['fault'],x['run']) for x in rows]!=expected:raise ValueError('Comparison matrix')
  for row in rows:
   escape=v=='baseline' and row['route']=='hh' and row['fault']=='cctor-ret';o=row['observations'];want='escaped' if escape else 'handled'
   if o['classification']!=want or any(x['finally_count']!=(0 if escape else 1) for x in o['attempts']):raise ValueError('Unexpected control outcome; causal result inconclusive')
 return dict(normal_processes=96,baseline_handled=45,baseline_escaped=3,counterfactual_handled=48,affected_route='hh/cctor-ret',unaffected_controls_preserved=True)
