#!/bin/bash

# ==========================================
# Google Cloud Run 部署脚本（使用 Secret Manager）
# 推荐用于生产环境
# ==========================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ==========================================
# 配置变量
# ==========================================

PROJECT_ID="project-36d4843f-b026-466b-bd4"
REGION="us-central1"
SERVICE_NAME="l1-recipe-generator"
CLOUD_SQL_INSTANCE="tuantyrecipe25"
CLOUD_SQL_CONNECTION_NAME="${PROJECT_ID}:${REGION}:${CLOUD_SQL_INSTANCE}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Secret Manager 中的 secret 名称
DB_PASSWORD_SECRET="Tuantuan_123"
DB_USER_SECRET="db-user"

# ==========================================
# 函数定义
# ==========================================

print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ==========================================
# 1. 创建 Secrets（如果不存在）
# ==========================================

print_step "检查/创建 Secrets..."

# 检查 DB_USER secret
if ! gcloud secrets describe ${DB_USER_SECRET} --project=${PROJECT_ID} &>/dev/null; then
    print_step "创建 ${DB_USER_SECRET} secret..."
    echo -n "postgres" | gcloud secrets create ${DB_USER_SECRET} \
        --data-file=- \
        --replication-policy="automatic" \
        --project=${PROJECT_ID}
else
    print_step "${DB_USER_SECRET} secret 已存在"
fi

# 检查 DB_PASSWORD secret
if ! gcloud secrets describe ${DB_PASSWORD_SECRET} --project=${PROJECT_ID} &>/dev/null; then
    print_step "创建 ${DB_PASSWORD_SECRET} secret..."
    read -sp "请输入数据库密码: " db_password
    echo
    echo -n "${db_password}" | gcloud secrets create ${DB_PASSWORD_SECRET} \
        --data-file=- \
        --replication-policy="automatic" \
        --project=${PROJECT_ID}
else
    print_step "${DB_PASSWORD_SECRET} secret 已存在"
fi

# ==========================================
# 2. 授予 Cloud Run 访问 Secrets 的权限
# ==========================================

print_step "授予 Cloud Run 访问 Secrets 的权限..."

# 获取 Cloud Run 的服务账号
PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# 授予访问权限
gcloud secrets add-iam-policy-binding ${DB_USER_SECRET} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor" \
    --project=${PROJECT_ID} \
    --quiet

gcloud secrets add-iam-policy-binding ${DB_PASSWORD_SECRET} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor" \
    --project=${PROJECT_ID} \
    --quiet

print_step "权限授予完成 ✓"

# ==========================================
# 3. 构建 Docker 镜像
# ==========================================

print_step "构建 Docker 镜像..."

gcloud builds submit \
    --tag ${IMAGE_NAME} \
    --timeout=10m \
    --project=${PROJECT_ID}

print_step "Docker 镜像构建成功 ✓"

# ==========================================
# 4. 部署到 Cloud Run（使用 Secrets）
# ==========================================

print_step "部署到 Cloud Run（使用 Secret Manager）..."

gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --project=${PROJECT_ID} \
    --set-env-vars "ENVIRONMENT=production" \
    --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars "GCP_REGION=${REGION}" \
    --set-env-vars "CLOUD_SQL_INSTANCE=${CLOUD_SQL_INSTANCE}" \
    --set-env-vars "DB_NAME=pet_recipe_db" \
    --set-secrets "DB_USER=${DB_USER_SECRET}:latest" \
    --set-secrets "DB_PASSWORD=${DB_PASSWORD_SECRET}:latest" \
    --add-cloudsql-instances ${CLOUD_SQL_CONNECTION_NAME} \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --concurrency 80 \
    --min-instances 0 \
    --max-instances 10

print_step "部署成功 ✓"

# ==========================================
# 5. 获取服务 URL
# ==========================================

SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --project=${PROJECT_ID} \
    --format 'value(status.url)')

echo ""
echo "=========================================="
echo -e "${GREEN}部署完成！${NC}"
echo "=========================================="
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "测试命令:"
echo "  curl ${SERVICE_URL}/health"
echo "  curl ${SERVICE_URL}/docs"
echo ""
echo "=========================================="