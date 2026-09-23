# JiuwenSwarm v4 完整工程归档说明

生成时间：2026-09-22T03:51:21.253888Z

本文件夹同时保存两类东西：

1. **比赛提交包**：适合提交比赛，内容经过清理和验证；
2. **完整工程归档**：额外保存从服务器只读复制回来的 JiuwenSwarm/custom_rails 源码快照，以及服务器 v4 实验工作区。

## 重要区别

比赛提交包不包含服务器原始源码，也不包含 Git 历史、缓存、临时日志或敏感凭据。服务器源码位于 `03_服务器源码快照`，主要用于以后继续开发和复查，不建议直接上传比赛平台。

## 主要位置

- 比赛 ZIP：`01_比赛提交包/CCF_BDCI_1167_Prototype_Submission_20260920_v4.zip`
- v4 本机工作副本：`02_v4本机工作副本/`
- JiuwenSwarm 源码快照：`03_服务器源码快照/jiuwenswarm/`
- custom_rails 源码快照：`03_服务器源码快照/custom_rails/`
- 服务器 v4 实验区：`04_服务器v4实验工作区/v4_server_workspace/`
- 校验资料：`05_归档校验/`

## 服务器来源

服务器地址：`10.182.68.242`

服务器用户：`vergil`

服务器实验目录：`/data/vergil-CCF/ccf/v4_server_workspace`

原始 JiuwenSwarm 和 custom_rails 工程在服务器上没有被修改。本归档是只读复制形成的本地快照。

## 服务器实验目录说明

- `research_matrix_v4`：初次真实运行记录；
- `research_matrix_v4_mock`：离线 mock 运行记录；
- `research_matrix_v4_retry`：历史重试记录；
- `research_matrix_v4_retry2`：最终重试成功记录。

正式 v4 提交包只使用整理后的 `demo_runs/research_matrix_v4/`，不能把 mock 或 retry 结果当作正式最终实验。

## 当前项目状态

- 技术结构：已验证；
- v4 提交包：已准备；
- LaTeX/PDF：已编译并纳入 v4 ZIP；
- Provider 调用：3 个主题共 9 次；
- 主题状态：`completed_pending_human_review`；
- 比赛上传：未上传；
- 最终状态：`prepared_not_uploaded`。

## 还需要人工完成的事情

1. 审核检索来源是否确实适合引用；
2. 审核研究问题、实验真实性和论文结论范围；
3. 在自己的电脑上打开并检查 PDF；
4. 按比赛要求完成网页提交。


## 验证结果

- 最终 v4 ZIP 已生成，SHA-256：`F8ED0B78865AFE32D73030633ED9A998EF325D645640F2050631DE2554D257E3`。
- `01_比赛提交包/extracted_verified/` 是从最终 v4 ZIP 实际解压后再次验证的副本。
- 解压后的 `verify_submission.py` 已返回 `submission_ready: true`。
- 完整归档中的服务器源码是只读复制快照；本轮没有修改服务器原始 JiuwenSwarm、custom_rails 或服务器实验目录。
- 归档根目录不是比赛上传包；比赛上传时只使用 `01_比赛提交包/CCF_BDCI_1167_Prototype_Submission_20260920_v4.zip`。
- 归档校验文件使用 SHA-256；深层路径文件按 Windows extended-length path 方式计入，避免遗漏。
