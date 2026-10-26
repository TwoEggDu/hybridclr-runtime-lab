# constrained.／装箱调用综合实验设计
用户已确认推荐方案并授权执行；实现阶段执行实验与补稿；2026-10-26用户追加授权提交推送实验仓库与文稿，并补齐固定提交链接。
## 目标与约束
固定lab-lock原自定义Unity2022.3.62f3_96770f904ca7、package9.0.3/runtime9.0.1、Windows x64 Development/IL2CPP C++ Debug/Minimal，不使用exception-flow补丁，不改变旧项目或shared runtime。独立projects/constrained-boxing、artifacts/constrained-boxing。无需UniTask依赖。
## 模型与矩阵
初值10，自有Counter struct实现IMutableCounter并override ToString；PlainCounter无override；RefCounter class对照。
六模式：value泛型按值(return11/original10)；ref泛型ref(return11/original11)；box同一接口装箱对象两次Increment达12、原变量10、unbox.any副本继续改到13且箱内仍12、两接口别名同一对象；text-override="counter:10"；text-fallback类型名以.PlainCounter结尾；reference类按值与ref连续操作11/12且原对象身份保持。
三路线aot/hot/cross。AOT与hot共用情景模板；AOT调用绑定本地泛型helper，hot纯对照同理；cross仅hot源码绑定到AOT GenericCalls<T>，AOT源码不得引入GenericCalls具体实例。box作为不经过AOT泛型helper的语义控制，不误称为交叉泛型路径。cross off/on只改变提前加载最终匹配Probe.AOT.dll SuperSet，native实现是否缺失以实测为准。aot/hot只off，各6模式×3独立Player；cross off/on各6×3，总72普通Player。
## 验收
读最终自有DLL的所有IL操作数和方法签名，验证byvalue用地址访问副本、byref接收T&、constrained./callvirt、显式box/unbox.any，以及override/fallback分派。结果事件含原变量/返回/box/copy/identity/text，不能只看exit0。仅cross/off允许明确MissingMethodException作为观察，标注失败阶段与尚未完成的语义，不当作成功；其他异常为失败。
匹配PDB跟踪解释方法准备/转换/执行、AOT泛型body来源与Object::Box，使用自有类型过滤。选择aot/box、hot/box、hot/ref、hot/text-override、hot/text-fallback、cross/on/ref、cross/off/ref各3新进程，共21native；记录实际路径而非预设metadata必要或boxing次数。不做性能或无分配结论。
源码/依赖/runtime919文件/产物/原始日志/工具哈希绑定，重解析后公开自有事件。第三方实现、Unity C++、二进制与完整调试日志不公开。
## 文稿
四现有正文：类型系统集中值/箱身份，调用语义集中constrained.与fallback，AOT泛型篇与调用链篇补对应证据回链；三索引、三canonical plans与执行记录更新，不新增正文或改URL。全测试、公共边界、Hugo/链接/浏览器与最终独立审查；不得用桌面测试替代Player。

## 执行补充
普通矩阵发现cross/value off失败而ref成功，因此添加value on/off各3个native，最终27。源码、Player和runtime不变；原21进程不重复计数。
