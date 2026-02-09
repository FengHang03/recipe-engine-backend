"""
数据库连接配置
支持本地开发和 Google Cloud Run 部署
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from google.cloud.sql.connector import Connector

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """数据库配置管理"""
    
    def __init__(self):
        self.environment = os.environ.get('ENVIRONMENT', 'development')
        
        # Cloud SQL 配置
        self.project_id = os.environ.get('GCP_PROJECT_ID', 'your-project-id')
        self.region = os.environ.get('GCP_REGION', 'us-central1')
        self.instance_name = os.environ.get('CLOUD_SQL_INSTANCE', 'your-instance-name')
        
        # 数据库凭证
        self.db_user = os.environ.get('DB_USER', 'postgres')
        self.db_password = os.environ.get('DB_PASSWORD', '')
        self.db_name = os.environ.get('DB_NAME', 'pet_recipe_db')
        
    def get_connection_string(self) -> str:
        """获取数据库连接字符串"""
        if self.environment == 'production':
            # Cloud Run 环境：使用 Unix socket 连接
            return self._get_cloud_sql_connection_string()
        else:
            # 本地开发环境：使用 TCP 连接
            return self._get_local_connection_string()
    
    def _get_cloud_sql_connection_string(self) -> str:
        """
        Cloud Run 连接字符串（使用 Unix socket）
        格式: postgresql+pg8000://user:pass@/dbname?unix_sock=/cloudsql/PROJECT:REGION:INSTANCE/.s.PGSQL.5432
        """
        connection_name = f"{self.project_id}:{self.region}:{self.instance_name}"
        
        connection_string = (
            f"postgresql+pg8000://{self.db_user}:{self.db_password}@/"
            f"{self.db_name}?"
            f"unix_sock=/cloudsql/{connection_name}/.s.PGSQL.5432"
        )
        
        logger.info(f"Using Cloud SQL connection: {connection_name}")
        return connection_string
    
    def _get_local_connection_string(self) -> str:
        """
        本地开发连接字符串
        格式: postgresql://user:pass@host:port/dbname
        """
        db_host = os.environ.get('DB_HOST', 'localhost')
        db_port = os.environ.get('DB_PORT', '5432')
        
        connection_string = (
            f"postgresql://{self.db_user}:{self.db_password}@"
            f"{db_host}:{db_port}/{self.db_name}"
        )
        
        logger.info(f"Using local PostgreSQL connection: {db_host}:{db_port}")
        return connection_string
    
    def create_engine(self):
        """创建 SQLAlchemy Engine"""
        connection_string = self.get_connection_string()
        
        # Cloud Run 使用 NullPool (无连接池)
        # 因为每个请求都是短暂的，不需要保持连接
        if self.environment == 'production':
            engine = create_engine(
                connection_string,
                poolclass=NullPool,
                echo=False
            )
        else:
            engine = create_engine(
                connection_string,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,  # 自动检测断开的连接
                echo=False
            )
        
        logger.info("Database engine created successfully")
        return engine


# ==========================================
# 使用 Cloud SQL Python Connector (推荐方式)
# ==========================================

class CloudSQLConnector:
    """
    使用 Google Cloud SQL Python Connector
    这是 Google 推荐的连接方式，自动处理认证和连接管理
    """
    
    def __init__(self):
        self.config = DatabaseConfig()
        self.connector = None
    
    def get_connection_pool(self):
        """
        创建连接池（使用 Cloud SQL Connector）
        适用于 Cloud Run
        """
        if self.config.environment != 'production':
            # 本地开发使用标准连接
            return self.config.create_engine()
        
        # Cloud Run 使用 Connector
        self.connector = Connector()
        
        def getconn():
            """获取数据库连接"""
            connection_name = (
                f"{self.config.project_id}:"
                f"{self.config.region}:"
                f"{self.config.instance_name}"
            )
            
            conn = self.connector.connect(
                connection_name,
                "pg8000",
                user=self.config.db_user,
                password=self.config.db_password,
                db=self.config.db_name
            )
            return conn
        
        # 创建 SQLAlchemy engine
        engine = create_engine(
            "postgresql+pg8000://",
            creator=getconn,
            poolclass=NullPool
        )
        
        logger.info("Cloud SQL Connector initialized")
        return engine
    
    def close(self):
        """关闭连接"""
        if self.connector:
            self.connector.close()
            logger.info("Cloud SQL Connector closed")


# ==========================================
# 便捷函数
# ==========================================

def get_database_engine():
    """
    获取数据库引擎（便捷函数）
    自动根据环境选择连接方式
    """
    connector = CloudSQLConnector()
    return connector.get_connection_pool()


def test_connection():
    """测试数据库连接"""
    try:
        engine = get_database_engine()
        
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            logger.info("✅ Database connection successful!")
            return True
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


# ==========================================
# 环境变量检查
# ==========================================

def validate_environment():
    """验证必需的环境变量"""
    required_vars = {
        'production': [
            'GCP_PROJECT_ID',
            'GCP_REGION', 
            'CLOUD_SQL_INSTANCE',
            'DB_USER',
            'DB_PASSWORD',
            'DB_NAME'
        ],
        'development': [
            'DB_USER',
            'DB_PASSWORD',
            'DB_NAME'
        ]
    }
    
    environment = os.environ.get('ENVIRONMENT', 'development')
    missing_vars = []
    
    for var in required_vars.get(environment, []):
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        return False
    
    logger.info(f"✅ All required environment variables present for {environment}")
    return True


if __name__ == "__main__":
    # 测试连接
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if not validate_environment():
        sys.exit(1)
    
    if test_connection():
        print("Database connection test passed!")
    else:
        print("Database connection test failed!")
        sys.exit(1)