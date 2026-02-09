"""
表生成函数模块 - 精简重构版
拆分原来的大函数为更小、更专注的函数
"""

import pandas as pd
import numpy as np
import uuid
import logging
from pathlib import Path
from typing import Dict, List, Tuple

from dataset_preparing_refactored import (
    NutrientID, IdentityTagger, AutoTagConfig, UnitConverter,
    clean_tags, validate_dataframe, Constants
)


# ============================================
# 营养素表生成
# ============================================

def table_nutrients_generation(input_path: str, output_path: str) -> pd.DataFrame:
    """
    生成营养素表
    简化：直接读取、处理、保存
    """
    try:
        logging.info("生成营养素表...")
        
        df = pd.read_csv(input_path)
        
        # 数据清洗
        df['nutrient_id'] = pd.to_numeric(df['nutrient_id'], errors='coerce')
        df = df.dropna(subset=['nutrient_id'])
        df['nutrient_id'] = df['nutrient_id'].astype(int)
        
        # 保存
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        
        logging.info(f"✓ 营养素表已生成: {len(df)} 行")
        return df
        
    except Exception as e:
        logging.error(f"生成营养素表失败: {e}")
        raise


# ============================================
# 食材表生成
# ============================================

def generate_short_name(description: str) -> str:
    """
    生成食材简称
    简化：移除烹饪方式关键词
    """
    if not description:
        return ""
    
    cooking_keywords = [
        'raw', 'cooked', 'boiled', 'baked', 'fried', 'roasted',
        'steamed', 'grilled', 'broiled', 'braised', 'stewed'
    ]
    
    parts = [part.strip() for part in description.split(',')]
    filtered = [p for p in parts if not any(kw in p.lower() for kw in cooking_keywords)]
    
    return ' '.join(filtered).title() if filtered else description.title()


def infer_food_group(description: str, category_id: int) -> str:
    """
    推断食材组别
    简化：基于关键词和分类ID
    """
    desc_lower = description.lower()
    
    # 预定义映射
    group_map = {
        # 蛋白质
        (5, None): 'PROTEIN_MEAT',  # 禽类
        (10, None): 'PROTEIN_MEAT',  # 猪肉
        (13, None): 'PROTEIN_MEAT',  # 牛肉
        (17, None): 'PROTEIN_MEAT',  # 羊肉等
        (15, 'shellfish'): 'PROTEIN_SHELLFISH',
        (15, None): 'PROTEIN_FISH',
        (1, 'egg'): 'PROTEIN_EGG',
        
        # 碳水
        (20, None): 'CARB_GRAIN',
        (16, None): 'CARB_LEGUME',
        (11, 'potato'): 'CARB_TUBER',
        
        # 蔬果
        (11, None): 'VEGETABLE',
        (9, None): 'FRUIT',
        
        # 油脂
        (4, None): 'FAT_OIL',
    }
    
    # 关键词检测
    keywords = {
        'shellfish': ['shrimp', 'crab', 'oyster', 'clam', 'mussel'],
        'egg': ['egg', 'yolk', 'white'],
        'potato': ['potato', 'sweet potato', 'yam'],
        'organ': ['liver', 'kidney', 'heart', 'brain'],
    }
    
    detected_keyword = None
    for key, terms in keywords.items():
        if any(term in desc_lower for term in terms):
            detected_keyword = key
            break
    
    # 特殊检查：内脏
    if detected_keyword == 'organ':
        return 'ORGAN'
    
    # 查找匹配
    result = group_map.get((category_id, detected_keyword)) or group_map.get((category_id, None))
    
    return result if result else 'OTHER'


