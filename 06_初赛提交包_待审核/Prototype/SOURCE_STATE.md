# 源状态与选择性整合记录

## 原始来源

- 仓库：`https://github.com/awei234/cff-final.git`
- 原始分支：`feature`
- 原始 HEAD：`57729914dae03136db9c65f575331bd0551b47f5`
- 远端状态：`origin/feature` 指向同一 HEAD
- 原始工作副本：`02_v4本机工作副本/CCF_BDCI_1167_Prototype_Submission_20260920_v4_work`

原 `feature` 工作树保持未提交、未合并、未推送状态，本审核包未在该工作树写入文件。

## 整合目标

- 整合分支：`codex/submission-review`
- 方式：从原始工作副本按白名单复制；
- 冻结保护：不修改 `01_比赛提交包` 与 `03_服务器源码快照`。

## 选择性纳入

- JIT/UCR 代码、测试和 v2 最终 12-run evidence；
- Competition Runner 与 Harness 安全控制；
- 授权研究运行及 seed 43/44 复现 evidence；
- JiuwenSwarm 源码及网页模型配置校验修复；
- 架构、模块调用、创新、发布与交接材料；
- Harness 源包、构建器和测试，但不纳入 ZIP。

## 明确排除

- `runtime_local/`；
- `.venv/`、`node_modules/`；
- 缓存、字节码、日志、会话历史；
- JIT v1、retry、smoke 等历史目录；
- API Key、Authorization Header 和本机模型配置；
- 最终提交 ZIP。

原始未提交文件的详细范围见 `docs/reports/副本开发整合交接文档.md`。审核包以自身 `CHECKSUMS.sha256` 固定选择结果。
