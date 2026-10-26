"""Self-authored read-only debugger script for the locked x64 Debug GC layout.
No target function calls, runtime patches, or added managed handles.
WBI_NATIVE_RETURN names the marker4 writer tail BEFORE KeepAlive/return;
marker6/PARK is after the writer actually returned.
"""
def quote(s):return '"'+s.replace('\\','\\\\').replace('"','\\"')+'"'
def bp(symbol,command):return 'bu '+symbol+' '+quote(command)+'\n'
def mark(address,out):
 return '; '.join([f'r @$t9=({address} >> 0n22)',
  'r @$t10=poi(GameAssembly!GC_arrays+0x29e2e0+((@$t9 & 0x7ff)*8))',
  '.for (r @$t11=0; (poi(@$t10+0x2010)!=@$t9) & (@$t10!=poi(GameAssembly!GC_arrays+0xa8)) & (@$t11<64); r @$t11=@$t11+1) {r @$t10=poi(@$t10+0x2018)}',
  f'r @$t10=poi(@$t10+((({address} >> 0n12)&0x3ff)*8))',
  f'.if (@$t10>0xfff) {{r @${out}=(poi(@$t10+0x40+((({address}&0xfff)>>0n10)*8)) >> ((({address}&0xfff)>>4)&0x3f)) & 1}} .else {{r @${out}=-1}}'])
