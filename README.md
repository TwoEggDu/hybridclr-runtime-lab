# hybridclr-runtime-lab

用可运行的 Unity Player 实验，把 ECMA-335 的调用描述、IL2CPP 的构建产物和 HybridCLR 的执行路径对应起来。

这是 [TwoEgg 技术专栏](https://twoeggdu.github.io/twoegg-tech-stack/engine-toolchain/hybridclr-series-index/) 的配套实验仓库。每次实验固定源码版本、构建配置、输入与结果；文章引用对应 commit，后续实验在此维护。

## 第一版实验

| 实验 | Unity 工程 | 核验内容 |
|---|---|---|
| 基础调用链 | [projects/call-chain](projects/call-chain) | Add(2,3)=5、Add(7,8)=15；首调转换、再次复用同一缓存 |
| 泛型调用 | [projects/generic-p0](projects/generic-p0)、[projects/generic-p1](projects/generic-p1) | string/int/结构体；显式 AOT 实例 × 补充元数据四组对照 |

P0 无显式 seeds，P1 在 AOT 启动阶段实际调用三种 Echo 实例。每种启动方式使用独立进程。两份 Player 最终投放同一份热更 DLL，补充元数据分别匹配各自主包的裁剪产物。P1 seeds 同时预先调用目标，因此本实验不比较两组的冷启动性能。

首版实测记录：[2026-10-25 构建、运行与原生路径证据](evidence/2026-10-25/README.md)。

## 环境基线

| 项目 | 固定记录 |
|---|---|
| Editor | **本机自定义** Unity `2022.3.62f3_96770f904ca7` |
| 平台 | Windows x64、IL2CPP、Development、C++ Debug |
| 构建设置 | Managed Stripping Minimal、IL2CPP OptimizeSpeed |
| HybridCLR package | v9.0.3，`6cadd24d101f4cbd00cd80190106f6621132d24d` |
| runtime | v9.0.1，`83929787581bce6c7219418f62348a10c33582ee` |
| il2cpp_plus | v2022.3.x-9.0.1，`ba3a76c9979d14cee404fb5d44301773e0768866` |
| 工具 | Git、Python 3.12+、.NET SDK 10；Player 需要 Windows IL2CPP / MSVC；断点需要 Windows SDK x64 CDB |

版本与下载来源集中在 [lab-lock.json](lab-lock.json)。当前证据来自自定义 Editor，**尚未完成标准 Unity 发行版、移动端、WebGL 或 Release 配置验证**。构建入口会核对实际 Editor ProductVersion；使用其他 Editor 时应先建立独立版本基线并修改锁定文件、重新取证，不能直接沿用本仓的通过结论。Editor 安装与第三方实现不随仓库分发。

## 从克隆到运行

在仓库根目录执行。建议使用较短的本地路径，避免 Windows 原生工具链的路径长度限制。先关闭将要构建的三个 Unity 工程。

```powershell
git clone https://github.com/TwoEggDu/hybridclr-runtime-lab.git
cd hybridclr-runtime-lab
python tools/prepare.py
```

准备脚本按锁定提交获取上游仓库，写入忽略的 `.local/`，并检查 package 的配套版本映射。已有依赖只验证，不自动 reset、清理或覆盖本地修改。联网首次准备耗时取决于上游仓库下载。

Unity manifests 使用相对于 Packages 的 `file:../../../.local/src/package`，避免保存作者机器路径。完成 prepare 后，也可以通过 Unity Hub 打开任意 projects 子目录。

将 `$editor` 设置为自己的 Unity.exe 路径后：

```powershell
python tools/lab.py build --editor $editor
python tools/lab.py run
```

构建入口会设置样本工程的场景、IL2CPP 和 HybridCLR 配置，只用于这三个隔离工程。三个 Player 与日志都写入 `artifacts/`，不会覆盖 Editor 安装。旧 Library 的 runtime 锁不匹配，或 919 个非生成实现文件与准备源不一致时会报错；先检查本地改动，再使用全新 Library，不能把旧版缓存当作新版安装。

每次构建都有唯一 build ID 和产物哈希；开始重建就使旧构建成功标记失效。运行与调试日志分别绑定 build ID 和日志哈希，旧记录不能与新二进制拼接验收。

运行器自动检查：Add 的返回值，以及下表中每个泛型输入的两次结果。

| 组别 | string | int | Payload | 退出码 |
|---|---|---|---|---|
| P0/M0：无 seeds、不补 | 成功 | MissingMethodException | MissingMethodException | 2（预期对照） |
| P0/M1：无 seeds、补充 | 成功 | 成功 | 成功 | 0 |
| P1/M0：有 seeds、不补 | 成功 | 成功 | 成功 | 0 |
| P1/M1：有 seeds、补充 | 成功 | 成功 | 成功 | 0 |

`run` 只有在所有组都符合期望时才通过。P0/M0 的退出 2 是样本的负对照；任何其他退出码或缺少对应日志都会失败。原始日志和进程回执位于 `artifacts/call-chain/`、`artifacts/generics/logs/`。

## 从执行结果追到原生路径

把 `$cdb` 设置为 Windows SDK 的 x64 cdb.exe 路径：

```powershell
python tools/lab.py trace --cdb $cdb
```

它使用每份 Player 自己的 PDB，在启动前设置延迟断点，依次执行五个进程，再校验方法身份、缓存、目标函数和内联转换记录。

- Add：装载 1 次、invoker 2 次、Transform 1 次、Execute 2 次；返回 5、15。
- P0/M1 的 int/Payload：方法体来自补充 AOT image，Echo 进入 TransformSubMethodBody，随后由包装方法解释执行。
- P1：原生共享实现命中要区分 seeds 与热更调用；补元数据没有强制替换已经可用的原生路径。

断点寄存器与类型名针对固定 v9、Windows x64，不能直接套到 ARM64 或另一版函数签名。`Interpreter::Execute` 命中也不等于整个调用成功，校验器同时检查返回值或预期异常。

产出 `artifacts/call-chain/verified-results.json` 和 `artifacts/generics/verified-results.json`。公共摘要应人工检查后另存 evidence/，不要直接发布整份 CDB 日志。

## 读取实际 CLI 签名

```powershell
dotnet run --project tools/MetadataReader -- artifacts/generics/Player-p0/RuntimeGenericProbe_Data/StreamingAssets/HotUpdate.dll.bytes artifacts/generics/Player-p0/RuntimeGenericProbe_Data/StreamingAssets/Generic.AOT.dll.bytes
```

只读 DLL，不执行程序集。它按 IL 操作数宽度定位真实 call，输出 MemberRef、MethodSpec 和目标签名。类型解码只覆盖本实验的 string、int32、valuetype；不作为通用反编译器。

## 对象保留与托管工作线程

独立工程 `projects/lifetime-threads` 沿用同一份 `lab-lock.json`。详见 [本轮记录](evidence/2026-10-25-lifetime-threads/README.md)。

```powershell
python tools/lifetime_lab.py build --editor $editor
python tools/lifetime_lab.py run
python tools/lifetime_lab.py trace --cdb $cdb
python tools/lifetime_lab.py verify
```

输出单独保存在 `artifacts/lifetime/`，不覆盖前两组实验。构建前后核对完整源码清单；运行前核对源码、构建身份与二进制哈希；验收时再次解析日志并核对构建回执。

GC 与 threads 分别启动三个独立 Player。GC 以每组 16 个对象对照无强引用、静态数组持有、实例委托订阅持有；逐步清理后观察弱引用。持有组意外丢失属于失败，解除引用后仍存活则保留为观察，不能让校验器把它隐去。线程组让两个同时存活的托管工作线程串行调用相同热更 Add，各调用两次；它不测试并发首次转换竞争或线程池。

CDB 脚本按 Windows x64 ABI 读取固定版本的入口参数。验收关联 Player 的 OS 线程号、四次 Execute、一次转换、非空共享 interpData、两份同时存在的 MachineState、各自注册／注销根与销毁的顺序。原始调用栈与符号日志留在本地；公共摘要不包含 Unity 实现正文。

## 目录与维护约定

```text
projects/     独立 Unity 工程、自有源文件及稳定 .meta
lab-lock.json 固定 Editor 身份与上游提交
tools/       准备、构建、运行、校验、metadata 读取
debugger/    固定版本 CDB 指令
evidence/    审阅后的版本信息、结果与哈希
docs/        实验设计、复现边界及维护说明
.local/      本机准备的第三方依赖（忽略）
artifacts/   本机构建和调试输出（忽略）
```

新增实验先写问题、变量、判据与版本，再跑 Player。不要用普通 .NET 测试或仓库结构检查替代 Unity runtime 结果。更改锁定版本时重新构建、重新取证，旧证据作为历史记录保留。

文章入口：[源码阅读起步](https://twoeggdu.github.io/twoegg-tech-stack/engine-toolchain/hybridclr-source-reading-start/)、[泛型调用综合实验](https://twoeggdu.github.io/twoegg-tech-stack/engine-toolchain/runtime-generic-call-experiment/)。文章发布进度与本实验仓库独立；页面尚未上线时以仓库内实验说明和证据为准。

## 本地结构检查

```powershell
python tools/check_repo.py
python -m unittest discover -s tests -v
```

检查项目结构、依赖路径、固定版本、seeds 隔离和公开文件范围。它不需要 Unity，也不证明 Player 可运行。

上游项目及 Unity 安装遵循各自许可。本仓不复制或重新授权第三方实现；源码阅读只发布自有样本、符号指引和可核对的行为记录。
