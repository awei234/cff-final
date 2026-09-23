# 基础质量修复 和 JIT Harness 联合升级 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不修改服务器源码快照和已冻结 v4 提交包的前提下，先修复可复现性、PDF、检索审核和 Claim–Evidence 基础质量，再完成受约束 JIT Harness 最小试点及四臂多 seed 对照实验。

**Architecture:** 采用独立工作副本和新增输出目录。基础质量层负责路径、产物状态、来源审核和证据账本；Harness 层通过 Schema、Profile、白名单、预算和 Rail 校验生成受约束 Manifest，并在无效时回退固定 `full-rail`。实验层统一任务、输入、模型、工具、预算和 seed，比较 `baseline`、`prompt-only`、`full-rail`、`jit-constrained`。

**Tech Stack:** Python 3.x、pytest、JSON Schema、SHA256、LaTeX/PDF 工具链、现有 research matrix runner、现有 UCR/Rail 和实验日志系统。

**Spec:** `00_归档说明/JIT与基础质量联合升级路线.md`

## Global Constraints

- 不修改 `03_服务器源码快照/**`。
- 不修改 `01_比赛提交包/**` 中已冻结的 v1–v4 提交包。
- 只在独立工作副本或当前 `feature` 分支中开发。
- 修改前记录 Git 状态、环境、测试结果和关键产物 SHA256。
- JIT Harness 不得执行任意 Python、任意 shell 或未批准工具。
- Manifest 无效时必须回退固定 `full-rail`。
- 不得提升 provider call、retry、token、成本或时延预算。
- 不得禁用 Rail、白名单、预算、来源审核或人工放行门。
- 正式 Claim 必须绑定可定位、可验证且带哈希的 Evidence。
- `approved_for_submission` 只能在人工审核完成后出现。
- 实验臂固定为 `baseline`、`prompt-only`、`full-rail`、`jit-constrained`，seed 至少为 `42、43、44`。

## Review Focus

- 工作副本路径变化时，根目录解析不能依赖固定 `parents[n]`；由 Task 1 的跨环境路径测试固定行为。
- LaTeX 编译启动、成功验证和失败状态不能互相矛盾；由 Task 2 的状态机和失败测试固定行为。
- 未审核来源不能成为正式证据；由 Task 3 的来源状态和放行测试固定行为。
- 被篡改的证据文件必须被发现；由 Task 3 的 SHA256/Provenance 测试固定行为。
- JIT Manifest 试图启用未批准工具、提高预算或关闭 Rail 时必须拒绝并回退；由 Task 5 的校验和回退测试固定行为。

---

### Task 1: 基线冻结与独立工作副本

**Files:**
- Create: `02_v4本机工作副本/baseline/baseline_manifest.json`
- Create: `02_v4本机工作副本/baseline/environment.json`
- Create: `02_v4本机工作副本/baseline/test_baseline.json`
- Create: `02_v4本机工作副本/baseline/checksums.sha256`
- Test: `tests/test_baseline_integrity.py`

**Interfaces:**
- Consumes: 当前 Git 状态、Python/依赖版本、现有测试命令、冻结文件清单。
- Produces: 可审计的基线清单、哈希清单和测试基线，供所有后续任务比较。

- [ ] **Step 1: 写入基线记录测试**

```python
def test_protected_paths_are_recorded_and_unchanged():
    manifest = load_baseline_manifest()
    assert "03_服务器源码快照" in manifest["protected_roots"]
    assert manifest["checksums_sha256"]
```

- [ ] **Step 2: 运行测试确认初始失败**

运行：`pytest tests/test_baseline_integrity.py -q`

预期：FAIL，原因是基线文件尚未生成。

- [ ] **Step 3: 生成基线文件**

记录提交、分支、解释器、依赖、模型配置、运行命令、测试结果和受保护文件 SHA256；输出只写入 `02_v4本机工作副本/baseline/`。

- [ ] **Step 4: 运行测试确认通过**

