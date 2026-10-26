# async／UniTask 跨 AOT／解释器实验设计

用户已确认上一条方案并授权完整执行。实现阶段只执行实验与补稿；2026-10-26用户追加授权提交推送实验仓库及文稿，并补齐固定提交链接。

## 问题与方案
沿用当前自定义Unity2022.3.62f3_96770f904ca7、package9.0.3/runtime9.0.1、Windows x64 Development IL2CPP Debug，不应用前轮反事实补丁。固定UniTask2.5.10/7c0f199fe0d3fc528024488ccd671e6c7b27745b，外部依赖只存ignored.local。独立projects/async-unitask和artifacts/async-unitask。
已选择最小正向基线与单变量metadata加载对照；不进行历史Android复现或引入多线程。Development与Release热更编译是独立形态维度，不称为metadata单变量；同一形态内on/off投放相同DLL/Player。

## 实验矩阵与接口
自有同源Cases.Work(string mode):UniTask<int>，AOT与hot命名空间不同。模式sync、frame、throw-before、throw-after。AOT侧native编译，hot-dev/hot-release分别读取实际状态机基类/字段/调用签名。AOT只off作为参考；hot两形态各off/on；每格3个独立Player，共60普通进程。
同步await结果7，Work正常返回42；before在首次await前抛InvalidOperationException；after在真正挂起/恢复后抛。挂起通过自有IUniTaskSource<int> gate记录continuation注册/调用，AOT Update完成gate后再await UniTask.NextFrame，记录frame/线程/结果。等待方AOT实际await task捕获异常/finally，反射仅创建缓存委托。Driver记录任务返回前是否同步escape，避免混同async fault和入口调用失败。
metadata仅按on加载该Player匹配裁剪UniTask.dll，Superset模式、返回码/hash/assembly身份绑定。若其他依赖需要补齐，先定位方法所属再新增最小对照，绝不隐藏失败。

## 验收与证据
on与AOT必须有正确事件顺序、次数、结果/异常与finally；off保留实际成功或明确MissingMethod，不强制制造崩溃。所有挂起路径frame推进、主线程一致；异常通过await传回、无未观察异常。取最终DLL的状态机IL和泛型MethodSpec；匹配PDB断点核查hot MoveNext、builder方法体来源/转换、恢复continuation，普通进程与调试进程分开计数。输入/依赖/runtime/产物/日志/解析工具哈希绑定；public仅自有源码与事件，不复制第三方实现、PDB、日志或Unity C++。

## 文稿
case：HCLR14保留历史边界与实测入口，HCLR17集中讲新实验；场景：HCLR23同步实际覆盖。三索引复用入口、canonical plans回写、docs/hybridclr-async-unitask-outline.md登记。不得把本机通过写成历史Android根因闭合，不报性能结论。
