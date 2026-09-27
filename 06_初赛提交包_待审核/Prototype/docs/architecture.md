# JiuwenSwarm 可审计科研 Agent 架构

## 1. 目标与边界

系统面向“基于公开资料形成研究计划、运行受约束实验、核对 Claim–Evidence、生成论文材料”的科研辅助流程。模型负责规划和文本综合，确定性程序负责权限、预算、Schema、执行证据、引用审批和发布门禁。

当前证据证明的是流程可追溯性和约束机制，不把 UCR 指标外推为三个研究主题的领域效果，也不声称完全无人监督科研。

## 2. 分层结构

```text
Web / CLI
   |
   v
JiuwenSwarm Agent Orchestrator
   |-- model/provider configuration
   |-- tools and skills
   |-- human interaction
   |
   v
Competition Research Runner
   |-- OpenAlex / arXiv / Crossref metadata retrieval
   |-- plan -> evidence review -> report
   |-- Claim–Evidence ledger and citation approval
   |
   +-----------------------------+
   |                             |
   v                             v
UCR Experiment Runner       JIT Harness Control Plane
   |-- no-rail                  |-- constrained Manifest
   |-- prompt-only              |-- safe Profile selector
   |-- full-rail                |-- Schema / allowlist / budget
   |-- jit-constrained          |-- hard Rail validation
   +-------------+---------------+
                 |
                 v
Audit Artifacts
Manifest, traces, costs, latency, evidence, hashes, provenance,
review decisions, verification reports
```

## 3. 研究数据流

1. 读取固定主题、seed、Provider 预算和输出目录。
2. 从 OpenAlex、arXiv、Crossref 获取公开元数据；按 DOI、来源 ID 和规范化标题去重。
3. 保存来源 ID、标题、作者、年份、URL、摘要边界和 SHA-256，不打包论文全文。
4. 生成研究计划；模型输出必须符合结构化契约。
5. 运行确定性 UCR 场景，先产生不可变工具事件，再提取完成性 Claim。
6. 将 Claim 与成功、失败、拒绝、缺失等执行事件匹配。
7. Rail 拒绝无证据完成声明；审核器只允许已批准来源和 Claim 进入论文材料。
8. 保存执行报告、人工决策、provenance 和验证结果。

Provider 输出不能修改原始实验结果；未知 citation、非法 JSON、预算越界或哈希不一致都会被阻断并留下失败证据。

## 4. JIT Harness

`jit-constrained` 是第四实验臂。它从受约束 Manifest 中选择安全 Profile，但不能生成或执行任意 Python/Shell，也不能扩大调用次数、工具白名单或 Rail 权限。

安全不变量：

- Manifest 必须通过 Schema；
- 工具必须属于白名单；
- Provider 调用同时受 `max_provider_calls` 与重试上限约束；
- JIT 运行时 Rail 必须启用；
- 无效选择回退到固定 `full-rail`；
- 每次运行保存策略选择、成本、时延、证据、档案与 SHA-256。

正式对照为 4 个实验臂 × seeds 42、43、44，共 12 个运行。历史冻结三臂数据不重写，避免破坏原任务与 Manifest 哈希。

## 5. 审核与发布门

来源审核决定材料能否正式引用；Claim 审核决定结论能否进入论文。当前授权运行中，`claim-018` 至 `claim-020` 已批准，`claim-002`、`003`、`005`、`007`、`009` 保留为明确排除项，三个主题均为 `allow_paper=true`。

seed 43/44 用于复现性证据，其新增来源仍保持未批准状态，不能自动进入正式引用清单。

## 6. 部署与数据边界

凭据只从环境变量或本机运行态配置读取，不写入实验产物。提交包排除 `.venv`、`node_modules`、`runtime_local`、会话历史、缓存、日志、字节码和 API Key。

审核包与原 `feature` 工作副本隔离；冻结提交包和服务器源码快照不修改。
