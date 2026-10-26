# Prefab / AssetBundle 资源挂载链路

2026-10-26。build_id `7adc9fed-3322-4778-8a64-c7e6bb2018eb`，独立工程 `projects/resource-mounting`。本轮源码与验证记录随同一提交发布；复现请固定文章所列的本轮提交。基线 `64938d5c5040fbc2f63274ee4efd8ab6b3c9d07a` 仅包含前轮写屏障实验，不包含本轮工程。

## 环境与控制

沿用锁文件中的自定义 Unity2022.3.62f3_96770f904ca7、package v9.0.3/runtime v9.0.1、配套 il2cpp_plus；Windows x64 Development、IL2CPP C++ Debug、Minimal stripping。本地未压缩 AssetBundle 保留 TypeTree，没有网络/Addressables 变量。Editor 安装与旧实验均未修改。

一个自有 `ResourceHot.MountProbe`：默认 Number=11、Label=constructor-default；资源中保存 Number=42、Label=resource-prefab-v1、子 Transform Anchor 与 TextAsset Payload。代码组在未激活对象上赋 Number=7、Label=code-runtime。BundleProbe 与 MainPackageProbe 是两个独立 Prefab 源资产，内容相同、打包路径不同；因此 Resources 对照不是只改一份Player文件的单变量因果证明。

所有对象初始不激活；先读取实例字段和引用身份，再激活、等待Start、禁用并Destroy。快照中 `anchor_matches` 比较字段是否指向实例自己的子 Transform，避免仅靠相同名字判定引用正确。Payload检查类型、名称及内容。`life`事件里的字段只表示对应时刻观察，不用于证明资源内存已释放。

## 15个独立进程

每种模式三个新进程，全部退出0。`done.completed=true`表示过程完成；负向是否恢复由实测记录，不用退出0冒充挂载成功。

| 模式 | DLL显式加载/静态Ping | 启动清单登记 | 资产加载时热更组件 | 实例化后 | 生命周期 |
|---|---|---|---|---|---|
| code | 成功 | 有 | 不经过资源加载 | 1个，Number7、code-runtime | 五个回调完整且有序 |
| bundle | 成功 | 有 | 1个，missing0 | 1个，Number42、resource-prefab-v1，引用正确 | 五个回调完整且有序 |
| late | 不加载 | 有 | 0个，missing1 | 0个，missing1 | 无热更回调 |
| unregistered | 成功 | 无 | 0个，missing1 | 0个，missing1 | 无热更回调 |
| resources | 成功 | 有 | 0个，missing1 | 0个，missing1 | 无热更回调 |

正向回调为 Awake→OnEnable→Start→OnDisable→OnDestroy。snapshot在激活前，字段42与源码初值11不同；子引用指向克隆实例的Anchor，Payload名称/文本正确。AssetBundle.LoadAsset阶段已可识别热更组件，Instantiate后保留正确字段与内部引用关系。负向资源读取阶段已出现missing，并有自有阶段标记间的Unity缺脚本诊断；后续Instantiate没有补救。本轮未测试晚加载DLL后重试能否恢复，不能据此宣称失败不可恢复。

unregistered使用原Player的副本，删除启动ScriptingAssemblies.json中HotUpdate.dll及同索引types项（72项变71项）。比较所有副本运行文件，唯一差异为该JSON；GameAssembly、热更DLL、AssetBundle及其他运行文件保持原哈希。生成的AssemblyManifest.inc仍保留HotUpdate，运行时Assembly.Load和Ping成功；这是区分“代码可执行”和“资源组件可恢复”的直接对照，不是禁用整个HybridCLR或伪造DLL缺失。

所有启动前对当前目标类型的解析检查均为false，且没有枚举到HotUpdate程序集名；不把这个托管枚举结果当作内部placeholder对象不存在的证明。源分析中的placeholder复用机制未用原生断点采对象地址，本轮只证明可观测的登记、装载、资源和生命周期结果。

## 复现

从仓库根目录使用自己的已锁定Editor路径：

```powershell
python tools/resource_lab.py build --editor <Unity.exe>
python tools/resource_lab.py run
python tools/resource_lab.py verify
python tools/resource_lab.py export
python -B -m unittest discover -s tests
python -B tools/check_repo.py
```

build先Prepare（配置、运行时锁、Prefab和AB、GenerateAll），然后冻结输入再构建Player；HotUpdate未进入AOT，启动清单原包包含一个HotUpdate.dll。生成清单在本版本为Library/HybridCLR/.../generated/AssemblyManifest.inc。重新构建会产生新的build_id和产物；必须重新run/verify/export，不能沿用旧运行记录。

原始日志和二进制在忽略目录artifacts/resource-mounting；results.json绑定46份输入、256项构建产物、验收工具及15份运行日志和完整矩阵结果。15份*-events.jsonl只包含自有RMP事件；diagnostics仅摘取缺脚本文案和自有阶段，不导出Unity源码路径/调用栈。公开事件重新解析后的判据摘要与原始日志一致。

## 拒绝记录与边界

初版Player编译成功，但混合编码编译日志触发UTF8解码错误；保留原始日志，验收改为原始字节上的ASCII标记检查并增加失败回归。一次检查误把临时构造名ResourcePrefab当作Unity保存后的Prefab名；实际名称是BundleProbe/MainPackageProbe。修正验收器并保留探索日志后运行完整矩阵，不修改Player来迎合错误预期。131项Python测试通过，其中35项为本轮验收与工具回归；它们不替代15个Player结果。

当前仅覆盖上述组件、标量/Unity对象引用、TypeTree开启及固定平台。没有字段schema演进、程序集改名/重复加载、禁用TypeTree、Addressables、远程分发、其他平台或性能验证。Destroy/Unload调用与正确性观察不等于GC、共享资源释放量或无泄漏结论。

独立审查修复了阶段时序与资源计数门槛：必需stage唯一且有序，DLL/Ping先于资源使用，实例化先于snapshot，asset与result计数类型/布尔值分别一致。负向意外恢复保留为restored_unexpectedly；零missing槽或阶段转换单独标needs_investigation，不混入本次缺脚本对照。原始15份日志哈希未变，重解析后为6 restored、9 missing_at_asset_and_instance。
