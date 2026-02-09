import os
import time
from typing import Optional, Dict, Any

import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException, responses
from jose import jwt
from jose.utils import base64url_decode

from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./dev.db")  # 先本地，后面换 Cloud SQL Postgres

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ===== startup =====
    await ensure_users_table()

    yield

app = FastAPI(lifespan = lifespan)

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],  # 允许 Authorization 等头
)
GOOGLE_JWKS_URL = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"
_jwks_cache: Dict[str, Any] = {"keys": None, "ts": 0}

async def get_google_jwks() -> Dict[str, Any]:
    # 简单缓存，避免每次请求都拉 jwks
    now = time.time()
    if _jwks_cache["keys"] and now - _jwks_cache["ts"] < 3600:
        return _jwks_cache["keys"]
    try:
        proxy_url = Proxy("http://127.0.0.1:10808")

        async with httpx.AsyncClient(timeout=10, proxy=proxy_url, trust_env=False) as client:
            r = await client.get(GOOGLE_JWKS_URL)
            r.raise_for_status()
            jwks_data = r.json()
        _jwks_cache["keys"] = jwks_data
        _jwks_cache["ts"] = now
        return jwks_data

    except Exception as e:
        error_type = type(e).__name__
        error_detail = str(e) if str(e) else "无具体描述（大概率是网络/代理配置问题）"
        error_msg = f"{error_type}: {error_detail}"

        if _jwks_cache["keys"]:
            # 打印警告日志，不抛异常，继续使用旧缓存
            print(f"警告：获取 Google JWKS 失败（{error_msg}），临时复用过期缓存")
            return _jwks_cache["keys"]
        else:
            # 无旧缓存，抛异常并明确提示，方便小白排查问题
            raise Exception(f"获取 Google JWKS 失败且无缓存可用：{error_msg}") from e

def _get_bearer_token(authorization: Optional[str]) -> str:
  if not authorization:
    raise HTTPException(status_code=401, detail="Missing Authorization header")
  parts = authorization.split(" ")
  if len(parts) != 2 or parts[0].lower() != "bearer":
    raise HTTPException(status_code=401, detail="Invalid Authorization header")
  return parts[1]

async def verify_firebase_id_token(id_token: str) -> Dict[str, Any]:
    if not FIREBASE_PROJECT_ID:
        raise HTTPException(status_code=500, detail="FIREBASE_PROJECT_ID not set")

  # 读取 header 里的 kid，用来匹配公钥
    try:
        header = jwt.get_unverified_header(id_token)
        kid = header.get("kid")
        if not kid:
            raise ValueError("Missing kid")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token header")

    print("get_google_jwks!")
    jwks = await get_google_jwks()
    keys = jwks.get("keys", {}) if isinstance(jwks, dict) else jwks
    # 注意：这个 endpoint 返回的是 kid -> cert 的 dict（不是标准 jwks list）
    cert = keys.get(kid)
    if not cert:
        raise HTTPException(status_code=401, detail="Unknown token kid")
    print("get cert!")
    issuer = f"https://securetoken.google.com/{FIREBASE_PROJECT_ID}"

    try:
        payload = jwt.decode(
        id_token,
        cert,
        algorithms=["RS256"],
        audience=FIREBASE_PROJECT_ID,
        issuer=issuer,
        options={"verify_at_hash": False},
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Token verification failed")

    return payload

async def ensure_users_table():
  # sqlite / postgres 通用的最简 DDL（postgres 你后面建议用迁移工具，这里先跑起来）
  async with engine.begin() as conn:
    if DATABASE_URL.startswith("sqlite"):
      await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
          uid TEXT PRIMARY KEY,
          email TEXT,
          created_at TEXT DEFAULT (datetime('now')),
          last_login_at TEXT DEFAULT (datetime('now'))
        );
      """))
    else:
      await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
          uid TEXT PRIMARY KEY,
          email TEXT,
          created_at TIMESTAMPTZ DEFAULT NOW(),
          last_login_at TIMESTAMPTZ DEFAULT NOW()
        );
      """))

@app.get("/me")
async def me(authorization: Optional[str] = Header(default=None)):
    token = _get_bearer_token(authorization)
    print("get token!")
    payload = await verify_firebase_id_token(token)
    print("get payload!")

    uid = payload.get("user_id") or payload.get("sub")
    email = payload.get("email")

    print("get uid!")
  
    if not uid:
        raise HTTPException(status_code=401, detail="Missing uid in token")

    print("Authorization header:", authorization[:40], "...")

  # upsert user
    async with SessionLocal() as session:
        if DATABASE_URL.startswith("sqlite"):
            await session.execute(
                text("""
                INSERT INTO users(uid, email, created_at, last_login_at)
                VALUES (:uid, :email, datetime('now'), datetime('now'))
                ON CONFLICT(uid) DO UPDATE SET
                    email=excluded.email,
                    last_login_at=datetime('now');
                """),
                {"uid": uid, "email": email},
            )
        else:
            await session.execute(
                text("""
                INSERT INTO users(uid, email, created_at, last_login_at)
                VALUES (:uid, :email, NOW(), NOW())
                ON CONFLICT (uid) DO UPDATE SET
                    email=EXCLUDED.email,
                    last_login_at=NOW();
                """),
                {"uid": uid, "email": email},
            )
        await session.commit()

    return {"uid": uid, "email": email}

@app.get("/ping")
async def ping():
    return {"ok": True}