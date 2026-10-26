"""Strict structural acceptance with relaxed beforefieldinit timing preserved."""
import json
MODES=('strict','relaxed','generic','failed','failed-outer')
SIDES=('aot','hot')
def parse_player(text,side,mode,build_id):
 def need(ok,msg):
  if not ok:raise ValueError(msg)
 need(side in SIDES and mode in MODES,'unknown case');case=mode.split('-')[0]
 need('TIP_FATAL' not in text,'fatal Player')
 try:r=[json.loads(x[4:]) for x in text.splitlines() if x.startswith('TIP ')]
 except (ValueError,TypeError) as e:raise ValueError('bad JSON') from e
 need(bool(r),'no evidence');need([x.get('seq') for x in r]==list(range(1,len(r)+1)),'sequence loss/reorder')
 need(all(x.get('kind') in {'env','stage','meta','init','method','read','caught','escaped','done'} for x in r),'unknown event')
 envs=[x for x in r if x['kind']=='env'];need(len(envs)==1,'environment count')
 env=envs[0];need(env.get('kind')=='env' and env.get('side')==side and env.get('mode')==mode and env.get('build')==build_id and env.get('hot_before') is False,'wrong environment')
 need(env.get('unity')=='2022.3.62f3','wrong Editor version')
 escaped=any(x['kind']=='escaped' for x in r)
 need(not escaped or mode=='failed','escape outside failure control')
 need(r[-1].get('kind')=='done' and r[-1].get('completed') is (not escaped),'completion missing')
 def expected(kind,**kw):return dict(kind=kind,**kw)
 subject={'strict':'Strict','relaxed':'Relaxed','generic':'Cache`1','failed':'Failed'}[case]
 skeleton=[expected('env'),*[expected('stage',phase=p) for p in ('before_load','after_load','after_resolve')],expected('meta',subject=subject,bfi=mode=='relaxed',cctor=True)]
 if mode in ('strict','relaxed'):
  skeleton += [expected('stage',phase='before_call1'),expected('method',subject='Ping',value=7),expected('read',subject='call1',value=7),expected('stage',phase='before_field'),expected('read',subject='field',value=41),expected('stage',phase='before_call2'),expected('method',subject='Ping',value=7),expected('read',subject='call2',value=7)]
 elif mode=='generic':
  for sub,v in [('int1',42),('string1',82),('int2',43),('string2',83)]:skeleton += [expected('stage',phase='before_'+sub),expected('method',subject='Next',value=v),expected('read',subject=sub,value=v)]
 else:
  if escaped:
   skeleton += [expected('stage',phase='before_call1'),expected('escaped',subject='outer_entry',type='System.Reflection.TargetInvocationException',detail='System.Reflection.TargetInvocationException>System.TypeInitializationException>System.InvalidOperationException')]
  else:
   for n in (1,2):
    outer=mode=='failed-outer';etype='System.Reflection.TargetInvocationException' if outer else 'System.TypeInitializationException';chain=('System.Reflection.TargetInvocationException>' if outer else '')+'System.TypeInitializationException>System.InvalidOperationException'
    skeleton += [expected('stage',phase='before_call'+str(n)),expected('caught',subject='call'+str(n),type=etype,detail=chain)]
 skeleton.append(expected('done'))
 actual=[x for x in r if x['kind']!='init'];need(len(actual)==len(skeleton),'event count')
 for x,y in zip(actual,skeleton):need(all(x.get(k)==v for k,v in y.items()),'event/order/value '+str(y))
 inits=[x for x in r if x['kind']=='init']
 wanted={'strict':[('Strict.field',41),('Strict.cctor',41)],'relaxed':[('Relaxed.field',41)],'generic':[('Cache<System.Int32>.field',41),('Cache<System.Int32>.cctor',41),('Cache<System.String>.field',81),('Cache<System.String>.cctor',81)],'failed':[('Failed.cctor',1)]}[case]
 need([(x.get('subject'),x.get('value')) for x in inits]==wanted,'initializer count/identity/value')
 def position(kind,key,val):return next(i for i,x in enumerate(r) if x['kind']==kind and x.get(key)==val)
 if mode=='relaxed':need(position('init','subject','Relaxed.field')<position('read','subject','field'),'initializer after field')
 else:
  groups={'strict':[('before_call1','call1',inits)],'failed':[('before_call1','outer_entry' if escaped else 'call1',inits)],'generic':[('before_int1','int1',inits[:2]),('before_string1','string1',inits[2:])]}[case]
  for before,after,group in groups:
   left=position('stage','phase',before);right=position('escaped' if escaped else 'caught' if case=='failed' else 'read','subject',after)
   need(all(left<r.index(x)<right for x in group),'initializer outside first trigger')
   if case!='failed':need(all(r.index(x)<next(i for i in range(left+1,right) if r[i]['kind']=='method') for x in group),'body before initializer')
 init_phases=[]
 for x in inits:
  earlier=[y['phase'] for y in r[:r.index(x)] if y['kind']=='stage']
  init_phases.append(dict(subject=x['subject'],value=x['value'],after_stage=earlier[-1] if earlier else 'startup',seq=x['seq']))
 return dict(side=side,mode=mode,classification='escaped_first_access' if escaped else 'completed',semantic_match=not escaped,initializers=init_phases,reads={x['subject']:x['value'] for x in r if x['kind']=='read'},exceptions=[dict(subject=x['subject'],type=x['type'],detail=x['detail']) for x in r if x['kind'] in ('caught','escaped')],events=r)
