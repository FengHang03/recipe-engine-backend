# 使用 Python 3.11 官方镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements 文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口（Cloud Run 会使用环境变量 PORT）
EXPOSE 8080

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# 启动命令
# Cloud Run 会自动设置 PORT 环境变量
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1