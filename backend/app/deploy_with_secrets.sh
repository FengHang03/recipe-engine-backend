#!/bin/bash

# ==========================================
# Google Cloud Run 部署脚本
# 放置位置：backend/deploy_with_secrets.sh
# 执行位置：必须在 backend/ 根目录下执行
#   cd backend/
#   bash deploy_with_secrets.sh
# ==========================================

set -e  # 任何命令失败立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_step()  { echo -e "${GREEN}[STEP]${NC} $1"; }
print_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ==========================================
# 配置变量（根据你的实际项目修改）
# ==========================================

PROJECT_ID="project-36d4843f-b026-466b-bd4"
REGION="us-central1"
SERVICE_NAME="l1-recipe-generator"
CLOUD_SQL_INSTANCE="tuantyrecipe25"
CLOUD_SQL_CONNECTION_NAME="${PROJECT_ID}:${REGION}:${CLOUD_SQL_INSTANCE}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
DB_NAME="tuanty_recipe"           # 实际数据库名

# Secret Manager 中的 secret 名称（只是名称，不是密码本身）
DB_USER_SECRET="db-user"
DB_PASSWORD_SECRET="db-password"  # secret 的标识符，密码值存在 Secret Manager 里

# ==========================================
# 前置检查
# ==========================================

print_step "检查执行目录..."

# 确认在 backend/ 根目录下执行（Dockerfile 必须存在）
if [ ! -f "Dockerfile" ]; then
    print_error "找不到 Dockerfile！请在 backend/ 根目录下执行此脚本"
    print_error "  cd backend/"
    print_error "  bash deploy_with_secrets.sh"
    exit 1
fi

print_step "当前目录：$(pwd) ✓"

# ==========================================
# 1. 创建 Secrets（如果不存在）
# ==========================================

print_step "检查/创建 Secret Manager Secrets..."

# DB_USER secret
if ! gcloud secrets describe ${DB_USER_SECRET} --project=${PROJECT_ID} &>/dev/null; then
    print_step "创建 ${DB_USER_SECRET} secret..."
    echo -n "postgres" | gcloud secrets create ${DB_USER_SECRET} \
        --data-file=- \
        --replication-policy="automatic" \
        --project=${PROJECT_ID}
    print_step "${DB_USER_SECRET} 创建成功 ✓"
else
    print_step "${DB_USER_SECRET} 已存在，跳过 ✓"
fi

# DB_PASSWORD secret
if ! gcloud secrets describe ${DB_PASSWORD_SECRET} --project=${PROJECT_ID} &>/dev/null; then
    print_step "创建 ${DB_PASSWORD_SECRET} secret..."
    read -sp "请输入数据库密码（输入时不显示）: " db_password
    echo
    echo -n "${db_password}" | gcloud secrets create ${DB_PASSWORD_SECRET} \
        --data-file=- \
        --replication-policy="automatic" \
        --project=${PROJECT_ID}
    print_step "${DB_PASSWORD_SECRET} 创建成功 ✓"
else
    print_step "${DB_PASSWORD_SECRET} 已存在，跳过 ✓"
fi

# ==========================================
# 2. 授予 Cloud Run 访问 Secrets 的权限
# ==========================================

print_step "获取项目 Service Account..."

PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

print_step "Service Account: ${SERVICE_ACCOUNT}"
print_step "授予 Secret 访问权限..."

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

print_step "构建 Docker 镜像（这可能需要几分钟）..."

gcloud builds submit \
    --tag ${IMAGE_NAME} \
    --timeout=15m \
    --project=${PROJECT_ID}

print_step "Docker 镜像构建成功 ✓"

# ==========================================
# 4. 部署到 Cloud Run
# ==========================================

print_step "部署到 Cloud Run..."

gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --project=${PROJECT_ID} \
    \
    `# 环境变量` \
    --set-env-vars "ENVIRONMENT=production" \
    --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars "GCP_REGION=${REGION}" \
    --set-env-vars "CLOUD_SQL_INSTANCE=${CLOUD_SQL_INSTANCE}" \
    --set-env-vars "DB_NAME=${DB_NAME}" \
    \
    `# 从 Secret Manager 读取敏感信息` \
    --set-secrets "DB_USER=${DB_USER_SECRET}:latest" \
    --set-secrets "DB_PASSWORD=${DB_PASSWORD_SECRET}:latest" \
    \
    `# Cloud SQL 连接` \
    --add-cloudsql-instances ${CLOUD_SQL_CONNECTION_NAME} \
    \
    `# 资源配置` \
    --memory 2Gi \
    --cpu 2 \
    \
    `# 超时：食谱生成需要 1-3 分钟，600s 足够` \
    --timeout 600 \
    \
    `# 并发：食谱生成是 CPU 密集型，每实例只处理 1 个请求` \
    --concurrency 1 \
    \
    `# 实例数：最少 1 个避免冷启动，最多 3 个（演示版够用）` \
    --min-instances 1 \
    --max-instances 3

print_step "部署成功 ✓"

# ==========================================
# 5. 获取服务 URL 并验证
# ==========================================

print_step "获取服务 URL..."

SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --project=${PROJECT_ID} \
    --format 'value(status.url)')

print_step "验证服务健康状态..."

# 等待几秒让服务启动
sleep 5

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/health" || echo "000")

echo ""
echo "=========================================="
if [ "${HTTP_STATUS}" = "200" ]; then
    echo -e "${GREEN}✅ 部署成功！服务运行正常${NC}"
else
    print_warn "服务已部署，但健康检查返回 ${HTTP_STATUS}（服务可能还在启动中）"
fi
echo "=========================================="
echo ""
echo "📌 Service URL : ${SERVICE_URL}"
echo ""
echo "🔍 验证命令："
echo "   curl ${SERVICE_URL}/health"
echo "   curl ${SERVICE_URL}/docs"
echo ""
echo "📋 查看日志："
echo "   gcloud run services logs read ${SERVICE_NAME} --region ${REGION} --limit 50"
echo ""
echo "=========================================="
