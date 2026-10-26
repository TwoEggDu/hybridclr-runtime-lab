# constrained.／装箱调用综合实验

2026-10-26，本轮源码与证据随包含本实验记录的同一提交发布。旧b34ac10仍为async实验，不能标识本轮；复现请固定包含本工程与记录的同一提交。

## 问题与固定身份
区分原变量、值副本、箱内值和拆箱副本；分别观察CIL语义、可用方法实现与实际执行路径。环境沿用lab-lock.json：本机自定义Unity2022.3.62f3_96770f904ca7，HybridCLR package9.0.3/runtime9.0.1、配套il2cpp_plus，Windows x64 Development/IL2CPP C++ Debug/Minimal。没有使用前轮异常反事实补丁，也不引入UniTask依赖。

独立projects/constrained-boxing，build_id=9e084001-a41b-42c2-8fbd-62efc0d147d4。48项源输入、236份产物有哈希，919个运行时实现文件与原始prepared逐项相同。Contracts为AOT公共接口/日志，Probe.AOT定义AOT泛型GenericCalls与AOT对照，HotUpdate只动态加载。实际最终DLL证实热更排除AOT；反射只创建入口委托。

情景模板在samples/constrained-boxing/Scenarios.cs；AOT／hot按相同模板生成，但cross调用绑定只出现在hot源码，AOT Cases.Run没有GenericCalls的具体调用种子。泛型定义保存在Probe.AOT，不等于为全部热更实参生成了可用native实现。

## 情景与普通Player
每个Counter或PlainCounter初值10。纯AOT/纯hot各6模式×3；cross off/on各6×3，共72个新进程。

| 模式 | 完成语义 |
|---|---|
| value | 泛型按值调用返回11，原变量仍10 |
| ref | 泛型ref T调用返回11，原变量也11 |
| box | 同一箱对象两次接口调用到12；原变量10；unbox.any取出副本再改到13，箱内仍12，两接口别名为同一对象 |
| text-override | Counter返回counter:10，原变量10 |
| text-fallback | 未覆盖ToString的PlainCounter返回对应命名空间的类型全名，原值10 |
| reference | RefCounter按值与ref调用依次返回11/12，原对象到12且对象身份不变 |

| 路线／metadata | value | ref | box控制 | 两种Text | reference |
|---|---|---|---|---|---|
| AOT/off | 3完成 | 3完成 | 3完成 | 各3完成 | 3完成 |
| hot/off | 3完成 | 3完成 | 3完成 | 各3完成 | 3完成 |
| cross/off | 3 MissingMethod | 3完成 | 3完成 | 各3完成 | 3完成 |
| cross/on | 3完成 | 3完成 | 3完成 | 各3完成 | 3完成 |

共69个完成、3个明确MissingMethodException对照；退出0只表示驱动完成采集，不把缺实现当语义通过。错误精确指出GenericCalls.ByValue<HotBox.Counter>(HotBox.Counter)没有已实例化的AOT方法。on在加载hot前用SuperSet补充最终Player匹配的裁剪Probe.AOT.dll，返回0，恢复相同按值样本；同一Player／hot DLL和输入不变。

box模式不经过GenericCalls，是两组cross进程中的语义控制，不应宣称其已经覆盖AOT泛型调用。reference对照解释的是复制对象引用，并非深拷贝，也不意味着ref T可以普遍免补metadata。

## 最终CIL
只读最终AOT和hot DLL的实际签名、每条指令与token：ByValueLocal接收!!0，核心ldarga.s／constrained. !!0／callvirt；ByRefLocal接收!!0&，使用ldarg.0／constrained.／callvirt。差别在接收者指向哪份存储；相同constrained.不抹平值复制。

Cases.Run包含对Counter的显式box和unbox.any；同一接口引用别名不再box。两个TextLocal都使用constrained.与Object.ToString，并不在该泛型方法IL中直接写一个box指令。类型是否覆盖方法与实际运行路径仍要观察，不能把constrained.等同永不装箱。

## 27个原生进程
最初计划21个；普通矩阵发现value失败/ref成功后，另加cross value的on/off各3，最终9组各3，共27个匹配private PDB进程。早期未包含native泛型入口的21进程归档为探索，不重复计入最终数量。

- AOT/box与hot/box均对自有Counter命中一次Object::Box，输入值10，返回对象payload也10；PDB确认本构建Il2CppObject大小16，payload=object+16，source与payload为不同地址。
- hot/box的三次Counter.Increment解释帧入口分别读到10/11/12。前两次this同为该payload；第三次this为另一地址，来自unbox.any副本。方法token与最终DLL匹配，interpData复用。
- hot/ref与hot/text-override没有命中自有接收者的Object::Box，目标方法this值10；override的TextLocal和Counter.ToString看到相同地址。这不是整条流程零分配结论。
- hot/text-fallback确实对PlainCounter命中Object::Box，输入就是TextLocal的ref地址、值10；返回箱内副本10。它是泛型constrained.执行时产生的回退装箱，不能仅搜索TextLocal IL有无box就判定。
- cross/ref的on/off都实际命中native GenericCalls_ByRef_TisIl2CppFullySharedGenericAny共享入口（MethodDef0x06000009），再经过native constrained调用进入hot Counter.Increment。两组原变量都改成11，无自有Counter装箱。
- cross/value的off在目标方法体前报告MissingMethod，未进入Counter.Increment；on从SuperSet image读取Probe.AOT的ByValue（MethodDef0x06000008），准备、转换并进入其解释帧各一次，完成返回11而原值10。两组都未命中native ByValue入口。

特别注意：cross/on/ref在准备Run时也读取了ByValue的补充body，栈含MethodBodyCache::IsInlineable；但实际执行的是native ByRef，没有执行ByValue。补充体被读取／准备，不等于当前选中路径是解释执行。仓库不公开完整栈和Unity生成C++，仅保存符号与自有事件摘要。

即使本构建生成物中存在带FullySharedGenericAny名称的ByValue函数，也不能仅据符号存在断言该具体签名一定能被当前runtime选用；应同时检查方法身份、可用入口选择和调用结果。本轮只报告实际选择差异，不推广所有平台或所有值类型的共享规则。

## 复现与验证

```powershell
python tools/prepare.py
python tools/box_lab.py build --editor $editor
python tools/box_lab.py run
python tools/box_trace.py --cdb $cdb
python tools/box_lab.py verify
python tools/box_lab.py export
python -m unittest discover -s tests -v
python tools/check_repo.py
```

输出在ignored artifacts/constrained-boxing。公开results.json和99份自有事件绑定构建、48输入、236产物、最终DLL、工具和原始日志哈希；每份事件重解析。工具测试不替代Player；不公开第三方源码、二进制、PDB、完整日志或Unity实现正文。

## 最终验收

完整206项Python测试、1016项公共文件边界检查通过。独立审查核对524项输入/产物/工具/原始/公开哈希与99事件一致。缺实现方法身份与override接收者地址的两项P2由5个RED→GREEN破坏测试修正，复核关闭，无剩余P1/P2。修订只收紧工具判据，Player、输入与原始日志不变。

## 结论边界
固定自定义Editor/v9、Windows x64样本；不涉及Nullable<T>、readonly防御性复制、泛型接口变体、并发、移动端或性能。零自有Object::Box命中不等于零分配；返回结果一致也不意味着执行路径一致。实际ByValue缺实现／补充恢复只属于本轮固定签名与输入，不宣布所有constrained.或ref泛型都已经覆盖。
