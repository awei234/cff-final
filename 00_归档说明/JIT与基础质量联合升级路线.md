# JiuwenSwarm：基础质量与 JIT Harness 联合升级路线

## 目标

在不改动已冻结 v4 提交包、服务器原始 `jiuwenswarm` 源码快照和 `custom_rails` 源码快照的前提下，先补齐项目的可信性与可复现性基础，再在独立工作副本中验证“受约束 JIT Harness”是否能带来真实提升。

本路线不把 JIT-Agent 视为对现有问题的替代方案。JIT 主要解决任务适配、策略选择、成本和性能权衡；路径、引用、PDF、人工审核与真实实验等基础问题必须单独完成。

## 总体路线

```text
冻结 v4 基线
  → 基础质量修复
  → 真实 context-engineering 实验
  → 受约束 JIT Harness 试点
  → 固定流程与 JIT 对照
  → 人工审核、论文更新与重新打包
```

## 不变原则

- 不修改 `03_服务器源码快照/jiuwenswarm/`；
- 不修改 `03_服务器源码快照/custom_rails/`；
- 不修改已冻结的 v1、v2、v3、v4 比赛 ZIP；
- 所有实现仅在独立工作副本或新分支中进行；
- Rail、调用预算、工具白名单、Claim--Evidence 和人工审核不能被 JIT 绕过；
- JIT 生成的任何策略都必须可审计、可验证、可回退。

## 阶段 0：冻结基线

### 目的

保留当前 v4 的可比较状态，避免后续改动后无法说明分数、结果或成本为什么变化。

### 工作项

- 保存当前工作副本、PDF、运行记录和校验和；
- 记录当前测试结果和已知失败用例；
- 固定 Python、依赖、模型 ID、提示词版本和运行命令；
- 为后续新实验使用新的输出目录，禁止覆盖现有 `demo_runs/research_matrix_v4/`。

### 验收

- 现有 ZIP 校验和不变；
- `verify_submission.py` 仍可执行；
- 新工作不修改原始归档文件。

## 阶段 1：基础质量修复

### 1.1 路径与跨环境复现

#### 问题

项目根目录发现和默认路径解析在不同目录结构中存在测试失败风险。

#### 改进

- 统一项目根目录发现规则；
- 所有默认路径从显式 project root 推导；
- 使用 `sys.executable`，不依赖固定 Python 路径；
- 移除用户名、服务器绝对路径和当前工作目录假设；
- 补齐 Windows、Linux 和项目目录外启动的测试。

#### 验收

- 所有路径相关测试通过；
- 从任意工作目录执行入口仍能定位项目；
- 输出目录、缓存目录和实验目录均可配置。

### 1.2 PDF 与 LaTeX 状态一致性

#### 问题

生成 `.tex`、真实编译 PDF 与 `compiled_verified` 状态必须严格对应。

#### 改进

- 明确 `tex_generated`、`pdf_compile_started`、`compiled_verified`、`compile_failed` 状态；
- 保存编译命令、日志、返回码、PDF 哈希和文本提取检查；
- 编译失败时不得生成伪成功 PDF 或成功状态。

#### 验收

- 任何 `compiled_verified` PDF 都可追溯至对应 `.tex`；
- 修改 `.tex` 后必须重新编译与重新计算哈希；
- 解压后的包可独立验证 PDF。

### 1.3 检索、引用与人工审核

#### 改进

- 保存查询词、时间、来源 URL、响应哈希和相关性理由；
- 基于 DOI、标题和版本进行去重；
- 人工对来源执行批准或拒绝；
- 仅 `citation_allowed=true` 的来源可进入正式引用；
- 保存审核人、时间、原因和被审核文件哈希。

#### 验收

- 每个主题至少 5 条人工确认的相关来源；
- 论文的正式引用都能追溯到已批准来源；
- 未批准来源被验证器阻止进入正式报告。

### 1.4 Claim--Evidence 强化

#### 改进

- 每条关键结论绑定 artifact、JSON Pointer 和 SHA-256；
- 报告只能引用账本中存在的 claim；
- 不支持或待审核 claim 必须显式标识；
- 篡改实验结果后，验证器应报错。

#### 验收

- 所有实验结论均可定位到原始记录；
- 报告中的 unsupported claims 与账本完全一致；
- 任意错误 JSON Pointer 或哈希都会导致验证失败。

## 阶段 2：真实 context-engineering 实验

### 目的

先证明一个真实任务上的能力提升，而不是继续扩展多个流程演示主题。

### 任务设计

选择固定资料集和固定 Agent 任务，例如：

```text
资料检索 → 事实整合 → 工具调用 → 带证据回答 → 结果核验
```

### 对照组

- `baseline`：普通提示词；
- `prompt-only`：结构化输出要求，但不启用硬性证据护栏；
- `full-rail`：启用 Rail、Claim--Evidence 和引用检查。

### 运行条件

- 相同输入、相同模型、相同工具集合；
- 至少 3 个固定 seed：`42`、`43`、`44`；
- 相同调用预算；
- 保存完整输入、轨迹、输出、成本、时延与哈希。

### 指标

- 任务成功率；
- 答案准确率；
- 证据覆盖率；
- 无证据完成声明率；
- 误引用率；
- 失败率；
- token、调用成本与时延。

### 验收

