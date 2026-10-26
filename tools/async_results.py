"""Strict own event acceptance; native evidence and runtime success remain separate."""
import json
SIDES=("aot","hot-dev","hot-release")
MODES=("sync","frame","throw-before","throw-after")
def parse_player(text,side,mode,metadata,build_id):
 def check(v,msg):
  if not v:raise ValueError(msg)
 check("AUT_FATAL" not in text and "AUT_UNOBSERVED" not in text,"Driver/unobserved failure")
 events=[json.loads(l.split("AUT ",1)[1]) for l in text.splitlines() if "AUT " in l]
 check(bool(events),"No events")
 check([e["seq"] for e in events]==list(range(1,len(events)+1)),"Sequence")
 env=events[0];check(env["kind"]=="env" and (env["side"],env["mode"],env["metadata"],env["build"])==(side,mode,metadata,build_id),"Environment identity")
 check(not env["hot_before"],"Hot code preloaded")
 check(events[-1]["kind"]=="done" and events[-1]["value"]==0,"No accepted completion")
 check(len({e["thread"] for e in events})==1,"Thread changed")
 check(all(a["frame"]<=b["frame"] for a,b in zip(events,events[1:])),"Frame reversed")
 def rows(k):return [e for e in events if e["kind"]==k]
 def one(k):
  r=rows(k);check(len(r)==1,"Expected one "+k);return r[0]
 def before(a,b):check(one(a)["seq"]<one(b)["seq"],a+" order "+b)
 mr=rows("metadata");check(len(mr)==(1 if metadata=="on" else 0),"Metadata count")
 if mr:check(mr[0]["value"]==0 and mr[0]["label"]=="UniTask" and mr[0]["detail"]=="Superset","Metadata failed")
 allowed={"env","metadata","enter","before_await","register","entry_return","consumer_begin","waiting","complete","dispatch_begin","gate_result","gate_resume","nextframe_wait","dispatch_end","resumed","work_finally","consumer_result","consumer_caught","consumer_finally","entry_error","done"}
 check(all(e["kind"] in allowed for e in events),"Unknown event")
 if rows("entry_error"):
  err=one("entry_error");check(metadata=="off" and side!="aot" and err["type"]=="System.MissingMethodException","Unexpected entry error")
  check(not rows("consumer_begin") and not rows("consumer_finally"),"Entry error reached consumer")
  return dict(classification="entry_missing_method",suspended=False,events=events)
 one("enter");one("entry_return");one("consumer_begin");one("waiting");one("consumer_finally")
 before("entry_return","consumer_begin");before("consumer_begin","consumer_finally")
 caught=rows("consumer_caught")
 if caught and caught[0]["type"]=="System.MissingMethodException":
  check(metadata=="off" and side!="aot" and not rows("consumer_result"),"Unexpected missing implementation")
  one("consumer_caught");before("consumer_caught","consumer_finally")
  return dict(classification="await_missing_method",suspended=bool(rows("register")),events=events)
 one("work_finally");before("work_finally","consumer_finally")
 if mode.startswith("throw-"):
  check(one("consumer_caught")["type"]=="System.InvalidOperationException" and not rows("consumer_result"),"Wrong exception")
  before("work_finally","consumer_caught");classification="caught"
 else:
  check(one("consumer_result")["value"]==42 and not caught,"Wrong result")
  before("work_finally","consumer_result");classification="result"
 suspended=mode in ("frame","throw-after")
 if suspended:
  chain=["enter","before_await","register","entry_return","consumer_begin","waiting","complete","dispatch_begin","gate_result","gate_resume","nextframe_wait","dispatch_end","resumed","work_finally"]
  for a,b in zip(chain,chain[1:]):before(a,b)
  check(one("entry_return")["label"]==one("waiting")["label"]=="Pending","Did not suspend")
  check(one("complete")["frame"]>one("register")["frame"] and one("resumed")["frame"]>one("gate_resume")["frame"],"Not cross frame")
 else:
  check(not any(rows(k) for k in ("register","complete","dispatch_begin","gate_result","gate_resume","nextframe_wait","dispatch_end")),"Sync unexpectedly registered")
  before("work_finally","entry_return")
  check(one("waiting")["label"]=="Succeeded","Consumer did not finish")
  if mode=="sync":one("before_await");before("before_await","resumed");before("resumed","work_finally");check(one("entry_return")["label"]=="Succeeded","Sync task status")
  else:check(not rows("resumed") and not rows("before_await") and one("entry_return")["label"]=="Faulted","Before exception shape")
 return dict(classification=classification,suspended=suspended,events=events)
