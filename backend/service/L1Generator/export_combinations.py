"""
L1 Recipe Generator - CSV 导出功能

将生成的所有组合导出到 CSV 文件，方便观察和分析
"""

import pandas as pd
from typing import List
from l1_recipe_generator import RecipeCombination

def export_combinations_to_csv(
    combinations: List[RecipeCombination],
    output_file: str = "l1_combinations.csv",
    format_style: str = "detailed"  # "detailed" or "compact"
) -> str:
    """
    将组合导出到 CSV 文件
    
    Args:
        combinations: 组合列表
        output_file: 输出文件路径
        format_style: 导出格式
            - "detailed": 每个槽位单独一列，显示所有食材
            - "compact": 紧凑格式，只显示食材名称
    
    Returns:
        输出文件路径
    """
    if format_style == "detailed":
        return _export_detailed_format(combinations, output_file)
    else:
        return _export_compact_format(combinations, output_file)


def _export_detailed_format(
    combinations: List[RecipeCombination],
    output_file: str
) -> str:
    """
    详细格式：每个槽位单独一列
    
    CSV 格式示例:
    combination_id | main_protein | carbohydrate | calcium | ... | diversity_score | risk_score
    combo_0001     | Chicken      | Rice         | Calcium | ... | 0.75           | 0.2
    """
    rows = []
    
    for combo in combinations:
        row = {
            'combination_id': combo.combination_id,
            'n_ingredients': len(combo.get_all_ingredients()),
            'n_active_slots': len(combo.active_slots),
            'diversity_score': round(combo.diversity_score, 3),
            'risk_score': round(combo.risk_score, 3),
            'completeness_score': round(combo.completeness_score, 3),
        }
        
        # 添加每个槽位的食材
        for slot_name, ing_list in combo.ingredients.items():
            # 合并多个食材为一个字符串
            ingredient_names = ', '.join([ing.short_name for ing in ing_list])
            row[f'slot_{slot_name}'] = ingredient_names
            
            # # 同时添加食材ID（用于追踪）
            # ingredient_ids = ', '.join([ing.ingredient_id for ing in ing_list])
            # row[f'slot_{slot_name}_ids'] = ingredient_ids
        
        # 添加启用的槽位列表
        row['active_slots'] = ', '.join(combo.active_slots)
        
        rows.append(row)
    
    # 转换为 DataFrame
    df = pd.DataFrame(rows)
    
    # 排序列：先显示基本信息，再显示槽位，最后显示评分
    basic_cols = ['combination_id', 'n_ingredients', 'n_active_slots']
    score_cols = ['diversity_score', 'risk_score', 'completeness_score']
    slot_cols = [col for col in df.columns if col.startswith('slot_')]
    other_cols = [col for col in df.columns 
                  if col not in basic_cols + score_cols + slot_cols]
    
    column_order = basic_cols + slot_cols + score_cols + other_cols
    df = df[[col for col in column_order if col in df.columns]]
    
    # 导出
    df.to_csv(output_file, index=False, encoding='utf-8-sig')  # utf-8-sig 支持中文
    
    print(f"✓ 导出 {len(combinations)} 个组合到: {output_file}")
    print(f"  格式: 详细格式（每个槽位单独一列）")
    print(f"  大小: {df.shape}")
    
    return output_file


