using System;
using Cysharp.Threading.Tasks;
namespace SAMPLE_NS {
 public static class Cases {
  public static async UniTask<int> Work(string mode){
   AsyncEvents.Log("enter","SAMPLE_SIDE");
   try{
    if(mode=="throw-before")throw new InvalidOperationException("before-await");
    AsyncEvents.Log("before_await");
    int value;
    if(mode=="sync")value=await UniTask.FromResult(7);
    else{
     value=await AsyncEvents.Gate.Task;AsyncEvents.Log("gate_resume");
     AsyncEvents.Log("nextframe_wait");await UniTask.NextFrame();
    }
    AsyncEvents.Log("resumed");
    if(mode=="throw-after")throw new InvalidOperationException("after-await");
    return value+35;
   }finally{AsyncEvents.Log("work_finally");}
  }
 }
}
