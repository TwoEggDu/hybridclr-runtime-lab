# 持续跨增量片段的引用修改与写屏障

2026-10-25，独立 `projects/incremental-barriers`，build_id `70a8a176-4eee-43b2-8aa8-a75754ac0bfb`。基线4861bed仅指前轮根区间实验，不包含本次样本；本轮源码和证据随包含本记录的同一提交发布；复现时使用文章给出的本轮固定提交，不能使用前轮基线替代。

## 问题与控制变量

前轮有界压力的128次CollectIncremental均返回false，无法展示同一未完成标记周期中的持续修改。本轮让同一周期跨12个连续帧，每帧先推进片段并确认more=True，再通过事件握手让一个预热的托管worker修改引用；writer返回并清理栈后，主线程才进入下一帧。

沿用自定义Unity2022.3.62f3_96770f904ca7、package9.0.3/runtime9.0.1/il2cpp_plus2022.3.x-9.0.1，Windowsx64 IL2CPP Development、C++Debug、Minimal stripping。启用增量GC，GCMode从前轮Enabled改为Manual，属于本次控制变量。环境及所有上游SHA见[结果](results.json)。不修改Editor、运行时或旧实验源码。

持有者及两个64槽数组在基线Full前建立；之后分配25万个节点和payload作保留负载。12个候选Node由短寿命creator线程创建，只留短弱引用，creator先Join。persistent worker在线程登记及解释入口预热完成后才开始基线收集。没有Normal/Pinned句柄保留候选；writer中的临时引用在下一片段前退出。

每帧CollectIncremental预算1000ns只是请求值，不是精确的微秒耗时承诺。结束12次修改后，在主线程紧凑推进现有原生collect-a-little直到第一次无剩余工作；收尾不继续逐帧分配，也不反复请求新周期。对象图和最终标记检查发生在worker Join之前，避免注销线程可能推进额外收集。结束窗口用marker7隔离。

## 实际结果

6个无调试器Player、6个独立匹配PDB的CDB Player，两种writer各3次，全部退出0。两组加载同一HotUpdate字节，HotUpdate没有进入AOT；AOT组调用本地writer，hot组委托进入解释器。96项Python检查通过，其中39项覆盖本次验收器。

| 判据 | AOT三进程 | hot三进程 |
|---|---|---|
| 连续12帧的more与标记完成数 | 12次true，完成数保持1 | 同左 |
| 原生GC编号（仅CDB进程） | 修改窗口4，结束5 | 同左 |
| 写入前Box/当前候选标记位 | 1 / 0 | 1 / 0 |
| writer末尾marker4（返回前）的候选标记位 | 0 | 0 |
| 本周期完成、Join前12目标标记位 | 全部1 | 全部1 |
| 对象图校验 | writes12/checksum12078/alive12 | 同左 |
| SetWriteBarrier重载入口命中数 | 每进程16 | 每进程24 |
| 脏页0→1的成对观察 | 每进程2次 | 每进程2次 |
| 目标槽所在页后续重扫 | 每进程3页 | 每进程3页 |
| scrub后活跃worker栈中的当前目标精确指针 | 12次均0处 | 同左 |
| 解释器根回调入口状态 | 无 | 每进程6次top0/frames0（基线1、目标周期收尾2、周期后及退出清理3），登记与注销所有者匹配 |

写入覆盖4次标量字段、4次引用数组元素、4次含两个引用的结构体赋值；每次结构体同时写Box.Pair和Pairs[seq]。因此实际目标存储区域共16个，16/24是重载函数入口命中数，不能当成不同写入次数或成本比。hot结构体路径会经过重载嵌套；可见Interpreter::Execute，AOT可见WbState_Write及codegen helper。原始调用栈在忽略目录，公开文件只保留自有WBI事件和判据摘要。

实际DLL的CIL见[cil.txt](cil.txt)：stfld Field、stelem.ref、stfld Pair、stelem WbPair均存在。将表内token解析为名称／字符串内容后，两个Write的指令序列一致，唯一诊断字面量分别是Candidate lost before write与Candidate lost before hot write。

CDB按当前PDB校验自有类型、GC数组与块头布局及GC_dirty_inner返回偏移，再只读解码标记位和dirty bitmap；不调用GC_is_marked、不添加托管句柄。每个目标槽的屏障调用和dirty前／后成对关联，after位均1。大部分页在写入前已经dirty，只有每进程2次观测到0→1；不能写成16次都新置脏。之后的页扫描调用栈包含GC_push_next_marked_dirty。

完整对象图校验同时检查Id、32字节payload、64槽占用、Pair左右身份／Tag、最新Field和Next为空，避免存活旧节点掩盖丢更新。解除Box和负载持有后三轮Full的弱引用观察，12个进程均为0存活；这只是本次窗口，不是释放时限保证。

## 周期身份与拒绝样本

此版本的profiler START/END不覆盖每个增量周期，不能用它们编号。MARK_START可在同一周期多次出现；用启动前MARK_END基线、12次修改前后完成数不变、结束恰好+1，以及独立原生GC_gc_no的4→5互证。六个CDB进程各自同时满足Player与原生门槛；不拼接不同进程地址。

探索中拒绝了：初始化观察器缺少heap-resize回调导致崩溃；预算设置过晚／已标记负载造成全部false；每次新建writer线程使周期在写入前完成；逐帧收尾让分配跨入额外周期。修正为完整的自有profiler回调、先设预算、预热常驻worker及无逐帧分配的收尾。观察器不在GC事件回调中分配或打印，用固定65536项缓冲且拒绝溢出。所有探索日志仅留忽略目录，不计为通过进程。

调试脚本探索还校正了重载符号、MASM条件和默认十六进制位移；错误解码／布局不匹配会被验收器拒绝，不用于最终结论。

## 结论边界

这里确认同一未完成周期的持续修改、标记状态、具体屏障／脏页／重扫路径和结果完整性。Box标记为1不等于其字段已完成扫描；未禁用屏障做反事实，也未排除所有其他根，不能证明某次存活只由写屏障保证。worker栈搜索仅限当前RSP到TEB.StackBase、按8字节对齐的当前目标精确地址，不包括寄存器、内部指针、其他目标和其他线程。

目标周期收尾的两次根查询发生在解释帧返回后、worker等待阶段，另有基线1次和周期后／退出清理3次；这些入口均top0/frames0。marker4在writer内部、KeepAlive和返回之前，WBI_NATIVE_RETURN只是沿用的事件名，不能视为真实返回断点；真实返回后marker6仅检查栈与周期。本轮未再次采真实根回调返回缓冲或快照。返回区间的独立验证仍见[前轮](../2026-10-25-gc-roots/README.md)。这是托管worker上的串行实验，不是外部原生回调、多线程并发写、所有解释指令、弱引用／终结器全矩阵、长期压力、性能或其他平台验收。

## 复现与证据

从仓库根目录依次运行README中build/run/trace/verify。Python验收器保留原始事件次序，逐次核对OBSERVE→屏障→dirty前／后→末尾marker4→返回后PARK，并要求最后PARK之后、END之前才重扫。拒绝非法dirty位、false片段、周期改变、事件乱序、缺失槽位、错误Id／checksum、未置脏、缺失重扫、无效标记解码及根所有者不匹配。

[results.json](results.json)绑定环境、源文件、DLL/PDB、工具和原始日志SHA256；六份*-events.txt只含自有数值观察，不含原始Unity实现或调用栈。真实日志、PDB和产物留在artifacts/incremental-barriers。重新构建后必须重新采证，不能沿用这些地址或哈希。