def script():
 observe='bd 2; be 0 1 7 8; r @$t0=@rcx; r @$t1=@rdx; r @$t2=@r8d; r @$t3=@r9d; r @$t17=@$tid; r @$t4=1; r @$t18=1; r @$t6=0; r @$t7=0; r @$t8=0; '
 observe+='.if (@$t2==0) {r @$t5=@$t0+0x10} .elsif (@$t2==1) {r @$t5=poi(@$t0+0x18)+0x20+@$t3*8} .else {r @$t5=@$t0+0x20; r @$t6=@$t0+0x28; r @$t7=poi(@$t0+0x38)+0x20+@$t3*0x18; r @$t8=@$t7+8}; '
 observe+=mark('@$t0','t12')+'; '+mark('@$t1','t13')+'; '
 observe+='.printf "WBI_NATIVE_OBSERVE seq=%d kind=%d tid=%x owner=%p target=%p ownerMark=%I64d targetMark=%I64d gc=%I64u state=%d slotA=%p slotB=%p slotC=%p slotD=%p\\n", @$t3, @$t2, @$tid, @$t0, @$t1, @$t12, @$t13, poi(GameAssembly!GC_gc_no), dwo(GameAssembly!GC_mark_state), @$t5, @$t6, @$t7, @$t8; k 8; g'
 wanted='(@$t4==1) & (@$tid==@$t17) & ((@rcx==@$t5) | (@rcx==@$t6) | (@rcx==@$t7) | (@rcx==@$t8))'
 barrier='.if ('+wanted+') {.printf "WBI_NATIVE_BARRIER seq=%d kind=%d slot=%p value=%p gc=%I64u state=%d\\n", @$t3, @$t2, @rcx, poi(@rcx), poi(GameAssembly!GC_gc_no), dwo(GameAssembly!GC_mark_state); k 8}; g'
 dirty='.if (@$tid==@$t17) {r @$t16=0; .if ('+wanted+') {r @$t16=@rcx; r @$t14=GameAssembly!GC_arrays+0x462e0+((((@rcx>>0n12)&0x1fffff)>>6)*8); r @$t15=1<<((@rcx>>0n12)&0x3f); .printf "WBI_NATIVE_DIRTY phase=before seq=%d kind=%d slot=%p bit=%d\\n", @$t3, @$t2, @rcx, (poi(@$t14)&@$t15)!=0}}; g'
 dirty_return='.if ((@$tid==@$t17) & (@$t16!=0)) {.printf "WBI_NATIVE_DIRTY phase=after seq=%d kind=%d slot=%p bit=%d\\n", @$t3, @$t2, @$t16, (poi(@$t14)&@$t15)!=0; r @$t16=0}; g'
 marker='.if (@ecx==1) {.printf "WBI_NATIVE_BEGIN gc=%I64u state=%d\\n", poi(GameAssembly!GC_gc_no), dwo(GameAssembly!GC_mark_state)}; .if (@ecx==7) {bd 2; .printf "WBI_NATIVE_END gc=%I64u state=%d\\n", poi(GameAssembly!GC_gc_no), dwo(GameAssembly!GC_mark_state)}; .if ((@ecx==4) & (@$tid==@$t17)) {'+mark('@$t1','t13')+'; .printf "WBI_NATIVE_RETURN seq=%d target=%p mark=%I64d gc=%I64u state=%d\\n", @$t3, @$t1, @$t13, poi(GameAssembly!GC_gc_no), dwo(GameAssembly!GC_mark_state); r @$t4=0; bd 0 1 7 8; be 2}; '
 marker+='.if ((@ecx==6) & (@$tid==@$t17)) {r @$t19=0; .for (r @$t9=@rsp; @$t9<poi(@$teb+8); r @$t9=@$t9+8) {.if (poi(@$t9)==@$t1) {r @$t19=@$t19+1}}; .printf "WBI_NATIVE_PARK seq=%d tid=%x stackHits=%I64u gc=%I64u state=%d\\n", @$t3, @$tid, @$t19, poi(GameAssembly!GC_gc_no), dwo(GameAssembly!GC_mark_state)}; .if (@ecx==5) {r @$t18=0}; g'
 rescan='.if (@$t18==1) {.if ((@rcx==(@$t0 & 0xfffffffffffff000)) | (@rcx==(poi(@$t0+0x18)&0xfffffffffffff000)) | (@rcx==(poi(@$t0+0x38)&0xfffffffffffff000))) {.printf "WBI_NATIVE_RESCAN seq=%d block=%p gc=%I64u state=%d\\n", @$t3, @rcx, poi(GameAssembly!GC_gc_no), dwo(GameAssembly!GC_mark_state); k 5}}; g'
 final='r @$t4=0; .for (r @$t3=1; @$t3<=0n12; r @$t3=@$t3+1) {.if (((@$t3-1)%3)==0) {r @$t1=poi(poi(@$t0+0x38)+0x20+(@$t3+2)*0x18+8)} .elsif (((@$t3-1)%3)==1) {r @$t1=poi(poi(@$t0+0x18)+0x20+@$t3*8)} .else {r @$t1=poi(poi(@$t0+0x38)+0x20+@$t3*0x18)}; '+mark('@$t1','t13')+'; .printf "WBI_NATIVE_FINAL seq=%d target=%p mark=%I64d gc=%I64u state=%d\\n", @$t3, @$t1, @$t13, poi(GameAssembly!GC_gc_no), dwo(GameAssembly!GC_mark_state)}; g'
 result='r @$t0=0; r @$t4=0; r @$t16=0; r @$t17=0; r @$t18=0\n'
 
 result+=bp('GameAssembly!GC_dirty_inner',dirty)+bp('GameAssembly!GC_dirty_inner+0x5e',dirty_return)
 result+=bp('GameAssembly!GC_push_marked',rescan)+bp('NativeProbe!WB_Marker',marker)
 result+=bp('GameAssembly!il2cpp::gc::GarbageCollector::RegisterDynamicRoot','.printf "WBI_ROOT_ADD tid=%x root=%p\\n", @$tid, @rcx; g')
 result+=bp('GameAssembly!il2cpp::gc::GarbageCollector::UnregisterDynamicRoot','.printf "WBI_ROOT_REMOVE tid=%x root=%p\\n", @$tid, @rcx; g')
 result+=bp('GameAssembly!hybridclr::interpreter::MachineState::GetGCRootData','.printf "WBI_ROOT_QUERY tid=%x root=%p top=%d frames=%d\\n", @$tid, @rdx, dwo(@rdx+0xc), dwo(@rdx+0x20); g')
 module='bm GameAssembly!*SetWriteBarrier* '+quote(barrier)+'; bm GameAssembly!WbState_Observe* '+quote(observe)+'; bm GameAssembly!WbState_CheckGraph* '+quote(final)+'; lmv m GameAssembly; dt GameAssembly!WbBox_tA67C51756C9115AA9F05267920AC4A268D1CDA6E; dt GameAssembly!WbPair_tFF6CF314A2EB0B6B20F8EA62B37615C8E8AB9A0D; dt GameAssembly!_GC_arrays _dirty_pages _grungy_pages _top_index _all_nils; dt GameAssembly!hdr hb_marks; uf GameAssembly!GC_dirty_inner; bd 0 1 2 7 8; g'
 result+='sxe -c '+quote(module)+' ld:GameAssembly.dll\ng\n'
 return result
