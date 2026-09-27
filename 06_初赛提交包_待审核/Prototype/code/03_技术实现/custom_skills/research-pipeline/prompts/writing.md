# Writing 论文写作操作手册

> 如何写出符合学术规范（NeurIPS/ICML/ICLR 风格）的论文。改编自 FARS 附录 B Paper Writing Guidelines（Simon Peyton Jones 写作建议 + 会议格式要求）。
> 执法者：F03（数字必须与 results.json 一致）、F04（引用必须真实可核验）、F01（词数≥4000 / 图≥4 / 表≥6 / 含复杂度分析 / 7 段结构）。

## 核心原则

你的论文讲一个故事：问题 → 为什么重要 → 你的方法 → 有效的证据 → 意味着什么。每个章节服务这条叙事。

## 从 proposal.md 出发

你已经写过研究提案（proposal.md），包含 introduction、approach、related work、references。**把它当基础**：
- **Introduction**：改编自 proposal.md 的 Introduction，实验完成后补充具体结果
- **Related Work**：从 proposal.md 的 Related Work 扩展，用 references/ 里的 BibTeX
- **Method**：从 proposal.md 的 Proposed Approach 扩展，补全技术细节、符号、算法描述
- **References**：从 proposal.md 和 references/ 的引用起步，补实验中发现的新论文

**不要从零重写**——精炼和扩展已有的。

## 写作顺序（≠ 成稿顺序）

1. Methods → Experiments → Contributions 列表 → Conclusion
2. 然后 Introduction（现在知道要引什么了）
3. 然后 Related Work
4. **Abstract 最后写**（总结完成的论文）

## 成稿结构

```
1. Title
2. Abstract（150-250 词，单段）
3. Introduction（问题、缺口、贡献列表、路线图）
4. Related Work（漏斗：宽 → 窄，以定位收尾）
5. Method（完整、可复现的描述）
6. Experiments（Setup、结果表、消融、分析）
7. Discussion / Limitations
8. Conclusion
9. References
```

## Abstract

- 单段 150-250 词
- 结构：context → problem → method → key result → implication
- 自包含——不读正文也能懂
- 摘要中不引用文献
- 尽量包含一个具体量化结果

## Introduction

- 从已知开始（context）
- 指出缺口（缺什么、坏在哪）
- 一句话说清你的方法
- 显式列出贡献：
  ```latex
  Our contributions are:
  \begin{itemize}
    \item We propose X, which addresses Y.
    \item We show that Z through experiments on A and B.
    \item We release our code and data at [URL].
  \end{itemize}
  ```
- 结尾给路线图："Section 2 reviews..., Section 3 describes..., Section 4 presents..."

## Related Work

- 按方法/概念组织，**不按时间**
- 漏斗结构：宽领域 → 具体子问题 → 直接竞争方法
- 每组相关工作说明：①他们做什么 ②你的工作有何不同
- 以 "Unlike [prior work], our approach..." 收尾
- **每条引用必须是真实可核验的**——引用前到 OpenAlex（api.openalex.org）或 arXiv 确认论文存在

## Method

- 完整到专家只读论文就能复现
- 显式陈述所有假设
- 包含：模型架构、损失函数、训练算法
- 符号清晰，首次使用即定义
- 多组件方法配一张方法概览图

## Experiments

结构：Setup → Main results → Ablations → Analysis

### Setup 小节
- 数据集：名称、规模、划分、预处理
- Baseline：是什么、为什么选、怎么训练（公平对比）
- 指标：哪些、为什么合适
- 实现：优化器、lr、epochs、batch size、硬件、训练时间
- 种子：几个、哪些值

### Results 小节
- 主对比表：你的方法 vs 所有 baseline
- 每列最优值加粗
- ↑/↓ 标注高低哪个更好
- **论文里每个数字必须与 experiments/ 的结果完全一致**

### Ablation 小节
- 一张表：完整方法、然后移除每个组件
- 证明每个组件都有贡献

### Analysis 小节（可选但增强论文）
- 失败案例：你的方法在哪失败、为什么
- 定性示例：展示模型实际产出
- 训练曲线：展示收敛行为

## 表格

```latex
\begin{table}[t]
\caption{Comparison on [Dataset]. Best results in \textbf{bold}. $\uparrow$ means higher is better.}
\label{tab:main}
\centering
\begin{tabular}{lccc}
\toprule
Method & Accuracy $\uparrow$ & F1 $\uparrow$ & Latency (ms) $\downarrow$ \\
\midrule
Baseline A & 82.1 $\pm$ 0.3 & 79.4 $\pm$ 0.5 & 12.3 \\
Baseline B & 84.7 $\pm$ 0.2 & 81.2 $\pm$ 0.4 & 15.7 \\
\textbf{Ours} & \textbf{87.3 $\pm$ 0.2} & \textbf{84.1 $\pm$ 0.3} & 14.1 \\
\bottomrule
\end{tabular}
\end{table}
```

规则：
- 用 booktabs（\toprule, \midrule, \bottomrule）——**不要竖线**
- caption 在**表格上方**
- caption 自包含：不读正文也能懂
- 正文必须引用每张表："As shown in Table~\ref{tab:main}..."
- 数字必须与实验结果完全一致

## 图

```latex
\begin{figure}[t]
\centering
\includegraphics[width=0.8\linewidth]{figures/training_curve.pdf}
\caption{Training loss over epochs. Our method (blue) converges faster than Baseline A (orange) and Baseline B (green).}
\label{fig:training}
\end{figure}
```

规则：
- caption 在**图下方**
- caption 自包含
- 尽量用 PDF/矢量格式（不用低清 PNG）
- 印刷尺寸可读（图中字号 ≥8pt）
- 正文必须引用每张图："Figure~\ref{fig:training} shows..."
- 所有图配色统一

## Discussion / Limitations

- 讨论结果**意味着什么**，不只结果是什么
- 诚实承认局限：
  - "Our method assumes X, which may not hold in Y scenarios"
  - "We evaluated on Z datasets; generalization to other domains is untested"
- 评审奖励诚实——隐藏局限会被拒稿

## Conclusion

- 各用一句话复述问题和你的方法
- 用具体数字总结关键发现
- 陈述更广泛的影响
- 建议未来工作
- **不引入新结果或新声明**
- 0.5-1 页

## References（关键）

- **每条引用必须是真实、可核验的出版物**
- 用 OpenAlex 或 arXiv 找到并验证论文（Semantic Scholar 限流严重默认不用）
- 伪造或幻觉引用破坏科学诚信
- 格式正确：authors, title, venue, year
- 优先已发表会议/期刊论文而非 arXiv 预印本
- 典型 ML 论文 15-30 条引用
- `\citep{}` 括号式："(Smith et al., 2023)"
- `\citet{}` 文本式："Smith et al. (2023) showed..."

## LaTeX 最佳实践

- 用会议官方 style 文件（iclr2026.sty 等）
- 表格用 booktabs（无竖线）
- `\usepackage{hyperref}` 可点击引用
- 符号用 `\newcommand` 保持一致性
- 引用前用 `~` 非断行空格：Table~\ref{tab:main}
- 至少编译两遍解析交叉引用
- 正文 8-10 页（不含参考文献和附录）

## 导致拒稿的常见错误

- Introduction 没有显式贡献列表
- 声明没有实验证据支撑
- 正文数字与实验结果不一致
- 没有消融研究
- baseline 对比不公平
- 伪造引用
- 没有局限讨论
- 写作质量差 / 主要贡献不清晰
