# Context-Engineering 真实多 seed 实验汇总

日期：2026-09-25  
实验标签：`process_evidence_only`

## 结论

在真实研究矩阵运行中，seed 42、43、44 均成功完成 9 次公开检索调用，并各自完成 `no-rail`、`prompt-only`、`full-rail` 三个对照臂。三组 seed 的过程指标一致：`prompt-only` 与 `full-rail` 将 UCR 降至 0，`full-rail` 额外记录了 1 次 Rail 校验；`no-rail` 保留 5 个未执行 Claim，UCR 为 0.5556。

这些结果只证明当前实验流程和证据约束机制的可复现性，不代表领域任务准确率或科学结论有效性。

## 多 seed 对照结果

| seed | arm | UCR | task success rate | supported | unexecuted | Rail |
|---:|---|---:|---:|---:|---:|---|
| 42 | no-rail | 0.5556 | 1.0 | 4 | 5 | disabled |
| 42 | prompt-only | 0.0000 | 1.0 | 4 | 0 | disabled |
| 42 | full-rail | 0.0000 | 1.0 | 4 | 0 | enabled, 1 attempt, accepted |
| 43 | no-rail | 0.5556 | 1.0 | 4 | 5 | disabled |
| 43 | prompt-only | 0.0000 | 1.0 | 4 | 0 | disabled |
| 43 | full-rail | 0.0000 | 1.0 | 4 | 0 | enabled, 1 attempt, accepted |
| 44 | no-rail | 0.5556 | 1.0 | 4 | 5 | disabled |
| 44 | prompt-only | 0.0000 | 1.0 | 4 | 0 | disabled |
| 44 | full-rail | 0.0000 | 1.0 | 4 | 0 | enabled, 1 attempt, accepted |

## 可复现性与审计状态

- 每个 seed：9 次公开检索调用；三主题运行状态为 `completed_pending_human_review`。
- 原始运行目录保留完整输入、输出、成本/时延字段、证据记录和哈希：
  - `demo_runs/research_matrix_live_20260924_authorized/`
  - `demo_runs/research_matrix_live_20260925_seed43/`
  - `demo_runs/research_matrix_live_20260925_seed44/`
- seed 42 已完成来源与 Claim 审核，论文侧 `allow_paper=true`，并保留 5 条明确排除的失败/阻断类 Claim：`claim-002`、`claim-003`、`claim-005`、`claim-007`、`claim-009`。
- seed 43/44 的新来源仍保持待人工审核状态，未自动进入正式论文引用清单。

## 下一步

1. 如需把 seed 43/44 的来源用于正式论文，先逐条完成来源审核，再按允许 Claim 清单重新运行审核器。
2. 将本报告与三份原始运行目录一并纳入发布审计；不要把未审核来源标记为论文允许引用。
3. 后续扩大到真实任务标签和更多 seed，补充准确率、证据覆盖率、误引用率和成本/时延的统计置信区间。
