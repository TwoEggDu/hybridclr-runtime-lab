# Constrained Boxing Implementation Plan
> **For agentic workers:** Use superpowers:executing-plans task-by-task.
**Goal:** 对齐值/地址/装箱语义、实际CIL与AOT/解释路径。
**Architecture:** 独立Unity项目；同模板六情景，72普通与21native；严格解析与哈希回执。
**Tech Stack:** locked Unity/HybridCLR、Python、.NET Metadata、CDB。
**Spec:** docs/superpowers/specs/2026-10-26-constrained-boxing-design.md
## Global Constraints
旧工程和runtime不改；用户已追加授权发布本轮实验与文稿，按精确文件范围提交推送；无第三方实现公开，无性能/所有平台结论。
## Review Focus
原变量与箱副本混淆；跨组输入不同却当metadata因果；缺实现被当语义通过；IL token与实际DLL错配；原生box断点含框架噪声。
### Task 1: Sample and acceptance
- [x] tests/test_box_results.py先RED；实现tools/box_results.py，拒绝错误值/身份、漏事件、错build和错误异常。
- [x] 创建samples/constrained-boxing/Scenarios.cs与projects/constrained-boxing：Contracts/AOT/HotUpdate/Editor；精确源模板绑定，无AOT GenericCalls种子。
Interfaces: parse_player(text,route,mode,metadata,build_id)->events/classification。
### Task 2: Build, CIL and Player
- [x] tools/BoxMetadata与tests真实编译fixture验证operand/signatures；tools/box_lab.py build/run/verify/export。
- [x] 固定原始runtime，完成72Player，保存实际失败或成功；校验最终匹配metadata和热更排除AOT。
### Task 3: Native and documents
- [x] tools/box_trace.py、box_native.py与破坏测试；27native（发现value差异后增补6）按实际符号/box/方法体路径验收。
- [x] 回填4正文3索引3计划和执行记录，干净文稿候选不带无关改动。
- [x] 完整测试、公共边界、Hugo/站内链接/浏览器；独立最终审查并关闭P1/P2。

完成：72普通＋27native＝99事件；206测试、1016公共文件边界通过；Hugo/7页440链接与浏览器表格检查完成，独立审查2项P2修复后关闭。用户已追加授权交付：先提交推送实验，再补齐固定SHA并提交推送文稿。
