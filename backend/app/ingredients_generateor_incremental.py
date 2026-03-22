"""
食材表生成函数 - 增量更新版本
支持保留已存在记录的ID和创建时间
"""

import pandas as pd
import uuid
import logging
from pathlib import Path


def table_ingredients_generation(input_file_path, output_file_path):
    """
    读取 food.csv 并生成食材数据库数据
    
    增量更新逻辑：
    - 如果 output_file_path 已存在，读取现有数据
    - 对于已存在的 fdc_id，保留原有的 id, created_at
    - 对于新的 fdc_id，生成新的 id, created_at
    - 所有记录都更新 updated_at
    """
    
    column_name = [
        'id', 'source', 'owner_uid', 'fdc_id', 'description', 'short_name',
        'food_category_id', 'food_category_label', 'food_group', 'is_active',
        'max_g_per_bg_bw', 'max_pct_kcal', 'created_at', 'updated_at'
    ]
    
    _Food_id_to_category = {
        1: "Dairy and Egg Products",
        4: "Fats and Oils",
        5: "Poultry Products",
        9: "Fruits",
        10: "Pork Products",
        11: "Vegetables and Vegetable Products",
        12: "Nut and Seed Products",
        13: "Beef Products",
        15: "Finfish and Shellfish Products",
        16: "Legume and Legume Products",
        17: "Lamb, Veal, and Game Products",
        20: "Cereal Grains and Pasta",
        21: "Supplements Products"
    }
    
    try:
        # ============================================
        # 步骤1: 读取并处理输入数据
        # ============================================
        target_fdc_ids = set(TargetConfigure.get_all_fdc_id())
        food_df = (pd.read_csv(input_file_path, usecols=['fdc_id', 'description', 'food_category_id'])
                   .query('fdc_id in @target_fdc_ids'))
        
        # 数据清洗
        food_df['fdc_id'] = pd.to_numeric(food_df['fdc_id'], errors='coerce')
        food_df['food_category_id'] = pd.to_numeric(food_df['food_category_id'], errors='coerce')
        food_df = food_df.dropna(subset=['fdc_id'])
        food_df['fdc_id'] = food_df['fdc_id'].astype(int)
        food_df['food_category_id'] = food_df['food_category_id'].astype(int)
        
        # ============================================
        # 步骤2: 尝试加载现有数据
        # ============================================
        existing_df = None
        output_path = Path(output_file_path)
        
        if output_path.exists():
            try:
                existing_df = pd.read_csv(output_file_path)
                # 确保 fdc_id 类型一致
                existing_df['fdc_id'] = existing_df['fdc_id'].astype(int)
                logging.info(f"✓ 找到现有数据文件，包含 {len(existing_df)} 条记录")
            except Exception as e:
                logging.warning(f"无法读取现有文件: {e}，将创建新文件")
                existing_df = None
        
        # ============================================
        # 步骤3: 生成新字段
        # ============================================
        logging.info("生成食材短名称和分类...")
        
        food_df['short_name'] = food_df['description'].apply(_get_short_name)
        food_df['food_category_label'] = food_df['food_category_id'].map(_Food_id_to_category).fillna('Others')
        food_df['food_group'] = food_df.apply(
            lambda row: _infer_food_category(
                description=row['description'],
                category_id=row.get('food_category_id'),
            ),
            axis=1
        )
        
        # 设置默认值
        food_df['source'] = 'built_in'
        food_df['owner_uid'] = None
        food_df['max_g_per_bg_bw'] = None
        food_df['max_pct_kcal'] = None
        food_df['is_active'] = True
        
        # ============================================
        # 步骤4: 增量更新逻辑
        # ============================================
        now_str = pd.Timestamp.now().isoformat()
        
        if existing_df is not None and len(existing_df) > 0:
            logging.info("执行增量更新...")
            
            # 创建 fdc_id 到现有记录的映射
            existing_lookup = existing_df.set_index('fdc_id')
            
            # 为每条记录分配 ID 和时间戳
            ids = []
            created_ats = []
            
            for idx, row in food_df.iterrows():
                fdc_id = row['fdc_id']
                
                if fdc_id in existing_lookup.index:
                    # 已存在：保留原有的 id 和 created_at
                    ids.append(existing_lookup.loc[fdc_id, 'id'])
                    created_ats.append(existing_lookup.loc[fdc_id, 'created_at'])
                else:
                    # 新记录：生成新的 id 和 created_at
                    ids.append(str(uuid.uuid4()))
                    created_ats.append(now_str)
            
            food_df['id'] = ids
            food_df['created_at'] = created_ats
            
            # 统计
            new_count = sum(1 for fdc_id in food_df['fdc_id'] if fdc_id not in existing_lookup.index)
            updated_count = len(food_df) - new_count
            
            logging.info(f"  - 更新已存在记录: {updated_count} 条")
            logging.info(f"  - 新增记录: {new_count} 条")
            
        else:
            # 没有现有数据，全部作为新记录
            logging.info("创建新数据文件...")
            food_df['id'] = [str(uuid.uuid4()) for _ in range(len(food_df))]
            food_df['created_at'] = now_str
            logging.info(f"  - 新建记录: {len(food_df)} 条")
        
        # 所有记录都更新 updated_at
        food_df['updated_at'] = now_str
        
        # ============================================
        # 步骤5: 保存结果
        # ============================================
        # 确保列顺序正确
        food_df = food_df[column_name]
        
        # 创建输出目录
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存（使用 \\N 表示 NULL）
        food_df.to_csv(output_path, index=False, na_rep='\\N')
        
        logging.info(f"✓ 食材表已生成: {output_path}")
        logging.info(f"  - 总记录数: {len(food_df)}")
        
        return food_df
    
    except Exception as e:
        logging.error(f"生成食材表时出错: {e}")
        raise


