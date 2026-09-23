# 服务器连接和来源说明

## 连接信息

- SSH 别名：`ws`
- 用户：`vergil`
- 地址：`10.182.68.242`
- 服务器实验目录：`/data/vergil-CCF/ccf/v4_server_workspace`

## 已复制内容

本地归档中包含：

- `/data/vergil-CCF/ccf/jiuwenswarm` 的源码快照；
- `/data/vergil-CCF/ccf/custom_rails` 的源码快照；
- `/data/vergil-CCF/ccf/v4_server_workspace` 的 v4 实验工作区快照。

## 复制原则

- 使用只读 SSH/SCP 复制；
- 没有在服务器上运行删除、移动、覆盖命令；
- 没有修改服务器原始 JiuwenSwarm 工程；
- 没有修改服务器原始 custom_rails 工程；
- 复制后在本机归档目录中移除了 `.git`、`__pycache__`、`.pyc`、缓存和运行日志。

## 安全说明

源码中的部分测试和文档可能包含公开示例字符串，例如 `api_key`、Bearer 示例或测试私钥标记。这些属于源码测试/文档样例，不是本次 DeepSeek 运行密钥。

本归档不保存当前环境中的实际 API Key、Authorization Header 或 SAR Token。最终提交包还会继续执行敏感信息检查。
