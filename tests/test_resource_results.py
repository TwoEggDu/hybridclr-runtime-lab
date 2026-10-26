import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from resource_results import parse_player
BUILD="test-build"
def events(mode="bundle"):
 restored=mode in ("code","bundle")
 rows=[dict(event="env",mode=mode,build=BUILD,hot_before=False,registration=mode!="unregistered")]
 if mode!="late":rows.extend([dict(event="stage",stage="Assembly.Load"),dict(event="dll",name="HotUpdate"),dict(event="ping",value="resource-hot-v1")])
 if mode!="code":
  for stage in (["Resources.Load"] if mode=="resources" else ["AssetBundle.LoadFromFile","AssetBundle.LoadAsset"]):rows.append(dict(event="stage",stage=stage))
  rows.append(dict(event="asset",value="MainPackageProbe" if mode=="resources" else "BundleProbe",stage="Resources.Load" if mode=="resources" else "AssetBundle.LoadAsset",typed=1 if restored else 0,missing=0 if restored else 1,restored=restored))
  rows.append(dict(event="stage",stage="Instantiate"))
 rows.append(dict(event="instantiate",value="ResourceInstance"))
 if restored:
  values=dict(instance=123,number=7 if mode=="code" else 42,label="code-runtime" if mode=="code" else "resource-prefab-v1",anchor="Anchor",payload="resource-payload-v1",type="ResourceHot.MountProbe",assembly="HotUpdate",anchor_matches=True,payload_name="Payload")
  rows.append(dict(event="snapshot",**values));rows.extend(dict(event="life",name=name,**values) for name in ("Awake","OnEnable","Start","OnDisable","OnDestroy"))
 rows += [dict(event="result",restored=restored,typed=1 if restored else 0,missing=0 if restored else 1,hot_loaded=mode!="late"),dict(event="done",completed=True)]
 return rows

def text(rows):return "\n".join("RMP "+json.dumps(row) for row in rows)
class ResourceResultsTests(unittest.TestCase):
 def test_bundle_restores_serialized_values_and_lifecycle(self):self.assertTrue(parse_player(text(events()),"bundle",BUILD)["restored"])
 def test_code_baseline(self):self.assertTrue(parse_player(text(events("code")),"code",BUILD)["restored"])
 def test_late_dll_control(self):self.assertFalse(parse_player(text(events("late")),"late",BUILD)["restored"])
 def test_unregistered_control_keeps_code_type_loadable(self):self.assertFalse(parse_player(text(events("unregistered")),"unregistered",BUILD)["restored"])
 def reject(self,rows,mode="bundle",build=BUILD):
  with self.assertRaises(ValueError):parse_player(text(rows),mode,build)
 def test_missing_asset_checkpoint(self):self.reject([r for r in events() if r["event"]!="asset"])
 def test_missing_instantiate_checkpoint(self):self.reject([r for r in events() if r["event"]!="instantiate"])
 def test_wrong_anchor_identity(self):r=events();next(x for x in r if x["event"]=="snapshot")["anchor_matches"]=False;self.reject(r)
 def test_main_package_prefab_has_distinct_asset_identity(self):self.assertFalse(parse_player(text(events("resources")),"resources",BUILD)["restored"])
 def test_wrong_build(self):self.reject(events(),build="other")
 def test_wrong_mode(self):self.reject(events(),mode="code")
 def test_preloaded_hot_assembly_rejected(self):r=events();r[0]["hot_before"]=True;self.reject(r)
 def test_wrong_serialized_value(self):r=events();next(x for x in r if x["event"]=="snapshot")["number"]=11;self.reject(r)
 def test_missing_reference(self):r=events();next(x for x in r if x["event"]=="snapshot")["anchor"]="";self.reject(r)
 def test_wrong_assembly(self):r=events();next(x for x in r if x["event"]=="snapshot")["assembly"]="Probe.AOT";self.reject(r)
 def test_lifecycle_order(self):r=events();a=next(i for i,x in enumerate(r) if x.get("name")=="Awake");r[a],r[a+1]=r[a+1],r[a];self.reject(r)
 def test_identity_changes(self):r=events();next(x for x in r if x.get("name")=="OnDestroy")["instance"]=999;self.reject(r)
 def test_missing_completion(self):self.reject(events()[:-1])
 def test_duplicate_completion(self):r=events();r.append(r[-1]);self.reject(r)
 def test_unexpected_exception(self):
  with self.assertRaises(ValueError):parse_player(text(events())+"\nException: unexpected","bundle",BUILD)
 def test_negative_outcome_is_observation_not_forced_failure(self):
  r=events("bundle");r[0]["mode"]="unregistered";r[0]["registration"]=False
  self.assertTrue(parse_player(text(r),"unregistered",BUILD)["restored"])
 def test_missing_all_stages_rejected(self):self.reject([r for r in events() if r['event']!='stage'])
 def test_duplicate_stage_rejected(self):r=events();r.insert(1,r[1]);self.reject(r)
 def test_dll_and_ping_after_result_rejected(self):
  r=events();moved=[x for x in r if x['event'] in ('dll','ping')];r=[x for x in r if x['event'] not in ('dll','ping')];r[-1:-1]=moved;self.reject(r)
 def test_snapshot_before_instantiate_rejected(self):
  r=events();a=next(i for i,x in enumerate(r) if x['event']=='snapshot');b=next(i for i,x in enumerate(r) if x['event']=='instantiate');r[a],r[b]=r[b],r[a];self.reject(r)
 def test_asset_boolean_count_contradiction_rejected(self):r=events();next(x for x in r if x['event']=='asset')['restored']=False;self.reject(r)
 def test_positive_requires_restoration_at_asset_stage(self):r=events();next(x for x in r if x['event']=='asset').update(typed=0,missing=1,restored=False);self.reject(r)
 def test_asset_count_bool_rejected(self):r=events();next(x for x in r if x['event']=='asset')['typed']=True;self.reject(r)
 def test_negative_missing_count_must_be_integer(self):r=events('late');next(x for x in r if x['event']=='result')['missing']='1';self.reject(r,mode='late')
 def test_negative_missing_count_is_required(self):r=events('late');del next(x for x in r if x['event']=='result')['missing'];self.reject(r,mode='late')
 def test_negative_zero_missing_slot_requires_investigation(self):
  r=events('late');next(x for x in r if x['event']=='result')['missing']=0
  self.assertEqual(parse_player(text(r),'late',BUILD)['classification'],'needs_investigation')
 def test_negative_stage_transition_requires_investigation(self):
  r=events();r[0].update(mode='unregistered',registration=False);next(x for x in r if x['event']=='asset').update(typed=0,missing=1,restored=False)
  value=parse_player(text(r),'unregistered',BUILD);self.assertTrue(value['restored']);self.assertFalse(value['asset_restored']);self.assertEqual(value['classification'],'needs_investigation')
 def test_unexpected_negative_success_remains_observable(self):
  r=events();r[0].update(mode='unregistered',registration=False)
  self.assertEqual(parse_player(text(r),'unregistered',BUILD)['classification'],'restored_unexpectedly')
 def test_unknown_rmp_event_rejected(self):r=events();r.insert(1,dict(event='unknown'));self.reject(r)
if __name__=="__main__":unittest.main()
