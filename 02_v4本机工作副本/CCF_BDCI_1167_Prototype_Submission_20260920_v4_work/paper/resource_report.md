# 论文资源报告（paper/resource_report.md）

更新时间：`2026-09-30T17:15:06+08:00`（Asia/Shanghai）
范围：`paper/paper.tex`（再生成的英文 LaTeX 源）、`paper/paper_v5_en.pdf`（本轮产物）
说明：**本报告只记录本轮「按系统流程真实重跑」所消耗的资源**；历史资源消耗数据已按要求全部移除。

---

## 1. 概述与口径

本报告为**本轮再生成论文**建立可追溯记录，严格区分两类字段：

| 分类 | 口径 |
|---|---|
| 真实记录 | 来自本轮真实运行文件（`demo_runs/research_matrix_v5_live/`）的实测值 |
| 缺失字段 | 无法从真实运行记录确认：数值写 `null`，字符串写 `not_recorded` |
| 生成方式 | `generated_by_pipeline`（真实 DeepSeek 调用 + 公开资料检索 + UCR 本地基准 + XeLaTeX 编译） |

**本轮事实：** 依据系统流程真实重跑研究矩阵流水线，产出可审计证据；并以英文 LaTeX 路线再生成
论文《CGA-Agent: Structured Context Engineering and Claim-Evidence Guardrails for Trustworthy Multi-Agent LLM Systems》。
**原论文 `paper/paper.docx` 与 `paper/paper.pdf` 未被覆盖**；再生成 PDF 另存为 `paper/paper_v5_en.pdf`。

> **数据来源边界（重要）**：论文正文中的实验数字（如 `77.9%`、`91.7%`、`6.4%`、`3.1%`、`7.15K`、`59.1%`、消融各值等）与全部 40 条参考文献，
> **继承自参考论文 `paper/paper.docx`（用户提供的英文论文）**，**不是**本轮 `research_matrix_v5_live` 流水线产出的实验结果。
> 本轮 v5 运行产出的是 `process_evidence_only` 流程证据（审计状态类 Claim：每主题 20 条，12 `supported` + 8 `pending_human_review`），
> 二者口径不同，不得混同；本报告只记录**本轮生成过程**真实消耗的资源，不对论文实验数字做任何背书。

---

## 2. 论文文件（本轮）

| 文件 | 字节数 | 页数 | SHA-256 |
|---|---|---|---|
| `paper/paper.tex`（再生成英文 LaTeX 源） | `101725` | —（编译 15 页） | `76ec8bac29c2128f07a7f57a66b382d0fada563c3acb851ff05fabe2c5f76e4e` |
| `paper/paper_v5_en.pdf`（本轮产物 PDF） | `211703` | `15` | `07e6fb0c65da9467d0b672fb83f3e0b2201afe3df378a178c23849bbdb16c3ee` |

- 页面尺寸：`595.28 x 841.89 pts (A4)`；
- 编译：XeLaTeX（MiKTeX 25.12），两遍编译，无致命错误；
- **排版一致性修订（2026-09-30 补做，仅排版、未改数据/结论）**：
  - 6 张表格全部用 `\resizebox{\columnwidth}{!}{}` 统一到单栏宽度；
  - 4 张 pgfplots 图轴宽由 `0.92\columnwidth` 改为 `\columnwidth`；
  - 3 张 TikZ 图（架构图 / 规划流程图 / Claim–Evidence 门控图）用 `\resizebox{\columnwidth}{!}{}` 统一宽度，架构图节点宽度收窄并加 `text width` 使标签换行；
  - 原第 4 图（任务成功率）由**占位文本框**替换为基于 `Table 5` 的 SR 列绘制的矢量柱状图，正文对应句同步改写（数据仍来自 `Table 5`，未新增任何数据）；
  - 两处超出栏宽的公式（`S(m)`、`score(c_i,d)`）改用 `split` 折行；
  - 结果：`Overfull \hbox = 0`；PDF 文本边界全部落在页边距内（x ∈ [40.6, 554.7] pt，页宽 595.3 pt）；页数仍为 `15`。
- 原论文（保留未动）：`paper/paper.docx` = `eef7facb…0b7a`，`paper/paper.pdf` = `26f9ed09…ad84`（15 页）。

---

## 3. 本轮全流程真实资源消耗

来源目录：`demo_runs/research_matrix_v5_live/`（运行状态 `completed_pending_human_review`，`valid: true`）。

### 3.1 模型调用（Provider）

