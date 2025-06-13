#!/bin/bash

echo "Stopping backend service..."
# 查找并终止运行在8000端口的进程
lsof -ti:8000 | xargs kill -9 2>/dev/null || echo "No backend service running on port 8000"

echo "Stopping frontend service..."
# 查找并终止运行在5173端口的进程
lsof -ti:5173 | xargs kill -9 2>/dev/null || echo "No frontend service running on port 5173"

echo "All services stopped." 