运行：`pytest tests/test_baseline_integrity.py -q`

预期：PASS。

- [ ] **Step 5: 提交基线变更**

```bash
git add "02_v4本机工作副本/baseline" tests/test_baseline_integrity.py
git commit -m "chore: freeze v4 baseline"
```

### Task 2: 路径解析、跨环境复现与 PDF 状态一致性

**Files:**
- Create: `competition_runner/competition_runner/paths.py`
- Create: `competition_runner/competition_runner/pdf_state.py`
- Modify: `competition_runner/competition_runner/cli.py`
- Modify: `competition_runner/competition_runner/research_matrix_v4.py`
- Test: `competition_runner/tests/test_paths.py`
- Test: `competition_runner/tests/test_cli.py`
- Test: `competition_runner/tests/test_pdf_state.py`
- Test: `competition_runner/tests/test_pdf_consistency.py`

**Interfaces:**
- Consumes: 当前脚本路径、项目根标记、显式环境变量和输出目录配置。
- Produces: `resolve_project_root(start: Path) -> Path`、`PdfStateMachine`、统一 PDF 状态记录。

- [ ] **Step 1: 写路径和 PDF 状态失败测试**

测试至少覆盖：独立副本、嵌套目录、缺失根标记、`tex_generated`、`pdf_compile_started`、`compiled_verified`、`compile_failed`。

- [ ] **Step 2: 运行测试确认失败**

运行：`pytest competition_runner/tests/test_paths.py competition_runner/tests/test_pdf_state.py -q`

预期：FAIL，原因是统一解析器和状态机尚未实现。

- [ ] **Step 3: 实现统一路径解析和 PDF 状态机**

禁止使用固定 `parents[4]`；PDF 只有在文件存在、可读取、页数有效且哈希已记录后才能进入 `compiled_verified`。

- [ ] **Step 4: 将 CLI 和 research matrix 接入统一接口**

保持现有调用兼容，不改变原始 v4 输出目录；新状态写入新增运行目录。

- [ ] **Step 5: 运行目标测试**

运行：`pytest competition_runner/tests/test_paths.py competition_runner/tests/test_cli.py competition_runner/tests/test_pdf_state.py competition_runner/tests/test_pdf_consistency.py -q`

预期：全部 PASS。

- [ ] **Step 6: 提交路径和 PDF 变更**

```bash
git add competition_runner/competition_runner competition_runner/tests
git commit -m "fix: make paths and pdf state reproducible"
```

### Task 3: 来源审核与 Claim–Evidence 账本

**Files:**
- Create: `competition_runner/competition_runner/source_registry.py`
- Create: `competition_runner/competition_runner/review_gate.py`
- Create: `competition_runner/competition_runner/claim_evidence.py`
- Create: `competition_runner/competition_runner/provenance.py`
- Create: `schemas/source_record.schema.json`
- Create: `schemas/claim_evidence.schema.json`
- Test: `competition_runner/tests/test_source_registry.py`
- Test: `competition_runner/tests/test_review_gate.py`
- Test: `competition_runner/tests/test_claim_evidence.py`
- Test: `competition_runner/tests/test_provenance_hash.py`

**Interfaces:**
- Consumes: 检索结果、来源文件、Claim 文本和证据定位信息。
- Produces: `SourceRecord`、`ClaimEvidenceRecord`、审核状态和 SHA256 provenance。

- [ ] **Step 1: 写来源状态和 Claim–Evidence 失败测试**

覆盖 `discovered → retrieved → verified → approved_for_claim`，以及未审核来源、缺定位信息、文件篡改三类拒绝路径。

- [ ] **Step 2: 运行测试确认失败**

运行：`pytest competition_runner/tests/test_source_registry.py competition_runner/tests/test_claim_evidence.py -q`

预期：FAIL。

- [ ] **Step 3: 实现来源注册表、审核门和证据账本**