实验结论必须能够回答：在相同任务与预算下，证据护栏是否改善了可审计性，且没有不合理损失任务效果？

## 阶段 3：受约束 JIT Harness 试点

### 目标

让系统根据任务、资料、历史结果和预算，选择合适的 Harness 策略；但不允许模型直接生成或执行任意 Python 代码。

### 架构

```text
任务输入 + 检索资料 + 历史运行结果
                ↓
       Harness Planner
                ↓
     Harness Manifest（JSON）
                ↓
Schema / Rail / 预算 / 工具白名单校验
                ↓
        现有 Runner 执行
                ↓
证据账本、指标、Provenance、人工审核
                ↓
      通过门槛后写入 Harness 档案
```

### 四模块映射

| JIT 模块 | 在项目中的对应内容 |
|---|---|
| Memory | 检索资料、Claim Ledger、历史运行与失败记录 |
| Planning | 研究计划、阶段顺序、验证与重试策略 |
| Action | UCR 或真实 Agent 任务执行器 |
| Capability orchestration | Provider、检索、引用验证、PDF 编译和工具预算 |

### 第一版安全策略库

| Profile | 适用场景 | 行为 |
|---|---|---|
| `evidence_first` | 事实核验、研究报告 | 先检索与引用审批，再形成结论 |
| `experiment_first` | Benchmark、可复现实验 | 先运行实验，再依据结果形成报告 |
| `repair_first` | 上一次运行失败或格式不稳定 | 先执行 Schema、接口与失败恢复 |
| `cost_limited` | 预算受限 | 限制检索数、调用数和重试数 |

### Harness Manifest 示例

```json
{
  "profile": "evidence_first",
  "memory_mode": "structured_evidence",
  "planning_mode": "sequential_verify",
  "enabled_tools": ["retrieval", "ucr", "citation_rail"],
  "max_provider_calls": 3,
  "max_retries": 1,
  "selection_reason": "任务包含外部来源与可验证结论要求"
}
```

### 必须保留的硬约束

- 不能提高既定 Provider 调用上限；
- 不能启用未批准工具；
- 不能关闭 Rail；
- 不能将待审核来源用于正式引用；
- 不能将未执行步骤写成成功；
- Manifest 校验失败时，自动回退到固定 `full-rail` 策略。

## 阶段 4：固定流程与 JIT 的对照实验

### 实验臂

```text
baseline
prompt-only
full-rail
jit-constrained
```

`jit-constrained` 是新增第四臂，不替代原有三臂。

### 公平比较要求

- 相同任务集、输入、模型和 seed；
- 相同工具白名单与调用预算；
- 相同 Rail 和人工审核规则；
- 独立保存每个 Harness Manifest、选择原因与验证结果。

### JIT 通过门槛

JIT 只有同时满足以下条件才可进入主线：

```text
1. 不降低任务成功率；
2. 不新增证据违规或误引用；
3. UCR、无证据声明率或证据覆盖率出现明确改善；
4. 成本或时延没有不可接受的恶化；
5. 每次策略选择均可由 JSON、日志和哈希复核；
6. 人工审核负担没有显著增加。
```

若不能满足，应保留 JIT 为实验分支，不进入正式竞赛主线。

## 阶段 5：Harness 档案与受控进化

### 档案内容

对通过门槛的 Harness 保存：

- 任务类型和特征；
- Manifest；
- 性能、成本、时延、失败率；
- Rail 与验证结果；
- 关联的输入和输出哈希；
- 人工审核结论。

### 进化边界

允许优化：

- 检索数量；
- 并行度；
- 摘要长度；
- 重试次数；
- Profile 选择。

禁止优化：

- 关闭 Rail；
- 绕过人工审核；
- 突破工具白名单；
- 突破调用与成本上限；
- 自行生成未经审查的可执行代码。

## 推荐代码布局（仅限独立工作副本）

```text
competition_runner/
  competition_runner/
    harness/
      schema.py
      profiles.py
      planner.py
      validator.py
      selector.py
      archive.py
  schemas/
    harness.schema.json
  config/
    harness_profiles.json
  tests/
    test_harness_schema.py
    test_harness_validator.py
    test_harness_selector.py
    test_harness_archive.py
```

现有 `research_matrix_v4.py` 只应在 `run_topic()` 中接入：

```text
build_harness_manifest()
→ validate_harness_manifest()
→ run_real_task_or_ucr()
→ write_claim_evidence_and_provenance()
```

## 预期收益与判断标准

### 可能收益

- 不同任务使用不同的记忆、规划和工具策略；
- 复用历史成功 Harness；
- 使成本、时延和任务效果成为可比较目标；
- 将“上下文工程、记忆、进化”从主题描述升级为实际系统能力；
- 增强 Agent 系统能力和 openJiuwen 工程贡献的可展示性。

### 不应承诺的收益

- 不应在实验前声称 JIT 一定提高分数；
- 不应将流程指标改写为领域科学结论；
- 不应将 JIT 作为跳过真实实验、引用审核或人工确认的理由。

## 完成后的交付物

- 独立工作副本与清晰变更说明；
- 全绿测试结果；
- 真实 context-engineering 对照实验；
- JIT 与固定流程的对照报告；
- Harness Manifest、档案和验证记录；
- 更新后的论文及 PDF 编译证据；
- 重新生成的校验和与独立验证结果。
