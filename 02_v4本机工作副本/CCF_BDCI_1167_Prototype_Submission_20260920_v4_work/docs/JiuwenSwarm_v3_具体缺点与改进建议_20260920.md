# JiuwenSwarm v3 项目具体缺点与改进建议

> **文档用途**：用通俗的话解释当前项目到底做到了什么、还缺什么、为什么这些缺点重要，以及下一步应该怎样改。
>
> **检查时间**：2026-09-20
>
> **检查对象**：`CCF_BDCI_1167_Prototype_Submission_20260919_v3_work` 工作副本，以及已经生成的 v3 提交 ZIP。
>
> **一句话结论**：当前项目已经是一个“能真实调用模型、能检索公开资料、能运行本地证据流程、能留下完整审计记录的科研论文半流程原型”，但还不能严谨地称为“能够完成真实领域科研的自动科研系统”。目前最大的问题不是“有没有代码”，而是**科研实验的真实性、资料检索的相关性、原始 JiuwenSwarm 的实际接入程度和最终报告的科学可信度还不够**。

---

## 1. 先给结论：项目现在处于什么阶段

### 1.1 已经完成的事情

当前 v3 已经完成了一条真实运行链路：

```text
三个固定主题
    ↓
公开资料检索（OpenAlex / arXiv / Crossref）
    ↓
DeepSeek 生成研究计划
    ↓
本机运行固定 seed 的本地证据基准
    ↓
DeepSeek 审查实验结果
    ↓
DeepSeek 生成研究报告
    ↓
Rail 证据规则检查和引用映射过滤
    ↓
保存 prompt、工具轨迹、实验结果、PDF、哈希和验证报告
    ↓
等待人工确认
```

三个主题是：

1. Agent 上下文工程：`context-engineering`
2. Agent 记忆引擎：`memory-engine`
3. Agent 自我进化：`self-evolution`

v3 的真实矩阵记录显示：

| 项目 | 当前结果 |
|---|---:|
| 主题数量 | 3 个 |
| 每个主题模型调用 | 3 次 |
| 总模型调用 | 9 次 |
| 每个主题保存的检索来源 | 10 条 |
| 本地实验 | 3 个主题都执行成功 |
| 每个主题 verification report | `valid: true` |
| 总体状态 | `completed_pending_human_review` |
| 人工审核 | 尚未完成 |
| 比赛网页上传 | 未上传 |

因此，现在最准确的说法是：

> **三条“检索—计划—实验—审查—报告”的半自动流程已经跑通，并且证据文件完整；但是人工还没有批准研究问题、资料适用性、实验真实性和最终结论，所以它还不是最终科研结论，也不是已经提交的比赛成果。**

### 1.2 当前没有做到的事情

当前版本还没有证明：

- Agent 上下文工程确实在某个真实任务上提升了效果；
- Agent 记忆引擎确实比其他方法更好；
- Agent 自我进化确实能够稳定提升能力；
- JiuwenSwarm 原始框架已经被完整调用并形成闭环；
- 生成的论文 PDF 是经过真正 LaTeX 排版、可直接作为正式论文提交的版本；
- 公开检索到的 10 条来源都与主题高度相关；
- 模型写出的每一个结论都经过了真正的语义证据核验；
- 自动流程可以替代人的研究判断。

这不是说项目失败，而是说项目目前应该被准确定位为：

> **可审计的科研论文半流程 Agent 原型，重点证明“流程、证据、边界和失败记录”能够工作，尚未完成“领域科学效果证明”。**

---

## 2. 专业名词用大白话解释

### 2.1 Agent 是什么

普通聊天机器人主要是“你问一句，它答一句”。

Agent 可以理解为“会自己分步骤办事的模型程序”：

1. 先理解任务；
2. 制定计划；
3. 调用搜索、文件、代码或实验工具；
4. 观察结果；
5. 根据结果继续下一步；
6. 最后给出报告。

本项目中的 Agent 不是一个单纯聊天窗口，而是一个带有**计划、工具、实验、证据和报告**的流程。

### 2.2 半流程 Agent 是什么

“半流程”不是贬义，而是表示：

- 机器自动做重复、机械、可检查的工作；
- 人保留必须由研究者判断的工作。

本项目自动完成的工作包括：

- 访问公开资料源；
- 保存标题、作者、摘要、URL 和哈希；
- 调用模型生成研究计划；
- 运行本地实验；
- 检查引用 ID 是否存在；
- 生成报告文件；
- 保存日志和校验结果。

本项目不应该自动替代人的工作包括：

- 这个研究问题是否值得研究；
- 找到的论文是否真正适合引用；
- 实验是否合理；
- 结论是否超过证据范围；
- 最终材料是否符合比赛要求。

### 2.3 Provider 是什么

Provider 就是“模型服务提供方”。例如本项目的 DeepSeek。

代码不会把模型写死在每个函数中，而是通过 Provider 配置决定：

- 请求地址；
- 模型名称；
- 从哪个环境变量读取 API Key。

这样做的好处是可以替换模型，坏处是不同模型的输出格式和能力并不完全相同，所以必须严格校验模型输出。

### 2.4 Retrieval（检索）是什么

Retrieval 就是从公开资料库中找资料。

本项目使用：

- OpenAlex：学术论文元数据聚合服务；
- arXiv：预印本论文库；
- Crossref：DOI 和出版物元数据服务。

当前保存的是必要的元数据和摘要，不把未确认版权的整篇论文打包进去。

### 2.5 Benchmark（基准测试）是什么

Benchmark 可以理解为“固定规则的考试题”。

它的作用是让两次运行能够比较：

- 输入是否相同；
- 运行方式是否相同；
- 输出是否一致；
- 某个改动是否带来变化。

但是，基准测试只能证明它测试的东西。当前 v3 的基准主要测试：

- 是否保存输入哈希；
- 是否记录 Rail 决策；
- 没有证据的陈述是否被阻止；
- 同一个 seed 是否得到相同结果。

它不能自动证明“上下文工程、记忆引擎、自我进化在真实领域任务上更有效”。

### 2.6 Baseline 和 Full-Rail 是什么

- **Baseline / no-rail**：不打开严格证据门的基线方案。
- **Full-rail**：打开证据规则，缺少证据的结论会被拦截。

当前本地基准中有 3 条 claim：

- baseline 接受 3 条；
- full-rail 接受 2 条；
- full-rail 把没有证据的第 3 条标记为 `blocked_missing_evidence`。

这说明“证据门”这段控制逻辑能运行，但它只说明控制逻辑有效，不说明某个研究领域取得了科学进步。

### 2.7 Rail 是什么

Rail 可以理解为“护栏”或“门卫”。

它不负责创造知识，而负责阻止明显不合规的输出，例如：

