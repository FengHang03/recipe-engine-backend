"""
L2 优化器测试脚本
Test Script for L2 Optimizer

这个脚本创建一个简单的测试用例来验证求解器
"""
import logging

from app.datebase.data_loader import IngredientDataLoader

from app.L1Generator.l1_recipe_generator import L1RecipeGenerator
from app.L1Generator.l1_config import L1Config

from l2_data_models import (
    PetProfile, Ingredient, RecipeCombination, L2Input,
    LifeStage, NutrientID, SlotType
)
from l2_optimizer import L2Optimizer

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_ingredients():
    """创建测试食材库"""
    
    ingredients = []
    
    # 主肉: 鸡胸肉
    ingredients.append(Ingredient(
        id="chicken_breast",
        name="鸡胸肉",
        slot=SlotType.MAIN_PROTEIN,
        calories_per_100g=165,
        nutrients={
            NutrientID.PROTEIN.value: 31.0,      # g/100g
            NutrientID.FAT.value: 3.6,
            NutrientID.CALCIUM.value: 15,        # mg/100g
            NutrientID.PHOSPHORUS.value: 220,
            NutrientID.IRON.value: 0.7,
            NutrientID.ZINC.value: 1.0,
            NutrientID.COPPER.value: 0.05,
            NutrientID.SELENIUM.value: 27.6,     # µg/100g
            NutrientID.VITAMIN_B12.value: 0.3,   # µg/100g
        },
        category="poultry"
    ))
    
    # 器官: 鸡肝
    ingredients.append(Ingredient(
        id="chicken_liver",
        name="鸡肝",
        slot=SlotType.ORGAN_LIVER,
        calories_per_100g=116,
        nutrients={
            NutrientID.PROTEIN.value: 16.9,
            NutrientID.FAT.value: 4.8,
            NutrientID.CALCIUM.value: 8,
            NutrientID.PHOSPHORUS.value: 297,
            NutrientID.IRON.value: 9.0,
            NutrientID.ZINC.value: 2.7,
            NutrientID.COPPER.value: 0.4,
            NutrientID.SELENIUM.value: 54.6,
            NutrientID.VITAMIN_A.value: 11078,   # IU/100g (非常高!)
            NutrientID.VITAMIN_B12.value: 16.6,
        },
        tags=["risk_high_vit_a"]
    ))
    
    # 器官: 鸡心
    ingredients.append(Ingredient(
        id="chicken_heart",
        name="鸡心",
        slot=SlotType.ORGAN_MUSCULAR,
        calories_per_100g=153,
        nutrients={
            NutrientID.PROTEIN.value: 15.6,
            NutrientID.FAT.value: 9.3,
            NutrientID.CALCIUM.value: 6,
            NutrientID.PHOSPHORUS.value: 153,
            NutrientID.IRON.value: 6.3,
            NutrientID.ZINC.value: 1.8,
            NutrientID.COPPER.value: 0.3,
            NutrientID.SELENIUM.value: 25.0,
        }
    ))
    
    # 蔬菜: 胡萝卜
    ingredients.append(Ingredient(
        id="carrot",
        name="胡萝卜",
        slot=SlotType.VEGETABLE,
        calories_per_100g=41,
        nutrients={
            NutrientID.PROTEIN.value: 0.9,
            NutrientID.FAT.value: 0.2,
            NutrientID.CALCIUM.value: 33,
            NutrientID.PHOSPHORUS.value: 35,
            NutrientID.IRON.value: 0.3,
            NutrientID.VITAMIN_A.value: 16706,  # IU/100g (很高!)
        }
    ))
    
    # 碳水: 红薯
    ingredients.append(Ingredient(
        id="sweet_potato",
        name="红薯",
        slot=SlotType.CARBOHYDRATE,
        calories_per_100g=86,
        nutrients={
            NutrientID.PROTEIN.value: 1.6,
            NutrientID.FAT.value: 0.1,
            NutrientID.CALCIUM.value: 30,
            NutrientID.PHOSPHORUS.value: 47,
            NutrientID.IRON.value: 0.6,
            NutrientID.VITAMIN_A.value: 14187,
        }
    ))
    
    return ingredients


