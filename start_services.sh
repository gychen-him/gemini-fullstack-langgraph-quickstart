#!/bin/bash

# 确保脚本在出错时停止执行
set -e

# 创建根目录日志目录
mkdir -p logs

echo "Starting backend service..."
cd backend
# 后端日志写到根目录 logs
langgraph dev --port 8000 --no-reload --server-log-level debug 2>&1 | tee ../logs/backend.log &
BACKEND_PID=$!

echo "Starting frontend service..."
cd ../frontend
# 前端日志也写到根目录 logs
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!

# 将进程ID保存到文件中，以便后续停止服务
echo $BACKEND_PID > .backend.pid
echo $FRONTEND_PID > .frontend.pid

echo "Services started:"
echo "Backend running on http://localhost:8000"
echo "Frontend running on http://localhost:5173/app/"
echo "Use ./stop_services.sh to stop the services"
echo "Frontend logs are available in logs/frontend.log" 