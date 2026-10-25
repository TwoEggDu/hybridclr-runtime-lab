# 2026-10-25 实测记录

本目录记录从本仓三个隔离工程重新构建、运行、调试后的结果。使用本机自定义 Unity `2022.3.62f3_96770f904ca7`，依赖提交与参数见根目录 [lab-lock.json](../../lab-lock.json)。不代表标准 Unity 发行版兼容性。

- 三个 Windows x64 IL2CPP Development / C++ Debug Player 构建成功。
- 五个普通 Player 进程、五个 CDB 进程均符合预期；P0/M0 是退出 2 的负对照。
- [call-chain.json](call-chain.json)：Add 返回 5、15；首次转换一次，两次执行使用同一方法与缓存。
- [generics.json](generics.json)：四组的返回值或异常、元数据与热更 DLL 哈希、原生共享与内联路径计数。
- [metadata.txt](metadata.txt)：同一份实际 DLL 的 MemberRef / MethodSpec / MethodDef 信息。
- 六个证据隔离测试通过，覆盖重建、产物或日志改变、旧运行记录、被中断阶段。

构建标识：`136f3c65-0c8b-4944-a838-39a5f4024e27`。两份 JSON 的构建标识与实际 Editor 身份一致。完整产物与日志保留在本地忽略目录，公开摘要不包含第三方实现或本机绝对路径。

结论仅适用于锁定的版本与配置。P1 的 seeds 已预先调用目标方法；这些计数不能用于比较冷启动耗时。
