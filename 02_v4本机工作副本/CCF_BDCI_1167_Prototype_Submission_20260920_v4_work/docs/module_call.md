# v3 模块调用说明

## 主入口

`code/03_技术实现/competition_runner/run_research_matrix.py` 只负责参数解析和安全门；实际流程在同目录包中的 `competition_runner/research_matrix.py`。

## 调用顺序

1. 读取 `config/research_matrix_v3.json`；
2. 校验三个主题和调用预算；
3. 校验确认开关、输出目录和 `DEEPSEEK_API_KEY`；
4. 访问公开元数据源并保存来源哈希；
5. 执行本地 deterministic benchmark；
6. 调用 DeepSeek 生成 plan；
7. 调用 DeepSeek 审查 experiment results；
8. 调用 DeepSeek 生成 report；
9. 过滤未知 citation，写出 Rail 事件和人工待审核记录；
10. 写出 paper、provenance 和 verification report。

## 错误语义

- `retrieval_failed`：没有得到公开资料；
- `partial_retrieval`：部分来源成功、部分失败；
- `provider_invalid_json`：模型没有返回合法 JSON；
- `citation_mapping_blocked`：模型引用了未保存的来源 ID，相关映射被阻止；
- `partial_failed`：矩阵中至少一个主题失败，但没有被包装成整体成功；
- `completed_pending_human_review`：自动流程完成，但人还没有确认最终研究与提交。
