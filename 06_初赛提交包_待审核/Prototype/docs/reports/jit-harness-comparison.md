# JIT Harness 对照实验报告

## 范围

本报告对应 `research_matrix_live_20260924_authorized` 与已归档的 `jit_comparison_v1_final`。JIT 只以受约束 Manifest 运行，不生成或执行任意 Python/shell；无效策略回退到固定 `full-rail`。

## 实验设计

- 实验臂：`baseline`、`prompt-only`、`full-rail`、`jit-constrained`。
- Seed：`42`、`43`、`44`。
- 保持相同任务输入、工具白名单、预算、Rail 规则和证据审核规则。
- 每个运行保存策略选择、Manifest、校验结果、成本、时延、证据路径及 SHA-256。

## 结果摘要

最终 fixture 对照中，12 个运行全部完成。`baseline` 的 UCR 为 `0.5556`，`prompt-only`、`full-rail` 与 `jit-constrained` 的 UCR 为 `0`；四臂任务成功率均为 `1.0`。fixture 成本为 `0`，因为该对照不调用外部模型。

这些结果只能支持“过程证据护栏在该固定任务集上降低无证据完成声明率”的审计结论，不能外推为领域效果或因果性能提升。真实检索运行的来源与 Claim 审核结果另见 `human_review_decisions.json` 和 `claim_review_audit.json`。

## 通过门槛

| 门槛 | 结果 |
|---|---|
| 不降低任务成功率 | 通过；四臂均为 1.0 |
| 不新增证据违规/误引用 | 通过；允许 Claim 均有证据或已批准来源 |
| UCR 或证据覆盖改善 | 通过；JIT 与 full-rail 为 0 UCR |
| 成本/时延在预算内 | 通过；fixture 成本为 0，Manifest 预算受限 |
| 策略选择可复核 | 通过；Manifest、校验和 Harness archive 已保存 |
| 不绕过人工审核 | 通过；来源批准记录与排除 Claim 保留 |

## 限制

真实 DeepSeek 运行仍属于过程级研究证据；论文不得把 UCR 改写成领域准确率或能力提升。最终发布前仍需重新编译论文 PDF，并重新计算 PDF 与 provenance 哈希。