- 引用了一个没有保存的 `source_id`；
- 把没有运行的实验写成已经运行；
- 把缺少证据的结论直接写成事实。

当前项目的 Rail 做得比较好的地方是：发现模型提供了未保存的来源 ID 时，会删除这条引用映射，并留下 `citation_mapping_blocked` 事件。

### 2.8 Provenance（溯源）是什么

Provenance 就是“这份结果是怎样产生的证明”。

本项目的 provenance 主要记录：

- 关键文件 SHA-256 哈希；
- 来源记录哈希；
- Provider、模型和调用次数；
- 运行时间。

如果文件被改过，哈希就会变，验证器能够发现不一致。

### 2.9 Verification report（验证报告）是什么

Verification report 是“机器检查清单”，它会检查：

- 必要文件是否存在；
- JSON 是否可以解析；
- 引用的 `source_id` 是否存在于检索材料；
- 实验是否标注为“流程证据而不是领域科学证据”；
- provenance 中的哈希是否匹配；
- JSON 中是否出现替换字符。

它能证明“文件和证据合同大体完整”，但不能单独证明“科学结论正确”。

---

## 3. 当前系统实际是怎样工作的

### 3.1 入口和安全门

v3 的三主题入口是：

```powershell
cd code/03_技术实现/competition_runner
python run_research_matrix.py `
  --provider deepseek `
  --confirm-live `
  --allow-research-matrix-demo `
  --allow-public-retrieval `
  --max-calls-per-topic 3 `
  --max-total-calls 9 `
  --output-root demo_runs/research_matrix_v3_new
