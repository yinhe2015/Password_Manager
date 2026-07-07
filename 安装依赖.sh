#!/usr/bin/env bash

# 检查 Python3 是否安装
python3 --version >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo python3 未安装
    exit 1
fi

# 安装必要的包
python3 -m pip install -r requirements.txt

echo "安装完成"