def _export_compact_format(
    combinations: List[RecipeCombination],
    output_file: str
) -> str:
    """
    紧凑格式：所有食材在一列
    
    CSV 格式示例:
    combination_id | ingredients | active_slots | diversity_score
    combo_0001     | Chicken, Rice, Calcium | main_protein, carb, calcium | 0.75
    """
    rows = []
    
    for combo in combinations:
        # 收集所有食材
        all_ingredients = combo.get_all_ingredients()
        ingredient_names = ', '.join([ing.short_name for ing in all_ingredients])
        ingredient_ids = ', '.join([ing.ingredient_id for ing in all_ingredients])
        
        row = {
            'combination_id': combo.combination_id,
            'ingredients': ingredient_names,
            'ingredient_ids': ingredient_ids,
            'n_ingredients': len(all_ingredients),
            'active_slots': ', '.join(combo.active_slots),
            'n_active_slots': len(combo.active_slots),
            'diversity_score': round(combo.diversity_score, 3),
            'risk_score': round(combo.risk_score, 3),
            'completeness_score': round(combo.completeness_score, 3),
        }
        
        rows.append(row)
    
    df = pd.DataFrame(rows)
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"✓ 导出 {len(combinations)} 个组合到: {output_file}")
    print(f"  格式: 紧凑格式（所有食材在一列）")
    
    return output_file


def export_combinations_to_excel(
    combinations: List[RecipeCombination],
    output_file: str = "l1_combinations.xlsx"
) -> str:
    """
    导出到 Excel（支持多个 sheet）
    
    Sheet 1: 组合概览
    Sheet 2: 每个槽位详细信息
    Sheet 3: 评分统计
    """
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Sheet 1: 组合概览
        overview_data = []
        for combo in combinations:
            overview_data.append({
                'combination_id': combo.combination_id,
                'n_ingredients': len(combo.get_all_ingredients()),
                'active_slots': ', '.join(combo.active_slots),
                'diversity_score': round(combo.diversity_score, 3),
                'risk_score': round(combo.risk_score, 3),
                'completeness_score': round(combo.completeness_score, 3),
            })
        
        df_overview = pd.DataFrame(overview_data)
        df_overview.to_excel(writer, sheet_name='Overview', index=False)
        
        # Sheet 2: 详细槽位信息
        detail_data = []
        for combo in combinations:
            for slot_name, ing_list in combo.ingredients.items():
                for ing in ing_list:
                    detail_data.append({
                        'combination_id': combo.combination_id,
                        'slot_name': slot_name,
                        'ingredient_id': ing.ingredient_id,
                        'ingredient_name': ing.short_name,
                        'food_group': ing.food_group,
                        'food_subgroup': ing.food_subgroup,
                        'diversity_cluster': ing.diversity_cluster,
                    })
        
        df_detail = pd.DataFrame(detail_data)
        df_detail.to_excel(writer, sheet_name='Details', index=False)
        
        # Sheet 3: 评分统计
        stats_data = {
            'Metric': [
                'Total Combinations',
                'Avg Diversity Score',
                'Avg Risk Score',
                'Avg Completeness Score',
                'Max Diversity Score',
                'Min Risk Score',
            ],
            'Value': [
                len(combinations),
                round(sum(c.diversity_score for c in combinations) / len(combinations), 3),
                round(sum(c.risk_score for c in combinations) / len(combinations), 3),
                round(sum(c.completeness_score for c in combinations) / len(combinations), 3),
                round(max(c.diversity_score for c in combinations), 3),
                round(min(c.risk_score for c in combinations), 3),
            ]
        }
        
        df_stats = pd.DataFrame(stats_data)
        df_stats.to_excel(writer, sheet_name='Statistics', index=False)
    
    print(f"✓ 导出 {len(combinations)} 个组合到 Excel: {output_file}")
    print(f"  包含 3 个 sheets: Overview, Details, Statistics")
    
    return output_file


