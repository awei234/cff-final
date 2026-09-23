#!/bin/bash
# CCF 比赛服务器便捷连接脚本（SSH 免密）
# 用法: ccfssh.sh           # 交互式登录
#       ccfssh.sh '命令'    # 执行单条命令
ssh -o BatchMode=yes -o ConnectTimeout=10 vergil@10.182.68.242 "$@"
