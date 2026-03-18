#!/bin/bash

# 启动后端服务器
cd backend

# 检查是否安装了 uv
if ! command -v uv &> /dev/null; then
    echo "正在安装 uv..."
    pip install uv
fi

# 使用 uv 同步依赖
echo "同步依赖..."
uv sync

# 启动服务器
echo "启动后端服务器..."
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

