# Prototype 初赛正式提交包

本目录是基于 JiuwenSwarm 的可审计科研 Agent 初赛正式提交包，包含英文论文、Agent 源码、Agentic Reviewer Token、实验材料与受约束 JIT Harness。

目录映射、运行环境与复现命令见 [提交说明](提交说明.md)。技术设计见 `docs/architecture.md`、`docs/module_call.md`、`docs/innovation.md`，框架贡献与资源情况见 `framework_contribution.md`、`resource_report.md`。

提交前完整性校验：

```powershell
python verify_submission.py --stage final
```

本包不包含 API Key、运行态、会话历史、虚拟环境、依赖目录、缓存及应用运行日志；保留 provenance 所需的编译日志和实验 stdout/stderr。Token 仅用于正式交付，校验器只检查其存在与非空，不读取、不输出、不写入 Git。
