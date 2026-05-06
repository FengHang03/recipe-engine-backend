"""
app/db/io.py

通用数据库 I/O 工具函数，与业务逻辑完全无关。

提供：
  - read_sql_df
  - execute_sql
  - execute_many
  - scalar_query
  - write_df_to_table
"""

from __future__ import annotations

from typing import Any, List, Mapping, Optional, Sequence, Union

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def read_sql_df(
    engine: Engine,
    query: str,
    params: Optional[Mapping[str, Any]] = None,
    index_col: Optional[Union[str, List[str]]] = None,
) -> pd.DataFrame:
    """
    执行 SELECT 查询并将结果封装为 DataFrame。
    """
    with engine.connect() as conn:
        return pd.read_sql(
            sql=text(query),
            con=conn,
            params=params or {},
            index_col=index_col,
        )


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def execute_sql(
    engine: Engine,
    statement: str,
    params: Optional[Mapping[str, Any]] = None,
) -> None:
    """
    执行单条 DML / DDL 语句（INSERT / UPDATE / DELETE / CREATE …）。
    """
    with engine.begin() as conn:
        conn.execute(text(statement), params or {})


def execute_many(
    engine: Engine,
    statement: str,
    params_seq: Sequence[Mapping[str, Any]],
) -> None:
    """
    批量执行同一条语句（适用于批量 INSERT / UPDATE）。
    """
    if not params_seq:
        return

    with engine.begin() as conn:
        conn.execute(text(statement), list(params_seq))


def write_df_to_table(
    engine: Engine,
    df: pd.DataFrame,
    table_name: str,
    *,
    schema: Optional[str] = None,
    if_exists: str = "append",
    index: bool = False,
    chunksize: Optional[int] = 1000,
    method: str = "multi",
) -> None:
    """
    将 DataFrame 写入数据库表。

    Args:
        engine: SQLAlchemy Engine
        df: 要写入的 DataFrame
        table_name: 目标表名
        schema: 可选 schema
        if_exists: {'fail', 'replace', 'append'}
        index: 是否写入 DataFrame index
        chunksize: 分块写入大小
        method: pandas.to_sql 的 method 参数，默认 multi
    """
    if df.empty:
        return

    df.to_sql(
        name=table_name,
        con=engine,
        schema=schema,
        if_exists=if_exists,
        index=index,
        chunksize=chunksize,
        method=method,
    )


# ---------------------------------------------------------------------------
# Scalar query
# ---------------------------------------------------------------------------

def scalar_query(
    engine: Engine,
    query: str,
    params: Optional[Mapping[str, Any]] = None,
) -> Any:
    """
    执行查询并返回第一行第一列的单个值（标量）。
    """
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        return result.scalar()

        