# 可审计科研闭环升级实施方案

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 JiuwenSwarm 从“能生成科研流程产物的半流程原型”升级为“能够用一个真实 Agent 任务证明证据护栏有效、结果可复现、结论可追溯”的可审计科研闭环。

**Architecture:** 保留现有 `competition_runner`、UCR、Rail 和 Claim—Evidence 账本，不先扩展更多主题。先修复路径和交接证据，再以 `context-engineering` 为唯一真实试验主题，最后把实验结果、引用审核和论文生成统一接入同一条证据链。`memory-engine` 与 `self-evolution` 在首个主题验收通过后再复用同一协议。

**Tech Stack:** Python 3、pytest、JSON/JSONL、UCR benchmark、JiuwenSwarm Rail、XeLaTeX、SHA-256 provenance。

**Spec:** `00_归档说明/下一步优先改进清单.md`；侧边聊天结论为“Rail 与部分回归测试已经落地，但 D01—D10 资料追踪、缺失证据清单、正式映射文件及完整阶段验收尚未闭环”。

## Global Constraints

- 当前工作分支固定为 `feature`，不直接在 `main` 上开发。
- 现有 v1/v2/v3/v4 归档和已生成实验结果只读保留，不覆盖历史证据。
- UCR 的 `process_evidence_only` 结果不能写成领域科学效果结论。
- 没有原始运行目录、人工标签或环境记录时，必须标记为证据缺失，不得推断完成。
- 所有正式结论必须绑定 Claim—Evidence 记录、JSON Pointer 和 SHA-256。
- 外部 Provider 调用必须通过显式安全开关，并记录调用预算、模型、提示词哈希和响应哈希。
- 论文只有在 XeLaTeX 编译成功、PDF 检查通过且人工审核完成后，才能标记为可提交。

## Review Focus

- 从归档根目录外启动 CLI：必须解析到正确项目根，不得依赖当前工作目录。
- 缺少 D01—D10 原始证据：必须生成可追踪的缺失记录，不得生成“已验证”结论。
- 同一条声明同时包含成功和失败操作：必须逐操作绑定证据，不能按整句错误放行。
- 实验结果 JSON 被修改：相关 provenance 和 claim 哈希必须验证失败。
- LaTeX 编译失败或引用未批准：必须阻止 `compiled_verified` 或 `approved_for_submission` 状态。

## 核心思想

项目的核心不是让 Agent 自动写出一篇看起来像论文的文本，而是把 Agent 的每一个“完成声明”绑定到可验证的执行证据上。

核心闭环如下：

```text
Agent 计划
  → 调用工具和执行任务
  → 记录成功、失败、拒绝、缺失和重试事件
  → Rail 检查声明是否有匹配证据
  → Claim—Evidence 账本记录结论及 JSON Pointer
  → 人工确认来源、实验真实性和结论范围
  → 生成可复核的报告与论文
```

因此，项目的第一研究问题应收敛为：

> 在相同输入和任务预算下，结构化上下文与证据护栏能否降低 Agent 的无证据完成声明，并提高结果的可追溯性？

这里的“提高”必须由真实任务指标和固定对照实验支持，而不能只由流程文件是否生成来证明。

## 当前状态结论

- 已完成：Rail 核心机制、部分声明/执行证据测试、UCR 三 arm 协议、三阶段 Provider 流程、provenance 和提交包验证。
- 部分完成：项目路径可移植性、正式 Rail 映射、复杂句逐操作绑定、冲突/重试/时间关系测试。
- 未完成：D01—D10 证据库存和缺失清单、人工来源审批、一个真实 Agent 任务的多 seed 对照实验、完整阶段验收闭环。

---

### Task 1: 建立稳定的项目根和跨环境运行基线