每条正式 Claim 保存 `claim_id`、`evidence_id`、artifact 路径、JSON pointer/页码、摘录、来源状态、SHA256、验证时间和审核状态。

- [ ] **Step 4: 实现哈希篡改检测**

证据内容变化时返回明确的 `hash_mismatch`，禁止继续进入正式 Claim。

- [ ] **Step 5: 运行目标测试**

运行：`pytest competition_runner/tests/test_source_registry.py competition_runner/tests/test_review_gate.py competition_runner/tests/test_claim_evidence.py competition_runner/tests/test_provenance_hash.py -q`

预期：全部 PASS。

- [ ] **Step 6: 提交证据链变更**

```bash
git add competition_runner/competition_runner schemas competition_runner/tests
git commit -m "feat: strengthen source review and claim evidence ledger"
```

### Task 4: 真实 Context-Engineering 三 seed 基线实验

**Files:**
- Create: `experiments/context_engineering_v1/task_set.json`
- Create: `experiments/context_engineering_v1/run_config.json`
- Create: `experiments/context_engineering_v1/run_experiment.py`
- Create: `experiments/context_engineering_v1/metrics.py`
- Create: `experiments/context_engineering_v1/aggregate_results.py`
- Create: `competition_runner/tests/test_context_experiment.py`
- Create: `competition_runner/tests/test_metrics.py`
- Create: `experiments/context_engineering_v1/reports/README.md`

**Interfaces:**
- Consumes: 固定任务集、统一模型/工具/预算和 seeds `42、43、44`。
- Produces: `baseline`、`prompt-only`、`full-rail` 逐任务轨迹、指标、成本、时延和报告。

- [ ] **Step 1: 写实验配置和指标失败测试**

指标必须包含任务成功率、准确率、证据覆盖率、unsupported completion rate、误引用率、失败率、token、成本和时延。

- [ ] **Step 2: 运行测试确认失败**

运行：`pytest competition_runner/tests/test_context_experiment.py competition_runner/tests/test_metrics.py -q`

预期：FAIL。

- [ ] **Step 3: 实现固定任务和三臂运行器**

所有实验臂复用相同任务、输入、模型、工具、预算和人工审核规则。

- [ ] **Step 4: 执行三个 seed**

输出写入 `experiments/context_engineering_v1/results/seed-{seed}/{arm}/`，不得覆盖历史结果。

- [ ] **Step 5: 汇总并运行测试**

运行：`pytest competition_runner/tests/test_context_experiment.py competition_runner/tests/test_metrics.py -q`

预期：PASS，且三个 seed 的所有实验臂均有逐任务记录。

- [ ] **Step 6: 提交实验基础设施**

```bash
git add experiments/context_engineering_v1 competition_runner/tests
git commit -m "feat: add reproducible context engineering baselines"
```

### Task 5: JIT Harness Manifest、Profile、Schema 与校验器

**Files:**
- Create: `competition_runner/competition_runner/harness/schema.py`
- Create: `competition_runner/competition_runner/harness/profiles.py`
- Create: `competition_runner/competition_runner/harness/planner.py`
- Create: `competition_runner/competition_runner/harness/validator.py`
- Create: `schemas/harness.schema.json`
- Create: `config/harness_profiles.json`
- Test: `competition_runner/tests/test_harness_schema.py`
- Test: `competition_runner/tests/test_harness_validator.py`
- Test: `competition_runner/tests/test_harness_budget.py`
- Test: `competition_runner/tests/test_harness_fallback.py`

**Interfaces:**
- Consumes: 任务特征、材料特征、历史失败模式和预算。
- Produces: `HarnessManifest`、`ValidationResult`；无效 Manifest 必须回退 `full-rail`。

- [ ] **Step 1: 写 Manifest Schema 和安全约束失败测试**

覆盖四个 Profile：`evidence_first`、`experiment_first`、`repair_first`、`cost_limited`；覆盖未批准工具、超预算、关闭 Rail、任意执行字段和超重试次数。

- [ ] **Step 2: 运行测试确认失败**