```

三个开关分别表示：

- `--confirm-live`：我明确同意这次是真实调用；
- `--allow-research-matrix-demo`：我明确同意运行三主题演示；
- `--allow-public-retrieval`：我明确同意访问公开网络资料。

这样做是为了避免用户只输入一个普通命令，就意外触发付费 API 或联网请求。

### 3.2 资料检索阶段

当前代码在 `research_matrix.py` 中：

- 每个主题读取最多 3 个关键词；
- 每个关键词访问 OpenAlex、arXiv、Crossref；
- 每个来源最多拉取 10 个候选；
- 用 DOI、来源 ID 或规范化标题做一次去重；
- 按“有无摘要、标题字母顺序、来源 ID”排序；
- 最终保留前 10 条。

这一步“能跑通”，但也是当前最明显的技术短板之一，后文会详细说明。

### 3.3 本地实验阶段

每个主题都运行一个固定 seed=42 的本地基准。

实验会保存：

- 固定输入；
- baseline 和 full-rail 两个方案；
- stdout 和 stderr；
- 返回码；
- stdout/stderr 哈希；
- 结果 JSON；
- 可重复性 token。

但是，当前 v3 矩阵中的实验命令是：

```text
<embedded deterministic benchmark>
```

也就是说，矩阵实际运行的是 `research_matrix.py` 内嵌的一段很小的确定性 Python 基准，而不是直接调用 `ucr_benchmark/run_experiment.py`，也不是直接运行一个完整的 JiuwenSwarm 科研任务。这一点是当前项目最需要正视的缺口。

### 3.4 三次模型调用

每个主题固定最多三次：

1. **Plan**：生成研究问题、假设、变量、实验计划和成功标准；
2. **Review**：审查本地实验结果，指出哪些结论有证据、哪些没有；
3. **Report**：生成摘要、方法、结果、限制、结论和引用映射。

当前实现只检查返回值是否是 JSON 对象，以及几个必需字段是否存在。例如计划必须包含：

```text
research_question
hypotheses
variables
experiment_plan
success_criteria
expected_evidence
human_confirmation_points
```

这比直接接收一段自然语言可靠，但仍然不是完整的 JSON Schema 校验，后面会解释。

### 3.5 结果保存阶段

每个主题目录保存了：

```text
run_manifest.json          运行状态、主题、模型调用次数
prompt.txt                 三个阶段的提示词
research_materials.json    公开资料、摘要、URL、来源哈希
tool_trace.jsonl           检索、实验、模型调用轨迹
rail_events.jsonl          Rail 事件
plan.json                  研究计划
experiment_config.json     实验配置
experiment_results.json    原始实验结果
results.json               审查结果和报告结果
paper.tex                  论文文本源
paper.pdf                  PDF 载体
execution_report.json      执行成功或失败原因
human_interventions.jsonl  等待人工确认的记录
provenance.json            文件和来源哈希
verification_report.json   机器验证结果
```

这个产物链是项目当前最有价值的成果之一：即使失败，也不会只留下一个“程序报错”，而会保留失败状态和原因。

---

## 4. 当前项目做得好的地方

这里也要客观说清楚，项目并不是“只有问题”。

### 4.1 安全门设计比较清楚

真实 DeepSeek 运行需要同时满足：

- Provider 必须是 DeepSeek；
- 必须有 `--confirm-live`；
- 必须有 `--allow-research-matrix-demo`；
- 必须有 `--allow-public-retrieval`；
- 每主题调用数只能在 1 到 3；
- 总调用数不能超过 9；
- `DEEPSEEK_API_KEY` 必须存在；
- 输出目录非空时拒绝覆盖。

这解决了实际工程中很常见的两个问题：意外产生费用，以及新运行覆盖旧证据。

### 4.2 失败不伪装成成功

当检索失败、Provider 返回非法 JSON、模型调用失败时，代码会保存：

- 失败状态；
- 失败原因；
- 已消耗的调用次数；
- 未完成阶段的占位结果；
- execution report；
- verification report。

这比“程序报错后什么都没有”好，也比“失败了但生成一份看起来成功的论文”可靠。

### 4.3 证据文件比较完整

一个主题不是只输出 `paper.pdf`，而是保存了完整的过程材料。对于竞赛评审，这有助于回答：

- 这个结论从哪里来？
- 模型看到了什么提示词？
- 实验真的执行了吗？
- 是否超过调用预算？
- 是否有人为确认留痕？
- 文件有没有被事后修改？

### 4.4 版本备份策略正确

当前有三个版本：

- v1：冻结；
- v2：冻结；
- v3：单独工作副本和 ZIP。

v1、v2 没有被覆盖，这是正确的工程习惯。它可以让我们在 v3 改坏时回到之前的可提交版本。

### 4.5 项目对边界的文字说明是诚实的

README 和 manifest 已经明确写出：

- fixture 不是真实模型实验；
- 本地 benchmark 不是三个领域的科学结论；
- 最终需要人工确认；
- 当前没有自动上传比赛网页。

这会降低“过度宣传”的风险，是很重要的优点。

---

## 5. 当前最具体、最重要的缺点

下面按严重程度说明。严重程度含义：

- **P0：必须优先修复，否则容易被认为核心能力没有证明；**
- **P1：不一定阻止运行，但会明显影响可信度、复现和评审理解；**
- **P2：属于工程质量和长期维护问题。**

---

### P0-1：矩阵实验不是实际的领域实验，只是一个很小的流程控制测试

#### 现象

当前 v3 的三个主题虽然分别生成了研究计划和报告，但本地实验内容实际上是同一个内嵌的确定性基准：

- 固定输入：`alpha`、`beta`、`gamma`；
- 只有 3 条 claim；
- 其中 1 条没有证据；
- full-rail 把这 1 条拦截。

`experiment_config.json` 中保存的命令是 `<embedded deterministic benchmark>`，而不是一个真正的 JiuwenSwarm 研究任务命令。

同时，项目中已经存在更完整的 UCR 基准入口：

```text
code/03_技术实现/ucr_benchmark/run_experiment.py
```

但是当前 v3 `research_matrix.py` 没有直接调用它。

#### 为什么这是缺点

这会造成一个重要的“表面像科研，实际上测流程”的问题：

- 研究问题谈的是上下文工程、记忆、自己进化；
- 实验测的却是“一个 claim 有没有 evidence_ref”；
- 论文中可以说流程确实拦截了无证据断言；
- 但不能据此说三个主题的技术方案在实际任务上更强。

这叫做**外部有效性不足**：实验在自己的小测试里成立，但不一定能推广到真实任务。

#### 怎么改

第一步不要同时做三个复杂领域实验，而是先选一个主题做真实闭环，例如 `context-engineering`：

1. 固定一个真实研究任务输入；
2. 让 JiuwenSwarm 或一个明确的最小 Agent 场景运行；
3. 设置两个条件：
   - no-rail：不启用证据护栏；
   - full-rail：启用证据护栏；
4. 至少运行多个 seed，而不是只运行一次；
5. 统计真实指标：
   - 无证据结论比例；
   - 引用映射正确率；
   - 任务完成率；
   - 运行时间；
   - 模型调用次数和成本；
   - 失败率。

第二步再把同一个实验模板参数化到 memory-engine 和 self-evolution。

最终要把实验命令改成真实可执行命令，例如：

```json
{
  "command": [
    "python",
    ".../run_experiment.py",
    "--arm",
    "full-rail",
    "--seed",
    "42",
    "--mode",
    "fixture"
  ],
  "working_directory": ".../ucr_benchmark",
  "entrypoint_sha256": "..."
}
```

如果暂时只能运行流程基准，就必须把名字写得更准确：

```text
ucr-evidence-process-benchmark-v1
```

并且不要在论文标题或摘要中暗示它已经验证了领域效果。

---

### P0-2：公开资料检索“有结果”，但相关性不可靠

#### 现象

当前检索逻辑主要是：

1. 关键词搜索；
2. 从三个来源抓候选；
3. 按“有没有摘要、标题字母顺序、来源 ID”排序；
4. 截取前 10 条。

它没有真正做主题相关性排序，也没有让人确认来源是否适合引用。

实际运行中，`context-engineering` 保存的来源中出现了明显不相关的标题，例如：

- `A Constrained Shortest Path Scheme for Virtual Network Service Management`
- `A graphene quantum dot photodynamic therapy agent with high singlet oxygen generation`
- `A Stochastic Processes Toolkit for Risk Management`
- `An Analysis of the Driving Factors of Implementing Green Supply Chain Management...`

这些标题与 Agent 上下文工程没有直接关系。

`self-evolution` 还出现了同一预印本不同版本的重复记录：

- `doi:10.21203/rs.3.rs-8139402/v1`
- `doi:10.21203/rs.3.rs-8139402/v2`

#### 为什么这是缺点

检索数量多不等于检索质量高。

如果不相关文献进入 prompt，模型可能会：

- 把不相关论文误认为领域背景；
- 在报告中产生“已有研究表明”的错误语气；
- 造成引用看似存在，但实际上不能支持结论；
- 让人工审核需要重新从头检查所有来源。

当前验证器只检查：

```text
引用的 source_id 是否存在
```

它不检查：

```text
这篇论文是否真的支持这句话
```

#### 怎么改

建议把检索改成五层：

**第一层：查询扩展**

为每个主题准备同义词、技术术语和排除词。例如上下文工程可拆成：

```text
context engineering
LLM context management
prompt context optimization
agent evidence grounding
long context agent
```

并排除明显不相关领域词。

**第二层：候选扩大**

每个关键词从每个来源取 20～50 条，不要直接只保留 10 条。

**第三层：规范化去重**

同时使用：

- DOI 规范化；
- arXiv ID；
- 标题规范化；
- 标题相似度；
- 预印本版本归并。

不能只选择 `doi or source_id or title` 中的一个作为去重键。

**第四层：相关性排序**

先用简单、可解释的方法：

- 标题和摘要的 BM25/TF-IDF 关键词得分；
- 主题关键词覆盖率；
- 年份；
- 是否有摘要；
- 来源质量；
- 是否为重复版本。

之后如果需要，再加入 embedding 相似度或 cross-encoder。第一版不建议一开始就引入复杂模型，因为复杂模型也要被审计。

**第五层：人工来源确认**

把每条候选保存为：

```json
{
  "source_id": "arxiv:xxxx.xxxxx",
  "relevance_score": 0.87,
  "relevance_reasons": ["标题命中 agent memory", "摘要提到 long-term memory"],
  "quality_status": "pending_human_review",
  "citation_allowed": false
}
```

人工确认后才把 `citation_allowed` 改为 `true`。这样可以保证“被检索到”不等于“已经批准引用”。

---

### P0-3：原始 JiuwenSwarm 的实际接入程度还不够清楚

#### 现象

提交包中包含大量 JiuwenSwarm 原始源码，但 v3 研究矩阵的主要逻辑集中在：

```text
code/03_技术实现/competition_runner/competition_runner/research_matrix.py
```

该流程主要直接完成：

- HTTP 检索；
- 本地内嵌 benchmark；
- DeepSeek HTTP 调用；
- JSON 解析；
- 文件保存。

虽然路径配置中有 `jiuwenswarm_command` 字段，但 v3 矩阵核心流程没有把它作为实际的 Agent 执行入口。

#### 为什么这是缺点

比赛题目与 JiuwenSwarm 有关。评审很可能会问：

> 这到底是基于 JiuwenSwarm 的科研论文 Agent，还是一个另写的 DeepSeek + 文件保存脚本？

如果不能清晰展示原始框架的调用链，就会削弱项目的题目契合度。

#### 怎么改

需要增加一层明确的 Adapter（适配器）：

```text
ResearchMatrix
    ↓
JiuwenSwarmResearchAdapter
    ↓
JiuwenSwarm 原始 Agent / Skill / Tool
    ↓
