"""Validate resource evidence without forcing negative hypotheses to fail."""
import json
MODES=("code","bundle","late","unregistered","resources")
LIFECYCLE=("Awake","OnEnable","Start","OnDisable","OnDestroy")
def parse_player(text,mode,build_id):
 if mode not in MODES:raise ValueError("Unknown route")
 if "Exception:" in text or "RMP_FATAL" in text:raise ValueError("Unexpected runtime exception")
 try:rows=[json.loads(l[4:]) for l in text.splitlines() if l.startswith("RMP ")]
 except (ValueError,TypeError) as e:raise ValueError("Invalid event JSON") from e
 known={"env","stage","dll","ping","asset","instantiate","snapshot","life","result","done"}
 if any(not isinstance(r,dict) or r.get('event') not in known for r in rows):raise ValueError("Unknown protocol event")
 def one(name):
  values=[r for r in rows if r.get("event")==name]
  if len(values)!=1:raise ValueError("Missing/duplicate "+name)
  return values[0]
 def counts(row):
  typed,missing,restored=(row.get(k) for k in ('typed','missing','restored'))
  if type(typed) is not int or type(missing) is not int or type(restored) is not bool:raise ValueError("Component count types")
  if typed not in (0,1) or missing not in (0,1) or typed+missing>1 or restored!=(typed==1):raise ValueError("Component count contradiction")
 env=one("env");done=one("done");result=one("result");instance=one('instantiate');asset=None
 if not rows or rows[0]!=env or rows[-1]!=done or done.get("completed") is not True:raise ValueError("Incomplete process record")
 if env.get("mode")!=mode or env.get("build")!=build_id or env.get("hot_before") is not False:raise ValueError("Wrong process/build identity")
 if env.get("registration") is not (mode!="unregistered"):raise ValueError("Wrong assembly registration control")
 loaded=mode!="late"
 if result.get("hot_loaded") is not loaded:raise ValueError("Wrong DLL timing control")
 stages=[r for r in rows if r['event']=='stage'];expected_stages=['Assembly.Load'] if loaded else []
 if mode!='code':expected_stages+=['Resources.Load'] if mode=='resources' else ['AssetBundle.LoadFromFile','AssetBundle.LoadAsset']
 if mode!='code':expected_stages+=['Instantiate']
 if [r.get('stage') for r in stages]!=expected_stages:raise ValueError("Required stage sequence/count")
 stage={r['stage']:r for r in stages};ordered=[env]
 if loaded:
  dll,ping=one('dll'),one('ping')
  if dll.get("name")!="HotUpdate" or ping.get("value")!="resource-hot-v1":raise ValueError("Hot code baseline failed")
  ordered.extend([stage['Assembly.Load'],dll,ping])
 elif any(r['event'] in ('dll','ping') for r in rows):raise ValueError("Late control loaded DLL")
 if mode!='code':
  asset=one('asset');counts(asset)
  if asset.get('value')!=('MainPackageProbe' if mode=='resources' else 'BundleProbe') or asset.get('stage')!=('Resources.Load' if mode=='resources' else 'AssetBundle.LoadAsset'):raise ValueError("Resource load checkpoint")
  ordered.extend([stage[n] for n in (['Resources.Load'] if mode=='resources' else ['AssetBundle.LoadFromFile','AssetBundle.LoadAsset'])])
  ordered.extend([asset,stage['Instantiate']])
  if mode=='bundle' and not asset['restored']:raise ValueError("Positive asset stage did not restore component")
 elif any(r['event']=='asset' for r in rows):raise ValueError("Code baseline unexpectedly used resource asset")
 if instance.get('value')!='ResourceInstance':raise ValueError("Instance checkpoint")
 ordered.append(instance);counts(result);restored=result['restored']
 if mode in ('code','bundle') and not restored:raise ValueError("Positive route missing component")
 lives=[r for r in rows if r['event']=='life']
 if restored:
  snap=one('snapshot')
  if snap.get('anchor_matches') is not True or snap.get('payload_name')!='Payload':raise ValueError("Serialized reference identity")
  expected={'number':7 if mode=='code' else 42,'label':'code-runtime' if mode=='code' else 'resource-prefab-v1','anchor':'Anchor','payload':'resource-payload-v1','type':'ResourceHot.MountProbe','assembly':'HotUpdate'}
  if type(snap.get('instance')) is not int or snap['instance']==0:raise ValueError("Invalid instance identity")
  for row in [snap]+lives:
   if any(row.get(k)!=v for k,v in expected.items()) or row.get('instance')!=snap['instance']:raise ValueError("Serialized state/reference/identity mismatch")
  if [r.get('name') for r in lives]!=list(LIFECYCLE):raise ValueError("Lifecycle order/count")
  ordered.extend([snap]+lives)
 elif lives or any(r['event']=='snapshot' for r in rows):raise ValueError("Missing component unexpectedly executed")
 ordered.extend([result,done]);positions=[rows.index(r) for r in ordered]
 if any(a>=b for a,b in zip(positions,positions[1:])):raise ValueError("DLL/resource/instance/lifecycle ordering")
 if mode in ('code','bundle'):classification='restored'
 elif asset['restored'] and restored:classification='restored_unexpectedly'
 elif asset['typed']==0 and asset['missing']==1 and result['typed']==0 and result['missing']==1:classification='missing_at_asset_and_instance'
 else:classification='needs_investigation'
 return {'mode':mode,'restored':restored,'typed':result['typed'],'missing':result['missing'],'asset_restored':asset['restored'] if asset else None,'asset_typed':asset['typed'] if asset else None,'asset_missing':asset['missing'] if asset else None,'classification':classification,'hot_loaded':loaded,'registration':env['registration'],'lifecycle':[r['name'] for r in lives],'events':rows}
