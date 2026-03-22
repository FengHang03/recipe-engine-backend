# import pandas as pd
# import sys
# import os
# from pathlib import Path
# from typing import Dict, Union

# current_file = Path(__file__).resolve()
# BACKEND_DIR = current_file.parent.parent.parent.parent
# sys.path.append(str(BACKEND_DIR))
# print(f"BACKEND_DIR:{BACKEND_DIR}")

# from app.common.enums import LifeStage, NutrientID
# from app.L2Generator.l2_aafco_config import AAFCO_STANDARDS

# nutrition_matrix = pd.read_csv('clean_matrix.csv').set_index('ingredient_id')
# ingredient_ids = nutrition_matrix.index.to_list()
# nutrition_cols = nutrition_matrix.columns

# filtered_df = nutrition_matrix.copy().fillna(0)

# nutrient_sum: Dict[int, float]

# nutrient_cols = [col for col in filtered_df.columns if col != 'ingredient_id']

# standards_value_dict: Dict[int, Dict[str, Union[float, int]]] = {}

# standards_value_dict[1003] = 1
# filtered_df['weight'] = 0.0

# for ing_id in ingredient_ids:
#     # print(f"filtered_df.loc[ing_id]: {filtered_df.loc[ing_id]}")
#     filtered_df.loc[ing_id, 'weight'] = 1.5
#     filtered_df.loc[ing_id] = filtered_df.loc[ing_id] * 1.5

# result1 = filtered_df[nutrient_cols].sum(axis=0)
# print(f'type od result1: {type(result1)}')
# print(f'result1: {result1}')
# nutrient_sum = filtered_df.sum(axis=1).to_dict()

# standards = AAFCO_STANDARDS.get(LifeStage.DOG_ADULT)
# standards_value_dict = dict()

# for nut_id in NutrientID:
#     if nut_id in standards:
#         constraint_value = standards.get(nut_id)
#         print(f"constraint_max={constraint_value['max']}, constraint_min：{constraint_value.get('min')}")
#         standards_value_dict['min'] = constraint_value.get('min')
