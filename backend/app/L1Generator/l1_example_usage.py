"""
L1 Recipe Generator - 使用示例

展示如何使用 L1 层生成食材组合
"""

import pandas as pd
import logging
from app.database.data_loader import IngredientDataLoader
from l1_recipe_generator import L1RecipeGenerator
from l1_config import L1Config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_basic_usage():
    """示例1: 基础使用"""
    print("=" * 80)
    print("示例1: 基础使用 - 生成标准食谱组合")
    print("=" * 80)
    
    # 1. 加载数据
    logger.info("步骤1: 从数据库加载食材数据...")
    loader = IngredientDataLoader('postgresql://postgres:Tuantuan_123@127.0.0.1:15432/tuanty_recipe')
    ingredients_df = loader.load_ingredients_for_l1()
    logger.info(f"  加载完成! 共 {len(ingredients_df)} 个食材")
    
    # 2. 创建 L1 生成器 (使用默认配置)
    logger.info("步骤2: 创建 L1 生成器...")
    l1_generator = L1RecipeGenerator(ingredients_df)
    
    # 3. 生成组合
    logger.info("步骤3: 生成食材组合...")
    combinations = l1_generator.generate(max_combinations=500)
    logger.info(f"  生成完成! 共 {len(combinations)} 个组合")
    
    # 4. 查看 Top 10 组合
    logger.info("步骤4: 查看 Top 10 组合...")
    summary = l1_generator.export_combinations_summary(combinations, top_n=10)
    print("\n=== Top 10 组合摘要 ===")
    print(summary.to_string())
    
    # 5. 查看第一个组合的详细信息
    print("\n=== 第一个组合的详细信息 ===")
    first_combo = combinations[0]
    print(f"组合ID: {first_combo.combination_id}")
    print(f"多样性评分: {first_combo.diversity_score:.3f}")
    print(f"风险评分: {first_combo.risk_score:.3f}")
    print(f"完整性评分: {first_combo.completeness_score:.3f}")
    print(f"\n启用的槽位: {first_combo.active_slots}")
    print(f"\n食材详情:")
    for slot_name, ing_list in first_combo.ingredients.items():
        print(f"  {slot_name}:")
        for ing in ing_list:
            print(f"    - {ing.description} ({ing.ingredient_group} / {ing.food_subgroup})")

    from export_combinations import export_combinations_to_csv

    export_combinations_to_csv(combinations, "combinations.csv", "detailed")
    print(f"✓ 已导出 {len(combinations)} 个组合!")
    
    return combinations


def example_with_dog_profile():
    """示例2: 根据狗的健康状况生成定制食谱"""
    print("\n" + "=" * 80)
    print("示例2: 定制食谱 - 针对高血脂犬")
    print("=" * 80)
    
    # 1. 加载数据
    loader = IngredientDataLoader('postgresql://postgres:Tuantuan_123@127.0.0.1:15432/tuanty_recipe')
    ingredients_df = loader.load_ingredients_for_l1()
    
    # 2. 创建 L1 生成器
    l1_generator = L1RecipeGenerator(ingredients_df)
    
    # 3. 定义狗的健康状况
    dog_profile = {
        'name': 'Max',
        'weight_kg': 10,
        'age_years': 5,
        'conditions': ['hyperlipidemia'],  # 高血脂
        'allergies': [],
        'preferences': {}
    }
    
    logger.info(f"狗的信息: {dog_profile['name']}, {dog_profile['weight_kg']}kg")
    logger.info(f"健康状况: {dog_profile['conditions']}")
    
    # 4. 生成组合 (会自动排除高胆固醇食材)
    combinations = l1_generator.generate(
        max_combinations=300,
        dog_profile=dog_profile
    )
    
    # 5. 查看结果
    summary = l1_generator.export_combinations_summary(combinations, top_n=5)
    print("\n=== Top 5 组合 (已排除高胆固醇食材) ===")
    print(summary.to_string())
    
    return combinations


def example_custom_config():
    """示例3: 自定义配置"""
    print("\n" + "=" * 80)
    print("示例3: 自定义配置 - 修改槽位和规则")
    print("=" * 80)
    
    # 1. 加载数据
    loader = IngredientDataLoader('postgresql://postgres:Tuantuan_123@127.0.0.1:15432/tuanty_recipe')
    ingredients_df = loader.load_ingredients_for_l1()
    
    # 2. 创建自定义配置
    custom_config = L1Config()
    
    # 修改: 强制开启碳水槽 (默认是条件启用)
    custom_config.slots["carbohydrate"].is_mandatory_default = True
    logger.info("修改配置: 强制开启碳水槽")
    
    # 修改: 增加蔬菜数量
    custom_config.slots["vegetable"].max_items = 3
    logger.info("修改配置: 蔬菜槽最多3种")
    
    # 修改: 关闭 omega6 自动跳过逻辑
    custom_config.policies.skip_omega6_la_if_fatty_meat = False
    logger.info("修改配置: 关闭 omega6 自动跳过逻辑")
    
    # 3. 使用自定义配置创建生成器
    l1_generator = L1RecipeGenerator(ingredients_df, config=custom_config)
    
    # 4. 生成组合
    combinations = l1_generator.generate(max_combinations=200)
    
    # 5. 查看结果
    summary = l1_generator.export_combinations_summary(combinations, top_n=5)
    print("\n=== Top 5 组合 (自定义配置) ===")
    print(summary.to_string())
    
    return combinations


