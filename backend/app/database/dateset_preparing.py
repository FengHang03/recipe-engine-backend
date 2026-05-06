from __future__ import annotations

import logging

from app.database.db_config import get_database_engine
from app.database.ingredients.tagging_config import AutoTagConfig
from app.database.ingredients.transformers import (
    build_ingredients_table,
    build_nutrients_table,
    build_ingredient_nutrients_table,
)
from app.db.io import write_df_to_table


logger = logging.getLogger(__name__)


def run_dataset_prepare_pipeline(
    food_csv_path: str,
    nutrient_data_csv_path: str,
    nutrient_def_csv_path: str,
) -> None:
    config = AutoTagConfig()
    engine = get_database_engine()

    logger.info("Building nutrients table...")
    nutrients_df = build_nutrients_table(nutrient_def_csv_path)

    logger.info("Building ingredients table...")
    ingredients_df = build_ingredients_table(food_csv_path)

    logger.info("Building ingredient tags table...")
    ingredient_tags_df = build_ingredient_nutrients_table(
        path_food_new=food_csv_path,
        path_nutrient_data=nutrient_data_csv_path,
        path_nutrient_def=nutrient_def_csv_path,
        config=config,
    )

    logger.info("Writing tables to database...")
    write_df_to_table(nutrients_df, "nutrients", engine)
    write_df_to_table(ingredients_df, "ingredients", engine)
    write_df_to_table(ingredient_tags_df, "ingredient_tags", engine)

    logger.info("Dataset pipeline completed successfully.")