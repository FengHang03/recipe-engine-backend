"""
数据导入模块 - 从 Google Cloud SQL 导入数据到 pandas DataFrame
用于 L1 和 L2 算法
"""

import ast
from unittest import result
import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine
from typing import Dict, List, Tuple, Any, Optional
import os
from functools import lru_cache
import sys
from pathlib import Path

current_file = Path(__file__).resolve()
BACKEND_DIR = current_file.parent.parent.parent.parent
sys.path.append(str(BACKEND_DIR))

print("✅ 项目根目录：", BACKEND_DIR)
print("✅ 项目根下是否有backend目录：", (BACKEND_DIR / "backend").exists())
print("✅ sys.path前3项：", sys.path[:3])
print("✅ backend目录下是否有__init__.py：", (BACKEND_DIR / "backend" / "__init__.py").exists())

from backend.service.DataProcessor.dataset_preparing_refactored import ThresholdValue
from backend.service.common.enums import FoodGroup, FoodSubgroup, LifeStage, NutrientID
from backend.service.common.models import Ingredient
from backend.service.common.utils import UnitConverter
from backend.service.L2Generator.l2_aafco_config import AAFCO_STANDARDS

class IngredientDataLoader:
    """食材数据加载器"""
    
    def __init__(self, connection_string: str = None):
        """
        初始化数据库连接
        
        Args:
            connection_string: 数据库连接字符串
                格式: postgresql+pg8000://user:password@tuanty_recipe?unix_sock=/cloudsql/project-36d4843f-b026-466b-bd4:us-central1:tuantyrecipe25/.s.PGSQL.5432
                或从环境变量读取: DATABASE_URL
        """
        if connection_string is None:
            connection_string = os.getenv('DATABASE_URL')

        if not connection_string:
            raise ValueError(
                "未找到数据库连接字符串。请检查是否传入了参数，"
                "或正确设置了环境变量 'DATABASE_URL'。"
            )   

        self.engine = create_engine(connection_string)
        
        # 缓存的DataFrame
        self._ingredients_df: pd.DataFrame | None = None
        self._nutrients_df: pd.DataFrame | None = None
        self._nutrition_values_df: pd.DataFrame | None = None
    
    # ========== L1 数据加载 ==========
    
    @lru_cache(maxsize=1)
    def load_ingredients_for_l1(self) -> pd.DataFrame:
        """
        加载食材信息（用于L1筛选）
        
        Returns:
            DataFrame with columns:
            - ingredient_id (str/UUID)
            - description (str)
            - short_name (str)
            - ingredient_group (str)
            - food_subgroup (str)
            - tags (List[str]) - 所有标签的列表
            - diversity_cluster (str)
            - is_active (bool)
        """
        if self._ingredients_df is not None:
            return self._ingredients_df
        
        query = """
        WITH "ingredient_tags_agg" AS (
            SELECT 
                "ingredient_tags"."ingredient_id",
                array_agg("ingredient_tags"."tag") AS "tags"
            FROM "ingredient_tags"
            GROUP BY "ingredient_tags"."ingredient_id"
        )
        SELECT 
            "i"."id"::text AS "ingredient_id",
            "i"."description",
            "i"."short_name",
            "i"."ingredient_group",
            "i"."food_subgroup" AS "food_subgroup",
            COALESCE("it"."tags", ARRAY[]::text[]) AS "tags",
            -- The original query had 'i.diversity_cluster' here, but 'diversity_cluster' is in 'recipe_items', not 'ingredients'.
            -- Removing it as it's not available from the 'ingredients' table or the CTE.
            "i"."max_g_per_kg_bw",
            "i"."max_pct_kcal",
            "i"."is_active"
        FROM "ingredients" AS "i"
        LEFT JOIN "ingredient_tags_agg" AS "it" ON "i"."id" = "it"."ingredient_id"
        WHERE "i"."is_active" = TRUE
        AND "i"."source" = 'built_in'
        ORDER BY "i"."ingredient_group", "i"."food_subgroup", "i"."description";
        """
        
        df = pd.read_sql(query, self.engine)
        
        # 确保 tags 是 list 类型（PostgreSQL array 转 Python list）
        if 'tags' in df.columns:
            df['tags'] = df['tags'].apply(lambda x: x if isinstance(x, list) else [])
        
        # df=df.rename(columns={'ingredient_group': 'food_group'})
        self._ingredients_df = df
        return df
    
    def filter_ingredients_by_slot(
        self, 
        df: pd.DataFrame,
        allowed_groups: List[str] = None,
        allowed_subgroups: List[str] = None,
        required_tags: List[str] = None,
        excluded_tags: List[str] = None
    ) -> pd.DataFrame:
        """
        根据槽位条件筛选食材
        
        Args:
            df: 食材 DataFrame
            allowed_groups: 允许的 ingredient_group 列表
            allowed_subgroups: 允许的 food_subgroup 列表
            required_tags: 必须包含的标签（AND）
            excluded_tags: 必须排除的标签（NOT）
        
        Returns:
            筛选后的 DataFrame
        """
        result = df.copy()
        
        # 筛选 ingredient_group
        if allowed_groups:
            result = result[result['ingredient_group'].isin(allowed_groups)]
        
        # 筛选 food_subgroup
        if allowed_subgroups:
            result = result[result['food_subgroup'].isin(allowed_subgroups)]
        
        # 必须包含的标签
        if required_tags:
            def has_all_tags(tags_list):
                return all(tag in tags_list for tag in required_tags)
            result = result[result['tags'].apply(has_all_tags)]
        
        # 必须排除的标签
        if excluded_tags:
            def has_no_excluded_tags(tags_list):
                return not any(tag in tags_list for tag in excluded_tags)
            result = result[result['tags'].apply(has_no_excluded_tags)]
        
        return result
    
    # ========== L2 数据加载 ==========
    
    @lru_cache(maxsize=1)
    def load_nutrients_metadata(self) -> pd.DataFrame:
        """
        加载营养素元数据（用于L2优化）
        
        Returns:
            DataFrame with columns:
            - nutrient_id (int)
            - name (str)
            - unit_name (str)
            - is_key (bool)
            - group_name (str)
        """
        if self._nutrients_df is not None:
            return self._nutrients_df
        
        query = """
        SELECT 
            nutrient_id,
            name,
            unit_name,
            is_key,
            group_name
        FROM nutrients
        ORDER BY 
            CASE group_name
                WHEN 'protein_amino' THEN 1
                WHEN 'fat_fatty_acid' THEN 2
                WHEN 'minerals' THEN 3
                WHEN 'vitamins_other' THEN 4
            END,
            display_order NULLS LAST,
            name
        """
        
        df = pd.read_sql(query, self.engine)
        self._nutrients_df = df
        return df
    
    @lru_cache(maxsize=1)
    def load_nutrition_values(self) -> pd.DataFrame:
        """
        加载食材营养成分数据（长表格式，用于L2优化）
        
        Returns:
            DataFrame with columns:
            - ingredient_id (str/UUID)
            - nutrient_id (int)
            - amount_per_100g (float)
            - data_source (str)
        """
        if self._nutrition_values_df is not None:
            return self._nutrition_values_df
        
        query = """
        SELECT 
            ingredient_id::text as ingredient_id,
            nutrient_id,
            amount_per_100g,
            data_source
        FROM ingredient_nutrients
        ORDER BY ingredient_id, nutrient_id
        """
        # WHERE amount_per_100g > 0  -- 排除0值

        
        df = pd.read_sql(query, self.engine)
        self._nutrition_values_df = df
        return df
    
    def get_nutrition_matrix_for_l2(
        self, 
        ingredient_ids: List[str]
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        为L2优化生成营养矩阵
        
        Args:
            ingredient_ids: 要包含的食材ID列表
        
        Returns:
            (wide_matrix, nutrients_info)
            
            wide_matrix: 宽表格式
                index: ingredient_id
                columns: nutrient_id
                values: amount_per_100g
            
            nutrients_info: 营养素信息
                columns: nutrient_id, name, unit_name, is_key
        """
        # 加载数据
        nutrition_df = self.load_nutrition_values()
        nutrients_meta = self.load_nutrients_metadata()
        
        # 筛选指定的食材
        nutrition_df = nutrition_df[
            nutrition_df['ingredient_id'].isin(ingredient_ids)
        ]


        
        # 转为宽表（pivot）
        wide_matrix = nutrition_df.pivot(
            index='ingredient_id',
            columns='nutrient_id',
            values='amount_per_100g'
        ).fillna(0)  # 缺失值填0
        
        # 确保所有食材都在矩阵中（即使没有营养数据）
        for ing_id in ingredient_ids:
            if ing_id not in wide_matrix.index:
                # 添加全0行
                wide_matrix.loc[ing_id] = 0
        
        return wide_matrix, nutrients_meta
    
    # ========== 辅助方法 ==========
    def get_nutrition_unit_factor(self, nutrient_info: pd.DataFrame, life_stage: LifeStage = LifeStage.DOG_ADULT) -> Dict[int, float]:
        
        factors_map = {}

        standards = AAFCO_STANDARDS.get(life_stage, {})
        if not standards:
            print(f"Warning: No standards found for life stage {life_stage}")
            return factors_map

        for row in nutrient_info.reset_index().itertuples(index=False):
            # 通过元组属性取值（属性名=列名，小写/无特殊字符）
            if hasattr(row, 'nutrient_id'):
                nut_id = row.nutrient_id
            elif hasattr(row, 'index'): 
                nut_id = row.index
            else:
                # 这种情况极少发生，除非列名完全不对
                continue

            nut_unit = row.unit_name

            if nut_id not in standards:
                factors_map[nut_id] = 1.0 # 无标准，不转换
                continue

            # B. 获取目标单位 (AAFCO Unit)
            std_config = standards.get(nut_id)
            if not std_config:
                factors_map[nut_id] = 1.0 # 无标准，保持原样
                continue
            
            target_unit_str = std_config.get("unit") 
            if not target_unit_str:
                factors_map[nut_id] = 1.0
                continue

            try:
                mag_factor = UnitConverter.get_unit_factor(
                    nutrient_id=nut_id, 
                    nutrient_unit=nut_unit, 
                    threshold_unit=target_unit_str
                )

                factors_map[nut_id] = mag_factor

            except Exception as e:
                print(f"Error converting nutrient {nut_id}: {e}")

        return factors_map
    
    def get_ingredient_details(self, ingredient_ids: List[str]) -> pd.DataFrame:
        """
        获取指定食材的详细信息
        
        Args:
            ingredient_ids: 食材ID列表
        
        Returns:
            DataFrame with detailed ingredient information
        """
        ingredients_df = self.load_ingredients_for_l1()
        return ingredients_df[
            ingredients_df['ingredient_id'].isin(ingredient_ids)
        ]
    
    def search_ingredients(
        self, 
        keyword: str,
        limit: int = 20
    ) -> pd.DataFrame:
        """
        按关键词搜索食材
        
        Args:
            keyword: 搜索关键词
            limit: 返回结果数量
        
        Returns:
            匹配的食材 DataFrame
        """
        ingredients_df = self.load_ingredients_for_l1()
        
        # 在 description 或 short_name 中搜索
        mask = (
            ingredients_df['description'].str.contains(keyword, case=False, na=False) |
            ingredients_df['short_name'].str.contains(keyword, case=False, na=False)
        )
        
        return ingredients_df[mask].head(limit)
    
    def get_ingredients_by_tags(
        self,
        tags: List[str],
        match_all: bool = True
    ) -> pd.DataFrame:
        """
        按标签查找食材
        
        Args:
            tags: 标签列表
            match_all: True=必须包含所有标签, False=包含任一标签即可
        
        Returns:
            匹配的食材 DataFrame
        """
        ingredients_df = self.load_ingredients_for_l1()
        
        if match_all:
            # AND 逻辑
            mask = ingredients_df['tags'].apply(
                lambda x: all(tag in x for tag in tags)
            )
        else:
            # OR 逻辑
            mask = ingredients_df['tags'].apply(
                lambda x: any(tag in x for tag in tags)
            )
        
        return ingredients_df[mask]

    def normalize_nutrition_matrix(
        self, 
        matrix: pd.DataFrame, 
        info_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        将营养矩阵中的数值转换为标准单位 (Standard Units)
        
        Args:
            matrix: 原始宽表 (values 可能混杂 mg, ug, IU)
            info_df: 营养素元数据 (包含 unit_name)
        """
        normalized_matrix = matrix.copy()

        # 1. 获取热量列 (NutrientID.ENERGY = 1008)
        # 计算密度(per 1000kcal)必须依赖热量数据
        ENERGY_ID = NutrientID.ENERGY
        if ENERGY_ID not in matrix.columns:
            print("Warning: Energy column (1008) missing. Cannot calculate nutrient density.")
            return matrix

        energy_series = matrix[ENERGY_ID]

        # 2. 获取当前阶段的标准配置
        standards = AAFCO_STANDARDS[LifeStage.DOG_ADULT]

        # 3. 遍历矩阵中的每一个营养素列
        for nutrient_id in normalized_matrix.columns:
            # 跳过能量列 (1008)
            # if nutrient_id == ENERGY_ID:
            #     continue

            # A. 获取来源单位 (Database Unit)
            # e.g., 'mg' (假设数据库里都是基于重量 /100g 的)
            if nutrient_id not in info_df.index:
                continue
            source_unit = info_df.loc[nutrient_id, 'unit_name'] 

            # B. 获取目标单位 (AAFCO Unit)
            std_config = standards.get(nutrient_id)
            if not std_config:
                continue
            
            raw_target_unit = std_config.get("unit") # e.g., "g" OR "IU"
            if not raw_target_unit:
                continue
            print(f'raw_target_unit: {raw_target_unit}')

            # C. 计算转换系数 (核心)
            if '/' in raw_target_unit:
                # 如果配置里显式写了 (e.g., "g/100g"), 尊重配置
                final_target_unit_str = raw_target_unit
            else:
                # 否则，默认为 "Per 1000kcal"
                # 结果变成: "g/1000kcal", "IU/1000kcal", "mg/1000kcal"
                final_target_unit_str = f"{raw_target_unit}/1000kcal"

            try:
                # c1. 数量级系数 (Magnitude Factor): mg -> g
                mag_factor = UnitConverter.get_unit_factor(
                    nutrient_id=nutrient_id,
                    nutrient_unit=source_unit,     # 源: mg
                    threshold_unit=raw_target_unit # 目标: g/1000kcal -> 解析出 g
                )
                print(f"mag_factor: {mag_factor}")
                
                # c2. 基准系数 (Base Factor): /100g -> /1000kcal
                # 这会返回一个 Series，因为每个食材的热量不同，系数也不同
                base_factor_series = UnitConverter.get_base_factor(
                    energy_series=energy_series,
                    threshold_unit=final_target_unit_str # 目标: g/1000kcal -> 解析出 1000kcal
                )
                print(f"base_factor_series: {base_factor_series}")
                
                # c3. 应用转换
                # 新值 = 旧值 * 数量级系数 * 密度系数
                # pandas 支持 列 * 标量 * Series (自动对齐 index)
                normalized_matrix[nutrient_id] = normalized_matrix[nutrient_id] * mag_factor * base_factor_series
                
                # Debug 日志 (可选)
                # print(f"Convert {nutrient_id}: {source_unit} -> {target_unit_str} | Mag: {mag_factor}")

            except Exception as e:
                print(f"Error converting nutrient {nutrient_id}: {e}")

        return normalized_matrix

    def get_supplement_toolkit(self) -> pd.DataFrame:
        """
        获取supplement toolkit List

        Args:

        Returns:
            合适的补剂 DataFrame
        """
        df = self.load_ingredients_for_l1()

        is_supplement = df['ingredient_group'] == FoodGroup.SUPPLEMENT
        excluded_subgroups = [
        FoodSubgroup.FIBER_SUPPLEMENT,
        FoodSubgroup.SUPPLEMENT_CALCIUM,  # 建议保留：L2 需要钙粉来平衡骨头
        FoodSubgroup.SUPPLEMENT_IODINE    # 建议保留：L2 需要碘源
        ]

        result = []

        is_not_excluded = ~df['food_subgroup'].isin(excluded_subgroups)
        
        toolkit_df = df[is_supplement & is_not_excluded].copy()

        toolkit_list = []

        for _, row in toolkit_df.iterrows():
        # 这里假设你有一个 helper 方法把 series 转为 Ingredient 对象
        # 如果没有，你需要在这里手动实例化，例如:
        # ing = Ingredient(id=row['id'], name=row['name'], ...)
            ing = self._convert_row_to_ingredient(row) 
            toolkit_list.append(ing)

        return toolkit_list

    def _convert_row_to_ingredient(self, row: pd.Series) -> Ingredient:
        """
        将 DataFrame 的一行转换为 Ingredient 对象
        处理类型转换、NaN 值和列表解析
        """
        # --- 内部辅助函数：解析列表字段 ---
        def parse_list_field(val: Any) -> List[str]:
            """安全地解析字符串列表，如 "['beef', 'red_meat']" 或 "beef, red_meat" """
            if pd.isna(val) or val == "":
                return []
            
            if isinstance(val, list):
                return val  # 已经是列表了（比如从 Parquet 读取）
                
            if isinstance(val, str):
                val = val.strip()
                # 尝试解析 Python 风格的列表字符串 "['tag1', 'tag2']"
                if val.startswith('[') and val.endswith(']'):
                    try:
                        parsed = ast.literal_eval(val)
                        if isinstance(parsed, list):
                            return [str(x) for x in parsed]
                    except (ValueError, SyntaxError):
                        pass # 解析失败，回退到逗号分隔
                
                # 回退：尝试逗号分隔 "tag1, tag2"
                return [x.strip() for x in val.split(',') if x.strip()]
                
            return []

        def parse_opt_float(val: Any) -> Optional[float]:
            """处理 NaN 转 None"""
            if pd.isna(val) or val == "":
                return None
            try:
                return float(val)
            except (ValueError, TypeError):
                return None

        # --- 内部辅助函数：解析 Optional String ---
        def parse_opt_str(val: Any) -> Optional[str]:
            """处理 NaN 转 None"""
            if pd.isna(val) or val == "":
                return None
            return str(val).strip()

        # --- 构造对象 ---
        return Ingredient(
            # 1. 基础字段 (强制转字符串，处理 NaN 为空串)
            ingredient_id=str(row.get('ingredient_id', '')).strip(),
            description=str(row.get('description', '')).strip(),
            short_name=str(row.get('short_name', '')).strip(),
            ingredient_group=str(row.get('ingredient_group', '')).strip(),
            food_subgroup=str(row.get('food_subgroup', '')).strip(),
            
            # 2. 列表字段 (解析 JSON 串或逗号分隔串)
            tags=parse_list_field(row.get('tags')),
            diversity_tags=parse_list_field(row.get('diversity_tags')),
            
            # 3. 可选字符串字段
            diversity_cluster=parse_opt_str(row.get('diversity_cluster')),
            
            # 4. 可选数值字段 (处理 NaN -> None)
            max_g_per_kg_bw=parse_opt_float(row.get('max_g_per_kg_bw')),
            max_pct_kcal=parse_opt_float(row.get('max_pct_kcal'))
        )
    
    def close(self):
        """关闭数据库连接"""
        self.engine.dispose()


# ========== 使用示例 ==========
if __name__ == "__main__":
    # 初始化加载器
    loader = IngredientDataLoader("postgresql://postgres:Tuantuan_123@127.0.0.1:15432/tuanty_recipe")
    
    # === L1 使用示例 ===
    print("=== L1: 加载食材数据 ===")
    ingredients = loader.load_ingredients_for_l1()
    print(f"总食材数: {len(ingredients)}")
    print(f"\n前5个食材:")
    print(ingredients.head())
    
    # 按槽位筛选
    print("\n=== L1: 筛选内脏食材 ===")
    organs = loader.filter_ingredients_by_slot(
        ingredients,
        allowed_groups=["ORGAN"],
        allowed_subgroups=["organ_liver", "organ_kidney", "organ_heart"]
    )
    print(f"符合条件的内脏: {len(organs)}")
    print(organs[['description', 'food_subgroup', 'tags']].head())
    
    # 按标签查找
    print("\n=== L1: 查找钙源 ===")
    calcium_sources = loader.get_ingredients_by_tags(
        tags=["role_calcium_source"],
        match_all=True
    )
    print(f"钙源数量: {len(calcium_sources)}")
    print(calcium_sources[['description', 'ingredient_group', 'food_subgroup']].head())
    
    # === L2 使用示例 ===
    print("\n=== L2: 加载营养数据 ===")
    
    # 假设 L1 选出了这些食材
    selected_ids = organs['ingredient_id'].head(3).tolist()
    
    # 获取营养矩阵
    nutrition_matrix, nutrients_info = loader.get_nutrition_matrix_for_l2(selected_ids)

    nutrition_matrix.to_csv("nutrition_matrix.csv")
    nutrients_info.to_csv("nutrients_info.csv")

    nut_conv_factors = loader.get_nutrition_unit_factor(nutrient_info=nutrients_info)
    for row in nutrients_info.itertuples(index=False):
        current_nutrient_id = row.nutrient_id
        current_unit_name = row.unit_name
        nut_conv_factor = nut_conv_factors.get(current_nutrient_id)
    
        # 业务处理
        # print(f"营养素ID: {current_nutrient_id} → 单位名称: {current_unit_name} : 转换系数 {nut_conv_factor}")
    
    print(f"\n营养矩阵形状: {nutrition_matrix.shape}")
    print(f"  - 食材数: {nutrition_matrix.shape[0]}")
    print(f"  - 营养素数: {nutrition_matrix.shape[1]}")
    
    print(f"\n营养素元数据:")
    print(nutrients_info.head(10))
    
    print(f"\n营养矩阵示例 (前5个营养素):")
    print(nutrition_matrix.iloc[:, :5])
    
    # 关闭连接
    loader.close()