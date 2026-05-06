"""
app/scripts/dataset_import_pipeline.py

用途：
1. 调用 dateset_preparing.py 中的 DataFrame 生成函数
2. 将生成后的 DataFrame 写入 PostgreSQL / Cloud SQL
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from app.db.connection import create_db_engine, dispose_engine, test_connection
from app.db.io import write_df_to_table

# 这里按你项目真实路径改
from app.database.dateset_preparing import (
    table_nutrients_generation,
    table_ingredients_generation,
    table_ingredient_nutrients_generation,
)

logger = logging.getLogger(__name__)


def build_all_tables(
    *,
    nutrient_def_csv: str,
    food_csv: str,
    food_nutrient_csv: str,
    staging_dir: str = "./data/staging",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    构建三张核心表对应的 DataFrame。
    """
    staging_path = Path(staging_dir)
    staging_path.mkdir(parents=True, exist_ok=True)

    nutrients_out = staging_path / "nutrients_out.csv"
    ingredients_out = staging_path / "ingredients_out.csv"
    ingredient_nutrients_out = staging_path / "ingredient_nutrients_out.csv"

    logger.info("Building nutrients dataframe...")
    nutrients_df = table_nutrients_generation(
        input_file_path=nutrient_def_csv,
        output_file_path=str(nutrients_out),
    )

    logger.info("Building ingredients dataframe...")
    ingredients_df = table_ingredients_generation(
        input_file_path=food_csv,
        output_file_path=str(ingredients_out),
        merge_strategy="replace",
    )

    logger.info("Building ingredient_nutrients dataframe...")
    ingredient_nutrients_df = table_ingredient_nutrients_generation(
        input_food_path=str(ingredients_out),
        input_nut_path=food_nutrient_csv,
        output_file_path=str(ingredient_nutrients_out),
    )

    return nutrients_df, ingredients_df, ingredient_nutrients_df


def import_all_tables(
    *,
    nutrient_def_csv: str,
    food_csv: str,
    food_nutrient_csv: str,
    staging_dir: str = "./data/staging",
    connection_string: Optional[str] = None,
    schema: Optional[str] = None,
    if_exists: str = "append",
) -> None:
    """
    生成并导入三张表：
      - nutrients
      - ingredients
      - ingredient_nutrients
    """
    engine = create_db_engine(connection_string=connection_string)

    try:
        if not test_connection(engine):
            raise RuntimeError("Database connection test failed.")

        nutrients_df, ingredients_df, ingredient_nutrients_df = build_all_tables(
            nutrient_def_csv=nutrient_def_csv,
            food_csv=food_csv,
            food_nutrient_csv=food_nutrient_csv,
            staging_dir=staging_dir,
        )

        logger.info("Writing nutrients table...")
        write_df_to_table(
            engine,
            nutrients_df,
            table_name="nutrients",
            schema=schema,
            if_exists=if_exists,
        )

        logger.info("Writing ingredients table...")
        write_df_to_table(
            engine,
            ingredients_df,
            table_name="ingredients",
            schema=schema,
            if_exists=if_exists,
        )

        logger.info("Writing ingredient_nutrients table...")
        write_df_to_table(
            engine,
            ingredient_nutrients_df,
            table_name="ingredient_nutrients",
            schema=schema,
            if_exists=if_exists,
        )

        logger.info("All tables imported successfully.")

    finally:
        dispose_engine(engine)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    import_all_tables(
        nutrient_def_csv="./data/nutrient.csv",
        food_csv="./data/food.csv",
        food_nutrient_csv="./data/food_nutrient.csv",
        staging_dir="./data/staging",
        if_exists="append",
    )
    