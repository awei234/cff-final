# 最终论文允许使用的 Claim 清单

生成依据：三个主题目录下的 `claim_ledger.json` 与 `review.json`。

## 使用规则

- 本清单只收录当前状态为 `supported`、具备 `experiment_results.json` JSON Pointer 和 SHA256 的实验观察 Claim。
- 这些 Claim 只能表述“审计状态/过程证据”，不能改写成真实领域效果、性能提升或因果结论。
- `pending_human_review` Claim 暂不进入论文正文、摘要、结论或图表；完成审核后再单独更新清单。
- 背景 Claim（`claim-018` 至 `claim-020`）因来源尚未批准引用，当前全部排除。

## A. context-engineering

证据文件：`context-engineering/experiment_results.json`；每条 Claim 的 JSON Pointer 和 SHA256 以对应账本为准。

| Claim ID | 当前允许写入论文的表述 |
|---|---|
| claim-001 | no-rail 对操作 `run_success` 的审计状态为 `supported`。 |
| claim-004 | no-rail 对操作 `inspect_existing` 的审计状态为 `supported`。 |
| claim-006 | no-rail 对操作 `query_available` 的审计状态为 `supported`。 |
| claim-008 | no-rail 对操作 `validate_success` 的审计状态为 `supported`。 |
| claim-010 | prompt-only 对操作 `run_success` 的审计状态为 `supported`。 |
| claim-011 | prompt-only 对操作 `inspect_existing` 的审计状态为 `supported`。 |
| claim-012 | prompt-only 对操作 `query_available` 的审计状态为 `supported`。 |
| claim-013 | prompt-only 对操作 `validate_success` 的审计状态为 `supported`。 |
| claim-014 | full-rail 对操作 `run_success` 的审计状态为 `supported`。 |
| claim-015 | full-rail 对操作 `inspect_existing` 的审计状态为 `supported`。 |
| claim-016 | full-rail 对操作 `query_available` 的审计状态为 `supported`。 |
| claim-017 | full-rail 对操作 `validate_success` 的审计状态为 `supported`。 |

## B. memory-engine

证据文件：`memory-engine/experiment_results.json`；每条 Claim 的 JSON Pointer 和 SHA256 以对应账本为准。

| Claim ID | 当前允许写入论文的表述 |
|---|---|
| claim-001 | no-rail 对操作 `run_success` 的审计状态为 `supported`。 |
| claim-004 | no-rail 对操作 `inspect_existing` 的审计状态为 `supported`。 |
| claim-006 | no-rail 对操作 `query_available` 的审计状态为 `supported`。 |
| claim-008 | no-rail 对操作 `validate_success` 的审计状态为 `supported`。 |
| claim-010 | prompt-only 对操作 `run_success` 的审计状态为 `supported`。 |
| claim-011 | prompt-only 对操作 `inspect_existing` 的审计状态为 `supported`。 |
| claim-012 | prompt-only 对操作 `query_available` 的审计状态为 `supported`。 |
| claim-013 | prompt-only 对操作 `validate_success` 的审计状态为 `supported`。 |
| claim-014 | full-rail 对操作 `run_success` 的审计状态为 `supported`。 |
| claim-015 | full-rail 对操作 `inspect_existing` 的审计状态为 `supported`。 |
| claim-016 | full-rail 对操作 `query_available` 的审计状态为 `supported`。 |
| claim-017 | full-rail 对操作 `validate_success` 的审计状态为 `supported`。 |

## C. self-evolution

证据文件：`self-evolution/experiment_results.json`；每条 Claim 的 JSON Pointer 和 SHA256 以对应账本为准。

| Claim ID | 当前允许写入论文的表述 |
|---|---|
| claim-001 | no-rail 对操作 `run_success` 的审计状态为 `supported`。 |
| claim-004 | no-rail 对操作 `inspect_existing` 的审计状态为 `supported`。 |
| claim-006 | no-rail 对操作 `query_available` 的审计状态为 `supported`。 |
| claim-008 | no-rail 对操作 `validate_success` 的审计状态为 `supported`。 |
| claim-010 | prompt-only 对操作 `run_success` 的审计状态为 `supported`。 |
| claim-011 | prompt-only 对操作 `inspect_existing` 的审计状态为 `supported`。 |
| claim-012 | prompt-only 对操作 `query_available` 的审计状态为 `supported`。 |
| claim-013 | prompt-only 对操作 `validate_success` 的审计状态为 `supported`。 |
| claim-014 | full-rail 对操作 `run_success` 的审计状态为 `supported`。 |
| claim-015 | full-rail 对操作 `inspect_existing` 的审计状态为 `supported`。 |
| claim-016 | full-rail 对操作 `query_available` 的审计状态为 `supported`。 |
| claim-017 | full-rail 对操作 `validate_success` 的审计状态为 `supported`。 |

## 当前排除项

以下 Claim 在三套账本中均为 `pending_human_review`，当前不得进入论文：

- `claim-002`：`run_failed`
- `claim-003`：`run_denied`
- `claim-005`：`inspect_missing`
- `claim-007`：`query_unavailable`
- `claim-009`：`validate_failed`
- `claim-018` 至 `claim-020`：背景来源 Claim，尚未完成来源批准

## 重要限制

当前三个主题的 `review.json` 均为 `allow_paper=false`、`citation_coverage=0.0`。因此，本文件是“按 Claim 粒度筛出的候选允许清单”，并不等同于整篇论文已经获得发布许可。正式提交前仍需完成：

1. 对 15 条 `pending_human_review` 实验/失败状态 Claim 做人工文字审核；
2. 对每个主题的 3 个背景来源作批准或拒绝决定；
3. 将批准结果回写审核记录，并重新生成 `review.json`，确认 `allow_paper=true`。
