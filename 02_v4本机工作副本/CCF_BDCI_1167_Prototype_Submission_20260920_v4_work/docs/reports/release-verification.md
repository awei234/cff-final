# 发布验证说明

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

## 发布前最后一步

当前 live 运行的 `run_manifest.json` 明确标记 `latex_compilation_status=user_compile_required`。因此发布前必须在目标环境中编译对应 `paper.tex`，记录编译命令、返回码、页数、PDF SHA-256，并更新 provenance；不能仅凭 `allow_paper=true` 宣称 PDF 已验证。

## 验证命令

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
pytest -q tests/test_release_verification.py
```

完整 `verify_submission.py` 还会检查工作副本中既有的缓存、校验清单和快照哈希；这些包级问题须单独清理，不应通过修改 Claim 审核结果绕过。