def export_combinations_filtered(
    combinations: List[RecipeCombination],
    output_file: str,
    filter_function = None,
    top_n: int = None
):
    """
    导出筛选后的组合
    
    Args:
        combinations: 组合列表
        output_file: 输出文件
        filter_function: 筛选函数，例如 lambda c: "Cod" in str(c.ingredients)
        top_n: 只导出前 N 个组合
    
    Examples:
        # 只导出包含 Cod 的组合
        export_combinations_filtered(
            combinations, 
            "cod_combinations.csv",
            filter_function=lambda c: any(
                ing.short_name == "Cod" 
                for ings in c.ingredients.values() 
                for ing in ings
            )
        )
        
        # 只导出前 50 个高分组合
        export_combinations_filtered(
            combinations,
            "top_50_combinations.csv",
            top_n=50
        )
    """
    filtered = combinations
    
    # 应用筛选函数
    if filter_function:
        filtered = [c for c in filtered if filter_function(c)]
        print(f"✓ 筛选后保留 {len(filtered)} 个组合")
    
    # 应用数量限制
    if top_n:
        filtered = filtered[:top_n]
        print(f"✓ 只导出前 {top_n} 个组合")
    
    # 导出
    return export_combinations_to_csv(filtered, output_file)


# ========== 使用示例 ==========

if __name__ == "__main__":
    """
    使用示例
    """
    from l1_recipe_generator import L1RecipeGenerator
    import pandas as pd
    
    # 假设你已经有了 ingredients_df 和生成的 combinations
    # 这里只是演示 API 用法
    
    print("L1 组合导出工具使用示例\n")
    
    # 示例1: 基础导出
    print("=" * 60)
    print("示例 1: 导出所有组合到 CSV（详细格式）")
    print("=" * 60)
    print("""
# 生成组合
l1_generator = L1RecipeGenerator(ingredients_df)
combinations = l1_generator.generate(max_combinations=500)

# 导出到 CSV（详细格式 - 每个槽位单独一列）
export_combinations_to_csv(
    combinations, 
    output_file="combinations_detailed.csv",
    format_style="detailed"
)
""")
    
    # 示例2: 紧凑格式
    print("\n" + "=" * 60)
    print("示例 2: 导出到 CSV（紧凑格式）")
    print("=" * 60)
    print("""
# 导出到 CSV（紧凑格式 - 所有食材在一列）
export_combinations_to_csv(
    combinations,
    output_file="combinations_compact.csv",
    format_style="compact"
)
""")
    
    # 示例3: 导出到 Excel
    print("\n" + "=" * 60)
    print("示例 3: 导出到 Excel（多个 sheets）")
    print("=" * 60)
    print("""
# 导出到 Excel（包含多个 sheets）
export_combinations_to_excel(
    combinations,
    output_file="combinations.xlsx"
)
""")
    
    # 示例4: 筛选导出
    print("\n" + "=" * 60)
    print("示例 4: 只导出包含 Cod 的组合")
    print("=" * 60)
    print("""
# 只导出包含 Cod 的组合
export_combinations_filtered(
    combinations,
    output_file="cod_combinations.csv",
    filter_function=lambda c: any(
        ing.short_name == "Cod"
        for ings in c.ingredients.values()
        for ing in ings
    )
)
""")
    
    # 示例5: 只导出前 N 个
    print("\n" + "=" * 60)
    print("示例 5: 只导出前 50 个高分组合")
    print("=" * 60)
    print("""
# 组合已经按分数排序，只导出前 50 个
export_combinations_filtered(
    combinations,
    output_file="top_50_combinations.csv",
    top_n=50
)
""")
    
    print("\n" + "=" * 60)
    print("完整使用流程")
    print("=" * 60)
    print("""
# 1. 生成组合
from l1_recipe_generator import L1RecipeGenerator
from data_loader import IngredientDataLoader
from export_combinations import export_combinations_to_csv

# 加载数据
loader = IngredientDataLoader()
ingredients_df = loader.load_ingredients_for_l1()

# 生成组合
l1_generator = L1RecipeGenerator(ingredients_df)
combinations = l1_generator.generate(max_combinations=500)

# 2. 导出到 CSV
export_combinations_to_csv(
    combinations,
    output_file="all_combinations.csv",
    format_style="detailed"  # 或 "compact"
)

# 3. 在 Excel 或 Python 中分析
import pandas as pd
df = pd.read_csv("all_combinations.csv")
print(df.head())
""")