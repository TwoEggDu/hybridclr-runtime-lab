# GC 对象快照与解释器活跃根区间

2026-10-25，独立 gc-roots 工程，build_id `993e5b9e-1f71-4949-b339-39ff10d359b1`。沿用已发布449a994的环境锁及自有原生插件；449a994不包含本轮新增项目和证据，本轮样本与本记录位于同一Git提交，固定源码和证据一起发布。

## 环境与采证分层

本机自定义 Unity `2022.3.62f3_96770f904ca7`，package9.0.3 / runtime9.0.1 / il2cpp_plus2022.3.x-9.0.1，Windows x64 IL2CPP Development、C++ Debug、Minimal stripping，增量GC启用。HotUpdate.dll动态加载且未进入AOT。完整版本、源码和产物指纹见 results.json。

- 9个无快照、无调试器Player：handle/stack/idle各3次，均退出0。
- 6个独立快照Player：handle/stack各3次，均退出0；生成21份真实.snap，CaptureFlags.ManagedObjects=1。
- 9个独立CDB Player：handle/stack/idle各3次，均退出0，匹配GameAssembly及NativeProbe private PDB；没有在这些进程中拍快照。
- 1个独立Editor分析进程用未修改的官方Memory Profiler1.1.0读取21份快照，189组条目的数量和拼接内容SHA256与自有读取器全部一致。

## 实际返回区间

CDB在GetGCRootData入口和真实返回指令处成对记录，读取ABI结果缓冲；不是仅把stackTop公式代入。入口调用栈包含GC_push_roots。当前Debug产物经PDB/反汇编确认：StackObject8字节，字段偏移base0、capacity8、top12、frames32，返回指令偏移0xa9。脚本仅适用该版本/配置；其他产物必须重新核验ABI与返回点。

| 对照 | 三次进程各自的3个GC回调样本 | 目标引用偏移 |
|---|---|---|
| handle | frameTop1，top36，返回base等于分配base，length288 | 每次24字节 |
| stack，无Context句柄 | frameTop1，top36，返回base等于分配base，length288 | 每次48、264字节 |
| idle，解释方法已返回但托管线程仍等待 | backing base仍非空，capacity131072槽，frameTop0/top0，实际返回null/0 | 不报告槽位 |

每组9个样本，一共27个返回；分配容量各为131072槽（1 MiB），活跃返回288字节，空闲返回0。动态根注册、实际回调、根注销完整匹配，读取发生在注销前。区间所有8字节槽位逐项记录并验证连续、无遗漏、无越界，目标地址来自自有GcState.Track的参数，保存在调试器伪寄存器，不向Player新增Normal/Pinned句柄。三次stack均仍返回257并完成payload检查；idle弱引用均在本次收集窗口失效，但不把弱引用立即失效当作通用GC时限保证。

这说明目标引用确实出现在收集器查询到的活跃区间中；不是唯一根归因、逐字标记访问记录，也不证明allocated capacity整段都被扫描。进程地址不跨运行比较。

## 对象快照与可见引用路径

官方读取器来自Unity registry的com.unity.memoryprofiler1.1.0，归档SHA256 `c01e96c3da508dc1d37591f0ce47db82dbc316c99154d52d0f114d81cd83b270`；仅用于独立分析工程，不加入Player依赖。快照format16、指针8、对象头16、数组头32字节。

handle每个进程四阶段：before-native、active、joined-held、released。前三阶段的GCHandles_Target各有同一GcHot.Context目标，Tag73、Head为null；通过快照字段描述中的Slots偏移24，解析到GcHot.Node[]、length64、所有元素null。Free后GcHot强句柄目标数0；正常运行日志中弱引用也在观察窗口失效。这是“强句柄目标→Context→Slots数组”的快照路径，未用堆中残留字节推断对象活着。

stack每个进程三阶段：before-native、active、released。三阶段均无GcHot强句柄目标；active期间局部Node跨收集仍校验成功。所有21份快照ManagedStacks条目数0。该快照与自有解码范围没有提供解释器动态根边，因此不把强句柄表中没有Node误写成Node无根/已回收，也不宣称Memory Profiler可完整显示HybridCLR根路径。

快照前后不能与另一个CDB进程拼成同一瞬间；采集可能触发收集并改变时序，结果分开保存。

## 复现与验收

```powershell
python tools/gc_roots_lab.py build --editor $editor
python tools/gc_roots_lab.py run
python tools/gc_roots_lab.py inspect --cdb $cdb
python tools/gc_roots_lab.py trace --cdb $cdb
python tools/check_snapshots_unity.py --editor $editor
python tools/gc_roots_lab.py verify
python -B -m unittest discover -s tests
python -B tools/check_repo.py
```

固定上游源码仍通过tools/prepare.py准备。所有Player、PDB、21份.snap、官方分析工程、原始调用栈/日志在忽略目录artifacts/gc-roots与.local；公开仅自有样本、命令、事件和结构化结果，不复制第三方C++实现或原始内存。57项Python测试通过，包含缺失返回、错区间/结果缓冲、越界/漏槽、注销后读取、注销所有者不符、图身份/长度、快照签名/截断/目录越界及紧凑表头计数负例。

初次旧命名空间编译失败、初始快照计数解码及Mono反射参数试验分别保留本地，均非最终验收记录。最终来源/产物哈希和运行证据一致；读取器改进只重算派生摘要，原始日志/快照未改写。

## 仍未覆盖

唯一根证明、全对象图可达性分析、native释放字节/RSS、持续跨增量片段引用修改、写屏障完整性、性能/长期泄漏、多个原生线程竞争、异常注入及其他平台。结论只绑定这份自定义Editor、配套版本和本样本。

最终独立复核：实际15次根注销线程均与登记所有者一致；补充错误所有者负例后先观察到失败，再加入验收条件，57项测试通过。正文复现流程补齐inspect。复核无剩余阻断项。