def table_ingredients_generation_with_merge_options(
    input_file_path,
    output_file_path,
    merge_strategy='update',
    preserve_fields=None
):
    """
    高级版本：支持自定义合并策略
    
    参数:
        input_file_path: 输入CSV路径
        output_file_path: 输出CSV路径
        merge_strategy: 合并策略
            - 'update': 更新已存在记录（默认）
            - 'replace': 完全替换
            - 'append': 只添加新记录，不更新已存在的
        preserve_fields: 需要保留的字段列表
            - 默认保留: ['id', 'created_at']
            - 可自定义，如: ['id', 'created_at', 'source', 'owner_uid']
    
    返回:
        pd.DataFrame: 生成的食材表
    """
    
    if preserve_fields is None:
        preserve_fields = ['id', 'created_at']
    
    column_name = [
        'id', 'source', 'owner_uid', 'fdc_id', 'description', 'short_name',
        'food_category_id', 'food_category_label', 'food_group', 'is_active',
        'max_g_per_bg_bw', 'max_pct_kcal', 'created_at', 'updated_at'
    ]
    
    _Food_id_to_category = {
        1: "Dairy and Egg Products",
        4: "Fats and Oils",
        5: "Poultry Products",
        9: "Fruits",
        10: "Pork Products",
        11: "Vegetables and Vegetable Products",
        12: "Nut and Seed Products",
        13: "Beef Products",
        15: "Finfish and Shellfish Products",
        16: "Legume and Legume Products",
        17: "Lamb, Veal, and Game Products",
        20: "Cereal Grains and Pasta",
        21: "Supplements Products"
    }
    
    try:
        # 读取输入数据
        target_fdc_ids = set(TargetConfigure.get_all_fdc_id())
        food_df = (pd.read_csv(input_file_path, usecols=['fdc_id', 'description', 'food_category_id'])
                   .query('fdc_id in @target_fdc_ids'))
        
        # 数据清洗
        food_df['fdc_id'] = pd.to_numeric(food_df['fdc_id'], errors='coerce')
        food_df['food_category_id'] = pd.to_numeric(food_df['food_category_id'], errors='coerce')
        food_df = food_df.dropna(subset=['fdc_id'])
        food_df['fdc_id'] = food_df['fdc_id'].astype(int)
        food_df['food_category_id'] = food_df['food_category_id'].astype(int)
        
        # 生成新字段
        logging.info("生成食材短名称和分类...")
        food_df['short_name'] = food_df['description'].apply(_get_short_name)
        food_df['food_category_label'] = food_df['food_category_id'].map(_Food_id_to_category).fillna('Others')
        food_df['food_group'] = food_df.apply(
            lambda row: _infer_food_category(
                description=row['description'],
                category_id=row.get('food_category_id'),
            ),
            axis=1
        )
        
        food_df['source'] = 'built_in'
        food_df['owner_uid'] = None
        food_df['max_g_per_bg_bw'] = None
        food_df['max_pct_kcal'] = None
        food_df['is_active'] = True
        
        now_str = pd.Timestamp.now().isoformat()
        
        # 根据策略处理
        output_path = Path(output_file_path)
        existing_df = None
        
        if merge_strategy != 'replace' and output_path.exists():
            try:
                existing_df = pd.read_csv(output_file_path)
                existing_df['fdc_id'] = existing_df['fdc_id'].astype(int)
                logging.info(f"✓ 加载现有数据: {len(existing_df)} 条记录")
            except Exception as e:
                logging.warning(f"无法读取现有文件: {e}")
                existing_df = None
        
        if merge_strategy == 'replace' or existing_df is None:
            # 完全替换或没有现有数据
            logging.info(f"策略: {merge_strategy} - 创建全新数据")
            food_df['id'] = [str(uuid.uuid4()) for _ in range(len(food_df))]
            food_df['created_at'] = now_str
            
        elif merge_strategy == 'update':
            # 更新模式
            logging.info("策略: update - 增量更新")
            existing_lookup = existing_df.set_index('fdc_id')
            
            for col in preserve_fields:
                if col in food_df.columns:
                    # 为需要保留的字段创建新列
                    new_values = []
                    for fdc_id in food_df['fdc_id']:
                        if fdc_id in existing_lookup.index:
                            new_values.append(existing_lookup.loc[fdc_id, col])
                        else:
                            if col == 'id':
                                new_values.append(str(uuid.uuid4()))
                            elif col == 'created_at':
                                new_values.append(now_str)
                            else:
                                new_values.append(None)
                    food_df[col] = new_values
            
            # 如果 id 不在 preserve_fields 中，需要手动处理
            if 'id' not in preserve_fields:
                food_df['id'] = [str(uuid.uuid4()) for _ in range(len(food_df))]
            if 'created_at' not in preserve_fields:
                food_df['created_at'] = now_str
            
        elif merge_strategy == 'append':
            # 只添加新记录
            logging.info("策略: append - 只添加新记录")
            existing_lookup = existing_df.set_index('fdc_id')
            
            # 过滤出新记录
            new_records_mask = ~food_df['fdc_id'].isin(existing_lookup.index)
            food_df = food_df[new_records_mask].copy()
            
            if len(food_df) > 0:
                food_df['id'] = [str(uuid.uuid4()) for _ in range(len(food_df))]
                food_df['created_at'] = now_str
                
                # 合并现有数据和新记录
                food_df = pd.concat([existing_df, food_df], ignore_index=True)
            else:
                logging.info("没有新记录需要添加")
                food_df = existing_df
        
        # 所有记录都更新 updated_at
        food_df['updated_at'] = now_str
        
        # 保存
        food_df = food_df[column_name]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        food_df.to_csv(output_path, index=False, na_rep='\\N')
        
        logging.info(f"✓ 食材表已保存: {output_path}")
        logging.info(f"  - 总记录数: {len(food_df)}")
        
        return food_df
    
    except Exception as e:
        logging.error(f"生成食材表时出错: {e}")
        raise


# ============================================
# 使用示例
# ============================================

if __name__ == "__main__":
    # 示例1: 基本用法（自动增量更新）
    df = table_ingredients_generation(
        input_file_path='data/food.csv',
        output_file_path='data/food_new.csv'
    )
    
    # 示例2: 使用高级选项
    df = table_ingredients_generation_with_merge_options(
        input_file_path='data/food.csv',
        output_file_path='data/food_new.csv',
        merge_strategy='update',  # 'update', 'replace', 'append'
        preserve_fields=['id', 'created_at', 'source']  # 自定义保留字段
    )