def table_ingredients_generation(input_path: str, output_path: str) -> pd.DataFrame:
    """
    生成食材表
    简化：拆分为多个小步骤
    """
    try:
        logging.info("生成食材表...")
        
        # 1. 读取数据
        df = pd.read_csv(input_path, usecols=['fdc_id', 'description', 'food_category_id'])
        
        # 2. 数据清洗
        df['fdc_id'] = pd.to_numeric(df['fdc_id'], errors='coerce')
        df['food_category_id'] = pd.to_numeric(df['food_category_id'], errors='coerce')
        df = df.dropna(subset=['fdc_id'])
        df['fdc_id'] = df['fdc_id'].astype(int)
        df['food_category_id'] = df['food_category_id'].astype(int)
        
        # 3. 生成字段
        df['id'] = [str(uuid.uuid4()) for _ in range(len(df))]
        df['source'] = 'built_in'
        df['short_name'] = df['description'].apply(generate_short_name)
        df['food_group'] = df.apply(
            lambda row: infer_food_group(row['description'], row['food_category_id']),
            axis=1
        )
        
        # 4. 添加其他字段
        df['is_active'] = True
        df['created_at'] = pd.Timestamp.now()
        df['updated_at'] = pd.Timestamp.now()
        
        # 5. 保存
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        
        logging.info(f"✓ 食材表已生成: {len(df)} 行")
        return df
        
    except Exception as e:
        logging.error(f"生成食材表失败: {e}")
        raise


# ============================================
# 营养素关联表生成
# ============================================

def table_ingredient_nutrients_generation(
    food_path: str,
    nutrient_path: str,
    output_path: str
) -> pd.DataFrame:
    """
    生成食材-营养素关联表
    简化：使用骨架补全方法
    """
    try:
        logging.info("生成营养素关联表...")
        
        # 1. 读取食材表
        df_food = pd.read_csv(food_path, usecols=['id', 'fdc_id'])
        df_food.rename(columns={'id': 'ingredient_id'}, inplace=True)
        
        # 2. 读取营养素数据
        df_nut = pd.read_csv(nutrient_path, usecols=['fdc_id', 'nutrient_id', 'amount'])
        
        # 3. 合并数据
        df_merged = pd.merge(df_food, df_nut, on='fdc_id', how='inner')
        
        # 4. 补零（为缺失的营养素填充0）
        all_ingredients = df_food['ingredient_id'].unique()
        all_nutrients = df_nut['nutrient_id'].unique()
        
        # 创建完整骨架
        skeleton = pd.MultiIndex.from_product(
            [all_ingredients, all_nutrients],
            names=['ingredient_id', 'nutrient_id']
        )
        df_skeleton = pd.DataFrame(index=skeleton).reset_index()
        
        # 左连接补全
        df_final = pd.merge(
            df_skeleton,
            df_merged[['ingredient_id', 'nutrient_id', 'amount', 'fdc_id']],
            on=['ingredient_id', 'nutrient_id'],
            how='left'
        )
        
        df_final['amount'] = df_final['amount'].fillna(0.0)
        
        # 5. 保存
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df_final.to_csv(output_path, index=False)
        
        logging.info(f"✓ 营养素关联表已生成: {len(df_final)} 行")
        return df_final
        
    except Exception as e:
        logging.error(f"生成营养素关联表失败: {e}")
        raise


# ============================================
# 标签表生成（拆分为多个函数）
# ============================================

def load_and_pivot_nutrition_data(
    food_path: str,
    nutrient_data_path: str,
    nutrient_def_path: str
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[int, str]]:
    """
    步骤1：加载并透视营养数据
    """
    logging.info("1. 加载并透视数据...")
    
    # 读取食材表
    df_food = pd.read_csv(
        food_path,
        usecols=['id', 'food_group', 'fdc_id', 'description', 'food_category_id']
    )
    df_food.rename(columns={'id': 'ingredient_id'}, inplace=True)
    df_food.set_index('ingredient_id', inplace=True)
    
    # 读取营养素定义
    df_nut_def = pd.read_csv(nutrient_def_path, usecols=['nutrient_id', 'unit_name'])
    unit_map = dict(zip(df_nut_def['nutrient_id'], df_nut_def['unit_name']))
    
    # 读取并透视营养素数据
    df_nut_data = pd.read_csv(
        nutrient_data_path,
        usecols=['ingredient_id', 'nutrient_id', 'amount']
    )
    df_nut_pivot = df_nut_data.pivot(
        index='ingredient_id',
        columns='nutrient_id',
        values='amount'
    ).fillna(0)
    
    # 合并
    df_final = df_nut_pivot.join(df_food)
    
    return df_final, df_nut_pivot, unit_map


