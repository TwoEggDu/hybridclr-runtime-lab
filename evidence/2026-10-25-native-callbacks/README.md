# 原生线程回调与在途停止：Player 实测

2026-10-25，build_id `65d3ddb9-3bb0-4ce9-99b9-59f4ff1cc82b`。从实验仓库已发布 `a387d2807f4251fce0e5fc24e8d1debddb4ca79d` 继续扩展，新增样本与本记录保存在同一 Git 提交中，不属于旧提交。精确采集源码、工具、产物与日志指纹见 [results.json](results.json)。

## 固定环境与复现

根目录 lab-lock.json 不变：本机自定义 Unity `2022.3.62f3_96770f904ca7`，package v9.0.3 / runtime v9.0.1 / il2cpp_plus v2022.3.x-9.0.1，Windows x64、IL2CPP Development、C++ Debug、Minimal stripping。GCMode=Enabled，isIncremental=True。插件用本机 MSVC 14.51.36231、/LD /Od /Zi /MD 编译，编译器哈希记录在摘要中。

```powershell
python tools/callback_lab.py build --editor $editor
python tools/callback_lab.py run
python tools/callback_lab.py trace --cdb $cdb
python tools/callback_lab.py verify
```

独立 `projects/native-callbacks`、`artifacts/callbacks` 不覆盖前序实验。首轮 Unity 构建成功，但初始化改写了 ProjectSettings.asset，源码指纹检查拒绝验收；固定设置并补齐失败时停止/放行/Join 后重建，只接受上述完整 build_id。没有改 Editor 安装或第三方 runtime 源码。

`native/native-callbacks/plugin.cpp` 完全自有：用 Win32 CreateThread 模拟 SDK 线程，提供单个任务的启动、停止和有界 Join；不包含 Unity 实现。接口是 Windows x64 的 cdecl `int(int,int)`，仅传整数。热更静态 Call 标记 MonoPInvokeCallback，AOT 保留委托并取得函数指针。GenerateAll 为其产生签名 Bi4i4i4 的 `__ReversePInvokeMethod_0`；构建产物确认 HotUpdate 未进入 AOT 代码注册。

## 六次独立进程运行

registered、raw 各运行三个无调试器 Player，均退出 0：

| 场景 | 结果 |
|---|---|
| registered：托管 Thread 调用插件，再由插件同步回调 | 两次返回 5、15；进入前后 managed ID 相同；Join=True |
| raw：插件创建原生线程并重复回调 | 三次返回 5、15、23；同一 OS ID，managed ID 依次 5、6、7 |
| raw 在途停止 | 第三次回调 Hold；主线程停止；此时 Join(0) 尚未完成；放行后 Join 成功，最终次数为 3 |
| 委托释放 | registered 等托管 worker Join；raw 等原生 worker Join；完成后才清空 Root |

回调只调用纯框架/数据操作，不接触 Unity API。异常在回调边界转成失败计数和错误返回；本文仅验收正常路径，未专门注入异常。Abort 路径会请求停止并放行、等待；Join 失败时仍保留委托直到进程结束。此处事件/计数是封闭样本协议，不是通用 SDK 实现。

## 两次 CDB 进程的原生证据

每个场景另开一个进程，GameAssembly 和自有 NativeProbe 均加载匹配 private PDB。回调地址等于 wrapper 实际入口；调用栈为 NativeProbe → ReversePInvoke wrapper → N2M bridge → Interpreter::Execute，目标为热更 Call。

| 观察 | registered | raw |
|---|---|---|
| 目标 OS ID | 152068 | 119432 |
| 回调的 managed ID | 5、5 | 5、6、7 |
| wrapper 内 ScopedThreadAttacher 的 owned 字段 | 两次均为 0 | 三次各非 0 |
| 目标线程的 Attach 入口 | 0 次 | 3 次 |
| 目标线程的 Detach 重载入口 | 0 次 | 6 次，即每次回调 2 个重载入口 |
| MachineState 创建/动态根注销入口 | 各 1 次，worker 退出时清理 | 各 3 次，每次回调返回插件前清理 |
| Call 转换 | 1 次 | 1 次 |
| Execute 入口 interpData | 首次空，第二次非空 | 首次空，后两次为同一非空地址 |

首次 Execute 断点在缓存建立之前，不能要求它一开始就非空。Transform 随首次调用发生；后续方法缓存复用，与临时线程登记/TLS 状态的清理是两件事。raw 三次 MachineState 地址分别为 `000001ff959d8320`、`000001ff959d9470`、`000001ff959d9750`；只描述本进程，不能推出地址永不复用。

registered 的 wrapper 没有取得登记所有权，未在回调返回时 detach；正常托管 worker 退出后命中 FREE、析构和根注销。raw 每次 wrapper 临时登记，并在返回插件前命中 Detach 两个重载、FREE、析构、根注销。相同 OS ID 不代表跨回调保留同一托管身份或 MachineState。其他宿主线程的 attach/detach 不算入此表。

raw 第三次插件进入事件 < 主线程 STOP < 第三次返回事件 < 原生线程结束 < 主线程 JOIN 事件，配合 Player 的 JoinBefore=False 与 Join 后释放日志，形成在途停止记录。日志只证明函数入口和调用顺序，不证明 native 释放字节数、活跃根扫描内容或所有关闭竞争正确。

## 验收与范围

验收器关联构建、源码、二进制与完整日志哈希，并验证 wrapper 地址、OS 线程、参数/返回、scope 所有权、Attach/Detach、状态/根清理、首次转换/后续缓存与停止顺序。[registered-native-events.txt](registered-native-events.txt) 和 [raw-native-events.txt](raw-native-events.txt) 只发布自定义事件；完整日志、受限源码、二进制和 PDB 留在本地忽略目录。

22 项 Python 测试通过，含已有回执/GC/线程检查和新回调负例；独立审查发现的“释放记录可排在 Join 之前”漏检已补测试并修复；缺失缓存字段误当空值的漏检也已修复。调试准备中曾遇到 Detach 重载歧义，以及多条模块加载过滤相互覆盖；最终脚本在 GameAssembly 加载后绑定重载，并在插件事件确认自身符号。

当前未覆盖上下文 GCHandle、回调异常注入、GC 压力与引用写入、多原生线程竞争、强杀线程、真实第三方 SDK、其他平台或性能。只确认固定环境的单任务正常接入与有序退出闭环。