运行：`pytest competition_runner/tests/test_harness_schema.py competition_runner/tests/test_harness_validator.py -q`

预期：FAIL。

- [ ] **Step 3: 实现 JSON Schema 和 Profile 注册表**

Manifest 必须包含 `profile`、`memory_mode`、`planning_mode`、`enabled_tools`、`max_provider_calls`、`max_retries`、`selection_reason`。

- [ ] **Step 4: 实现白名单、预算和 Rail 校验**

校验器不得执行 Manifest 中的代码；只解释和校验声明。任何失败返回结构化原因并选择固定 `full-rail`。

- [ ] **Step 5: 实现确定性 Planner**

首版只允许规则化、可解释的策略选择，禁止自由生成工具或执行计划。

- [ ] **Step 6: 运行目标测试**

运行：`pytest competition_runner/tests/test_harness_schema.py competition_runner/tests/test_harness_validator.py competition_runner/tests/test_harness_budget.py competition_runner/tests/test_harness_fallback.py -q`

预期：全部 PASS。

- [ ] **Step 7: 提交 Harness 安全基础**

```bash
git add competition_runner/competition_runner/harness schemas/harness.schema.json config/harness_profiles.json competition_runner/tests
git commit -m "feat: add constrained jit harness validation"
```

### Task 6: Harness 选择器、运行集成与审计归档

**Files:**
- Create: `competition_runner/competition_runner/harness/selector.py`
- Create: `competition_runner/competition_runner/harness/archive.py`
- Modify: `competition_runner/competition_runner/research_matrix_v4.py`
- Test: `competition_runner/tests/test_harness_selector.py`
- Test: `competition_runner/tests/test_harness_archive.py`
- Test: `competition_runner/tests/test_harness_integration.py`

**Interfaces:**
- Consumes: Task 5 的 `HarnessManifest` 和 `ValidationResult`。
- Produces: `select_harness(task_features) -> HarnessManifest`、完整 Harness archive。

- [ ] **Step 1: 写选择器和归档失败测试**

测试不同任务特征的 Profile 选择、选择理由、无效回退和重复运行唯一标识。

- [ ] **Step 2: 运行测试确认失败**

运行：`pytest competition_runner/tests/test_harness_selector.py competition_runner/tests/test_harness_archive.py -q`

预期：FAIL。

- [ ] **Step 3: 实现选择器**

选择结果必须包含 Profile、原因、工具、预算和验证结果，且可复现。

- [ ] **Step 4: 实现归档器**

保存策略选择、Manifest、校验结果、调用次数、成本、时延、证据、Rail 结果、日志、输入输出哈希和人工审核结论。

- [ ] **Step 5: 只在 `run_topic()` 接入受控链路**

接入顺序固定为：

```text
build_harness_manifest()
→ validate_harness_manifest()
→ run_real_task_or_ucr()
→ write_claim_evidence_and_provenance()
→ archive_harness_run()
```

- [ ] **Step 6: 运行集成测试**

运行：`pytest competition_runner/tests/test_harness_selector.py competition_runner/tests/test_harness_archive.py competition_runner/tests/test_harness_integration.py -q`

预期：全部 PASS，且旧运行路径仍可用。

- [ ] **Step 7: 提交 Harness 集成**

```bash
git add competition_runner/competition_runner/harness competition_runner/competition_runner/research_matrix_v4.py competition_runner/tests
git commit -m "feat: integrate jit harness with auditable archive"
```

### Task 7: 四臂多 seed 对照实验与门槛判定

**Files:**
- Create: `experiments/jit_comparison_v1/arm_configs.json`
- Create: `experiments/jit_comparison_v1/run_comparison.py`
- Create: `experiments/jit_comparison_v1/metrics_schema.json`
- Create: `experiments/jit_comparison_v1/report.md`
- Create: `competition_runner/tests/test_jit_comparison.py`

