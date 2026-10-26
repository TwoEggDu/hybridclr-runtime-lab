# 并发首次调用与类型初始化

本轮是独立 `projects/concurrent-initialization`。沿用 lab-lock 的本机自定义 Unity 2022.3.62f3_96770f904ca7、package9.0.3/runtime9.0.1/il2cpp_plus2022.3.x-9.0.1，Windows x64 Development IL2CPP C++ Debug、Minimal stripping、OptimizeSpeed。919个安装运行时输入与原始prepared树完全相同，未安装前轮异常反事实补丁。

## 问题与样本

AOT/hot各比较Cold(no .cctor)、Strict、Failed、Cache<int>/Cache<string>，2/4个托管worker，各3个新Player。另加mixed的直接AOT与hot Bridge->AOT共享同一个AotConcurrent.Strict，共18组合、54普通进程。场景模板只替换命名空间；AOT泛型seeds保留但不执行。目标Type/MethodInfo先解析，所有worker ready后释放外部门闩；调用在日志锁之外，逐个有界Join。cctor仅用150ms Sleep延长窗口，不等待其他worker。

## 普通运行结果

54个进程全部通过结构/语义验收并退出0。162个成功结果、60个预期初始化异常（12个失败进程各含worker结果及Join后的两次主线程访问）。Cold为7；Strict为41083；两个封闭泛型分别41083/81123，每个封闭类型一次初始化。Failed每进程只尝试一次，无Read body，所有异常链和自有原因消息一致。mixed两种入口共享同一AOT静态状态。

AOT外层反射捕获TargetInvocationException->TypeInitializationException->InvalidOperationException。本轮没有验证或修复热更内部catch；该缺陷由前轮exception-flow独立维护。ready/attempt/body/result或caught/join按进程序号、managed和OS线程身份校验，未知worker异常、半初始化状态、缺失事件或超时拒收。

## 独立原生观察

8个独立PDB进程，不计入54个普通样本。hot的cold/strict/failed/generic和mixed使用硬件Transform/Execute入口，AOT的strict/failed/generic用独立软件ClassInit配置；AOT strict另采Sleep(1)等待栈。两套runtime断点配置不混用。

释放前目标Read缓存为空。成功hot调用后缓存非空，已捕获的入口使用同一缓存；Failed的cctor执行而Read不进入、Read缓存仍空；AOT目标无解释缓存。AOT ClassInit记录有started=1/finished=0/owner为其他线程的竞争者，Strict等待栈位于ClassInit/Sleep(1)。这里不公布Unity源函数体。

计数不能等同：最终hot Strict有4个自有body事件，但只捕获2个Execute入口；hot generic两个目标各4个body，也各只捕获2个入口。Cold捕获4个worker入口，mixed捕获2个hot入口。公开native字段保留命中数、命中线程、expected_interpreter_entries和all_expected_interpreter_threads_observed；AOT入口覆盖标为not_applicable/空值；不补齐或归一计数。conversion_count_conclusive始终为false，不能从选定断点样本推出所有调度下只转换一次。

早期软件/混合断点探索曾有漏记或重复，硬件ClassInit还触发本机CDB单步事件而未完成。这些均在忽略的artifacts/.../exploration另存，不计最终8个进程；没有靠探索中退出或部分日志充当验收。硬件断点和调试暂停也不构成完整运行时执行普查。

## 复现

```powershell
python tools/prepare.py
python tools/concurrent_lab.py build --editor $editor
python tools/concurrent_lab.py run
python tools/concurrent_trace.py --cdb $cdb
python tools/concurrent_lab.py verify
python tools/concurrent_lab.py export
python tools/check_repo.py
python -m unittest discover -s tests
```

`$editor`必须指向lab-lock身份相同的本机自定义安装，`$cdb`为Windows SDK x64 CDB。实际工具参数以--help为准。构建后源文件、产物、runtime输入和原始日志改变都会拒收。results.json含build_id、最终DLL metadata、工具/输入/产物/原始日志哈希及每个事件文件哈希；原始日志/PDB/Unity生成物只在忽略目录保存。公共JSONL只含自有事件，不替代原生raw日志。

## 发布与边界

本轮已完成本地验收；源码和证据随包含本记录的同一提交发布，复现请固定相关文章所列的本轮提交。baseline_commit5638131是前轮constrained/boxing，不是本轮版本。无性能、其他平台、循环/递归初始化、原生回调竞争、并发GC或长期压力结论；门闩及调用区间重叠不是每条runtime指令同时执行的证明。
