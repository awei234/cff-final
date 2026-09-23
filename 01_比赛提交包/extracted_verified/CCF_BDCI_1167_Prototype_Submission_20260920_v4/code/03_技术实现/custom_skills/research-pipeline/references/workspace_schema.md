# 工作区数据契约 Schema（references/ 拷贝）

> 本文件是 SKILL.md 引用的工作区完整目录树与各文件 Schema（与细化_02 §2 一致）。
> agent 写文件时对照本文件；rails（F02/F03/F04）按此结构校验。

## 工作区完整目录树

每个论文项目一个工作区目录。skill 在 `workspace/` 下按此结构产出；rails 按此结构校验。

```
workspace/<project_name>/
├── proposal.md                     # 阶段1：研究提案（§2.1）
├── idea.json                       # 阶段1：结构化选题（§2.2）
├── references/                     # 阶段1：文献池（§2.3）
│   ├── references_index.json       # 可选项：{bibkey: {title, year, ...}}（F04 优先读）
│   ├── smith2023/                  # 每文献一个目录，目录名 = bibkey
│   │   ├── meta/
│   │   │   ├── meta_info.txt       # title / authors / venue / year / URL
│   │   │   └── bibtex.txt          # BibTeX 条目
│   │   └── sections/
│   │       ├── abstract.md
│   │       ├── 1 Introduction.md
│   │       └── 2 Related Work.md
│   └── jones2024/ ...
├── plan.json                       # 阶段2：实验计划（F02 强制校验）
├── experiments/                    # 阶段3：实验产物区
│   ├── exp1/
│   │   ├── run.py                  # 实验脚本
│   │   ├── config.json             # 超参/种子/数据源（§2.4）
│   │   ├── results.json            # 唯一数据源（§2.5，F03 只认这个）
│   │   └── logs/                   # stdout/训练日志
│   ├── exp2/ ...
│   └── shared/                     # 共享工具（data_loader/metrics/models/utils）
└── paper/
    ├── paper.tex                   # 阶段4：论文（F01/F03/F04 校验）
    └── figures/                    # 图表（数据来源可追溯）
        ├── fig1_arch.pdf
        └── ...
```

## 2.1 `proposal.md` 结构（必含小节）

```
# <论文标题>（研究提案）
## Introduction      # 背景 / 问题陈述 / 关键洞见 / 假设
## Proposed Approach # 概述 / 方法细节 / 关键创新
## Related Work      # 关键文献 / 与我们的差异 / 定位
## Experiments       # 计划实验 / 基准 / 指标 / 预期结果
## Success Criteria  # 什么结果证实/证伪假设
## References        # 完整引用列表（必须全部真实可核验）
```

## 2.2 `idea.json` Schema

```json
{
  "title": "论文标题",
  "description": "1-3 句话：提出什么",
  "motivation": "为什么重要、填什么缺口",
  "proposed_approach": "高层方法 + 为什么有效",
  "related_work": ["真实文献：作者/标题/年份", "与我们的差异"],
  "hypothesis": "可证伪假设",
  "success_criteria": "证实/证伪的判据",
  "topic_mapping": "context | memory | self-evolution"
}
```

## 2.3 `references/` 规范

- 每文献一个目录，**目录名 = BibTeX key**（F04 池匹配用）
- `meta/meta_info.txt` 固定四行头：`title:` / `authors:` / `venue:` / `year:` / `url:`
- `meta/bibtex.txt`：完整 BibTeX 条目（写作阶段直接引用）
- 可选 `references_index.json`：`{"smith2023": {"title": "...", "year": 2023}, ...}`
- **所有文献必须是真实可核验的**（novelty 三步里搜到的，F04 会查）

## 2.4 `experiments/<id>/config.json` Schema

```json
{
  "experiment_id": "exp1",
  "seed": 42,
  "dataset": "数据集名（与 plan.json 声明一致）",
  "model": "deepseek-v4-flash",
  "hyperparams": {"lr": 0.001, "epochs": 50},
  "baseline_of": null,
  "created_at": "2026-08-14T10:00:00+08:00"
}
```

