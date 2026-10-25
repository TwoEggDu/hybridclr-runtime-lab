# 对象保留与释放、托管工作线程：实测记录

2026-10-25。构建 `70021d1d-8d18-4bdf-8066-446dd9898b80`。环境沿用根目录 lab-lock.json：本机自定义 Unity `2022.3.62f3_96770f904ca7`，package v9.0.3 / runtime v9.0.1 / il2cpp_plus v2022.3.x-9.0.1，Windows x64、IL2CPP Development、C++ Debug、Minimal stripping。不能据此宣称任意官方 Editor 或其他平台兼容。

本轮以已发布 `e0220099d293f7a1a4601ee9931b49a10dd519f9` 为起点；新增样本与本记录保存在同一提交中，不属于该旧提交。精确源文件指纹、依赖提交、二进制哈希、进程记录和原始日志哈希见 [results.json](results.json)。原始日志、Player、PDB 不进入公开仓。

## GC 对照

AOT 的 RetentionHub 保留短弱引用、静态数组与委托列表；热更 Target 不含终结器。对象由短寿命托管线程创建，创建线程 Join 后才开始收集，避免把创建栈还活跃误认为根清理失败。每阶段三次显式 GC.Collect / WaitForPendingFinalizers，跨帧观察 WeakReference.IsAlive；每组 16 个目标。GCMode=Enabled、isIncremental=True。

| 阶段 | 无强引用 | 静态数组 | 事件订阅 |
|---|---:|---:|---:|
| held | 0 | 16 | 16 |
| static-cleared | 0 | 0 | 16 |
| all-cleared | 0 | 0 | 0 |

三个无调试器的独立进程都得到此表并退出 0。解除订阅在这个封闭样本中通过清空自己拥有的整个委托列表完成；业务发布者通常应解除具体订阅，不能清掉他人的订阅。没有触发事件，也没有通过终结器计数。

这证明样本中的强引用确实保留热更实例，解除后弱引用在观察窗口内失效。没有采集 Memory Profiler 根快照、used/reserved、RSS、活跃解释器根区间或 GC 耗时；不证明程序集卸载、内存立即归还 OS、增量模式性能或所有引用写入路径正确。

## 托管工作线程

三个无调试器的独立进程均有不同于主线程、彼此也不同的 managed/OS ID；两个 worker 各返回 5、15，Join=True，退出 0。工作线程不调用 Unity API。两个 worker 同时存活，但通过 firstDone 串行执行目标；各自结束计算后等待统一 release，再退出。

额外一个 CDB 进程加载本次 GameAssembly 的 private PDB。其主线程 OS ID=137848；worker0 managed=5 / OS=141284，worker1 managed=6 / OS=149628。调试器输出十六进制线程号，验证器转换后关联 Player 记录。

| 观察 | 结果 |
|---|---|
| Add MethodInfo | `00000170f0145930`，四次 Execute 相同 |
| interpData | `00000171d04dd208`，四次非空且相同 |
| Transform | worker0 首次 Execute 前 1 次；后面没有重复转换 |
| worker0 MachineState | `00000172054163b0` |
| worker1 MachineState | `0000017205416580` |
| 每个 worker 的生命周期 | CREATE 1、ROOT_ADD 1、Execute 2、FREE 1、DESTROY 1、ROOT_REMOVE 1 |

两个状态都创建后才出现第一次销毁，排除了先销毁后地址复用的歧义。每个状态的注册／注销 root 地址与自身相同；清理发生在对应 OS 线程上。Execute 入口先于首次 MachineState 创建，这是入口断点与函数内部惰性初始化的顺序，不是线程状态缺失。

[native-events.txt](native-events.txt) 仅保留自定义断点事件。完整本地日志另外核对 Add 名称、interpData 和 InterpreterInvoke 调用栈；地址只在该进程内有意义。主线程也出现一次 MachineState 创建，且若干其他 runtime 线程进入 FREE 入口；不把这些记录算成目标 worker 的生命周期，不要求进程强制结束前所有宿主状态都有析构日志。

## 验收与剩余边界

`python tools/lifetime_lab.py verify` 核对同一构建的运行／调试日志哈希并解析上述记录。15 个 Python 测试通过，包含缺阶段、强引用丢失、环境不符、线程身份重复、根注销缺失、缓存漂移和命令回显误判等负例。它们验证验收器，不代替 Player 实测。

独立审查指出的构建指纹和环境记录漏检已修正；后续原生证据与文章新增段落复核通过。清理记录属于函数入口命中，不是 native 内存释放量测量。初次构建的 Player 成功，但后处理曾因系统默认 GBK 解码生成文件失败；改用 UTF-8 后重新构建，只有上面的完整 build_id 进入验收。没有修改 Editor 或第三方 runtime 源码。

尚未覆盖 native 插件 attach/detach、Reverse P/Invoke、线程池、并发首次转换、终结器、GCHandle、活跃根区间、写屏障压力、性能与其他平台。