统一 EvidenceRecord
```

适配器负责把 JiuwenSwarm 的内部结果转换成统一格式：

```json
{
  "task_id": "context-engineering-seed42",
  "agent_run_id": "...",
  "tool_calls": [],
  "claims": [],
  "evidence_refs": [],
  "status": "completed"
}
```

同时在日志里明确记录：

- 入口模块；
- Git 或源码版本；
- Agent 任务 ID；
- 实际工具调用；
- 运行命令；
- 成功和失败事件。

如果 JiuwenSwarm 暂时无法在提交环境完整运行，也要诚实地分成两条路径：

```text
流程审计路径：当前 v3 已可运行
JiuwenSwarm 真实闭环路径：待接入并单独验收
```

不要把二者混在同一份“成功”状态里。

---

### P0-4：当前 PDF 能打开，但不是标准 LaTeX 排版论文

#### 现象

代码中的 `paper_pdf.py` 会把 `paper.tex` 解析成纯文本，再用 Python 标准库手工拼出一个 PDF。

它的生产者明确写成：

```text
competition_runner stdlib-latex-text-pdf-v1
```

这种 PDF 可以有 `%PDF-` 头和 `%%EOF` 尾，因此基础验证会认为它是有效 PDF；但它不是由 `pdflatex`、XeLaTeX 或 LuaLaTeX 真正编译出来的学术论文。

#### 为什么这是缺点

这会带来几个问题：

- 中文会被替换成 `[U+XXXX]` 一类文本，而不是正常字体；
- 公式、表格、参考文献、分页和图表都没有真正排版；
- TeX 语法错误可能不会被发现，因为代码没有调用 TeX 编译器；
- 评审看到 PDF 后可能认为“论文格式不成熟”；
- `paper.tex` 与最终 PDF 的对应关系只是文本提取，不是真正编译关系。

#### 怎么改

优先方案：

1. 检测 `xelatex` 或 `lualatex`；
2. 在隔离临时目录编译；
3. 保存编译命令、stdout、stderr、返回码和编译器版本；
4. 失败时状态为 `paper_compile_failed`，不要生成看起来像成功的 PDF；
5. 用 `pdftotext` 或 PDF 解析器检查最终文本；
6. 在 provenance 中记录 TeX 源码哈希和 PDF 哈希。

如果比赛环境没有 TeX，则应明确分成两种模式：

```text
real_latex: 真正 TeX 编译
text_pdf_fallback: 仅用于离线合同验证，不是最终论文排版
```

最终提交包应尽量使用真正排版的 PDF。

---

### P0-5：当前“引用存在”不等于“引用支持结论”

#### 现象

当前检查逻辑主要验证：

```python
all(source_id in research_materials for source_id in citation_mapping)
```

这只能证明模型写的 ID 在来源列表中，不能证明该来源的摘要真的支持结论。

#### 为什么这是缺点

举例：模型写了一句“某方法能降低幻觉率”，然后引用了一篇标题里也出现 Agent 的论文。只要 `source_id` 存在，当前验证器可能就放行，即使摘要没有这项结果。

这属于**引用映射正确，但证据支持错误**。

#### 怎么改

把“引用”从一个字符串 ID 扩展为结构化 claim：

```json
{
  "claim_id": "claim-003",
  "claim_text": "full-rail 阻止了无 evidence_ref 的 C3",
  "claim_type": "experiment_observation",
  "evidence_refs": ["experiment_results.json#/arms/full_rail/decisions/2"],
  "source_refs": [],
  "support_status": "supported",
  "support_reason": "结果 JSON 中记录了 blocked_missing_evidence"
}
```

对于文献背景，只允许模型引用保存的 `source_id`，并要求同时提供：

- 被引用摘要片段；
- 支持的具体句子；
- 该来源支持的是背景、方法还是结果；
- 人工确认状态。

第一版可以采用规则 + 人工确认；不要一开始假设另一个模型审查就等于事实核验。

---

### P1-1：三阶段输出不是严格 JSON Schema，只是“字段存在检查”

#### 现象

当前 `validate_stage()` 只做几件事：

- 返回值是不是字典；
- 必需字段是否存在；
- 必需字段是不是空值。

它没有严格检查：

- `hypotheses` 是否一定是字符串数组；
- `variables` 是否是规定结构；
- `citation_mapping` 每一项是否有规定字段；
- `allow_paper` 是否是布尔值；
- `citation_coverage` 是否包含合法数字；
- 是否出现未知字段；
- 字符长度是否超限。

#### 为什么这是缺点

模型有时会返回：

```json
{"allow_paper": "yes"}
```

或者：

```json
{"hypotheses": "一条字符串，而不是数组"}
```

字段名对了，不代表数据可用。后续代码如果把这些内容直接拼进论文，就可能出现结构错误或逻辑误读。

#### 怎么改

保存三份 JSON Schema：

```text
schemas/plan.schema.json
schemas/review.schema.json
schemas/report.schema.json
```

每份 Schema 至少限制：

- `type`；
- `required`；
- `enum`；
- `minItems/maxItems`；
- 字符串长度；
- 数字范围；
- `additionalProperties: false`。

运行顺序应为：

```text
模型返回
  → JSON 解析
  → Schema 校验
  → 证据引用校验
  → 业务规则校验
  → 写入结果