def generate_food_subgroups(df: pd.DataFrame) -> pd.DataFrame:
    """
    步骤2：生成食材子分组
    简化版：基于food_group和基本逻辑
    """
    logging.info("2. 生成食材子分组...")
    
    def get_subgroup(row):
        group = row.get('food_group', 'OTHER')
        desc = str(row.get('description', '')).lower()
        fat = row.get(NutrientID.FAT, 0.0)
        
        # 简化的子分组逻辑
        subgroup_map = {
            'PROTEIN_MEAT': 'meat_lean' if fat < Constants.FAT_LEAN_THRESHOLD else 'meat_moderate',
            'PROTEIN_FISH': 'fish_lean',
            'PROTEIN_SHELLFISH': 'shellfish_protein',
            'PROTEIN_EGG': 'egg',
            'ORGAN': 'organ_liver' if 'liver' in desc else 'organ_other',
            'CARB_GRAIN': 'carb_grain',
            'CARB_TUBER': 'carb_tuber',
            'CARB_LEGUME': 'carb_legume',
            'VEGETABLE': 'vegetable',
            'FRUIT': 'fruit',
            'FAT_OIL': 'oil_other',
        }
        
        return subgroup_map.get(group, 'other')
    
    df['food_subgroup'] = df.apply(get_subgroup, axis=1)
    return df


def generate_role_risk_tags(
    df: pd.DataFrame,
    df_nut_pivot: pd.DataFrame,
    unit_map: Dict[int, str],
    config: AutoTagConfig
) -> pd.DataFrame:
    """
    步骤3：生成Role和Risk标签
    """
    logging.info("3. 生成Role和Risk标签...")
    
    df['role_tags'] = ""
    df['risk_tags'] = ""
    
    energy_series = df_nut_pivot[NutrientID.ENERGY]
    
    # 处理规则
    for rule_dict, target_col in [(config.role_rules, 'role_tags'), 
                                   (config.risk_rules, 'risk_tags')]:
        for nut_id, rule_list in rule_dict.items():
            for rule in rule_list:
                # 获取原始值
                if rule.source_type == 'SUM_EPA_DHA':
                    raw_values = (df_nut_pivot.get(NutrientID.EPA, 0) + 
                                 df_nut_pivot.get(NutrientID.DHA, 0))
                    source_unit = unit_map.get(NutrientID.EPA, 'g')
                elif nut_id in df_nut_pivot.columns:
                    raw_values = df_nut_pivot[nut_id]
                    source_unit = unit_map.get(nut_id, 'g')
                else:
                    continue
                
                # 计算标准化值
                mag_factor = UnitConverter.get_unit_factor(nut_id, source_unit, rule.threshold.unit)
                base_factor = UnitConverter.get_base_factor(energy_series, rule.threshold.unit)
                norm_values = (raw_values * mag_factor * base_factor).fillna(0)
                
                # 生成mask
                mask = norm_values >= rule.threshold.value
                
                if rule.min_raw_value > 0:
                    mask = mask & (raw_values >= rule.min_raw_value)
                
                # 添加标签
                if mask.any():
                    df.loc[mask, target_col] += "," + rule.tag_name
    
    return df


def generate_identity_tags(df: pd.DataFrame) -> pd.DataFrame:
    """
    步骤4：生成Identity标签
    """
    logging.info("4. 生成Identity标签...")
    
    identity_results = df.apply(
        lambda row: IdentityTagger.get_tags(row['description'], row['food_category_id']),
        axis=1,
        result_type='expand'
    )
    
    df[['diversity_tags', 'repeat_tags']] = identity_results
    return df


