# 创新点与技术贡献

## 1. Claim–Evidence 闭环

系统不是在生成后追加一句“请人工核实”，而是把 Claim、工具事件、引用来源、人工决策和发布状态绑定成可机读账本。没有成功证据的完成声明会被分类为 `unexecuted` 或阻断，不允许混入结论。

## 2. 受约束 JIT Harness

第四实验臂 `jit-constrained` 在运行时选择安全 Profile，同时受 Manifest Schema、工具白名单、预算上限和硬 Rail 约束。JIT 不能输出任意代码、放宽权限或绕过人工引用审核；选择失败时回退到 `full-rail`。

这使“动态策略选择”与“不可突破的安全边界”可以同时实验和审计。

## 3. 四臂、多 seed、可篡改检测的实验交付

对照保留 baseline、prompt-only、full-rail，并新增 jit-constrained，使用 seeds 42、43、44。每次运行保存：

- 策略和 Manifest；
- Schema、白名单、预算和 Rail 校验；
- 成本、时延、调用次数；
- 工具事件、Claim 决策和结果；
- provenance、档案自哈希和结果哈希。

独立验证器检查 12/12 运行，并验证篡改后的 Harness 档案会被拒绝。

## 4. 来源与 Claim 双重审核

来源获准引用不等于任意结论都能进入论文；Claim 获准也必须绑定允许来源或实验事实。当前流程保留五条失败/阻断 Claim 作为排除项，并对已批准的 `claim-018` 至 `claim-020` 记录来源绑定。

## 5. 诚实的指标边界

UCR 衡量“未执行却声称完成”的比例，是过程证据指标。fixture 结果中 baseline UCR 为 0.5556，其余三臂为 0，但该结果不能外推为领域准确率、任务质量或因果性能提升。

资源、Token、成本和未测量项均显式记录，不用估算值冒充实测值。

## 6. JiuwenSwarm 工程贡献

贡献包括执行证据 Rail、研究矩阵 Runner、Claim–Evidence 审核、JIT Harness 接入、交付验证器和网页模型配置校验。源码、测试、commit 链接和 patch 说明见根目录 `framework_contribution.md`。
