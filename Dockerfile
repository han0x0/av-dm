# ============================================
# 构建阶段：构建前端
# ============================================
FROM node:20-alpine AS web-builder

WORKDIR /app/web

# 复制前端依赖文件
COPY web/package.json ./

# 安装依赖
RUN npm install

# 复制前端源码
COPY web/ ./

# 构建前端
RUN npm run build

# ============================================
# 构建阶段：Python 依赖
# ============================================
FROM python:3.11-slim AS python-deps

WORKDIR /app

# 安装编译依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# 最终阶段：运行环境
# ============================================
FROM python:3.11-slim

# 安装 Nginx 和运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -f /etc/nginx/sites-enabled/default \
    && rm -f /usr/share/nginx/html/index.html

# 设置工作目录
WORKDIR /app

# 复制 Python 依赖
COPY --from=python-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-deps /usr/local/bin /usr/local/bin

# 复制应用代码
COPY app/ ./app/
COPY run.py .

# 复制前端构建产物
COPY --from=web-builder /app/web/dist /usr/share/nginx/html

# 复制 Nginx 配置（覆盖默认配置）
COPY nginx/default.conf /etc/nginx/sites-available/default
RUN ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# 创建数据目录和日志目录
RUN mkdir -p /app/data /app/logs

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 暴露端口
# 80 - Nginx (前端 + API 代理)
# 8080 - FastAPI (内部使用)
EXPOSE 80 8080

# 启动脚本
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/stats || exit 1

# 启动命令
CMD ["/app/start.sh"]
