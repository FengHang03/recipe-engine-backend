from __future__ import annotations

import math
from ast import Dict, List
from typing import Protocol, List, Dict, Any

import pandas as pd

import sys
import os
from pathlib import Path

BACKEND_DIR = "D:/Programs/Pet-Recipe-251204/backend"
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


from app.domains.recipe_generation.infra.data.raw_preset_recipe import PRESET_RECIPES

from app.domains.recipe_generation.contracts.recipe_spec import PresetRecipeSpec


class PresetRecipeDataSource(Protocol):
    def get_preset_recipe(self, preset_recipe_id: str) -> PresetRecipeSpec:
        ...

class PresetRecipeRepository:
    """
    Raw preset recipe repository.

    Responsibility:
    - Load raw preset JSON-like definitions from infra.data
    - Return raw dicts only
    - No ingredient hydration
    - No IngredientRef construction
    - No pet-weight resolution
    """

    def __init__(self) -> None:
        self._recipes: Dict[str, Dict[str, Any]] = {}

        for recipe in PRESET_RECIPES:
            recipe_id = str(recipe.get("recipe_id", "")).strip()
            if not recipe_id:
                raise ValueError("Every preset recipe must define a non-empty recipe_id.")
            if recipe_id in self._recipes:
                raise ValueError(f"Duplicated preset recipe_id detected: {recipe_id}")
            self._recipes[recipe_id] = dict(recipe)


    def get_raw_preset(self, recipe_id: str) -> Dict[str, Any]:
        recipe = self._recipes.get(recipe_id)
        if not recipe:
            raise ValueError(f"Preset recipe not found: {recipe_id}")
        return recipe


    def list_all_recipe_ids(self) -> List[str]:
        """获取所有已存储的食谱ID（辅助方法）"""
        return list(self._recipes.keys())


    def has_recipe(self, recipe_id: str) -> bool:
        return str(recipe_id).strip() in self._recipes


if __name__ == "__main__":

    # ---------------------- 1. initialization dependency ----------------------
    conn_str = 'postgresql://postgres:Tuantuan_123@127.0.0.1:15432/tuanty_recipe'


    # ---------------------- 2. 初始化仓库和食材仓库 ----------------------
    preset_repo = PresetRecipeRepository()  # 初始化预设食谱仓库
    generated_recipes = []  # 存储生成的食谱列表


    # ---------------------- 4. 测试根据recipe_id获取数据 ----------------------
    print("所有已存储的食谱ID：", preset_repo.list_all_recipe_ids())

    # 获取test_001
    try:
        recipe_001 = preset_repo.get_raw_preset("preset_recipe_beef_001")
        # recipe_002 = preset_repo.get_raw_preset("recipe_002")
        # print(f"recipe_001: {recipe_001}")
        # print(f"recipe_002: {recipe_002}")
        print("\n=== 获取test_001食谱 ===")
        print(f"食谱名称：{recipe_001.get('name')}")
        print(f"基础热量：{recipe_001.get('basis_kcal')} kcal")
        print(f"食材数量：{len(recipe_001.get('ingredients'))}")
        # for idx, item in enumerate(recipe_001.get('ingredients')):
            # print(f"  食材{idx+1}：{item.get('ingredients')['short_name']} | 比例：{item.get('base_ratio')} | 固定重量：{item.get('base_weight_g')} g")

    except ValueError as e:
        print(f"获取失败：{e}")
