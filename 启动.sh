#!/usr/bin/env bash

# 检查 Python3 是否安装
python3 --version >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo python3 未安装
    read -p "按任意键退出..." -n
    exit 1
fi

# 启动应用
nohup python3 图形.py &