# ==========================================
# Dockerfile
# 放置位置：backend/Dockerfile
# 构建上下文：backend/ 根目录
# ==========================================

FROM python:3.11-slim

WORKDIR /code

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 先复制 requirements.txt，利用 Docker 层缓存
# 只有 requirements.txt 变化时才重新安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制 app/ 目录，保留 app/ 这一层
# 这样容器里的结构是 /code/app/，from app.xxx 的 import 可以正常工作
COPY app/ ./app/

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# 暴露端口（Cloud Run 使用 PORT 环境变量，默认 8080）
EXPOSE 8080

# 启动命令
# 注意：因为 main.py 在 app/ 目录下，所以是 app.main:app
# workers=1：食谱生成是 CPU 密集型，单 worker 配合 Cloud Run 自动扩容
CMD exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8080} \
    --workers 1 \
    --log-level info