```

只要有一层失败，就进入 `provider_schema_invalid` 或 `needs_human_review`，不能继续生成成功论文。

---

### P1-2：检索缓存可用，但可复现信息还不够完整

#### 现象

缓存目录按 URL 哈希保存原始响应，来源记录保存响应哈希；但提交包主要保存解析后的元数据和摘要，不保存完整原始响应。

同时，当前检索没有完整记录：

- HTTP 状态码；
- `ETag` / `Last-Modified`；
- `Retry-After`；
- 请求发出的完整时间；
- 解析器版本；
- 来源 API 的版本或查询语法版本。

#### 为什么这是缺点

学术 API 会更新、排序会改变、同一个查询以后可能返回不同结果。只保存最终的 10 条记录，可以知道“当时保存了什么”，但不一定能完全重放“当时为什么得到这些结果”。

#### 怎么改

为每个检索请求保存一条 `retrieval_request.json` 或 JSONL 事件：

```json
{
  "provider": "openalex",
  "url": "https://...",
  "query": "agent context engineering",
  "requested_at_utc": "...",
  "http_status": 200,
  "response_sha256": "...",
  "cache_hit": false,
  "parser_version": "retrieval-parser-v3.1"
}
```

对于提交包，可以不放完整响应，但至少要把摘要、查询、哈希和解析器版本放进去；本地复现目录再保存原始响应。

---

### P1-3：网络检索缺少健壮的重试、限流和降级策略

#### 现象

当前实现有超时和异常捕获，但没有完整的：

- 指数退避；
- 429 限流处理；
- 读取 `Retry-After`；
- 每个来源的请求间隔；
- 网络重试上限；
- 失败后的可控降级。

#### 为什么这是缺点

公开服务不是永远稳定的。一次临时网络错误可能导致：

- 一个主题变成 `partial_retrieval`；
- 模型拿到不完整资料；
- 最后生成的报告质量不稳定；
- 评审无法判断是算法问题还是网络问题。

#### 怎么改

建议统一网络层：

```text
request_with_retry(
  timeout=20,
  max_attempts=3,
  backoff=[1, 2, 4],
  retry_on=[429, 500, 502, 503, 504]
)
```

每次重试都要记录事件，但不得把 API Key 或 Authorization Header 写进日志。

---

### P1-4：单个主题的报告可能仍然“看起来像论文”，即使没有科学证据

#### 现象

即使发生失败，`finally` 逻辑仍会生成：

- `paper.tex`；
- `paper.pdf`；
- `results.json`；
- `execution_report.json`。

这是为了保留失败审计载体，但从用户视觉上看，一个目录里有 `paper.pdf` 很容易被误认为“论文成功生成”。

#### 为什么这是缺点

机器状态是：

```text
status = failed
```

文件名却像：

```text
paper.pdf
```

这容易造成误读，尤其是评审或团队成员只打开 PDF、不先看 `execution_report.json` 的时候。

#### 怎么改

失败时采取更明确的文件策略：

```text
paper_failure_notice.txt
failure_report.json
```

或者保留 `paper.pdf`，但命名为：

```text
paper_failed_status.pdf
```

并在 PDF 首页用醒目文字写：

```text
FAILED RUN — NOT A VALID RESEARCH REPORT
```

只有满足“检索、实验、Schema、引用和人工状态”条件时，才输出正式名称 `paper.pdf`。

---

### P1-5：Provenance 记录了很多哈希，但没有形成完整的可复现实验环境

#### 现象

当前 provenance 已经记录关键产物哈希，这是优点。但还缺少：

- Git commit 或源码快照标识；
- Python 版本；
- 操作系统；
- 依赖列表和锁定版本；
- 真实入口脚本哈希；
- 完整实验环境变量白名单；
- Provider 返回的原始响应哈希；
- 模型参数的完整记录；
- prompt 的独立哈希和 stage ID。

#### 为什么这是缺点

同一个 seed 不代表同一个实验。

如果：

- Python 版本不同；
- 依赖版本不同；
- 模型版本被服务端替换；
- prompt 被改了；
- 原始代码改了；

最后仍然可能得到不同结果。

#### 怎么改

provenance 至少增加：

```json
{
  "source_revision": {
    "git_commit": null,
    "tree_sha256": "..."
  },
  "runtime": {
    "python_version": "3.12.x",
    "platform": "Windows ...",
    "dependency_lock_sha256": "..."
  },
  "provider": {
    "name": "deepseek",
    "model": "...",
    "request_count": 3,
    "request_hashes": ["..."],
    "response_hashes": ["..."]
  },
  "prompts": {
    "plan_sha256": "...",
    "review_sha256": "...",
    "report_sha256": "..."
  }
}
```

注意：这里记录哈希，不保存 API Key。

---

### P1-6：模型调用有次数上限，但没有真正的 Token/成本控制

#### 现象

当前限制了：

- 每主题最多 3 次；
- 总计最多 9 次；
- `max_tokens=4096`。

但没有把每次调用的：

- prompt token 数；
- completion token 数；
- 总 token 数；
- 实际费用；
- 失败重试成本

统一记录到 `resource.json`。

#### 为什么这是缺点

“调用次数不超过 9 次”不等于“成本一定不超过预期”。不同提示词长度、模型返回长度和服务计费规则都会影响成本。

#### 怎么改

每次 Provider 事件增加：

```json
{
  "stage": "plan",
  "call_index": 1,
  "prompt_sha256": "...",
  "response_sha256": "...",
  "usage": {
    "prompt_tokens": 1234,
    "completion_tokens": 456,
    "total_tokens": 1690
  },
  "estimated_cost": null
}
```

如果服务端没有返回 usage，就明确写 `usage_unavailable`，不要猜一个数字。

---

### P1-7：验证器验证了文件完整性，但验证深度还不够

#### 当前能验证什么

- 文件是否存在；
- JSON 是否能解析；
- 引用 ID 是否在来源列表；
- 基准是否有明确边界标签；
- provenance 哈希是否匹配；
- 公开文件没有替换字符；
- 总模型调用次数没有超过 9。

#### 当前不能验证什么

- 来源是否真的与主题相关；
- 来源是否支持报告中的具体结论；
- 模型是否在报告中夸大了实验结果；
- 实验是否真的调用了 JiuwenSwarm；
- PDF 是否是合理的论文排版；
- 人工是否实际点击或签署了批准；
- 生成的“结果”是否只是模型复述了输入；
- 代码是否在另一台干净机器上可运行。

#### 怎么改

将验证器分成四层：

1. **结构验证**：文件、JSON、目录、哈希；
2. **执行验证**：命令、返回码、stdout/stderr、实际输出；
3. **证据验证**：claim 到 artifact/source 的可追溯映射；
4. **人工验证**：问题、来源、实验、结论和提交的审批状态。

最终状态不要只用 `valid: true`，建议写成：

```json
{
  "structural_valid": true,
  "execution_valid": true,
  "evidence_valid": false,
  "human_approved": false,
  "submission_ready": false
}
```

这样比一个总布尔值更不容易被误解。

---

### P1-8：当前三主题只运行了一个 seed，无法说明结果稳定

#### 现象

当前矩阵固定 `seed=42`，三个主题各跑一次。

#### 为什么这是缺点

一次运行只说明“这一次发生了什么”。它无法回答：

- 换一个随机种子是否还成立；
- 换一个输入是否还成立；
- 模型稍微换一个版本是否还成立；
- 某个结果是不是偶然。

#### 怎么改

建议分层：

- 开发和比赛演示：每主题 1 个 seed，控制调用预算；
- 科研验收：每主题至少 3 个 seeds；
- 更严格评估：不同输入、不同任务难度和重复运行。

对于每个指标保存：

```text
mean
median
standard deviation
confidence interval（如果样本量足够）
```

如果预算不允许多次真实模型调用，可以让模型只负责计划和审查，实验部分用固定可重复任务，明确说明这只是流程评估。

---

### P1-9：测试代码存在，但当前环境没有安装 pytest，完整测试没有被执行

#### 现象

项目有 `tests/`，也有 `pytest.ini`。但是当前配置的 Python 环境执行：

```powershell
python -m pytest -q
```

返回：

```text
No module named pytest
```

因此当前不能说“整套 pytest 测试已经通过”。目前实际确认通过的是：

```powershell
python verify_submission.py
python main.py paths
```

以及已经保存的 v3 ZIP 完整性验证。

#### 为什么这是缺点

没有运行测试不等于代码一定有 bug，但表示我们没有完成自动证明。尤其当前测试没有全覆盖：

- 网络超时；
- 429 限流；
- 非法 JSON；
- 来源相关性；
- provider 响应泄密；
- 完整三主题 offline-mock；
- 一半主题失败时的矩阵状态；
- PDF 真编译失败。

#### 怎么改

在干净环境中固定：

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

并增加以下测试：

1. 固定 HTTP 响应的 OpenAlex/arXiv/Crossref 解析测试；
2. 429、500、超时和非法 JSON 测试；
3. 三主题完整 offline-mock 测试；
4. 一个主题失败、两个成功时必须是 `partial_failed`；
5. `DEEPSEEK_API_KEY` 不得进入任何文件；
6. 已存在输出目录必须拒绝；
7. 随机 seed 复现测试；
8. PDF 编译器不存在时必须进入明确 fallback 状态。

---

### P1-10：源代码量很大，但正式运行链路和原始源码之间的边界不清晰

#### 现象

提交包中包含大量原始 JiuwenSwarm 代码；当前工作副本的 `code/` 下有约 1,189 个 Python 文件，体积超过 16 MB。与此同时，正式竞赛 runner 目录本身约有 33 个 Python 文件、约 4,684 行代码。

#### 为什么这是缺点

代码多不等于能力强。如果评审看见大量源码，却无法快速知道：

- 哪些是比赛核心代码；
- 哪些是原始框架；
- 哪些是实验工具；
- 哪些真正被当前入口调用；
- 哪些只是保留的历史文件；

就会感觉项目复杂、难复现、难评审。

#### 怎么改

增加一张“调用关系和文件归属表”：

| 层 | 作用 | 当前是否被 v3 直接调用 |
|---|---|---|
| `competition_runner` | 比赛入口和证据编排 | 是 |
| `ucr_benchmark` | UCR 实验与评分 | 当前矩阵没有直接接入 |
| `jiuwenswarm` | 原始框架源码 | 需要明确实际接入点 |
| `custom_skills` | 研究规范和提示词 | 需要明确调度关系 |
| `custom_rails` | 证据护栏 | 需要明确哪些由 v3 调用 |

同时给每个核心模块补一条可追溯链：

```text
run_research_matrix.py
  → research_matrix.run_matrix()
  → retrieve_materials()
  → run_local_benchmark()
  → DeepSeekClient.call()
  → verify_matrix_run()