def transform_to_db_format(df: pd.DataFrame, output_path: str) -> pd.DataFrame:
    """
    步骤5：转换为数据库格式（长表）
    """
    logging.info("5. 转换为数据库格式...")
    
    # 清洗标签
    for col in ['role_tags', 'risk_tags', 'diversity_tags', 'repeat_tags']:
        df[col] = df[col].apply(clean_tags)
    
    # 定义映射
    tag_mapping = {
        'role_tags': 'role',
        'risk_tags': 'risk',
        'diversity_tags': 'diversity',
        'repeat_tags': 'repeat_policy',
    }
    
    # Melt操作
    df_reset = df.reset_index()
    df_melted = df_reset.melt(
        id_vars=['ingredient_id', 'food_subgroup', 'description', 'fdc_id'],
        value_vars=list(tag_mapping.keys()),
        var_name='source_col',
        value_name='tag_string'
    )
    
    # 过滤空标签
    df_melted = df_melted[df_melted['tag_string'] != ""].dropna(subset=['tag_string'])
    
    # Explode标签
    df_melted['tag_list'] = df_melted['tag_string'].apply(
        lambda x: [t.strip() for t in x.split(',') if t.strip()]
    )
    df_exploded = df_melted.explode('tag_list')
    
    # 格式化输出
    df_exploded['tag_type'] = df_exploded['source_col'].map(tag_mapping)
    df_exploded.rename(columns={'tag_list': 'tag'}, inplace=True)
    df_exploded['source'] = 'system'
    
    # 选择最终列
    df_final = df_exploded[[
        'ingredient_id', 'food_subgroup', 'tag_type', 'tag', 'source',
        'description', 'fdc_id'
    ]].copy()
    
    # 去重
    df_final.drop_duplicates(subset=['ingredient_id', 'tag_type', 'tag'], inplace=True)
    
    # 保存
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(output_path, index=False)
    
    logging.info(f"✓ 标签表已生成: {len(df_final)} 行")
    return df_final


def table_ingredient_tags_generation(
    food_path: str,
    nutrient_data_path: str,
    nutrient_def_path: str,
    output_path: str,
    config: AutoTagConfig
) -> pd.DataFrame:
    """
    生成食材标签表
    重构：拆分为5个步骤
    """
    try:
        # 步骤1：加载数据
        df, df_nut_pivot, unit_map = load_and_pivot_nutrition_data(
            food_path, nutrient_data_path, nutrient_def_path
        )
        
        # 步骤2：生成子分组
        df = generate_food_subgroups(df)
        
        # 步骤3：生成Role和Risk标签
        df = generate_role_risk_tags(df, df_nut_pivot, unit_map, config)
        
        # 步骤4：生成Identity标签
        df = generate_identity_tags(df)
        
        # 步骤5：转换格式并保存
        df_final = transform_to_db_format(df, output_path)
        
        return df_final
        
    except Exception as e:
        logging.error(f"生成标签表失败: {e}", exc_info=True)
        raise


# ============================================
# 主程序
# ============================================

if __name__ == "__main__":
    from pathlib import Path
    
    # 配置路径
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / 'data'
    
    # 输入输出文件
    files = {
        'nutrient_input': data_dir / 'nutrient.csv',
        'nutrient_output': data_dir / 'nutrient_new.csv',
        'food_input': data_dir / 'food.csv',
        'food_output': data_dir / 'food_new.csv',
        'food_nutrient_input': data_dir / 'food_nutrient.csv',
        'food_nutrient_output': data_dir / 'food_nutrient_new.csv',
        'food_tag_output': data_dir / 'food_tag_new.csv',
    }
    
    try:
        # 生成配置
        config = AutoTagConfig()
        
        # 执行生成流程
        logging.info("=" * 60)
        logging.info("开始数据处理流程")
        logging.info("=" * 60)
        
        # 1. 营养素表
        nutrient_df = table_nutrients_generation(
            files['nutrient_input'],
            files['nutrient_output']
        )
        
        # 2. 食材表
        food_df = table_ingredients_generation(
            files['food_input'],
            files['food_output']
        )
        
        # 3. 营养素关联表
        food_nut_df = table_ingredient_nutrients_generation(
            files['food_output'],
            files['food_nutrient_input'],
            files['food_nutrient_output']
        )
        
        # 4. 标签表
        tag_df = table_ingredient_tags_generation(
            files['food_output'],
            files['food_nutrient_output'],
            files['nutrient_output'],
            files['food_tag_output'],
            config
        )
        
        logging.info("=" * 60)
        logging.info("✓ 所有表生成完成!")
        logging.info("=" * 60)
        
    except Exception as e:
        logging.error(f"✗ 处理失败: {e}")
        raise