# 原生回调下的 GC 保留与有界压力

2026-10-25。build_id `148235df-910b-441f-94b2-b7348eb02d8c`。基于已发布 b9156325820312f4d290c4af8158f76a3a6f9beb 的后续扩展，新增样本与本记录保存在同一Git提交中，不属于旧提交。完整环境、源码、产物、工具、日志指纹与运行记录见 [results.json](results.json)。

## 环境与复现

环境锁不变：本机自定义 Unity `2022.3.62f3_96770f904ca7`，package v9.0.3 / runtime v9.0.1 / 配套 il2cpp_plus v2022.3.x-9.0.1，Windows x64 IL2CPP Development、C++ Debug、Minimal stripping。GCMode=Enabled、isIncremental=True。自有插件以 MSVC 14.51.36231 /Od /Zi /MD 编译，没有改 Editor 安装或第三方实现。

```powershell
python tools/gc_callback_lab.py build --editor $editor
python tools/gc_callback_lab.py run
python tools/gc_callback_lab.py trace --cdb $cdb
python tools/gc_callback_lab.py verify
python -B -m unittest discover -s tests
dotnet run --project tests/GcCallbackChecks -c Release --artifacts-path artifacts/dotnet-gc-checks
```

新项目 projects/gc-callbacks、自有 native/gc-callbacks/plugin.cpp、输出 artifacts/gc-callbacks 均与前序实验隔离。首次编译成功但 Unity 修改了项目设置并生成 AOTGenericReferences，指纹门禁拒绝验收；固定输入后重建。审查发现的对象图检查和记录顺序缺口修复后重新构建，再加入负载窗口的 GC 计数形成最终构建。中间观察保留在本地 initial-observations，不能作为最终构建的验收日志。

## 三个独立对照

静态回调 ABI 为 cdecl int(IntPtr,int,int)，native 仅保存 opaque GCHandle token，不保存托管对象地址。AOT 持有回调委托；回调工作仅涉及框架与自有数据。

| 模式 | 持有关系与操作 | 三个独立 Player 的结果 |
|---|---|---|
| handle | 短寿命托管线程创建热更 Context，Normal GCHandle 保留；native 两次回调，第二次停在关卡中收集三次 | 返回74/75，checksum149；开始前、回调中、Join后未Free时均存活，Free后弱引用失效 |
| stack | 不创建 Context 句柄；热更回调只以局部变量持有 Node，AOT 仅保存短弱引用；等待期间收集三次，放行后检查256字节内容并KeepAlive | 一次回调返回257；等待时存活，返回并Join后弱引用失效 |
| stress | Normal句柄持有Context；1024回调，每次分配32个Node，各256字节payload，并更新64槽对象图/Head/Next | count1024、checksum786944、errors0；32个检查点均存活，退出Free后弱引用失效 |

三个模式各启动三个新进程，共九个无调试器 Player，退出码均0。释放后按三轮显式收集观察弱引用；本次九轮均失效，但验收器允许释放后暂时存活并如实记录，不把立即归零当成运行时保证。

stress 的payload总量为8,388,608字节，不含对象头、数组头、上下文、生成物、互操作等分配。稳定对象图为64个槽：验证每个槽按当前序号应有的对象Id、payload、Head对象身份、最新Head.Next以及其他Next清空。只检查非空对象内容不能发现丢引用，因此补了四项直接编译实际热更源码的破坏测试：丢槽、陈旧Id、断Next、错误Head；旧校验0/4失败，修复4/4通过。这是桌面算法验证，不代替Player或GC验证。

## 收集请求与计数

stress 每32次回调停在检查点，主线程调用4次 CollectIncremental(1,000,000 ns)，跨帧放行后继续修改引用；共32检查点、128请求。负载期间没有调用显式 Full。每轮128次均返回false，GC.CollectionCount(0)在负载开始到Join后采样的差值均为256。开始前的持有检查、Join后的持有/释放检查所用显式收集不计入该窗口。

false 表示调用返回时没有剩余工作；它不能被读成“没有发生GC”。计数是整个进程在该窗口的API观察，包含Unity自动收集与显式增量请求影响，不能把256分摊为某个API的固定次数，也不解释为256次完整full GC。这批数据没有直接展示跨多帧仍在进行的同一标记周期，也不证明全部写屏障路径正确。

handle/stack 的回调活跃窗口分别记录GC计数差3，与三次显式收集对照。所有模式都在最后一个回调关卡请求stop，Join(0)必须未完成；放行后线程退出、Join成功，才Free Context句柄/释放委托，没有额外回调。失败时先请求停止并放行、等待，等待失败则保留根引用直到进程终止。

## 聚焦原生证据

handle/stack 各另开一个 CDB 进程，匹配 GameAssembly 与NativeProbe private PDB。验收关联实际wrapper地址、传入token、callback seq/mode、原生线程、Call方法身份、Attach/Detach、状态/根和FreeContext。插件调用栈确实进入动态加载的热更Call，而非AOT替代。

| 观察 | handle | stack |
|---|---:|---:|
| 目标OS线程 | 154732 | 100240 |
| 回调数 | 2 | 1 |
| Attach入口 | 2 | 1 |
| Detach重载入口 | 4 | 2 |
| 状态/根清理链 | 2 | 1 |
| 回调活跃、根注册后、scope退出前的Full入口 | 3 | 3 |
| Join后FreeContext入口 | 1 | 0 |

Detach入口数来自每条链的两个重载。stack的token为0且没有FreeContext入口；它不借Normal句柄保留目标。这里支持“活跃回调的本样本引用跨收集可用”，没有采集根快照、GetGCRootData实际范围或证明唯一根来源。清理断点是函数入口/顺序，不是native释放字节数。

[handle-native-events.txt](handle-native-events.txt)、[stack-native-events.txt](stack-native-events.txt)仅含自定义事件。完整调试日志、受限实现、Player和PDB留在本地忽略目录。stress没有逐次native断点跟踪，不把聚焦trace当成1024次压力运行的调用链证据。

## 验收边界

31项Python测试通过；实际热更源码四项桌面破坏测试通过。原始构建/运行/trace回执与最终摘要互相校验，源码和产物未混用。独立审查发现并修复了对象图身份/链关系与早期检查点可越出生命周期、显式收集计数过低仍能通过的缺口。

本轮不包含GC性能/帧耗时、堆容量/RSS、根快照、唯一根归因、写屏障完整性、长期泄漏、多个原生线程竞争、异常注入、强杀、真实SDK或其他平台验收。