```

如果原始源码只是参赛要求的一部分，但当前 demo 没有实际使用，也应明确写在 README 中，而不是让人自行猜测。

---

### P2-1：入口过多，用户容易不知道应该运行哪个

当前目录中同时存在多类入口：

- `main.py`：路径、fixture 和基础 runner；
- `run_cross_topic_live.py`：旧的单主题 live 路径；
- `run_cross_topic_protocol.py`：协议或冻结路径；
- `run_research_matrix.py`：v3 三主题入口；
- `ucr_benchmark/run_experiment.py`：UCR 基准入口；
- `ucr_benchmark/run_formal_experiment.py`：正式矩阵入口。

这对开发者有用，但对比赛评审不友好。

建议最终只突出三个命令：

```powershell
python verify_submission.py
python code/03_技术实现/competition_runner/main.py paths
python code/03_技术实现/competition_runner/run_research_matrix.py --offline-mock ...
```

真实 live 命令放在“高级运行”章节，并说明风险。

---

### P2-2：路径和环境仍有可移植性问题

部分运行记录包含本机绝对路径，例如：

```text
C:\Users\vergil\.pixi\envs\c4net\python.exe
```

这在本机审计时有用，但在别人机器上不可直接执行。

改进方式：

- 命令记录使用相对路径和 Python 模块入口；
- 同时保存 `executable_resolved` 作为环境信息；
- 运行时使用 `sys.executable`；
- README 提供 Windows 和 Linux 两种路径示例；
- 不把本机用户名和临时目录作为复现前提。

---

### P2-3：模型版本没有完全锁定“服务端行为”

配置中固定了模型 ID，例如：

```text
 deepseek-v4-flash
```

但模型服务端可能在同一个 ID 下更新模型或系统行为。只保存模型 ID，不足以保证长期一致。

改进方式：

- 记录模型 ID、服务响应中的版本字段（如果有）；
- 保存 prompt 哈希、参数、响应哈希；
- 记录运行时间和 Provider API 版本；
- 若比赛允许，保存小规模脱敏的 response fixture 作为离线回归样本。

---

### P2-4：人工确认只有“待确认”记录，还没有真正的批准流程

当前 `human_interventions.jsonl` 中有：

```json
{
  "event": "pending_human_review",
  "decision": "pending"
}
```

这能说明“需要人工”，但不能说明“人工已经看过”。

改进方式是增加命令或表单，至少支持：

```text
approve_plan
reject_source
approve_experiment
reject_conclusion
approve_for_submission
```

每条记录应包含：

- actor；
- 时间；
- decision；
- reason；
- 被批准文件的 SHA-256；
- 审核前后的版本关系。

只有所有主题都完成最终确认，矩阵才能从：

```text
completed_pending_human_review
```

变成：

```text
approved_for_submission
```

---

## 6. 建议的改进路线：为什么要按这个顺序

不要一开始同时修改所有模块。正确顺序应该是“先证明真实能力，再扩展自动化”。

### 阶段 0：先冻结现状，避免改进后无法比较

**目标**：保留当前 v1、v2、v3 作为对照。

操作：

1. 保持 v1/v2 ZIP 不动；
2. 保存 v3 当前 ZIP SHA-256；
3. 清理工作副本中的 `__pycache__`、`.pyc` 和临时输出；
4. 重新记录干净状态的文件清单；
5. 固定 Python、依赖和运行命令。

**为什么先做**：

如果不冻结基线，后面即使结果变好，也不知道是代码改进带来的，还是环境、模型或资料变化带来的。

### 阶段 1：先打通一个“真正使用 JiuwenSwarm 的主题闭环”

**目标**：不要先追求三个主题都看起来完成，先让一个主题真实可靠。

建议选：`context-engineering`。

完整流程：

```text
真实 JiuwenSwarm 入口
  → 真实工具调用
  → 真实实验输入
  → baseline / full-rail 对照
  → 保存 claims 和 evidence refs
  → 独立评分
  → 生成报告
