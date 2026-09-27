# JiuwenSwarm v3 research-pipeline

这个技能规范的是一个有界的科研论文半流程，不是无人值守科研系统。

## 固定边界

- 只允许使用配置中的三个主题；
- 公开资料必须有 URL、访问时间、摘要和 SHA-256；
- 本地实验必须真实执行并保存命令、工作目录、stdout/stderr 哈希和结果；
- fixture 只能做合同校验；
- UCR / 本地 benchmark 只能证明流程和证据能力，不能包装成领域科学结果；
- Provider 每主题最多三次、总共最多九次；
- 引用必须映射到已保存的 source_id；
- 没有人工最终确认时只能是 `completed_pending_human_review`。

## 阶段

1. 检索资料；
2. 生成研究计划；
3. 执行固定本地基准；
4. 审查实验结果；
5. 生成结构化报告；
6. 写出 provenance、verification 和人工待审核日志。

任何失败都要留下失败状态，禁止伪造成功论文、实验结果或引用。