**Interfaces:**
- Consumes: Task 4 的固定任务集和 Task 6 的 Harness 归档。
- Produces: 四臂、三 seed 的逐任务结果、聚合指标、门槛判定和可审计报告。

- [ ] **Step 1: 写四臂比较失败测试**

断言四个实验臂、三个 seed、相同任务输入和统一预算均存在。

- [ ] **Step 2: 运行测试确认失败**

运行：`pytest competition_runner/tests/test_jit_comparison.py -q`

预期：FAIL。

- [ ] **Step 3: 实现四臂运行器**

新增 `jit-constrained`，保留 `baseline`、`prompt-only`、`full-rail`，不改变实验输入和预算。

- [ ] **Step 4: 执行 42/43/44 三个 seed**

结果写入 `experiments/jit_comparison_v1/results/seed-{seed}/{arm}/`，同时保存 Manifest、选择理由、成本、时延、证据和哈希。

- [ ] **Step 5: 实现门槛判定**

至少检查：任务成功率不下降、证据覆盖率不下降、误引用率/UCR 不上升、成本和时延在预算内、审核负担没有大幅增加。

- [ ] **Step 6: 运行实验和测试**

运行：`pytest competition_runner/tests/test_jit_comparison.py -q`

预期：PASS；报告中明确记录通过、未通过或需要人工复核的门槛。

- [ ] **Step 7: 提交对照实验**

```bash
git add experiments/jit_comparison_v1 competition_runner/tests
git commit -m "exp: compare constrained jit against fixed rails"
```

### Task 8: 论文、PDF、复现说明和发布检查

**Files:**
- Modify: `docs/README.md` 或现有复现说明文件
- Modify: 论文源文件所在的独立工作副本
- Create: `docs/reports/jit-harness-comparison.md`
- Create: `docs/reports/release-verification.md`
- Test: `tests/test_release_verification.py`

**Interfaces:**
- Consumes: 所有阶段的测试结果、实验报告、证据账本、PDF 状态和哈希。
- Produces: 更新后的方法说明、实验报告、PDF 验证结果和独立发布检查单。

- [ ] **Step 1: 写发布检查失败测试**

检查受保护哈希、测试结果、PDF 状态、Claim–Evidence 完整性、JIT 归档完整性和人工审核状态。

- [ ] **Step 2: 运行测试确认失败**

运行：`pytest tests/test_release_verification.py -q`

预期：FAIL，直到所有实验和审核产物齐备。

- [ ] **Step 3: 更新论文和复现说明**

只写入实际完成并可追溯的结果；明确 JIT Harness 的约束、回退机制和人工审核边界。

- [ ] **Step 4: 重新生成并验证 PDF**

使用 Task 2 的状态机记录编译开始、编译成功/失败、PDF 哈希和页数。

- [ ] **Step 5: 运行完整验证**

运行：`pytest -q`

预期：全部 PASS；发布检查报告明确列出所有通过项和任何未决人工审核项。

- [ ] **Step 6: 提交最终文档**

```bash
git add docs tests
git commit -m "docs: publish quality and jit harness verification"
```

## 完成判定

只有同时满足以下条件才可称为完成：

1. `03_服务器源码快照/**` 和冻结 v4 提交包哈希未变化。
2. 路径解析可在独立工作副本和 CI 模拟环境复现。
3. 现有测试和新增测试全部通过。
4. LaTeX/PDF 状态、日志和提交报告一致。
5. 每个正式 Claim 都有可定位、已审核、带 SHA256 的 Evidence。
6. `baseline`、`prompt-only`、`full-rail`、`jit-constrained` 均完成 42/43/44 三 seed 对照。
7. JIT Harness 的 Manifest、Profile、Schema、白名单、预算、Rail、回退和归档均有测试。
8. 所有策略选择、成本、时延、证据和哈希均可审计。
9. JIT 不降低任务成功率，不增加证据违规、误引用或 unsupported completion。
10. 论文和 PDF 不包含未经验证或未经人工审核的结论。

