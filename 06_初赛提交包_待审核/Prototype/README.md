# Prototype 初赛提交包

本目录是基于 JiuwenSwarm 的可审计科研 Agent 初赛提交包，包含源码、论文、评审 Token、实验与 JIT Harness 证据。

完整的目录映射、复现命令、审核边界及压缩前检查，请阅读 [提交说明](提交说明.md)。

建议审核顺序：

1. `提交说明.md`
2. `docs/architecture.md`、`docs/module_call.md`、`docs/innovation.md`
3. `framework_contribution.md`、`resource_report.md`
4. `审核清单.md`

最终结构与完整性校验：

```powershell
python verify_submission.py --stage final
```

本包不包含 API Key、运行态、会话历史、虚拟环境、依赖目录、缓存及应用运行日志；保留 provenance 所需的编译日志和实验 stdout/stderr。尚未生成 ZIP，供人工审核后再压缩。