def create_test_supplements():
    """创建测试补剂库"""
    
    supplements = []
    
    # 海带粉 (碘源)
    supplements.append(Ingredient(
        id="sup_kelp",
        name="海带粉",
        slot=SlotType.IODINE,
        calories_per_100g=0,
        nutrients={
            NutrientID.IODINE.value: 1500,  # mg/100g (极高!)
            NutrientID.CALCIUM.value: 168,
        },
        is_supplement=True,
        tags=["risk_high_iodine"]
    ))
    
    # 锌螯合物
    supplements.append(Ingredient(
        id="sup_zinc",
        name="吡啶甲酸锌",
        slot=SlotType.SUPPLEMENT,
        calories_per_100g=0,
        nutrients={
            NutrientID.ZINC.value: 20000,  # mg/100g (纯锌补剂)
        },
        is_supplement=True
    ))
    
    # 碳酸钙
    supplements.append(Ingredient(
        id="sup_calcium",
        name="碳酸钙",
        slot=SlotType.SUPPLEMENT_CALCIUM,
        calories_per_100g=0,
        nutrients={
            NutrientID.CALCIUM.value: 40000,  # mg/100g (40% 钙)
        },
        is_supplement=True
    ))
    
    # 维生素 E
    supplements.append(Ingredient(
        id="sup_vit_e",
        name="维生素E油",
        slot=SlotType.SUPPLEMENT,
        calories_per_100g=884,  # 纯油
        nutrients={
            NutrientID.VITAMIN_E.value: 149253,  # IU/100g (极高!)
        },
        is_supplement=True
    ))
    
    # 鱼油
    supplements.append(Ingredient(
        id="sup_fish_oil",
        name="鱼油",
        slot=SlotType.OMEGA3_LC,
        calories_per_100g=902,
        nutrients={
            NutrientID.FAT.value: 100,
            NutrientID.EPA.value: 18.0,    # g/100g
            NutrientID.DHA.value: 12.0,
        },
        is_supplement=True
    ))
    
    return supplements


def create_test_case():
    """创建一个完整的测试用例"""
    
    # 宠物画像: 成年狗,10kg,500 kcal/day
    pet_profile = PetProfile(
        target_calories=1695.9,
        body_weight=30.0,
        life_stage=LifeStage.DOG_ADULT
    )
    

    # 食材组合 (L1 生成的)
    ingredients = create_test_ingredients()
    
    combination = RecipeCombination(
        combination_id="test_combo_001",
        ingredients=ingredients,
        # main_protein_category="chicken"
    )

    
    # 补剂工具箱
    supplements = create_test_supplements()
    
    # 完整输入
    l2_input = L2Input(
        pet_profile=pet_profile,
        combination=combination,
        supplement_toolkit=supplements
    )
    
    return l2_input

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


def print_result(result):
    """打印结果"""
    
    print("\n" + "="*60)
    print("📊 L2 优化结果")
    print("="*60)
    
    print(f"\n🔍 状态: {result.status.value}")
    print(f"⏱️  求解时间: {result.solve_time_seconds:.3f} 秒")
    
    if result.status.value == "optimal":
        print(f"🎯 目标函数值: {result.objective_value:.2f}")
        
        print(f"\n📦 总重量: {result.total_weight_grams:.1f} g")
        
        print("\n🥩 食材配方:")
        print("-" * 60)
        
        # 按重量排序
        sorted_weights = sorted(result.weights, key=lambda x: x.weight_grams, reverse=True)
        
        for w in sorted_weights:
            marker = "💊" if w.is_supplement else "🥬"
            print(f"{marker} {w.ingredient_name:20s} {w.weight_grams:6.1f} g  ({w.weight_grams/result.total_weight_grams*100:5.1f}%)")
        
        # 补剂使用情况
        if result.used_supplements:
            print(f"\n💊 使用的补剂: {', '.join(result.used_supplements)}")
        else:
            print("\n✅ 无需补剂!")
        
        # 营养分析 (只显示关键营养素)
        print("\n📊 关键营养素分析 (per 1000kcal):")
        print("-" * 60)
        
        key_nutrients = [
            "protein", "fat", "calcium", "phosphorus",
            "selenium", "vitamin_a", "iodine", "zinc"
        ]
        
        for analysis in result.nutrient_analysis:
            if analysis.nutrient_id not in key_nutrients:
                continue
            
            status_min = "✅" if analysis.meets_min else "❌"
            status_max = "✅" if analysis.meets_max else "❌"
            
            min_str = f"{analysis.min_required:.1f}" if analysis.min_required else "-"
            max_str = f"{analysis.max_allowed:.1f}" if analysis.max_allowed else "-"
            
            print(f"{analysis.nutrient_name:15s} {analysis.value:8.1f} {analysis.unit:4s}  "
                  f"[{min_str:8s} - {max_str:8s}]  {status_min}{status_max}")
    
    elif result.status.value == "infeasible":
        print("\n❌ 问题不可行!")
        
        if result.infeasibility_diagnostic:
            diag = result.infeasibility_diagnostic
            print(f"原因: {diag.reason.value}")
            print(f"建议: {diag.suggestion}")
    
    print("\n" + "="*60)


def main():
    """主函数"""
    
    print("🚀 L2 营养优化引擎测试")
    print("="*60)
    
    # 创建测试用例
    print("\n📝 创建测试用例...")
    l2_input = create_test_case()
    
    print(f"宠物: {l2_input.pet_profile.life_stage.value}, {l2_input.pet_profile.body_weight} kg")
    print(f"目标热量: {l2_input.pet_profile.target_calories} kcal/day")
    print(f"食材数量: {len(l2_input.combination.ingredients)}")
    print(f"补剂数量: {len(l2_input.supplement_toolkit)}")
    
    # 运行优化
    print("\n🔧 运行优化器...")
    optimizer = L2Optimizer(debug=True)
    
    result = optimizer.optimize(l2_input)
    
    # 打印结果
    print_result(result)


if __name__ == "__main__":
    main()