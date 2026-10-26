using UnityEngine;
namespace ResourceHot {
 public sealed class MountProbe:MonoBehaviour {
  public int Number=11;public string Label="constructor-default";public Transform Anchor;public TextAsset Payload;
  public static string Ping(){return "resource-hot-v1";}
  void Emit(string n){ResourceEvents.Life(n,this,Number,Label,Anchor,Payload);}
  void Awake(){Emit("Awake");}void OnEnable(){Emit("OnEnable");}void Start(){Emit("Start");}void OnDisable(){Emit("OnDisable");}void OnDestroy(){Emit("OnDestroy");}
 }
}
