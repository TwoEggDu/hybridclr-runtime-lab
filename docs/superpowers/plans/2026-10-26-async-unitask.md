# Async UniTask Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 固定环境验证跨边界状态机挂起、恢复和异常，补强现有案例。
**Architecture:** 独立Unity工程与外部固定UniTask；同源AOT/hot情景、60普通Player、聚焦native跟踪；哈希回执与严格事件解析。
**Tech Stack:** Unity2022.3.62f3 custom、HybridCLR9、UniTask2.5.10、Python、.NET metadata、CDB。
**Spec:** docs/superpowers/specs/2026-10-26-async-unitask-design.md

## Global Constraints
- 上游runtime与旧实验不改；不应用exception-flow补丁；public不复制第三方实现。
- 实现阶段不提交推送；用户后续已授权发布，按精确范围提交推送并保留文稿仓库其他工作；Development/Release热更维度不混作metadata变量。

## Review Focus
- 完成await被误判为真正挂起：验register/complete/dispatch/resume帧和顺序。
- 漏catch/finally仍退出0：逐事件分类，业务结果独立验收。
- 元数据身份/状态机形态猜测：实际最终DLL与裁剪来源读取。
- 旧日志/产物混用：build ID、输入/产物/日志哈希与重解析。
- 历史故障被新样本代替：稿件显式保留历史未知。

### Task 1: 事件验收器与独立工程
- [x] 写tests/test_async_results.py，首先验证缺少解析器失败，覆盖同步/跨帧/前后异常/重复或缺事件/错误build。
- [x] 实现tools/async_results.py；克隆仅tracked项目设置、复用LabRuntime校验；添加samples/async-unitask/Scenarios.cs、AOT事件/门/驱动、Editor构建。
- [x] 解析器测试GREEN；Prepare/Build核对源清单、锁与HotUpdate排除AOT。
Interfaces: parse_player(text,side,mode,metadata,build_id) -> dict(events,classification,counters)。

### Task 2: 构建、普通矩阵与metadata
- [x] tools/async_lab.py build/run/verify/export；独立async-lock.json与prepare入口；MetadataReader读取最终AOT/hot-dev/hot-release。
- [x] 完成60普通进程，对照失败保留；核查on与AOT事件语义以及off实际路径。
- [x] 一致性/日志/导出破坏测试；公开结果只用自有事件。
Interfaces: artifacts/async-unitask/{build-lock,run-results,metadata}.json，evidence/2026-10-26-async-unitask。

### Task 3: native与文稿
- [x] 匹配PDB为实际悬挂路径和AOT泛型方法转换采证；纳入trace/verify。
- [x] 回填3正文、3索引、3canonical plans、执行记录；现有URL不变。
- [x] 完整Python/公开边界检查；独立文稿候选Hugo、链接与页面检查；最终审查证据/结论一致。

完成：182测试、856公开文件检查、72事件验证；Hugo1414页/零错误，六页355链接；最终审查P2已关闭。用户已追加授权交付：先提交推送实验，再以固定SHA更新文章和索引。
