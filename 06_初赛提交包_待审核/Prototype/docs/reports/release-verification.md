# 发布验证说明

> 历史源工作副本验证记录：以下 demo_runs 路径和 JIT v1 命令不适用于当前审核目录。当前可运行的包级与 JIT v2 命令见根目录提交说明；授权发布验证入口迁移仍列为待完善项。

## 已验证项

- 三个主题的 Claim 审核已重跑；`unsupported_claims` 仅为 `claim-002、003、005、007、009`。
- `claim-018~020` 及其绑定来源已批准正式引用。
- 三个主题 `review.json` 均为 `allow_paper=true`。
- 四臂（baseline、prompt-only、full-rail、jit-constrained）和三 seed（42、43、44）结果已归档。
- Harness Manifest、Profile、Schema、白名单、预算、Rail 校验、回退与 archive 均存在。
- 受保护的服务器源码快照和冻结提交包未纳入本分支修改。

## 关键产物

- `demo_runs/research_matrix_live_20260924_authorized/claim_review_audit.json`
- `demo_runs/research_matrix_live_20260924_authorized/human_review_decisions.json`
- `demo_runs/jit_comparison_v1_final/`
- `experiments/jit_comparison_v1/README.md`
- `verify_authorized_release.py`
- `docs/reports/context-engineering-real-seeds.md`

## PDF 验证结果

已使用 MiKTeX 25.12 的 XeLaTeX 编译统一论文和三个主题论文。四个 PDF 均返回码为 0，并完成页数、文本提取、渲染和 SHA-256 检查；详细记录见 `pdf_compile_verification.json`。三个主题的 provenance 已同步更新。

## 验证命令

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
pytest -q tests/test_release_verification.py
pytest -q tests/test_authorized_release.py
python verify_authorized_release.py
```

`verify_authorized_release.py` 默认校验已审核的 `research_matrix_live_20260924_authorized` 与 `jit_comparison_v1_final`；需要检查其他目录时传入 `--run-dir` 和 `--jit-dir`。它核对审核决策、Claim–Evidence 与来源绑定、Harness 预算和白名单、三主题 provenance 哈希、四份 PDF 哈希，以及 JIT 四臂三 seed 的归档和证据哈希。返回码为 0 才表示这两份发布证据通过。

原 `verify_submission.py` 对应冻结的 `research_matrix_v4` 提交包快照，仍固定要求 `completed_pending_human_review`，并检查其历史 `CHECKSUMS.sha256` 和缓存目录。它不代表本次授权运行的发布状态；如需重新打包旧提交物，应单独修复该包级校验的问题。
