# """
# auth.py
# Firebase ID Token 验证模块
# 职责：验证前端传入的 Firebase Token，解析出 uid，作为 FastAPI 依赖注入使用
# """

# import os
# import logging
# from functools import lru_cache

# import firebase_admin
# from firebase_admin import auth, credentials
# from fastapi import Depends, HTTPException, status
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# logger = logging.getLogger(__name__)

# # ==========================================
# # Firebase Admin SDK 初始化（单例）
# # ==========================================

# @lru_cache(maxsize=1)
# def _get_firebase_app() -> firebase_admin.App:
#     """
#     初始化 Firebase Admin SDK（全局只初始化一次）
    
#     本地开发：需要设置环境变量 GOOGLE_APPLICATION_CREDENTIALS 指向 service account JSON 文件
#     Cloud Run：自动使用绑定的 Service Account，无需任何配置
#     """
#     if firebase_admin._DEFAULT_APP_NAME in firebase_admin._apps:
#         # 已经初始化过，直接返回
#         return firebase_admin.get_app()

#     env = os.environ.get("ENVIRONMENT", "development")

#     if env == "production":
#         # Cloud Run 环境：使用默认 Service Account（自动授权，无需密钥文件）
#         cred = credentials.ApplicationDefault()
#         logger.info("Firebase Admin SDK 初始化：使用 Application Default Credentials（Cloud Run）")
#     else:
#         # 本地开发环境：使用 Service Account JSON 文件
#         # 需要在 .env 中设置：FIREBASE_CREDENTIALS_PATH=path/to/serviceAccountKey.json
#         cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH")
#         if not cred_path:
#             raise RuntimeError(
#                 "本地开发环境缺少 FIREBASE_CREDENTIALS_PATH 环境变量，"
#                 "请在 .env 文件中设置 Firebase Service Account JSON 文件路径"
#             )
#         cred = credentials.Certificate(cred_path)
#         logger.info(f"Firebase Admin SDK 初始化：使用本地 Service Account 文件 {cred_path}")

#     app = firebase_admin.initialize_app(cred)
#     logger.info("Firebase Admin SDK 初始化成功")
#     return app


# # ==========================================
# # HTTP Bearer Token 提取器
# # ==========================================

# # FastAPI 内置的 Bearer Token 提取器
# # 自动从请求 Header 中提取：Authorization: Bearer <token>
# _bearer_scheme = HTTPBearer(
#     scheme_name="Firebase ID Token",
#     description="Firebase 登录后获取的 ID Token",
#     auto_error=True,  # Token 缺失时自动返回 401
# )


# # ==========================================
# # 用户信息数据类
# # ==========================================

# class FirebaseUser:
#     """经过验证的 Firebase 用户信息"""

#     def __init__(self, uid: str, email: str | None = None):
#         self.uid = uid
#         self.email = email

#     def __repr__(self):
#         return f"FirebaseUser(uid={self.uid}, email={self.email})"


# # ==========================================
# # FastAPI 依赖函数（核心）
# # ==========================================

# async def get_current_user(
#     credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
# ) -> FirebaseUser:
#     """
#     FastAPI 依赖注入函数：验证 Firebase ID Token，返回当前用户信息
    
#     使用方式：
#         @app.post("/recipes/generate")
#         async def generate(user: FirebaseUser = Depends(get_current_user)):
#             uid = user.uid  # 直接使用，已经过验证
    
#     验证失败时自动返回 401 Unauthorized
#     """
#     # 确保 Firebase SDK 已初始化
#     _get_firebase_app()

#     token = credentials.credentials  # 从 Header 取出的 Token 字符串

#     try:
#         # 用 Firebase Admin SDK 验证 Token
#         # 这一步会自动验证：签名、过期时间、发行方等
#         decoded_token = auth.verify_id_token(token)

#         uid = decoded_token.get("uid")
#         email = decoded_token.get("email")  # 可能为空（例如匿名登录）

#         if not uid:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Token 无效：无法解析用户 uid",
#             )

#         logger.debug(f"Token 验证成功：uid={uid}")
#         return FirebaseUser(uid=uid, email=email)

#     except auth.ExpiredIdTokenError:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Token 已过期，请重新登录",
#         )
#     except auth.InvalidIdTokenError as e:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail=f"Token 无效：{str(e)}",
#         )
#     except auth.RevokedIdTokenError:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Token 已被撤销，请重新登录",
#         )
#     except Exception as e:
#         logger.error(f"Token 验证异常：{e}", exc_info=True)
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Token 验证失败，请重新登录",
#         )
