"""Strict parsing of experiment records; released survivors remain observations."""
import re

def header(text,mode):
 env=re.findall(r"^LIFE_ENV mode=(\w+) unity=(\S+) incremental=(\w+) gcMode=(\w+)\s*$",text,re.M)
 load=re.findall(r"^LIFE_LOAD bytes=(\d+) assembly=(\S+)\s*$",text,re.M)
 if env!=[(mode,"2022.3.62f3","True","Enabled")] or len(load)!=1 or int(load[0][0])<=0 or load[0][1]!="HotUpdate":raise ValueError("Missing or mismatched environment/load record")
 return dict(mode=mode,unity=env[0][1],incremental=True,gcMode="Enabled",assembly="HotUpdate",bytes=int(load[0][0]))

def parse_gc(text):
 env=header(text,"gc")
 rows=re.findall(r"^LIFE_GC stage=([a-z-]+) none=(\d+) static=(\d+) event=(\d+) rounds=(\d+)\s*$",text,re.M)
 if [r[0] for r in rows]!=["held","static-cleared","all-cleared"] or text.count("LIFE_DONE mode=gc failures=0")!=1:
  raise ValueError("Missing, duplicate or unordered GC records")
 result={stage:dict(zip(["none","static","event","rounds"],map(int,values))) for stage,*values in rows}
 for stage,row in result.items():
  if row["rounds"]!=3 or any(row[k]>16 for k in ["none","static","event"]): raise ValueError("GC observation outside sample")
  if stage=="held" and row["static"]!=16 or stage!="all-cleared" and row["event"]!=16: raise ValueError("Live strong control was lost")
 result["environment"]=env
 return result

def parse_threads(text):
 env=header(text,"threads")
 mains=re.findall(r"^LIFE_MAIN managed=(\d+) native=(\d+)\s*$",text,re.M)
 rows=re.findall(r"^LIFE_WORKER index=(\d+) managed=(\d+) native=(\d+) first=(-?\d+) second=(-?\d+) joined=(True|False)\s*$",text,re.M)
 if len(mains)!=1 or len(rows)!=2 or [r[0] for r in rows]!=["0","1"] or text.count("LIFE_DONE mode=threads failures=0")!=1: raise ValueError("Incomplete worker records")
 main=dict(zip(["managed","native"],map(int,mains[0])))
 workers=[]
 for index,managed,native,first,second,joined in rows:
  if (first,second,joined)!=("5","15","True"): raise ValueError("Worker call or join failed")
  workers.append(dict(index=int(index),managed=int(managed),native=int(native),first=int(first),second=int(second),joined=True))
 for key in ["managed","native"]:
  ids=[main[key]]+[w[key] for w in workers]
  if len(set(ids))!=3 or min(ids)<=0: raise ValueError("Worker identities are not distinct")
 return dict(environment=env,main=main,workers=workers)


def parse_native(text,player):
 if "private pdb symbols" not in text:raise ValueError("Private symbols missing")
 records=list(re.finditer(r"^LIFE_NATIVE_(\w+) tid=([0-9a-f]+)([^\r\n]*)$",text,re.M|re.I))
 events=[]
 for i,m in enumerate(records):
  detail=text[m.end():records[i+1].start() if i+1<len(records) else len(text)]
  fields=dict(re.findall(r"(\w+)=([^ ]+)",m[3]))
  events.append(dict(kind=m[1],tid=int(m[2],16),fields=fields,detail=detail,pos=m.start()))
 execute=[e for e in events if e["kind"]=="EXECUTE"]
 transform=[e for e in events if e["kind"]=="TRANSFORM"]
 if len(execute)!=4 or len(transform)!=1:raise ValueError("Expected four Execute and one Transform")
 methods={e["fields"].get("method") for e in execute+transform}
 if len(methods)!=1 or not next(iter(methods),None) or int(next(iter(methods)),16)==0:raise ValueError("Method identity mismatch")
 caches=[]
 for e in execute+transform:
  if not re.search(r'name\s*:\s*0x[0-9a-f`]+\s+"Add"',e["detail"],re.I):raise ValueError("Unexpected method name")
 for e in execute:
  cache=re.search(r"interpData\s*:\s*0x([0-9a-f`]+)",e["detail"],re.I)
  if cache is None or "GameAssembly!hybridclr::interpreter::InterpreterInvoke" not in e["detail"]:raise ValueError("Cache or invoker stack missing")
  caches.append(int(cache[1].replace("`",""),16))
 if len(set(caches))!=1 or caches[0]==0:raise ValueError("Cache identity mismatch")
 workers=player["workers"]
 expected=[(w["native"],a) for w in workers for a in ("2,3","7,8")]
 if [(e["tid"],e["fields"].get("args")) for e in execute]!=expected:raise ValueError("Worker calls mismatch")
 if transform[0]["tid"]!=workers[0]["native"] or transform[0]["pos"]>=execute[0]["pos"]:raise ValueError("Conversion ordering mismatch")
 states=[];created=[];destroyed=[];result=[]
 for worker in workers:
  tid=worker["native"];own=[e for e in events if e["tid"]==tid]
  lifecycle={}
  for kind in ("CREATE","ROOT_ADD","FREE","DESTROY","ROOT_REMOVE"):
   matches=[e for e in own if e["kind"]==kind]
   if len(matches)!=1:raise ValueError("Missing or duplicate worker lifecycle: "+kind)
   lifecycle[kind]=matches[0]
  state=lifecycle["CREATE"]["fields"].get("state")
  if not state or int(state,16)==0 or lifecycle["DESTROY"]["fields"].get("state")!=state or any(lifecycle[k]["fields"].get("root")!=state for k in ("ROOT_ADD","ROOT_REMOVE")):raise ValueError("State/root identity mismatch")
  calls=[e for e in execute if e["tid"]==tid]
  sequence=[calls[0],lifecycle["CREATE"],lifecycle["ROOT_ADD"],calls[1],lifecycle["FREE"],lifecycle["DESTROY"],lifecycle["ROOT_REMOVE"]]
  if [e["pos"] for e in sequence]!=sorted(e["pos"] for e in sequence):raise ValueError("Lifecycle ordering mismatch")
  states.append(state);created.append(lifecycle["CREATE"]["pos"]);destroyed.append(lifecycle["DESTROY"]["pos"])
  result.append(dict(index=worker["index"],native=tid,state=state,execute_count=2,root_add=1,root_remove=1,free=1,destroy=1))
 if len(set(states))!=2 or max(created)>=min(destroyed):raise ValueError("States were not distinct and simultaneously alive")
 return dict(method=next(iter(methods)),interpData=f"{caches[0]:016x}",execute_count=4,transform_count=1,workers=result)