**Files:**
- Modify: `02_v4本机工作副本/CCF_BDCI_1167_Prototype_Submission_20260920_v4_work/code/03_技术实现/competition_runner/competition_runner/paths.py`
- Modify: `02_v4本机工作副本/CCF_BDCI_1167_Prototype_Submission_20260920_v4_work/code/03_技术实现/competition_runner/competition_runner/main.py`
- Test: `02_v4本机工作副本/CCF_BDCI_1167_Prototype_Submission_20260920_v4_work/code/03_技术实现/competition_runner/tests/test_paths.py`
- Test: `02_v4本机工作副本/CCF_BDCI_1167_Prototype_Submission_20260920_v4_work/code/03_技术实现/competition_runner/tests/test_cli.py`

**Interfaces:**
- Consumes: CLI 文件路径或模块路径作为 anchor。
- Produces: `find_project_root(anchor: Path) -> Path` 和 `resolve_paths(anchor: Path | None) -> ResolvedPaths`，两者不读取当前工作目录来决定项目根。

- [ ] **Step 1: 固定失败场景**：在 `tmp_path` 外部目录执行 `main.py paths`，并断言返回码为 0；断言 `project_root`、`workspace_root` 和 `experiment_script` 均位于同一个提交包根下。
- [ ] **Step 2: 运行路径测试**：运行 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_paths.py tests/test_cli.py -q`，确认当前失败集中在根目录识别。
- [ ] **Step 3: 实现候选根识别**：按“提交包标志文件、`code/03_技术实现`、`README.md`、`submission_manifest.json`”组合判断候选根，禁止依赖固定 `parents[n]`。
- [ ] **Step 4: 复跑路径测试**：同一命令必须全部通过，并从项目目录外再执行一次 CLI。
- [ ] **Step 5: 提交**：`git add` 相关代码和测试，提交信息为 `fix: make project root discovery portable`。

### Task 2: 建立第一批交接证据库存和缺失证据清单

**Files:**
- Create: `docs/evidence/experiment_inventory.csv`
- Create: `docs/evidence/evidence_index.csv`
- Create: `docs/evidence/missing_evidence.md`
- Create: `docs/evidence/rail_implementation_map.md`
- Create: `docs/evidence/acceptance_status.md`
- Modify: `00_归档说明/README_完整归档说明.md`

**Interfaces:**
- Consumes: 当前 `demo_runs`、`03_服务器源码快照/custom_rails`、`04_服务器v4实验工作区/v4_server_workspace` 和提交包中的 manifest/checksum。
- Produces: 每项证据的 `evidence_id`、来源路径、类型、SHA-256、状态、缺失原因和下一步责任。

- [ ] **Step 1: 建立库存字段**：`experiment_inventory.csv` 至少包含 `experiment_id, topic_id, arm, seed, source_path, status, sha256, environment, notes`。
- [ ] **Step 2: 建立证据索引字段**：`evidence_index.csv` 至少包含 `evidence_id, kind, artifact, json_pointer, sha256, status, reviewer, reviewed_at`。
- [ ] **Step 3: 逐项登记 D01—D10**：对存在的原始实验、人工标签、环境记录和图表输入填写路径和哈希；不存在的项写入 `missing_evidence.md`，状态使用 `missing_external_artifact`。
- [ ] **Step 4: 绘制 Rail 映射**：记录 `competition_runner → UCR → custom_rails → paper/report` 的真实调用关系，并区分“当前直接调用”和“仅归档保留”。
- [ ] **Step 5: 记录阶段状态**：在 `acceptance_status.md` 中明确 `implemented`、`partially_verified`、`missing_evidence`、`human_review_pending` 四种状态。
- [ ] **Step 6: 提交**：提交信息为 `docs: add evidence inventory and handoff status`。

### Task 3: 完成 context-engineering 真实 Agent 实验

**Files:**
- Create: `04_服务器v4实验工作区/v4_server_workspace/code/03_技术实现/competition_runner/config/context_engineering_task_v1.json`
- Create: `04_服务器v4实验工作区/v4_server_workspace/code/03_技术实现/competition_runner/tests/test_context_engineering_task.py`
- Modify: `04_服务器v4实验工作区/v4_server_workspace/code/03_技术实现/competition_runner/competition_runner/research_matrix_v4.py`
- Modify: `04_服务器v4实验工作区/v4_server_workspace/code/03_技术实现/competition_runner/competition_runner/research_matrix.py`
- Create: `04_服务器v4实验工作区/v4_server_workspace/demo_runs/context_engineering_real_v1/`

**Interfaces:**
- Consumes: 固定资料包、固定任务输入、三种 arm、seed 列表 `[42, 43, 44]`。
- Produces: 每次运行的 `task_input.json`、`tool_trace.jsonl`、`claims.json`、`evidence.jsonl`、`results.json`、`provenance.json` 和统一汇总 `aggregate_results.json`。

- [ ] **Step 1: 定义任务输入**：固定 10 个事实检索问题、2 个需要工具调用的问题和 2 个带干扰来源的问题；每个问题保存标准答案、允许来源和评分规则。
- [ ] **Step 2: 定义三种 arm**：`baseline` 仅使用普通提示；`prompt-only` 使用结构化输出格式；`full-rail` 额外要求每个结论绑定 evidence ref。
- [ ] **Step 3: 固定预算和 seed**：三种 arm、三个 seed 使用同一资料集、最大工具调用数和超时规则。
- [ ] **Step 4: 写失败测试**：测试缺失来源、错误引用、工具失败、重试和“成功/失败混合句”不得被整体标记为 supported。
- [ ] **Step 5: 接入真实 runner**：只允许通过现有 Provider 安全门调用；禁止将 fixture 输出伪装成真实任务结果。
- [ ] **Step 6: 运行三 seed**：分别保存原始 stdout、stderr、返回码、耗时、调用次数和响应哈希。
- [ ] **Step 7: 汇总结果**：计算任务成功率、答案准确率、证据覆盖率、无证据结论率、误引用率、耗时和调用成本。
- [ ] **Step 8: 提交**：提交信息为 `feat: add reproducible context engineering experiment`。

### Task 4: 强化 Claim—Evidence 账本和独立评分

**Files:**
- Modify: `04_服务器v4实验工作区/v4_server_workspace/code/03_技术实现/ucr_benchmark/ucr_benchmark/claims.py`
- Modify: `04_服务器v4实验工作区/v4_server_workspace/code/03_技术实现/ucr_benchmark/ucr_benchmark/evidence.py`
- Modify: `04_服务器v4实验工作区/v4_server_workspace/code/03_技术实现/ucr_benchmark/ucr_benchmark/metrics.py`
- Create: `04_服务器v4实验工作区/v4_server_workspace/code/03_技术实现/ucr_benchmark/tests/test_claim_evidence_integrity.py`
- Create: `04_服务器v4实验工作区/v4_server_workspace/code/03_技术实现/ucr_benchmark/tests/test_context_metrics.py`

**Interfaces:**
- Consumes: Task 3 的 `results.json`、执行事件和来源记录。
- Produces: `ClaimRecord`、`EvidenceRecord`、`MetricResult`；所有记录包含状态、来源 artifact、JSON Pointer 和 SHA-256。

- [ ] **Step 1: 固定账本结构**：实验 claim 使用 `claim_id, claim_type, status, evidence_refs, support_reason`；来源 claim 额外使用 `source_refs` 和 `citation_allowed`。
- [ ] **Step 2: 写完整性测试**：篡改实验 JSON、删除 JSON Pointer、替换来源哈希或引用未批准来源时，验证器必须失败。
- [ ] **Step 3: 写指标测试**：用固定小样本验证准确率、覆盖率、无证据率和误引用率的分子分母，避免把 `task_success_rate=1.0` 当成全部质量指标。
- [ ] **Step 4: 增加汇总器**：按 arm 和 seed 输出均值、标准差、样本数以及失败原因，不把失败运行从分母中静默删除。
- [ ] **Step 5: 复跑测试**：运行 UCR 和 context-engineering 相关测试，确保旧有 process-evidence 流程仍然通过。
- [ ] **Step 6: 提交**：提交信息为 `feat: enforce claim evidence integrity and metrics`。

### Task 5: 增加来源审核和论文生成门

**Files:**
- Modify: `04_服务器v4实验工作区/v4_server_workspace/code/03_技术实现/competition_runner/competition_runner/research_matrix_v4.py`
- Modify: `02_v4本机工作副本/CCF_BDCI_1167_Prototype_Submission_20260920_v4_work/verify_submission.py`
- Create: `docs/review/source_review_protocol.md`
- Create: `docs/review/paper_release_gate.md`
- Test: `02_v4本机工作副本/CCF_BDCI_1167_Prototype_Submission_20260920_v4_work/code/03_技术实现/competition_runner/tests/test_artifact_contract.py`

**Interfaces:**
- Consumes: 来源记录、人工审核事件、Claim—Evidence 账本、LaTeX 编译日志和 PDF 哈希。
- Produces: `approved_for_citation`、`compiled_verified`、`approved_for_submission` 三个可审计状态。

- [ ] **Step 1: 定义来源审核协议**：每条来源必须有 `reviewer, decision, reason, reviewed_at, source_sha256`；未审核来源只能保持 `citation_allowed=false`。
- [ ] **Step 2: 定义论文发布门**：存在 unsupported claim、未批准引用、实验哈希不匹配或 PDF 编译失败时，阻止正式论文状态。
- [ ] **Step 3: 增加状态测试**：分别测试来源拒绝、引用缺失、PDF 编译失败和人工审核未完成四种阻断。
- [ ] **Step 4: 执行真实 XeLaTeX 编译**：保存编译命令、两遍日志、返回码、PDF 页数、PDF SHA-256 和文本抽取检查结果。
- [ ] **Step 5: 复核提交包**：运行 `python verify_submission.py`，并在解压副本上再次执行。
- [ ] **Step 6: 提交**：提交信息为 `feat: add source and paper release gates`。

### Task 6: 形成第一阶段验收和后续扩展模板

**Files:**
- Create: `docs/acceptance/context-engineering-v1-acceptance.md`
- Modify: `00_归档说明/下一步优先改进清单.md`
- Modify: `00_归档说明/README_完整归档说明.md`

**Interfaces:**
- Consumes: Tasks 1—5 的测试结果、实验汇总、证据索引、人工审核和发布门状态。
- Produces: 一个可供评审查看的第一阶段验收报告，以及可复制到 `memory-engine` 和 `self-evolution` 的实验模板。

- [ ] **Step 1: 汇总验收矩阵**：列出路径、实验、指标、证据、来源、PDF、人工审核七类检查及状态。
- [ ] **Step 2: 明确结论边界**：报告只允许声称“在固定任务上观察到某指标变化”，不允许外推为三个领域已被证明有效。
- [ ] **Step 3: 记录尚未完成项**：所有缺失证据和未完成人工确认必须保留，不用成功状态覆盖。
- [ ] **Step 4: 复制主题模板**：只复制协议、schema 和测试框架，不复制实验结果或结论。
- [ ] **Step 5: 运行完整回归**：运行 competition runner、UCR benchmark、提交验证和 PDF 检查。
- [ ] **Step 6: 提交**：提交信息为 `docs: record context engineering acceptance`。

## 验收门槛

第一阶段只有同时满足以下条件，才算完成：

1. 路径和 CLI 测试全部通过；
2. D01—D10 有完整库存，缺失项有明确记录；
3. `context-engineering` 完成 3 个 seed × 3 个 arm 的真实任务实验；
4. 所有正式结论均能追溯到 Claim—Evidence 账本；
5. 至少 5 条来源完成人工批准或明确拒绝；
6. LaTeX/PDF 编译状态真实可复核；
7. 人工确认完成前，状态保持 `completed_pending_human_review`，不得标记为最终提交。

## 推荐提交节奏

```text
Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6
```

每个任务独立提交并通过对应测试后，再进入下一任务。这样可以在真实实验失败时回滚实验层，而不影响已经修复的路径、证据索引和验证器。

## 方案完成后的预期结果

完成第一阶段后，项目的定位可以从：

```text
可审计的科研论文半流程原型
```

提升为：

```text
在一个真实 Agent 任务上具备可复现对照实验、证据级追踪和明确结论边界的科研 Agent 评测系统
```

此后再扩展 `memory-engine` 和 `self-evolution`，才有足够可靠的协议、指标和证据基础。
