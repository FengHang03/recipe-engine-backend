# Google Cloud Run 部署指南

## 📋 目录

1. [前置准备](#前置准备)
2. [Cloud SQL 设置](#cloud-sql-设置)
3. [本地开发](#本地开发)
4. [部署到 Cloud Run](#部署到-cloud-run)
5. [测试与验证](#测试与验证)
6. [监控与日志](#监控与日志)
7. [常见问题](#常见问题)

---

## 前置准备

### 1. 安装必需工具

```bash
# Google Cloud SDK
# 访问: https://cloud.google.com/sdk/docs/install

# Docker
# 访问: https://docs.docker.com/get-docker/

# 验证安装
gcloud --version
docker --version
```

### 2. 登录 Google Cloud

```bash
# 登录
gcloud auth login

# 设置项目
gcloud config set project YOUR_PROJECT_ID

# 验证
gcloud config list
```

### 3. 启用必需的 API

```bash
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    sqladmin.googleapis.com \
    secretmanager.googleapis.com
```

---

## Cloud SQL 设置

### 1. 创建 Cloud SQL 实例

```bash
# 创建 PostgreSQL 实例
gcloud sql instances create pet-recipe-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --root-password=YOUR_ROOT_PASSWORD \
    --storage-size=10GB \
    --storage-type=SSD

# 等待实例创建完成（约5-10分钟）
gcloud sql instances list
```

### 2. 创建数据库

```bash
# 创建数据库
gcloud sql databases create pet_recipe_db \
    --instance=pet-recipe-db

# 创建用户（可选）
gcloud sql users create app_user \
    --instance=pet-recipe-db \
    --password=YOUR_APP_PASSWORD
```

### 3. 导入数据

#### 方式 A: 使用 Cloud SQL Proxy（本地导入）

```bash
# 1. 下载 Cloud SQL Proxy
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.7.0/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy

# 2. 启动 Proxy
./cloud-sql-proxy YOUR_PROJECT_ID:us-central1:pet-recipe-db

# 3. 在另一个终端，使用 psql 连接
psql -h 127.0.0.1 -U postgres -d pet_recipe_db

# 4. 导入数据
psql -h 127.0.0.1 -U postgres -d pet_recipe_db < schema.sql
psql -h 127.0.0.1 -U postgres -d pet_recipe_db < data.sql
```

#### 方式 B: 使用 Cloud SQL Import

```bash
# 1. 上传 SQL 文件到 Cloud Storage
gsutil cp schema.sql gs://YOUR_BUCKET/schema.sql
gsutil cp data.sql gs://YOUR_BUCKET/data.sql

# 2. 导入
gcloud sql import sql pet-recipe-db \
    gs://YOUR_BUCKET/schema.sql \
    --database=pet_recipe_db

gcloud sql import sql pet-recipe-db \
    gs://YOUR_BUCKET/data.sql \
    --database=pet_recipe_db
```

### 4. 验证数据

```bash
# 连接数据库
gcloud sql connect pet-recipe-db --user=postgres

# 查询表
\dt

# 查询数据
SELECT COUNT(*) FROM ingredients;
SELECT COUNT(*) FROM nutrients;
```

---

## 本地开发

### 1. 设置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
nano .env
```

`.env` 内容：
```bash
ENVIRONMENT=development
DB_HOST=127.0.0.1  # Cloud SQL Proxy 地址
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=YOUR_PASSWORD
DB_NAME=pet_recipe_db
```

### 2. 启动 Cloud SQL Proxy

```bash
# 启动 Proxy（保持运行）
./cloud-sql-proxy YOUR_PROJECT_ID:us-central1:pet-recipe-db
```

### 3. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 4. 运行应用

```bash
# 加载环境变量
export $(cat .env | xargs)

# 运行
python main.py

# 或使用 uvicorn
uvicorn main:app --reload --port 8080
```

### 5. 测试 API

```bash
# 健康检查
curl http://localhost:8080/health

# 查看 API 文档
open http://localhost:8080/docs

# 生成食谱组合
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "dog_profile": {
      "name": "Max",
      "weight_kg": 10,
      "age_years": 5,
      "conditions": [],
      "allergies": []
    },
    "max_combinations": 50
  }'
```

---

## 部署到 Cloud Run

### 方式 A: 使用部署脚本（推荐）

#### 1. 编辑配置

编辑 `deploy_with_secrets.sh`：
```bash
PROJECT_ID="your-project-id"        # 修改为你的项目ID
REGION="us-central1"                # 修改为你的区域
SERVICE_NAME="l1-recipe-generator"  # 服务名称
CLOUD_SQL_INSTANCE="pet-recipe-db"  # Cloud SQL 实例名
```

#### 2. 添加执行权限

```bash
chmod +x deploy_with_secrets.sh
```

#### 3. 执行部署

```bash
./deploy_with_secrets.sh
```

脚本会自动：
- 创建 Secret Manager secrets
- 授予权限
- 构建 Docker 镜像
- 部署到 Cloud Run
- 输出服务 URL

### 方式 B: 手动部署

#### 1. 创建 Secrets

```bash
# 创建数据库密码 secret
echo -n "YOUR_DB_PASSWORD" | gcloud secrets create db-password \
    --data-file=- \
    --replication-policy="automatic"

# 创建数据库用户 secret
echo -n "postgres" | gcloud secrets create db-user \
    --data-file=- \
    --replication-policy="automatic"
```

#### 2. 授予权限

```bash
# 获取项目编号
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID \
    --format="value(projectNumber)")

# Cloud Run 服务账号
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# 授予访问 secrets 的权限
gcloud secrets add-iam-policy-binding db-password \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding db-user \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"
```

#### 3. 构建镜像

```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/l1-recipe-generator
```

#### 4. 部署

```bash
gcloud run deploy l1-recipe-generator \
    --image gcr.io/YOUR_PROJECT_ID/l1-recipe-generator \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars "ENVIRONMENT=production" \
    --set-env-vars "GCP_PROJECT_ID=YOUR_PROJECT_ID" \
    --set-env-vars "GCP_REGION=us-central1" \
    --set-env-vars "CLOUD_SQL_INSTANCE=pet-recipe-db" \
    --set-env-vars "DB_NAME=pet_recipe_db" \
    --set-secrets "DB_USER=db-user:latest" \
    --set-secrets "DB_PASSWORD=db-password:latest" \
    --add-cloudsql-instances YOUR_PROJECT_ID:us-central1:pet-recipe-db \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10
```

---

## 测试与验证

### 1. 获取服务 URL

```bash
gcloud run services describe l1-recipe-generator \
    --platform managed \
    --region us-central1 \
    --format 'value(status.url)'
```

### 2. 测试端点

```bash
SERVICE_URL="https://l1-recipe-generator-xxxxx-uc.a.run.app"

# 健康检查
curl ${SERVICE_URL}/health

# 查看 API 文档
open ${SERVICE_URL}/docs

# 获取统计信息
curl ${SERVICE_URL}/stats

# 生成食谱
curl -X POST ${SERVICE_URL}/generate \
  -H "Content-Type: application/json" \
  -d '{
    "dog_profile": {
      "name": "Max",
      "weight_kg": 10,
      "age_years": 5,
      "conditions": ["hyperlipidemia"],
      "allergies": ["chicken"]
    },
    "max_combinations": 100
  }'
```

### 3. 性能测试

```bash
# 使用 Apache Bench
ab -n 100 -c 10 ${SERVICE_URL}/health

# 使用 hey
hey -n 1000 -c 50 ${SERVICE_URL}/health
```

---

## 监控与日志

### 1. 查看日志

```bash
# 实时日志
gcloud run logs tail l1-recipe-generator --region us-central1

# 最近日志
gcloud run logs read l1-recipe-generator \
    --region us-central1 \
    --limit 50

# 过滤错误日志
gcloud run logs read l1-recipe-generator \
    --region us-central1 \
    --filter="severity>=ERROR"
```

### 2. Cloud Console 监控

访问: https://console.cloud.google.com/run

查看：
- 请求数
- 延迟
- 错误率
- 实例数量
- 内存/CPU 使用率

### 3. 设置告警

```bash
# 创建告警策略（通过 Cloud Console 更方便）
# Monitoring > Alerting > Create Policy
```

---

## 常见问题

### Q1: 部署后无法连接数据库

**解决方案：**
```bash
# 检查 Cloud SQL 实例状态
gcloud sql instances describe pet-recipe-db

# 检查 Cloud Run 是否添加了 Cloud SQL 连接
gcloud run services describe l1-recipe-generator \
    --region us-central1 \
    --format="value(spec.template.spec.containers[0].env)"

# 检查日志
gcloud run logs read l1-recipe-generator --region us-central1 --limit 100
```

### Q2: 服务启动慢或超时

**解决方案：**
```bash
# 增加内存和 CPU
gcloud run services update l1-recipe-generator \
    --region us-central1 \
    --memory 4Gi \
    --cpu 4

# 增加启动超时时间
gcloud run services update l1-recipe-generator \
    --region us-central1 \
    --timeout 600
```

### Q3: 成本过高

**优化建议：**
```bash
# 设置最小实例为 0（冷启动）
gcloud run services update l1-recipe-generator \
    --region us-central1 \
    --min-instances 0

# 减少最大实例数
gcloud run services update l1-recipe-generator \
    --region us-central1 \
    --max-instances 5

# 优化内存
gcloud run services update l1-recipe-generator \
    --region us-central1 \
    --memory 1Gi
```

### Q4: Secret 更新后服务没有使用新值

**解决方案：**
```bash
# 创建新版本 secret
echo -n "NEW_PASSWORD" | gcloud secrets versions add db-password \
    --data-file=-

# 重新部署（触发使用新 secret）
gcloud run services update l1-recipe-generator \
    --region us-central1
```

### Q5: 如何查看环境变量

```bash
gcloud run services describe l1-recipe-generator \
    --region us-central1 \
    --format="yaml(spec.template.spec.containers[0].env)"
```

---

## 🚀 快速命令参考

```bash
# 部署
./deploy_with_secrets.sh

# 查看服务
gcloud run services list

# 查看日志
gcloud run logs tail l1-recipe-generator --region us-central1

# 更新服务
gcloud run deploy l1-recipe-generator --image gcr.io/PROJECT/IMAGE

# 删除服务
gcloud run services delete l1-recipe-generator --region us-central1

# 获取服务 URL
gcloud run services describe l1-recipe-generator \
    --region us-central1 \
    --format 'value(status.url)'
```

---

## 📞 支持

如有问题，请查看：
- [Cloud Run 文档](https://cloud.google.com/run/docs)
- [Cloud SQL 文档](https://cloud.google.com/sql/docs)
- [Secret Manager 文档](https://cloud.google.com/secret-manager/docs)

祝部署顺利！ 🎉