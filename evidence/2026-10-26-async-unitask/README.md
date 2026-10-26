# async／UniTask 跨 AOT／解释器实测

日期：2026-10-26。源码与本记录随包含本轮实验的同一提交发布，本轮不以先前f5ba510充当固定实验提交。复现时使用包含本工程和记录的同一提交。

## 问题与边界
重复builder／解释器帧不能单独证明递归，完成态await也不能证明跨帧恢复。本轮以同源AOT／hot方法区分同步结果、真正挂起、await前后异常，并比较同一Player是否加载UniTask补充metadata。

Editor仍是本机自定义Unity2022.3.62f3_96770f904ca7，HybridCLR package9.0.3/runtime9.0.1/配套il2cpp_plus与lab-lock.json一致。Windows x64 Development、IL2CPP C++ Debug、Minimal stripping。额外依赖UniTask2.5.10固定7c0f199fe0d3fc528024488ccd671e6c7b27745b，见async-lock.json。第三方源码仅在ignored.local，通过tools/prepare_async.py获取，不随本仓复制。

## 固定输入
build_id=c2a81f08-12d1-4f70-b333-d4bd26705388。44输入、264产物哈希；919runtime实现文件逐项与原始prepared一致，没有使用前轮exception-flow反事实补丁。AOT／hot情景仅命名空间和事件侧标识不同，模板在samples/async-unitask/Scenarios.cs。HotUpdate从最终AOT裁剪DLL／代码注册排除，入口反射只创建缓存委托。

同一Player投放hot-dev和hot-release两份DLL；实际读取前者状态机基类System.Object（class）、后者System.ValueType（struct），而非凭编译开关猜测。AOT最终状态机也是class。两个热更编译维度不同，不作为metadata单变量；各形态内off/on使用同一Player和同一DLL。UniTask.dll.bytes逐字节匹配最终Player备份的裁剪UniTask.dll，on在热更装载前用SuperSet加载，返回码均0。

本样本link.xml显式preserve整个UniTask程序集，目的是固定本轮builder依赖；off仅表示不加载补充metadata，不能被解释为没有任何可用native实例。不存在“删除已有native实现”的反事实。

## 普通Player结果

| 侧／metadata | sync | frame | throw-before | throw-after |
|---|---|---|---|---|
| AOT／off | 3×42 | 3×42 | 3×等待方捕获 | 3×等待方捕获 |
| hot-dev class／off | 3×42 | 3×42 | 3×等待方捕获 | 3×等待方捕获 |
| hot-dev class／on | 3×42 | 3×42 | 3×等待方捕获 | 3×等待方捕获 |
| hot-release struct／off | 3×42 | 3×42 | 3×等待方捕获 | 3×等待方捕获 |
| hot-release struct／on | 3×42 | 3×42 | 3×等待方捕获 | 3×等待方捕获 |

60个新进程，30结果／30预期InvalidOperationException；每次Work finally和AOT等待方finally各一次，没有入口同步escape或未观察异常。before是返回Faulted UniTask后由等待方await观察，不是entry委托直接抛出。AOT侧Consume实际await目标UniTask。

30个挂起样本：帧1注册自有ProbeGate continuation，entry与consumer均Pending；帧3由AOT Update完成gate，记录dispatch→GetResult→gate_resume，再实际await UniTask.NextFrame；帧4恢复，返回42或抛after，完成两层finally。注册、完成、恢复和结束事件都在主线程managed ID1。同步完成和before样本没有gate注册，不混作挂起证据。这里只验证单线程PlayerLoop调度；没有线程池、取消、并发或性能结论。

## 原生路径
12个匹配private PDB独立进程：class/off/frame、struct/off/frame、struct/on/frame、struct/on/throw-after，各3次。每进程Work Execute一次、转换一次；同一hot MoveNext Execute三次、转换一次；后两次复用同一非空interpData，native token与最终投放DLL对应（class MoveNext 0x06000005，struct 0x06000004）。

class组实际命中native引用共享的AsyncUniTaskMethodBuilder<int>.Start及两种AwaitUnsafeOnCompleted；struct组实际命中带Il2CppFullySharedGenericAny名称的native入口。每进程一Start／两AwaitUnsafeOnCompleted，与两次未完成await对应。on/off的struct组命中相同符号；所跟踪路径没有UniTask方法被解释转换或补充image的GetMethodBody读取。

这证明当前样本已有可运行native builder路径；加载metadata不会强制把它替换为解释执行。这里的FullySharedGenericAny名称既不是缺失实现占位证据，也不据此判断启用了HybridCLR商业FGS。原生符号只作当前构建行为指引，完整栈、PDB、生成C++和日志保留本地。

## 复现与验收

```powershell
python tools/prepare.py
python tools/prepare_async.py
python tools/async_lab.py build --editor $editor
python tools/async_lab.py run
python tools/async_trace.py --cdb $cdb
python tools/async_lab.py verify
python tools/async_lab.py export
python -m unittest discover -s tests -v
python tools/check_repo.py
```

输出在ignored artifacts/async-unitask，公开results.json绑定构建、输入、工具、原始日志哈希、60普通和12native观察；72份事件只含自有结构化日志，重解析后导出。调用边界的CIL与状态机类型在build.metadata中。

探索阶段日志混合编码、读取器延迟枚举导致的工具失败已归档；读取器经真实编译fixture RED→GREEN后修正。CDB条件／类型表达式错误已用单独诊断验证并重采。没有把失败工具输出、早期不含builder入口的采集或诊断进程加入最终72份事件。

## 最终检查

完整182项Python测试、856公共文件边界检查通过。最终独立审查复核原始哈希和72份事件一致；P2验收缺口已补零UniTask解释事件／补充体读取断言，两个RED→GREEN测试及24次真实日志内存破坏验证通过，无剩余P1/P2。此修订只改工具，不重建或修改Player。

## 仍未知
历史Android arm64 Release崩溃缺少原版本、DLL与符号身份，当前Windows正向结果不证明其根因或修复。没有复现metadata缺失失败，也没有验证错误/不匹配metadata、取消、同步重入、状态机递归、并发、其他版本／平台或性能。负对照是否失败必须由实际输入决定，不能预先认定struct async必然缺实例。
