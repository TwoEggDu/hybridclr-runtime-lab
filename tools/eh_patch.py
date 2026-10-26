"""One public HybridCLR macro counterfactual; never patches the shared runtime."""
def patched_source(text):
 head='#define PREPARE_NEW_FRAME_FROM_INTERPRETER';tail='#define LEAVE_FRAME'
 if text.count(head)!=1 or text.count(tail)!=1:raise ValueError('Unexpected public runtime source')
 a=text.index(head);b=text.index(tail,a);lines=text[a:b].splitlines(keepends=True)
 assign=[i for i,x in enumerate(lines) if 'imi = newMethodInfo->interpData ?' in x]
 init=[i for i,x in enumerate(lines) if 'RuntimeInitClassCCtorWithoutInitClass(newMethodInfo);' in x]
 if len(assign)!=1 or len(init)!=1 or init[0]!=assign[0]+1:raise ValueError('Macro differs/already patched')
 lines[assign[0]]=lines[assign[0]].replace('imi = newMethodInfo->interpData','auto nextImi = newMethodInfo->interpData')
 ending=chr(13)+chr(10) if lines[init[0]].endswith(chr(13)+chr(10)) else chr(10)
 lines.insert(init[0]+1,'        imi = nextImi; '+chr(92)+ending)
 return text[:a]+''.join(lines)+text[b:]