```

**为什么**：

一个真实闭环比三个“相同小玩具换三个 topic_id”更能证明项目价值。

### 阶段 2：把实验基准从流程测试升级为可解释的真实任务

实验需要有真实可测的任务。例如上下文工程可以测试：

- 同一组资料下，Agent 能否正确找到指定事实；
- 是否把来源 ID 绑定到答案；
- 长上下文和结构化上下文的差异；
- 误引用率和遗漏率。

记忆引擎可以测试：

- 多轮对话中历史事实的召回率；
- 错误记忆的污染率；
- 记忆更新后的可追溯性。

自我进化可以测试：

- 反馈前后任务分数变化；
- 改进是否可复现；
- 是否发生回归；
- 是否能回滚到旧版本。

**为什么**：

只有指标和对照组，报告才可能从“流程演示”走向“实验研究”。

### 阶段 3：修复检索质量

推荐实现顺序：

1. 先加 query 日志；
2. 再加相关性打分；
3. 再加跨来源去重；
4. 再加人工批准；
5. 最后考虑 embedding reranker。

**为什么**：

如果检索资料本身不相关，后面的模型计划和论文写得再好也是建立在错误输入上。

### 阶段 4：把自由文本变成“声明—证据”数据结构

不要只保存一段 `results` 文本，而要保存 claim ledger：

```json
{
  "claim_id": "C-001",
  "text": "full-rail 阻止了缺少证据的 C3",
  "kind": "observed_experiment_result",
  "evidence": [
    {
      "artifact": "experiment_results.json",
      "json_pointer": "/arms/full_rail/decisions/2",
      "sha256": "..."
    }
  ],
  "status": "supported"
}
```

**为什么**：

只有这样，验证器才能判断“每一句关键话到底从哪个文件、哪个 JSON 字段来的”。

### 阶段 5：改成真正的论文生成和编译链

最小目标：

- 真实生成 `.tex`；
- 真实调用 XeLaTeX；
- 保存编译日志；
- PDF 文本可提取；
- 引用和章节不缺失；
- 失败时不输出伪成功论文。

**为什么**：

比赛最终通常要看论文 PDF。PDF 是展示层，也是评审直接接触的成果，不能只满足“文件头看起来像 PDF”。

### 阶段 6：补全测试和干净环境复现

至少建立：

```text
requirements-dev.txt
pytest.ini
fixtures/http/openalex/*.json
fixtures/http/arxiv/*.xml
fixtures/http/crossref/*.json
tests/test_retrieval_failures.py
tests/test_matrix_offline.py
tests/test_secret_redaction.py
tests/test_provenance.py
tests/test_paper_compile.py
```

**为什么**：

项目当前最大风险之一是“本机能跑，但别人无法证明”。干净环境测试可以把隐性依赖暴露出来。

### 阶段 7：最后再重新打包

打包顺序：

1. 复制到干净 staging；
2. 删除 API Key、缓存、`.pyc`、临时目录；
3. 运行结构验证；
4. 运行离线测试；
5. 生成 manifest；
6. 生成 checksums；
7. 创建 ZIP；
8. 对 ZIP 做 integrity check；
9. 解压后再次验证；
10. 保存 ZIP SHA-256。

**为什么**：

manifest、checksums 和 ZIP 必须在最后生成。否则中途再修改一个 README，就会出现“文件内容和哈希不一致”。

---

## 7. 推荐的技术架构改造

### 7.1 将代码拆成五层

```text
1. Entry / CLI 层
   只负责参数、安全门、输出目录和退出码

2. Orchestration 层
   负责三阶段流程、失败状态和调用预算

3. Provider / Retrieval 层
   负责模型请求、公开资料请求、重试和脱敏

4. Evidence 层
   负责 claims、evidence refs、Rail、provenance

5. Presentation 层
   负责 paper.tex、真正 PDF 编译和报告格式
```

目前 `research_matrix.py` 把很多职责集中在一个文件中：

- 网络检索；
- XML/JSON 解析；
- benchmark；
- Provider；
- 论文文本；
- verification；
- failure artifacts。

这对原型开发很快，但长期维护困难。下一版应拆分为：

```text
retrieval.py
providers.py
benchmarks.py
evidence.py
schemas.py
paper.py
verification.py
orchestrator.py
```

### 7.2 建立统一状态机

建议使用明确状态：

```text
created
retrieving
retrieval_partial
planned
experiment_running
experiment_completed
reviewed
report_generated
needs_human_review
approved_for_submission
failed
partial_failed
```

每次状态变化都记录：

- 原状态；
- 新状态；
- 触发事件；
- 时间；
- 关联文件哈希。

这样比只在最后写一个 `status` 更容易排查问题。

### 7.3 建立统一的 EvidenceRecord

建议所有实验、工具和来源都转换成统一记录：

```json
{
  "evidence_id": "ev-0001",
  "kind": "experiment_observation",
  "source": {
    "artifact": "experiment_results.json",
    "json_pointer": "/arms/full_rail/decisions/2"
  },
  "content_sha256": "...",
  "created_at_utc": "...",
  "status": "verified"
}
```

模型只允许引用 `evidence_id`，而不是自己随便写一段来源文字。

### 7.4 把模型输出和最终报告分开

现在模型 report 输出会直接参与 `paper.tex` 生成。更安全的做法是：

```text
模型草稿
  → Schema 校验
  → 证据绑定
  → Rail 检查
  → 人工确认
  → 最终报告渲染
```

不要让“模型输出”直接等于“最终论文”。

---

## 8. 建议的验收标准

### 8.1 结构验收

```powershell
python verify_submission.py
```

要求：

- `submission_ready: true`；
- 没有敏感凭据；
- 必要文件都存在；
- v1/v2 哈希保持不变。

### 8.2 离线验收

```powershell
cd code/03_技术实现/competition_runner
python run_research_matrix.py --provider deepseek --offline-mock --output-root demo_runs/research_matrix_v3_mock_new
```

要求：

- 不联网；
- 不读取 API Key；
- 三个主题目录都生成；
- 失败状态可复现；
- 所有 hashes 能复核。

### 8.3 真实检索验收

要求每个主题：

- 至少 5 条人工确认相关来源；
- 每条有查询、URL、时间、响应哈希；
- 无明显无关论文；
- 重复版本已归并；
- 不能支持的引用被阻止。

### 8.4 真实实验验收

至少满足：

- 真实运行 JiuwenSwarm 或明确的最小 Agent 任务；
- baseline/full-rail 使用同一输入；
- 至少 3 个 seed 或明确说明预算限制；
- stdout、stderr、返回码和输出文件哈希齐全；
- 失败命令不能写成成功。

### 8.5 论文验收

- `paper.pdf` 由真实 LaTeX 编译；
- 章节、中文字体、表格和引用正常；
- PDF 与 `paper.tex` 哈希关系可追溯；
- 论文明确区分流程基准结果和领域科学结果。

### 8.6 人工验收

三个主题都必须存在：

```json
{
  "event": "approve_for_submission",
  "decision": "approved",
  "actor": "human",
  "reason": "...",
  "artifact_hashes": {
    "paper.pdf": "..."
  }
}
```

没有这个记录，状态只能是：

```text
completed_pending_human_review
```

### 8.7 打包验收

- ZIP integrity check 通过；
- 解压后再次执行 `verify_submission.py`；
- `CHECKSUMS.sha256` 全部匹配；
- 不包含 API Key、缓存、`.pyc`、临时文件；
- README、manifest 和 ZIP 中的状态一致。

---

## 9. 当前版本文件和证据位置

### 9.1 工作副本

```text
D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260919_v3_work
```

### 9.2 v3 ZIP

```text
D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260919_v3.zip
```

SHA-256：

```text
8B607F2A19F78BBAF45B590AB180F1BDF0A258147BACE70AB9CAF40A13BD776A
```

### 9.3 三主题运行记录

```text
D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260919_v3_work\demo_runs\research_matrix_v3\context-engineering
D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260919_v3_work\demo_runs\research_matrix_v3\memory-engine
D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260919_v3_work\demo_runs\research_matrix_v3\self-evolution
```

### 9.4 核心代码

```text
D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260919_v3_work\code\03_技术实现\competition_runner\run_research_matrix.py
D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260919_v3_work\code\03_技术实现\competition_runner\competition_runner\research_matrix.py
D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260919_v3_work\code\03_技术实现\ucr_benchmark\run_experiment.py
D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260919_v3_work\verify_submission.py
```

### 9.5 当前已有的自动验证结果

当前工作副本执行：

```powershell
python verify_submission.py
```

可得到：

```text
structure_and_security_passed: true
submission_ready: true
matrix_status: completed_pending_human_review
```

注意：`submission_ready: true` 在当前验证器语义中主要表示“结构、安全和基本证据合同通过”，不等于“科学结论已经被人工批准”。

另外，当前环境没有安装 pytest，因此不能把“完整 pytest 测试已经通过”写进成果说明。

---

## 10. 版本和打包方面的特别注意事项

### 10.1 本文档不自动改变已冻结的 v3 ZIP

本说明文档是对当前项目的分析附件，保存于 v3 工作副本的 `docs/` 目录。

当前已经生成的 v3 ZIP：

```text
D:\download\CCF\06_提交物\CCF_BDCI_1167_Prototype_Submission_20260919_v3.zip
```

不会因为本次新增这份 Markdown 自动变化。这样做是为了避免未经确认就改变已验证的提交包。

如果以后希望把本文档正式放入 ZIP，必须重新执行：

1. 清理 staging；
2. 复制文档；
3. 重新生成 manifest；
4. 重新生成 `CHECKSUMS.sha256`；
5. 重新打包；
6. 重新验证；
7. 生成新的 ZIP SHA-256。

### 10.2 文件数量可能因缓存而变化

当前 `verify_submission.py` 的 `source_files` 统计方式是递归统计 `code/` 下所有文件。运行 Python 后，`__pycache__` 和 `.pyc` 可能重新出现，因此本地工作副本的统计数量可能变化。

这不是源码真的增加了，而是验证器把运行时缓存也算进去了。下一版应改成只统计受支持的源文件，并明确排除：

```text
__pycache__/
*.pyc
*.pyo
.pytest_cache/
临时运行目录
```

否则 manifest 中的 `file_count` 和实际重新运行时的 `source_files` 可能不一致。

---

## 11. 最后给团队的直白判断

### 现在能不能作为比赛原型

**可以。**

因为它已经具备：

- 清晰的入口；
- 真实 Provider 调用记录；
- 公开检索路径；
- 三阶段模型流程；
- 本地实验记录；
- 失败审计；
- 证据哈希；
- 版本冻结和提交包。

### 现在能不能说已经完成了自动科研

**不能。**

因为：

- 本地实验主要验证流程控制，不是领域效果；
- 检索结果中存在明显无关资料；
- 原始 JiuwenSwarm 的真实调用链还不够清楚；
- PDF 不是标准 LaTeX 编译产物；
- 引用检查还停留在 ID 存在性，未达到语义支持核验；
- 三个主题都还没有人工批准；
- 完整 pytest 测试在当前环境没有实际跑通。

### 最应该先改哪三件事

如果只能做三件事，建议按这个顺序：

1. **把一个主题接到真正的 JiuwenSwarm/UCR 实验上**，不要继续只运行内嵌 toy benchmark；
2. **修复资料检索相关性和人工来源确认**，不要按字母顺序截取论文；
3. **让 PDF 真正编译，并建立 claim—evidence 结构化验证**。

这三件事分别解决：

- 项目到底有没有真实能力；
- 输入资料是否可信；
- 最终论文是否能被相信和复核。

### 项目最终应该怎样定位

最稳妥、最专业的定位是：

> **JiuwenSwarm 科研论文生成的可审计半流程 Agent：它自动完成公开资料整理、研究计划草拟、本地证据流程、模型审查和报告生成，并通过 Rail、provenance 和 verification report 记录边界；最终研究判断、科学结论和正式提交由人负责。**

这句话既能说明项目有真实工程成果，也不会把当前还没有证明的科研能力说得过头。

---

## 附录：专业名词速查表

| 名词 | 通俗解释 | 在本项目中的作用 |
|---|---|---|
| Agent | 会分步骤调用工具办事的模型程序 | 负责研究计划、审查和报告流程 |
| JiuwenSwarm | 项目要依托的 Agent/多智能体框架 | 原始源码和目标运行框架 |
| Provider | 模型服务提供方 | 当前真实演示使用 DeepSeek |
| Retrieval | 从公开资料库查找论文 | OpenAlex、arXiv、Crossref |
| Metadata | 论文标题、作者、年份、DOI、URL 等信息 | 作为可追溯资料记录 |
| Benchmark | 固定规则的测试题 | 检查流程和证据控制是否稳定 |
| Baseline | 不加改进的对照方案 | 与 full-rail 比较 |
| Rail | 阻止违规或无证据输出的护栏 | 拦截缺少证据的 claim |
| Claim | 报告中的一条可验证陈述 | 需要绑定 evidence |
| Evidence | 支持 claim 的实验、文件或来源 | 让结论可以复查 |
| Provenance | 结果从哪里来、怎么生成的记录 | 保存哈希、来源和运行信息 |
| Verification | 自动检查文件和证据合同 | 防止缺文件、错引用和哈希不一致 |
| Schema | 输出数据的格式合同 | 约束模型返回 JSON 的结构 |
| Fixture | 离线固定假数据/样本 | 无网络时测试流程，不代表真实发现 |
| Human-in-the-loop | 人在关键节点确认 | 审核问题、资料、实验、结论和提交 |
| External validity | 实验结果能否推广到真实场景 | 当前 v3 的主要不足之一 |
| Reproducibility | 同样输入是否能重复得到同样结果 | 用 seed、命令和哈希支持复现 |
| SHA-256 | 文件内容指纹 | 检查文件是否被修改 |

---

**文档结束。**
