"""
数据导入模块 - 从 Google Cloud SQL 导入数据到 pandas DataFrame
用于 L1 和 L2 算法
"""

import ast
import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy.engine import Engine

import sys
from pathlib import Path
from dotenv import load_dotenv

current_file = Path(__file__).resolve()
BACKEND_DIR = current_file.parent.parent.parent
# print(BACKEND_DIR)
sys.path.append(str(BACKEND_DIR))

ENV_FILE = BACKEND_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE)

from app.common.enums import LifeStage, NutrientID, FoodGroup, FoodSubgroup
from app.common.models import Ingredient
from app.common.utils import UnitConverter
from app.db.connection import create_db_engine, dispose_engine
from app.db.io import read_sql_df
from app.L2Generator.l2_aafco_config import AAFCO_STANDARDS

logger = logging.getLogger(__name__)

class IngredientDataLoader:
    """
    食材数据加载器。

    数据库层完全委托给 ``app.db.connection`` 和 ``app.db.io``，
    本类只负责 SQL 拼接、DataFrame 变换和业务缓存。

    支持两种使用方式：

    1. **依赖注入**（推荐，便于测试）::

           engine = build_engine()
           loader = IngredientDataLoader(engine=engine)
           df = loader.load_ingredients_for_l1()
           loader.close()

    2. **上下文管理器**（自动管理 engine 生命周期）::

           with IngredientDataLoader() as loader:
               df = loader.load_ingredients_for_l1()

    缓存字段命名规则：``_cache_<逻辑名>``，含义一目了然。
    """
    
    def __init__(
        self,
        engine: Optional[Engine] = None,
        connection_string: Optional[str] = None,
    ) -> None:
        """
        初始化数据库连接
        
        Args:
            engine:            外部传入的 SQLAlchemy Engine（优先使用）。
            connection_string: 数据库连接字符串；若两者均为 None，
                               则自动读取环境变量 ``DATABASE_URL``。
        """
        if engine is not None:
            self._engine = engine
            self._engine_owned = False        # 外部传入，不由本类 dispose
        else:
            self._engine = create_db_engine(connection_string)
            self._engine_owned = True         # 本类自行创建，负责释放

        # --- 业务缓存（明确命名，减少歧义）---
        self._cache_ingredients: Optional[pd.DataFrame] = None      # L1 食材列表
        self._cache_nutrients_meta: Optional[pd.DataFrame] = None   # 营养素元数据
        self._cache_nutrition_values: Optional[pd.DataFrame] = None # 食材营养成分（长表）
    
    # ------------------------------------------------------------------
    # 上下文管理器
    # ------------------------------------------------------------------

    def __enter__(self) -> "IngredientDataLoader":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
        return False  # 不吞异常

    # ------------------------------------------------------------------
    # 缓存管理
    # ------------------------------------------------------------------

    def clear_cache(self) -> None:
        """手动清除所有内存缓存，下次调用时重新查询数据库。"""
        self._cache_ingredients = None
        self._cache_nutrients_meta = None
        self._cache_nutrition_values = None

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------

    def close(self) -> None:
        """释放数据库连接池。仅当 engine 由本类创建时才执行 dispose。"""
        if self._engine_owned:
            dispose_engine(self._engine)

    # ==================================================================
    # L1 数据加载
    # ==================================================================
    
    def load_ingredients_for_l1(self) -> pd.DataFrame:
        """
        加载所有激活的内置食材（用于 L1 筛选）。

        结果会被缓存；多次调用只查一次数据库。

        Returns:
            DataFrame，列：
            ingredient_id, description, short_name,
            food_group, food_subgroup, tags (List[str]),
            max_g_per_kg_bw, max_pct_kcal, is_active
        """
        if self._cache_ingredients is not None:
            return self._cache_ingredients
        
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
            "i"."food_group",
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
        ORDER BY "i"."food_group", "i"."food_subgroup", "i"."description";
        """
        
        df = read_sql_df(self._engine, query)
        
        # PostgreSQL array → Python list 保险处理
        if "tags" in df.columns:
            df["tags"] = df["tags"].apply(
                lambda x: x if isinstance(x, list) else []
            )

        self._cache_ingredients = df
        return df
    
    def filter_ingredients_by_slot(
        self,
        df: pd.DataFrame,
        allowed_groups: Optional[List[str]] = None,
        allowed_subgroups: Optional[List[str]] = None,
        required_tags: Optional[List[str]] = None,
        excluded_tags: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        根据槽位条件对食材 DataFrame 进行筛选。

        Args:
            df:               来源 DataFrame（通常是 load_ingredients_for_l1 的结果）。
            allowed_groups:   food_group 白名单（OR 逻辑）。
            allowed_subgroups: food_subgroup 白名单（OR 逻辑）。
            required_tags:    必须全部命中的标签（AND 逻辑）。
            excluded_tags:    只要命中其中一个就排除（OR 逻辑）。

        Returns:
            筛选后的 DataFrame 副本。
        """
        result = df.copy()
        
        # 筛选 food_group
        if allowed_groups:
            result = result[result['food_group'].isin(allowed_groups)]
        
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

    def get_ingredient_details(self, ingredient_ids: List[str]) -> pd.DataFrame:
        """返回指定 ID 列表对应的食材行（从缓存中过滤）。"""
        return self.load_ingredients_for_l1()[
            self.load_ingredients_for_l1()["ingredient_id"].isin(ingredient_ids)
        ]

    def search_ingredients(self, keyword: str, limit: int = 20) -> pd.DataFrame:
        """
        按关键词在 description / short_name 中搜索食材。

        Args:
            keyword: 搜索关键词（大小写不敏感）。
            limit:   最多返回的行数。
        """
        df = self.load_ingredients_for_l1()
        mask = df["description"].str.contains(keyword, case=False, na=False) | \
               df["short_name"].str.contains(keyword, case=False, na=False)
        return df[mask].head(limit)

    def get_ingredients_by_tags(
        self,
        tags: List[str],
        match_all: bool = True,
    ) -> pd.DataFrame:
        """
        按标签查找食材。

        Args:
            tags:      目标标签列表。
            match_all: True = 必须包含所有标签（AND）；False = 任一即可（OR）。
        """
        df = self.load_ingredients_for_l1()

        if match_all:
            mask = df["tags"].apply(lambda x: all(t in x for t in tags))
        else:
            mask = df["tags"].apply(lambda x: any(t in x for t in tags))

        return df[mask]

    def get_supplement_toolkit(self) -> List[Ingredient]:
        """
        获取可用于 L2 优化的补剂食材列表（排除膳食纤维、钙粉、碘源等）。

        Returns:
            Ingredient 对象列表。
        """
        df = self.load_ingredients_for_l1()

        excluded_subgroups = [
            FoodSubgroup.FIBER_SUPPLEMENT,
            FoodSubgroup.SUPPLEMENT_CALCIUM,
            FoodSubgroup.SUPPLEMENT_IODINE,
        ]

        toolkit_df = df[
            (df["food_group"] == FoodGroup.SUPPLEMENT)
            & (~df["food_subgroup"].isin(excluded_subgroups))
        ].copy()

        return [self._row_to_ingredient(row) for _, row in toolkit_df.iterrows()]
    
    # ==================================================================
    # L2 数据加载
    # ==================================================================
    
    def load_nutrients_metadata(self) -> pd.DataFrame:
        """
        加载营养素元数据（用于L2优化）

        结果会被缓存。

        Returns:
           DataFrame，列：
          nutrient_id, name, unit_name, is_key, group_name
        
        """
        if self._cache_nutrients_meta is not None:
            return self._cache_nutrients_meta
        
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
        
        df = read_sql_df(self._engine, query)
        self._cache_nutrients_meta = df
        return df
    
    def load_nutrition_values(self) -> pd.DataFrame:
        """
        加载食材营养成分数据（长表格式，用于L2优化）
        
        结果会被缓存。

        Returns:
            DataFrame，列：
            ingredient_id, nutrient_id, amount_per_100g, data_source
        """
        if self._cache_nutrition_values is not None:
            return self._cache_nutrition_values
        
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
        df = read_sql_df(self._engine, query)
        self._cache_nutrition_values = df
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
        
            nutrients_meta: load_nutrients_metadata() 的完整结果。
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
    
    # ==================================================================
    # Nutrition 单位转换
    # ==================================================================

    def get_nutrition_unit_factors(
        self,
        nutrient_info: pd.DataFrame,
        life_stage: LifeStage = LifeStage.DOG_ADULT,
    ) -> Dict[int, float]:        
        """
        根据AAFCO营养标准，计算不同营养素的单位转换系数
        Parameters:
        -----------
        根据 AAFCO 标准计算每个营养素的数量级转换系数（magnitude factor）。

        Args:
            nutrient_info: 营养素元数据 DataFrame（需含 nutrient_id / index 和 unit_name）。
            life_stage:    宠物生命阶段，用于查找对应 AAFCO 标准。

        Returns:
            {nutrient_id: factor}；无法转换的营养素默认 factor = 1.0。
        """
        factors: Dict[int, float] = {}

        standards = AAFCO_STANDARDS.get(life_stage, {})
        if not standards:
            logger.warning(f"Warning: No standards found for life stage {life_stage}")
            return factors

        for row in nutrient_info.reset_index().itertuples(index=False):
            # 通过元组属性取值（属性名=列名，小写/无特殊字符）
            nut_id: int = (
                row.nutrient_id if hasattr(row, "nutrient_id") else row.index
            )
            nut_unit: str = row.unit_name

            # B. 获取目标单位 (AAFCO Unit)
            std_config = standards.get(nut_id)
            if not std_config:
                factors[nut_id] = 1.0 # 无标准，保持原样
                continue
            
            target_unit_str: Optional[str] = std_config.get("unit")
            if not target_unit_str:
                factors[nut_id] = 1.0
                continue

            try:
                mag_factor = UnitConverter.get_unit_factor(
                    nutrient_id=nut_id, 
                    nutrient_unit=nut_unit, 
                    threshold_unit=target_unit_str
                )

                factors[nut_id] = mag_factor

            except Exception as e:
                logger.warning(
                    "Error getting unit factor for nutrient %s: %s",
                    nut_id,
                    e,
                )
                factors[nut_id] = 1.0

        return factors
    
    def get_converted_nutrition_matrix(
        self,
        nutrient_matrix: pd.DataFrame,
        factor_map: Dict[int, float],
    ) -> pd.DataFrame:
        """
        将营养矩阵的每列乘以对应的单位转换系数。

        Args:
            nutrient_matrix: 宽表矩阵（index = ingredient_id，columns = nutrient_id）。
            factor_map:      get_nutrition_unit_factors() 返回的系数字典。

        Returns:
            转换后的矩阵（副本，不修改原数据）。
        """
        converted = nutrient_matrix.copy().fillna(0)
        numeric_cols = converted.select_dtypes(include=['int', 'float']).columns.drop(
            "ingredient_id", errors="ignore"
        )
        converted[numeric_cols] = converted[numeric_cols].fillna(0)

        for col in converted.columns:
            if col == 'ingredient_id':
                continue

            nut_id = int(col)
            factor = factor_map.get(nut_id, 1.0)
            if pd.api.types.is_numeric_dtype(converted[col]):
                converted[col] = converted[col] * factor
        
        return converted

    def normalize_nutrition_matrix(
        self, 
        matrix: pd.DataFrame, 
        info_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        将营养矩阵转换为标准单位（per 1000 kcal）。

        同时应用数量级系数（mg → g 等）和密度系数（/100g → /1000kcal）。

        Args:
            matrix:  宽表矩阵（values 可能混杂 mg / μg / IU，单位为 per 100g）。
            info_df: 以 nutrient_id 为 index 的营养素元数据（需含 unit_name 列）。

        Returns:
            标准化后的矩阵（副本）。
        """
        normalized = matrix.copy()

        # 1. 获取热量列 (NutrientID.ENERGY = 1008)
        # 计算密度(per 1000kcal)必须依赖热量数据
        ENERGY_ID = NutrientID.ENERGY
        if ENERGY_ID not in matrix.columns:
            logger.warning("Warning: Energy column (1008) missing. Cannot calculate nutrient density.")
            return matrix

        energy_series = matrix[ENERGY_ID]
        # 2. 获取当前阶段的标准配置
        standards = AAFCO_STANDARDS[LifeStage.DOG_ADULT]

        # 3. 遍历矩阵中的每一个营养素列
        for nutrient_id in normalized.columns:
            # A. 获取来源单位 (Database Unit)
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

            logger.info(f'raw_target_unit: {raw_target_unit}')

            final_target_unit = (
                raw_target_unit
                if "/" in raw_target_unit
                else f"{raw_target_unit}/1000kcal"
            )

            try:
                # c1. 数量级系数 (Magnitude Factor): mg -> g
                mag_factor = UnitConverter.get_unit_factor(
                    nutrient_id=nutrient_id,
                    nutrient_unit=source_unit,     # 源: mg
                    threshold_unit=raw_target_unit # 目标: g/1000kcal -> 解析出 g
                )
                logger.info(f"mag_factor: {mag_factor}")
                
                # c2. 基准系数 (Base Factor): /100g -> /1000kcal
                # 这会返回一个 Series，因为每个食材的热量不同，系数也不同
                base_factor_series = UnitConverter.get_base_factor(
                    energy_series=energy_series,
                    threshold_unit=final_target_unit # 目标: g/1000kcal -> 解析出 1000kcal
                )
                logger.info(f"base_factor_series: {base_factor_series}")
                

                normalized[nutrient_id] = (
                    normalized[nutrient_id] * mag_factor * base_factor_series
                )
                
            except Exception as e:
                logger.warning(f"Error converting nutrient {nutrient_id}: {e}")

        return normalized

    # ==================================================================
    # 内部辅助
    # ==================================================================

    def _row_to_ingredient(self, row: pd.Series) -> Ingredient:
        """将 DataFrame 的一行安全转换为 Ingredient 对象。"""
        # --- 内部辅助函数：解析列表字段 ---
        def _parse_list(val: Any) -> List[str]:
            """安全解析字符串列表字段（支持 Python list 字面量或逗号分隔字符串）。"""
            if pd.isna(val) or val == "":
                return []
            if isinstance(val, list):
                return val  # 已经是列表了（比如从 Parquet 读取）
            if isinstance(val, str):
                val = val.strip()
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

        def _parse_opt_float(val: Any) -> Optional[float]:
            """处理 NaN 转 None"""
            if pd.isna(val) or val == "":
                return None
            try:
                return float(val)
            except (ValueError, TypeError):
                return None

        # --- 内部辅助函数：解析 Optional String ---
        def _parse_opt_str(val: Any) -> Optional[str]:
            """处理 NaN 转 None"""
            if pd.isna(val) or val == "":
                return None
            return str(val).strip()

        # --- 构造对象 ---
        return Ingredient(
            # 1. 基础字段 (强制转字符串，处理 NaN 为空串)
            ingredient_id=str(row.get("ingredient_id", "")).strip(),
            description=str(row.get("description", "")).strip(),
            short_name=str(row.get("short_name", "")).strip(),
            food_group=str(row.get("food_group", "")).strip(),
            food_subgroup=str(row.get("food_subgroup", "")).strip(),
            tags=_parse_list(row.get("tags")),
            diversity_tags=_parse_list(row.get("diversity_tags")),
            diversity_cluster=_parse_opt_str(row.get("diversity_cluster")),
            max_g_per_kg_bw=_parse_opt_float(row.get("max_g_per_kg_bw")),
            max_pct_kcal=_parse_opt_float(row.get("max_pct_kcal")),
        )
        
# ========== 使用示例 ==========
if __name__ == "__main__":
    # ── 方式一：上下文管理器（推荐）──────────────────────────────────────
    # loader = IngredientDataLoader("postgresql://postgres:Tuantuan_123@127.0.0.1:15432/tuanty_recipe")
    
    # ── 方式一：上下文管理器（推荐）──────────────────────────────────────
    with IngredientDataLoader() as loader:

        # L1 —— 加载食材
        logger.info("=== L1: 加载食材数据 ===")
        ingredients = loader.load_ingredients_for_l1()
        logger.info(f"总食材数: {len(ingredients)}")
        logger.info(ingredients.head())

        # L1 —— 按槽位筛选
        logger.info("\n=== L1: 筛选内脏食材 ===")
        organs = loader.filter_ingredients_by_slot(
            ingredients,
            allowed_groups=["ORGAN"],
            allowed_subgroups=["organ_liver", "organ_kidney", "organ_heart"],
        )
        logger.info(f"符合条件的内脏: {len(organs)}")

        # L1 —— 按标签查找
        logger.info("\n=== L1: 查找钙源 ===")
        calcium_sources = loader.get_ingredients_by_tags(
            tags=["role_calcium_source"], match_all=True
        )
        logger.info(f"钙源数量: {len(calcium_sources)}")

        # L2 —— 营养矩阵
        logger.info("\n=== L2: 加载营养数据 ===")
        selected_ids = ingredients["ingredient_id"].tolist()

        nutrition_matrix, nutrients_info = loader.get_nutrition_matrix_for_l2(selected_ids)
        logger.info(f"营养矩阵形状: {nutrition_matrix.shape}")

        unit_factors = loader.get_nutrition_unit_factors(nutrient_info=nutrients_info)
        converted_matrix = loader.get_converted_nutrition_matrix(
            nutrition_matrix, unit_factors
        )
        logger.info(f"转换后矩阵形状: {converted_matrix.shape}")

    # ── 方式二：手动管理（适合复用同一 engine 的场景）─────────────────────
    # from app.db.connection import create_db_engine, dispose_engine
    # engine = create_db_engine()
    # loader = IngredientDataLoader(engine=engine)
    # ...
    # dispose_engine(engine)
    