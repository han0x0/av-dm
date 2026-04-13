#!/bin/bash
set -e

# 测试 Nginx 配置
echo "Testing Nginx configuration..."
nginx -t

# 启动 Nginx（后台运行）
echo "Starting Nginx..."
nginx

# 等待 Nginx 启动
sleep 2

# 检查 Nginx 是否在监听 80 端口
if netstat -tlnp 2>/dev/null | grep -q ':80'; then
    echo "Nginx started successfully (port 80)"
elif ss -tlnp 2>/dev/null | grep -q ':80'; then
    echo "Nginx started successfully (port 80)"
else
    echo "WARNING: Nginx may not have started properly"
fi

# 启动应用
echo "Starting AV Download Manager..."
exec python run.py
