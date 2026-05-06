"""
app/db/connection.py

负责：
  - 读取 DATABASE_URL 环境变量
  - 创建 / 关闭 SQLAlchemy engine
  - 提供 connection context manager
  - 提供 session context manager（可选，按需启用）
  - 提供轻量的数据库连通性测试
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import Connection, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


# ---------------------------------------------------------------------------
# Get Database URL
# ---------------------------------------------------------------------------

def get_database_url(explicit_url: Optional[str] = None) -> str:
    """
    Resolve the database URL in a predictable order:
    1. explicit_url
    2. environment variable DATABASE_URL

    Raises:
        ValueError: if no database URL is available.
    """
    db_url = explicit_url or os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError(
            "Database URL not found. Pass connection_string explicitly "
            "or set the DATABASE_URL environment variable."
        )
    return db_url


# ---------------------------------------------------------------------------
# Engine factory
# ---------------------------------------------------------------------------

def create_db_engine(
    connection_string: Optional[str] = None,
    *,
    echo: bool = False,
    pool_pre_ping: bool = True,
    pool_size: int = 5,
    max_overflow: int = 10,
) -> Engine:
    """
    Create a SQLAlchemy engine.

    Args:
        connection_string: Explicit database URL. If omitted, DATABASE_URL is used.
        echo: Whether to enable SQLAlchemy SQL echo logging.
        pool_pre_ping: Whether to validate connections before use.
        pool_size: SQLAlchemy connection pool size.
        max_overflow: Additional overflow connections beyond pool_size.

    Returns:
        SQLAlchemy Engine
    """
    db_url = get_database_url(connection_string)
    return create_engine(
        db_url,
        echo=echo,
        pool_pre_ping=pool_pre_ping,
        pool_size=pool_size,
        max_overflow=max_overflow,
        future=True,
    )


def dispose_engine(engine: Optional[Engine]) -> None:
    """
    Safely dispose a SQLAlchemy engine.
    """
    if engine is not None:
        engine.dispose()


def test_connection(engine: Engine) -> bool:
    """
    Run a minimal connectivity check.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Context managers
# ---------------------------------------------------------------------------

@contextmanager
def get_connection(engine: Engine) -> Iterator[Connection]:
    """
    提供一个 SQLAlchemy Connection 的上下文管理器。

    用法::

        with get_connection(engine) as conn:
            result = conn.execute(text("SELECT 1"))

    提交 / 回滚由调用方负责，或使用 SQLAlchemy 的 autobegin 机制。
    """
    with engine.connect() as conn:
        yield conn


def make_session_factory(engine: Engine) -> sessionmaker:
    """
    Create a SQLAlchemy session factory bound to the given engine.
    """
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@contextmanager
def get_session(engine: Engine) -> Iterator[Session]:
    """
    提供一个 ORM Session 的上下文管理器。

    用法::

        with get_session(engine) as session:
            obj = session.get(MyModel, pk)

    异常时自动回滚，正常退出时自动提交。
    """
    session_factory = make_session_factory(engine)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        