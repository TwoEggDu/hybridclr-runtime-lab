# hybridclr-runtime-lab 设计

公开仓库 TwoEggDu/hybridclr-runtime-lab，作为 ECMA-335、IL2CPP、HybridCLR 三栏的实验依据。用户已确认仓库名称、公开可见性并要求继续，沿用本轮讨论的独立实验工程方案。

第一版：projects/call-chain、projects/generic-p0、projects/generic-p1 三个独立 Unity 工程；后两者组成同一泛型实验。共用 tools/ 的依赖准备、构建与运行入口，debugger/ 放固定版本 CDB 指令，evidence/ 仅保存脱敏结果。

lab-lock.json 固定已验证的自定义 Editor 身份和三个上游提交；Packages 引用仓库相对路径。源码依赖获取到忽略的 .local/，Player、日志、PDB 到忽略的 artifacts/。不上传 Unity 安装、第三方实现或原始调试日志。

保留旧文章仓样本作为历史记录；本仓形成新维护基线。文章后续引用本仓的固定 commit。第一版不修改或发布文章仓的既有未提交改动。

验收：新路径首次准备和三个工程构建；Add 两次返回与缓存断点；泛型四组退出码、返回/异常、同一热更输入、同源补充元数据及 native/inline 断点；发布前逐文件检查，发布后读回远端 SHA。通用 CI 只做仓库结构检查，不将其写作 Unity Player 验证。
