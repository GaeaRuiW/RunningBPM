#!/bin/bash

# 启动前端开发服务器
cd frontend

# 检查 node_modules
if [ ! -d "node_modules" ]; then
    echo "安装依赖..."
    npm install
fi

# 启动开发服务器
echo "启动前端开发服务器..."
npm start

