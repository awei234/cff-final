# v3 架构说明

## 1. 分层

```text
run_research_matrix.py
        |
        v
research_matrix.py
  |-- 固定主题矩阵配置
  |-- OpenAlex / arXiv / Crossref 资料适配器
  |-- 去重、摘要截断、来源哈希和缓存
  |-- 本地 deterministic process-evidence benchmark
  |-- DeepSeek 三阶段 Provider 调用
  |-- citation / evidence / Rail 安全门
  |-- provenance 和 verification report
        |
        v
 demo_runs/research_matrix_v3/<topic_id>/
```

## 2. 三阶段 Provider 流程

第一阶段只生成研究计划；第二阶段只审查本地实验与证据；第三阶段才生成结构化研究报告。第二阶段不能修改原始实验结果，第三阶段只能引用 `research_materials.json` 中存在的 `source_id`。

Provider 返回非法 JSON、引用未知来源或报告证据不足时，系统会阻止相关结论、记录 Rail 事件或直接标记失败。不会把 Provider 的自然语言猜测写成已验证事实。

## 3. 公开检索

每个主题使用固定关键词，按 OpenAlex、arXiv、Crossref 的顺序取得候选元数据。只保存标题、作者、年份、摘要、DOI、URL、访问时间和哈希，不下载和打包未经确认版权的全文。重复项按 DOI、来源 ID 和规范化标题去重，最终保留最多 10 条。

缓存位于工作目录的 `.research_cache/v3/`，打包时排除。联网失败时 `research_materials.json` 的状态为 `partial_retrieval` 或 `retrieval_failed`。

## 4. 本地实验边界

三个主题使用同一个固定输入和 seed=42 的小型基准。它包含 baseline 和 full-rail 两个 arm，测试：

- 输入和命令是否被记录；
- stdout、stderr 和结果是否有哈希；
- 没有证据的断言是否被阻止；
- 相同输入和 seed 是否可复核。

这个基准只证明科研流程和证据控制能力，不证明上下文工程、记忆引擎或自我进化已经取得领域科学改进。