| 字段 | 值 | 说明 |
|---|---|---|
| Provider | `deepseek` | `provider_trace.jsonl` |
| model | `deepseek-chat` | 全部 9 次调用 |
| 调用次数 | `9`（3 主题 × {plan, review, report}） | 每主题 ≤ 3、总计 ≤ 9 |
| prompt_tokens | `22568` | 真实采集（本轮已为 `provider()` 增加 usage 采集） |
| completion_tokens | `4432` | 同上 |
| total_tokens | `27000` | 同上 |
| 单次耗时（秒） | `3.569 / 2.138 / 4.436 / 2.939 / 1.843 / 4.924 / 3.388 / 1.826 / 3.686` | 逐次真实值 |
| 时延合计（秒） | `28.749` | 9 次之和 |
| 全流程墙钟（秒） | `191.645` | 本轮命令实测（含检索、UCR、导出） |
| cost | `null` | 未记录单价，未估算 |

### 3.2 公开资料检索

| 主题 | 检索状态 | 候选数 | 保留数 | 去重移除 | 检索失败 |
|---|---|---:|---:|---:|---|
| context-engineering | `partial_retrieval` | 20 | 10 | 9 | openalex `429` ×3；arxiv `TimeoutError` ×2 |
| memory-engine | `retrieved` | 50 | 10 | 29 | openalex `429` ×2 |
| self-evolution | `partial_retrieval` | 30 | 10 | 9 | openalex `429` ×2；arxiv `TimeoutError` ×2 |

- 检索 Provider：OpenAlex / arXiv / Crossref；
- 来源默认 `citation_allowed=false`、`human_review_status=pending`，未人工批准前不得正式引用。

### 3.3 UCR 本地基准执行耗时

| 主题 | no-rail (s) | prompt-only (s) | full-rail (s) | 小计 (s) |
|---|---:|---:|---:|---:|
| context-engineering | 0.342 | 0.349 | 0.344 | 1.035 |
| memory-engine | 0.401 | 0.353 | 0.391 | 1.145 |
| self-evolution | 0.379 | 0.360 | 0.368 | 1.107 |
| 合计 | — | — | — | **3.287** |

### 3.4 论文编译

| 字段 | 值 |
|---|---|
| 编译工具 | XeLaTeX（MiKTeX 25.12） |
| 编译遍数 | 2 |
| 致命错误 | 0 |
| Overfull \hbox | `0`（排版一致性修订后） |
| 产出 | `paper/paper_v5_en.pdf`（15 页，A4） |

---

## 4. 缺失字段清单

以下字段本轮仍**无法从真实运行记录确认**，按规则留空：

1. `cost` —— 未记录 DeepSeek 计费单价，未估算；
2. 磁盘 / 显存 / CPU / 网络流量 —— 未采集。

> 说明：`prompt_tokens` / `completion_tokens` / `total_tokens` 本轮**已真实采集**（不再是缺失项）。

---

## 5. 复现命令

```powershell
# 1) 真实跑研究矩阵流水线（DeepSeek，3 主题 × 3 调用）
cd code/03_技术实现/competition_runner
py -3 run_research_matrix.py --provider deepseek --confirm-live --allow-research-matrix-demo `
  --allow-public-retrieval --max-calls-per-topic 3 --max-total-calls 9 `
  --output-root demo_runs/research_matrix_v5_live

# 2) 编译英文论文（不覆盖原 paper.pdf）
cd ../../../paper
xelatex -jobname=paper_v5_en -interaction=nonstopmode -halt-on-error paper.tex
xelatex -jobname=paper_v5_en -interaction=nonstopmode -halt-on-error paper.tex

# 3) 校验
pdfinfo paper_v5_en.pdf
```

期望：`demo_runs/research_matrix_v5_live/matrix_verification_report.json` 中 `valid: true`；
`paper_v5_en.pdf` 为 `15` 页。

---

## 6. 关联记录文件

| 文件 | 用途 |
|---|---|
| `demo_runs/research_matrix_v5_live/provider_trace.jsonl` | 9 次调用：stage / model / 请求与响应 SHA-256 / 耗时 / **Token** |
| `demo_runs/research_matrix_v5_live/matrix_execution_report.json` | `total_provider_calls: 9`、各主题状态 |
| `demo_runs/research_matrix_v5_live/matrix_verification_report.json` | `valid: true` |
| `demo_runs/research_matrix_v5_live/<topic>/research_materials.json` | 检索来源、去重、失败 |
| `demo_runs/research_matrix_v5_live/<topic>/experiment_results.json` | UCR 各臂耗时与决策 |
| `paper/generation/usage.json` | 本轮用量记录（含 Token） |
| `paper/generation/latency.json` | 本轮时延记录 |
| `paper/generation/retrieval.json` | 本轮检索记录 |
| `paper/generation/summarize_v5_run.py` | 本轮资源汇总脚本 |
| `paper/generation/extract_docx_text.py` | 参考论文文本提取脚本 |
| `runtime_local/patch_paper_tex.py` | 排版一致性修订脚本（表格/图统一单栏宽） |
| `paper/generation.log` | 追加式操作日志 |
| `submission_manifest.json` | 产物溯源（`paper_generated_v5`、`matrix_v5_live`） |