def example_export_for_l2():
    """示例4: 导出数据给 L2 优化"""
    print("\n" + "=" * 80)
    print("示例4: 导出数据给 L2 优化层")
    print("=" * 80)
    
    # 1. 生成组合
    loader = IngredientDataLoader('postgresql://postgres:Tuantuan_123@127.0.0.1:15432/tuanty_recipe')
    ingredients_df = loader.load_ingredients_for_l1()
    l1_generator = L1RecipeGenerator(ingredients_df)
    combinations = l1_generator.generate(max_combinations=100)
    
    # 2. 准备传递给 L2 的数据
    logger.info("准备传递给 L2 的数据...")
    
    for i, combo in enumerate(combinations[:5], 1):  # 只处理前5个
        print(f"\n=== 组合 {i}: {combo.combination_id} ===")
        
        # 获取食材ID列表
        ingredient_ids = combo.get_ingredient_ids()
        print(f"食材ID列表: {ingredient_ids}")
        
        # 获取营养矩阵 (给L2使用)
        nutrition_matrix, nutrients_info = loader.get_nutrition_matrix_for_l2(
            ingredient_ids
        )
        
        print(f"\n营养矩阵形状: {nutrition_matrix.shape}")
        print(f"  - 食材数: {nutrition_matrix.shape[0]}")
        print(f"  - 营养素数: {nutrition_matrix.shape[1]}")
        
        print(f"\n前5个营养素:")
        print(nutrients_info.head(5).to_string())
        
        print(f"\n营养矩阵样例 (前3个食材 × 前5个营养素):")
        print(nutrition_matrix.iloc[:3, :5].to_string())
        
        # 这里可以调用 L2 优化器
        print(f"\n→ 将此数据传递给 L2 优化器...")
        # l2_result = l2_optimizer.optimize(
        #     ingredient_ids=ingredient_ids,
        #     nutrition_matrix=nutrition_matrix,
        #     combo_metadata=combo.metadata
        # )
    
    logger.info("L2 输入数据准备完成!")


def example_analyze_combinations():
    """示例5: 分析生成的组合"""
    print("\n" + "=" * 80)
    print("示例5: 分析生成的组合")
    print("=" * 80)
    
    # 1. 生成组合
    loader = IngredientDataLoader('postgresql://postgres:Tuantuan_123@127.0.0.1:15432/tuanty_recipe')
    ingredients_df = loader.load_ingredients_for_l1()
    l1_generator = L1RecipeGenerator(ingredients_df)
    combinations = l1_generator.generate(max_combinations=500)
    
    # 2. 统计分析
    print("\n=== 统计分析 ===")
    
    # 统计每个槽位的使用频率
    slot_usage = {}
    for combo in combinations:
        for slot_name in combo.active_slots:
            slot_usage[slot_name] = slot_usage.get(slot_name, 0) + 1
    
    print("\n槽位使用频率:")
    for slot_name, count in sorted(slot_usage.items(), key=lambda x: -x[1]):
        percentage = count / len(combinations) * 100
        print(f"  {slot_name}: {count} / {len(combinations)} ({percentage:.1f}%)")
    
    # 统计内脏组合
    organ_combinations = {}
    for combo in combinations:
        organs = []
        if "organ_liver" in combo.ingredients:
            organs.append("肝脏")
        if "organ_secreting" in combo.ingredients:
            for ing in combo.ingredients["organ_secreting"]:
                organs.append(f"分泌型({ing.food_subgroup})")
        if "organ_muscular" in combo.ingredients:
            for ing in combo.ingredients["organ_muscular"]:
                organs.append(f"肌肉型({ing.food_subgroup})")
        
        organ_key = " + ".join(organs) if organs else "无内脏"
        organ_combinations[organ_key] = organ_combinations.get(organ_key, 0) + 1
    
    print("\n内脏组合分布 (Top 10):")
    for combo_str, count in sorted(
        organ_combinations.items(), 
        key=lambda x: -x[1]
    )[:10]:
        percentage = count / len(combinations) * 100
        print(f"  {combo_str}: {count} ({percentage:.1f}%)")
    
    # 评分分布
    diversity_scores = [c.diversity_score for c in combinations]
    risk_scores = [c.risk_score for c in combinations]
    
    print(f"\n多样性评分: 平均={sum(diversity_scores)/len(diversity_scores):.3f}, "
          f"最高={max(diversity_scores):.3f}, 最低={min(diversity_scores):.3f}")
    print(f"风险评分: 平均={sum(risk_scores)/len(risk_scores):.3f}, "
          f"最高={max(risk_scores):.3f}, 最低={min(risk_scores):.3f}")


def main():
    """主函数 - 运行所有示例"""
    try:
        # 示例1: 基础使用
        combinations = example_basic_usage()
        
        # 示例2: 根据健康状况定制
        example_with_dog_profile()
        
        # 示例3: 自定义配置
        example_custom_config()
        
        # 示例4: 导出给L2
        example_export_for_l2()
        
        # 示例5: 分析组合
        example_analyze_combinations()
        
        print("\n" + "=" * 80)
        print("所有示例运行完成!")
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"运行出错: {e}", exc_info=True)


if __name__ == "__main__":
    # 运行单个示例
    # example_basic_usage()
    
    # 或运行所有示例
    main()