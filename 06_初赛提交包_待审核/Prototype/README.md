# Prototype 初赛提交审核包

本包实现基于 JiuwenSwarm 的可审计科研 Agent：公开资料检索、研究计划、执行证据、Claim–Evidence 账本、来源审核、四臂 UCR 对照和受约束 JIT Harness。

当前为人工审核阶段，尚缺正式 `paper/paper.pdf` 和 `AgenticReviewer/paperReview-AccessToken.txt`，不应直接上传或压缩。

先阅读：

1. `提交说明.md`
2. `docs/architecture.md`
3. `docs/module_call.md`
4. `docs/innovation.md`
5. `framework_contribution.md`
6. `resource_report.md`

审核校验：

```powershell
python verify_submission.py --stage review
```

核心证据：

- `evidence/research_matrix_authorized/`
- `evidence/context_engineering_seed43/`
- `evidence/context_engineering_seed44/`
- `evidence/jit_comparison_v2_final/`

安全边界：排除 API Key、运行态、会话历史、虚拟环境、依赖目录、缓存及应用运行日志；保留 provenance 引用的编译日志和实验 stdout/stderr。未生成最终 ZIP。

当前缺项与验证边界见 [审核清单](审核清单.md)。
