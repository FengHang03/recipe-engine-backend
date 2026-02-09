from ipaddress import v4_int_to_packed
import sys
import logging
from typing import List
from concurrent.futures import ThreadPoolExecutor
from unittest import result
from pathlib import Path

from pandas._libs.tslibs import conversion

BACKEND_DIR = Path(__file__).parent.parent.parent  # 指向 backend
sys.path.append(str(BACKEND_DIR))

from backend.service.database import data_loader
from backend.service.database.data_loader import IngredientDataLoader
from backend.service.L1Generator.l1_recipe_generator import L1RecipeGenerator
from backend.service.L1Generator.l1_config import L1Config
from backend.service.L2Generator.l2_data_models import (
    PetProfile, Ingredient, RecipeCombination, L2Input,
    LifeStage, NutrientID, SlotType, OptimizationResult, SolveStatus
)
from backend.service.L2Generator.l2_optimizer import L2Optimizer

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RecipeEngine:
    def __init__(self, data_loader, l1_generator, l2_optimizer):
        self.data_loader = data_loader
        self.l1 = l1_generator
        self.l2 = l2_optimizer

    def generate_recipes(self, pet_profile: PetProfile, top_k: int = 5) -> List[OptimizationResult]:
        candidates = self.l1.generate(pet_profile)
        toolkit_list = self.data_loader.get_supplement_toolkit()
        toolkit_ids = [ing.ingredient_id for ing in toolkit_list]

        results = []

        # L2 批量计算
        for comb in candidates:
            combo_flat_ingredients = []
            for ing_list in comb.ingredients.values():
                combo_flat_ingredients.extend(ing_list)

            combo_ids = [ing.ingredient_id for ing in combo_flat_ingredients]   
            # 去重
            all_related_ids = list(set(combo_ids + toolkit_ids))

            # B. 调用 Loader 获取矩阵
            # (这里复用你 dataloader 里的 get_nutrition_matrix_for_l2 方法)
            nutrition_matrix, info_df = self.data_loader.get_nutrition_matrix_for_l2(all_related_ids)
            info_df = info_df.set_index('nutrient_id')

            conversion_factors = self.data_loader.get_nutrition_unit_factor(info_df)

            nutrition_matrix.to_csv("clean_matrix.csv")

            l2_input = L2Input(
                pet_profile=pet_profile,
                combination=comb,
                supplement_toolkit=self.data_loader.get_supplement_toolkit(),
                nutrient_matrix=nutrition_matrix,
                nutrient_info=info_df,
                nutrient_conversion_factor=conversion_factors
            )
            
            result = self.l2.optimize(l2_input)

            # 收集成功的解
            if result.status.value == SolveStatus.OPTIMAL.value:
                if self._is_quality_recipe(result):
                    results.append(result)

        # 最终排序
        results = sorted(results, key=lambda x: x.objective_value, reverse=True)

        return results[:top_k]

    def _is_quality_recipe(self, result: OptimizationResult) -> bool:
        """后置校验：虽然数学上可行，但人类看着是否靠谱？"""
        # 比如：补剂总重量不能超过 5%
        total_supp = sum(w.weight_grams for w in result.weights if w.is_supplement)
        if total_supp / result.total_weight_grams > 0.05:
            return False
        return True


def example_basic_usage():
    """示例1: 基础使用"""
    print("=" * 80)
    print("示例1: 基础使用 - 生成标准食谱组合")
    print("=" * 80)
    pet_profile = PetProfile(
        target_calories=1695.9,
        body_weight=30.0,
        life_stage=LifeStage.DOG_ADULT
    )
    
    # 1. 加载数据
    logger.info("步骤1: 从数据库加载食材数据...")
    loader = IngredientDataLoader('postgresql://postgres:Tuantuan_123@127.0.0.1:15432/tuanty_recipe')
    ingredients_df = loader.load_ingredients_for_l1()
    # supplement_toolkit = loader.get_supplement_toolkit()
    logger.info(f"  加载完成! 共 {len(ingredients_df)} 个食材")
    
    # 2. 创建 L1 生成器 (使用默认配置)
    logger.info("步骤2: 创建 L1 生成器...")
    l1_generator = L1RecipeGenerator(ingredients_df)
    
    # 3. 生成组合
    logger.info("步骤3: 生成食材组合...")
    combinations = l1_generator.generate(max_combinations=500)
    logger.info(f"  生成完成! 共 {len(combinations)} 个组合")

    logger.info(f"步骤4: 创建 L2 Optimizer...")
    l2_optimizer = L2Optimizer()

    logger.info(f"步骤5: 创建 Recipe Engine ...")
    recipe_engine = RecipeEngine(loader, l1_generator, l2_optimizer)

    logger.info(f"步骤6: 生成标准食谱...")
    result = recipe_engine.generate_recipes(pet_profile=pet_profile)
    logger.info(f"  生成完成! 共 {len(result)} 个组合")

    # 4. 查看 Top 10 组合
    logger.info("步骤6: 查看 Top 10 组合...")
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

    # from export_combinations import export_combinations_to_csv

    # export_combinations_to_csv(combinations, "combinations.csv", "detailed")
    # print(f"✓ 已导出 {len(combinations)} 个组合!")
    
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
    example_basic_usage()


if __name__ == "__main__":
    main()