## 2.5 `experiments/<id>/results.json` Schema（F03 唯一数据源）

```json
{
  "experiment": "exp1",
  "metrics": {
    "acc": {"mean": 87.3, "std": 0.2},
    "latency_ms": {"mean": 12.3, "std": 0.5}
  },
  "config": {"lr": 0.001, "epochs": 50, "seed": 42},
  "runtime_minutes": 45,
  "notes": ""
}
```

> 论文里出现的任何数字，要么等于这里某个值，要么能由这里推导（均值/百分比）——F03 就这么验。

## 2.6 `plan.json` Schema（F02 强制校验对象）

```json
{
  "title": "论文标题",
  "hypothesis": "要测试的可证伪假设",
  "reproducibility": {
    "environment": "Python 3.12 + jiuwenswarm 0.2.4b4",
    "dependencies": "依赖清单",
    "randomness": "固定 seed"
  },
  "experiments": [
    {
      "id": "exp1",
      "status": "planned | partial | completed",   // 可选；缺省视为 completed（F03 从严勾稽）
      "status_note": "执行状态说明（partial 时写已跑/待跑内容）",   // 可选
      "type": "comparison | ablation | scaling | analysis | systems",
      "title": "简短描述性标题",
      "description": "这一步做什么、为什么",
      "ablation": "消融前置规划（跑实验前声明每个新组件的消融设计，禁止看完结果再补）",
      "baselines": ["baseline 名称（简单）", "baseline 名称（强/新近）"],
      "seeds": [42, 43, 44],
      "datasets": ["数据集名（数组，独立声明，禁止一个数据集当多个用）"],
      "metrics": ["标准指标"],
      "budget": {"estimated_minutes": 120, "parallel": true},
      "steps": ["实验步骤（可选，复现用）"],
      "success_criteria": "成功/证伪标准（可选，复现用）"
    }
  ]
}
```

**F02 校验规则**：experiments ≥ 3；每个实验 baselines ≥ 2、seeds ≥ 3、**ablation 前置规划**、**datasets（复数，数组）**、budget 估算；主实验含 comparison 类型；顶层含 reproducibility。status 可选，取值必须为 `planned|partial|completed`。

**F03 勾稽语义（status 门控）**：`planned/partial` 视为进行中——仅提示不阻断（`_pending_experiments`）；`completed` 或**缺省**必须存在 `experiments/<id>/results.json`，否则报缺失（防捏造从严）。实验转 completed 前务必保证产物落位。产物目录支持两级：`experiments/<id>/results.json` 或 `experiments/<id>/<seed>/results.json`（F03 递归读取）。

## 勾稽链规则表（rails 校验"计划-执行-报告"一致）

| # | 勾稽规则 | 检查方 | 不满足时 |
|---|---|---|---|
| 1 | plan.json 声明且状态为 **completed/缺省** 的每个 experiment id，在 `experiments/<id>/results.json` 存在（planned/partial 仅提示） | F03 `_plan_results_missing` | 引导：补跑实验 或 从论文删除相关论断 |
| 2 | paper.tex 每个数字在 results.json 有出处（精确或推导）| F03 `_match` | 注入"未验证数字"清单引导修正 |
| 3 | paper.tex 每个 `\cite{key}` 在 references/ 池命中 | F04 | 引导替换为池中文献 或 在线核验 |
| 4 | plan.json 中 baseline/ablation 声明在论文 Experiments 中体现 | 人工/赛后复现审核 | 阶段 3 的 E1 指标"匹配率"统计用 |
| 5 | 论文图表数据源自 results.json | F07 生成规范 + F03 | 图表脚本数据源只允许 results.json |

## 数据契约速查（阶段间传递）

```
proposal.md ─→ idea.json ─→ plan.json ─→ experiments/*/results.json ─→ paper/paper.tex
   (F05/F02 校验)   (F02 强制)     (F03 勾稽)          (F03/F04/F01 校验)
```
