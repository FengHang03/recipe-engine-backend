from typing import Dict, Optional, Tuple
from enum import Enum as PyEnum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

class Species(str, PyEnum):
    DOG = "dog"
    CAT = "cat"

class LifeStage(str, PyEnum):
    DOG_PUPPY = "dog_puppy"
    DOG_ADULT = "dog_adult"
    DOG_SENIOR = "dog_senior"
    CAT_KITTEN = "cat_kitten"
    CAT_ADULT = "cat_adult"
    CAT_SENIOR = "cat_senior"

class ActivityLevel(str,PyEnum):
    SEDENTARY = "sedentary"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"

class ReproductiveStatus(str, PyEnum):
    INTACT = "intact"
    NEUTERED = "neutered"

class ReproState(str, PyEnum):
    NONE = "none"
    PREGNANT = "pregnant"
    LACTATING = "lactating"

class EnergyConstants:
    # RER 基础系数
    RER_BASE_COEFFICIENT = 70
    RER_EXPONENT = 0.75
    
    # 生命阶段系数
    PUPPY_EARLY_FACTOR = 3.0    # 0-4月幼犬
    PUPPY_LATE_FACTOR = 3.0     # 5-12月幼犬
    KITTEN_FACTOR = 2.5         # 0-12月幼猫
    ADULT_FACTOR = 1.0          # 成年
    
    # 活动系数
    ACTIVITY_FACTORS = {
        ActivityLevel.SEDENTARY: 1.4,   # 降低基础值
        ActivityLevel.LOW: 1.6,
        ActivityLevel.MODERATE: 1.8,
        ActivityLevel.HIGH: 2.0,
        ActivityLevel.EXTREME: 2.2
    }
    
    # 生理状态调整
    NEUTERED_REDUCTION = 0.2      # 绝育后能量需求降低
    SENIOR_REDUCTION = 0.2        # 老年宠物能量需求降低
    
    # 怀孕期系数
    PREGNANT_BASE_FACTOR = 1.8    # 基础怀孕系数
    PREGNANT_WEIGHT_COEFFICIENT = 26  # 体重相关增量
    
    # 哺乳期系数
    LACTATION_BASE_MULTIPLIER = 145  # 基础系数
    LACTATION_PER_PUPPY_BASE = 24    # 每只幼崽基础需求
    LACTATION_PER_PUPPY_EXTRA = 12   # 超过4只后每只额外需求
    
    # 哺乳周数系数
    LACTATION_WEEK_FACTORS = {
        1: 0.75,
        2: 0.95,
        3: 1.1,
        4: 1.2,
    }
    
    # 年龄边界（月）
    DOG_PUPPY_EARLY_MAX = 4
    DOG_PUPPY_MAX = 12
    CAT_KITTEN_MAX = 12
    DEFAULT_SENIOR_AGE = 84  # 7岁
    
    # 品种体型系数（可选）
    BREED_SIZE_FACTORS = {
        'toy': 0.95,        # 玩具犬（<5kg）
        'small': 1.0,       # 小型犬（5-10kg）
        'medium': 1.0,      # 中型犬（10-25kg）
        'large': 1.05,      # 大型犬（25-45kg）
        'giant': 1.1        # 巨型犬（>45kg）
    }

@dataclass
class EnergyCalculationResult:
    """能量计算结果"""
    resting_energy_kcal: float
    daily_energy_kcal: float
    life_stage: str
    model_version: str
    calculation_breakdown: Dict[str, float]  # 计算过程分解
    warnings: list[str]  # 警告信息

class EnergyCalculator:
    """宠物能量需求计算器"""
    VERSION = "EnergyCalculator-v0.2"

    @staticmethod
    def calculate_resting_energy_requirement(weight_kg: float) -> float:
        """
        计算静息能量需求 (RER)
        
        Args:
            weight_kg: 体重（公斤）
            
        Returns:
            RER（千卡/天）
            
        Raises:
            ValueError: 体重无效
        """
        if weight_kg <= 0:
            raise ValueError("The weight of pets must be greater than 0")
        if weight_kg > 50:
            logger.warning(f"Recipe are not available for pets over 50 kg")

        # RER = 70 × (体重kg)^0.75
        rer = EnergyConstants.RER_BASE_COEFFICIENT * (
            weight_kg ** EnergyConstants.RER_EXPONENT
        )
        
        return rer
    
    @staticmethod
    def get_activity_factor(age_months: int, activity_level: ActivityLevel, is_young: bool) -> float:
        """
        获取活动系数
        
        Args:
            age_months: 年龄（月）
            activity_level: 活动水平
            is_young: 是否为幼年动物
            
        Returns:
            活动系数
        """
        base_factor = EnergyConstants.ACTIVITY_FACTORS[activity_level]
        
        # 幼年动物的生命阶段系数已经包含了高能量需求
        # 所以活动系数应该降低，避免重复计算
        if is_young:
            # 幼年动物已有 2.5-3.0 的生命阶段系数
            # 活动系数只做微调：0.9-1.1
            adjustment = (base_factor - 1.8) * 0.25  # 将1.2-2.0压缩到±0.1范围
            return 1.0 + adjustment
        
        return base_factor
    
    @staticmethod
    def get_life_stage_factor(species: Species, age_months: int) -> tuple[float, LifeStage]:
        """
        获取生命阶段系数和阶段名称
        
        Args:
            species: 物种
            age_months: 年龄（月）
            
        Returns:
            (系数, 生命阶段)
        """
        
        if species == Species.DOG:
            if age_months < EnergyConstants.DOG_PUPPY_EARLY_MAX:
                return (
                    EnergyConstants.PUPPY_EARLY_FACTOR, 
                    LifeStage.DOG_PUPPY
                ) # 幼犬需要更多能量
            elif age_months < EnergyConstants.DOG_PUPPY_MAX:
                return (
                    EnergyConstants.PUPPY_LATE_FACTOR, 
                    LifeStage.DOG_PUPPY
                )
            elif age_months > EnergyConstants.DEFAULT_SENIOR_AGE:
                return (
                    EnergyConstants.ADULT_FACTOR, 
                    LifeStage.DOG_SENIOR
                )
            else:
                return (
                    EnergyConstants.ADULT_FACTOR, 
                    LifeStage.DOG_ADULT
                )
        
        else:  # CAT
            if age_months <= EnergyConstants.CAT_KITTEN_MAX:
                return (
                    EnergyConstants.KITTEN_FACTOR, 
                    LifeStage.CAT_KITTEN
                )
            elif age_months > EnergyConstants.DEFAULT_SENIOR_AGE:
                return (
                    EnergyConstants.ADULT_FACTOR, 
                    LifeStage.CAT_SENIOR
                )
            else:
                return (
                    EnergyConstants.ADULT_FACTOR, 
                    LifeStage.CAT_ADULT
                )
    
    @staticmethod
    def get_lactation_factor(lactation_week: int) -> float:
        """
        获取哺乳周数系数
        
        Args:
            lactation_week: 哺乳周数（1-8）
            
        Returns:
            哺乳系数
            
        Raises:
            ValueError: 周数无效
        """
        if lactation_week < 1 or lactation_week > 8:
            raise ValueError(
                f"哺乳周数必须在1-8之间，当前值: {lactation_week}"
            )
        
        return EnergyConstants.LACTATION_WEEK_FACTORS.get(
            lactation_week, 
            0.75  # 默认值
        )

    @staticmethod
    def get_breed_size_factor(weight_kg: float, breed: Optional[str] = None) -> float:
        """
        根据品种或体重获取体型系数
        
        Args:
            weight_kg: 体重
            breed: 品种（可选）
            
        Returns:
            体型系数
        """
        if breed and breed in EnergyConstants.BREED_SIZE_FACTORS:
            return EnergyConstants.BREED_SIZE_FACTORS[breed]
        
        # 根据体重推断体型
        if weight_kg < 5:
            return EnergyConstants.BREED_SIZE_FACTORS['toy']
        elif weight_kg < 10:
            return EnergyConstants.BREED_SIZE_FACTORS['small']
        elif weight_kg < 25:
            return EnergyConstants.BREED_SIZE_FACTORS['medium']
        elif weight_kg < 45:
            return EnergyConstants.BREED_SIZE_FACTORS['large']
        else:
            return EnergyConstants.BREED_SIZE_FACTORS['giant']

    @classmethod
    def calculate_daily_energy_requirement(cls, 
                                         weight_kg: float,
                                         species: Species,
                                         age_months: int,
                                         activity_level: ActivityLevel,
                                         reproductive_status: ReproductiveStatus,
                                         repro_state: ReproState,
                                         breed: Optional[str] = None,
                                         lactation_week: Optional[int] = 4,
                                         nursing_count: Optional[int] = 1,
                                         senior_month: Optional[int] = 84,
                                         energy_requirement: float = None) -> EnergyCalculationResult:
        """
        计算每日能量需求（改进版）

        Args:
            weight_kg: 体重（公斤）
            species: 物种
            age_months: 年龄（月）
            activity_level: 活动水平
            reproductive_status: 绝育状态
            repro_state: 怀孕状态
            breed: 品种（可选）
            lactation_week: 哺乳周数（1-8）
            nursing_count: 哺乳幼崽数量
            senior_month: 老年起始月龄
            energy_requirement: 手动指定能量需求（可选）
            
        Returns:
            EnergyCalculationResult
            
        Raises:
            ValueError: 参数无效
        """
        warnings = []
        breakdown = {}

        try:
            # ========== 1. 输入验证 ==========
            if weight_kg <= 0:
                raise ValueError(f"体重必须大于0，当前值: {weight_kg}")

            if age_months < 0:
                raise ValueError(f"年龄不能为负数，当前值: {age_months}")
            
            if weight_kg < 0.5:
                warnings.append(f"体重过小({weight_kg}kg)，计算结果可能不准确")

            if weight_kg > 100:
                warnings.append(f"体重过大({weight_kg}kg)，请确认是否正确")
            
            # ========== 2. 计算 RER ==========
            rer = cls.calculate_resting_energy_requirement(weight_kg)
            breakdown['rer'] = round(rer, 2)

            # ========== 3. 获取生命阶段信息 ==========
            life_stage_factor, life_stage = cls.get_life_stage_factor(
                species, 
                age_months
            )
            breakdown['life_stage_factor'] = life_stage_factor
            
            is_young = life_stage in [
                LifeStage.DOG_PUPPY, 
                LifeStage.CAT_KITTEN
            ]

            if is_young and repro_state in [
                ReproState.PREGNANT, 
                ReproState.LACTATING
            ]:
                warning_msg = (
                    f"Pet cub ({age_months}month-old, {life_stage.value}) "
                    f"Should not be in {repro_state.value} state. "
                    f"Calculate the required energy based on normal conditions."
                )
                warnings.append(f"Pet cub should not be in {repro_state.value} state, calculate the required energy based on normal conditions.")
                logging.warning(warning_msg)

                # 2. 重置生理状态为正常
                repro_state = ReproState.NONE
            
            # ========== 4. 如果手动指定能量需求 ==========
            if energy_requirement is not None:
                if energy_requirement <= 0:
                    raise ValueError(
                        f"手动指定的能量需求必须大于0，"
                        f"当前值: {energy_requirement}"
                    )

                return EnergyCalculationResult(
                    resting_energy_kcal=round(rer, 1),
                    daily_energy_kcal=round(energy_requirement, 1),
                    life_stage=life_stage.value,
                    model_version=cls.VERSION,
                    calculation_breakdown={
                        'rer': round(rer, 2),
                        'manual_override': round(energy_requirement, 2)
                    },
                    warnings=['使用手动指定的能量需求']
                )
            ## ========== 5. 计算基础 DER ==========
            base_der = life_stage_factor * rer # life stage factor * 70 * BW **0.75
            breakdown['base_der'] = round(base_der, 2)

            # ========== 6. 根据生理状态调整 ==========
            if not is_young and repro_state == ReproState.PREGNANT:
                # ✅ 修复：基于基础 DER 而不是覆盖
                pregnancy_multiplier = EnergyConstants.PREGNANT_BASE_FACTOR # 1.8
                pregnancy_addition = EnergyConstants.PREGNANT_WEIGHT_COEFFICIENT * weight_kg # 26 * BW
                
                der = base_der * pregnancy_multiplier + pregnancy_addition
                
                breakdown['pregnancy_multiplier'] = pregnancy_multiplier
                breakdown['pregnancy_addition'] = round(pregnancy_addition, 2)
                breakdown['der_after_pregnancy'] = round(der, 2)
                    
            elif not is_young and repro_state == ReproState.LACTATING:
                lactation_factor = cls.get_lactation_factor(lactation_week)
                
                # ✅ 修复：基于基础 DER 而不是覆盖
                base_lactation = EnergyConstants.LACTATION_BASE_MULTIPLIER * (
                    weight_kg ** EnergyConstants.RER_EXPONENT
                )
                
                if nursing_count <= 4:
                    puppy_energy = weight_kg * (
                        EnergyConstants.LACTATION_PER_PUPPY_BASE * nursing_count
                    )
                else:
                    puppy_energy = weight_kg * (
                        96 + EnergyConstants.LACTATION_PER_PUPPY_EXTRA * (
                            nursing_count - 4
                        )
                    )
                
                # 考虑生命阶段的基础需求
                der = base_lactation + puppy_energy * lactation_factor
                
                breakdown['lactation_factor'] = lactation_factor
                breakdown['lactation_week'] = lactation_week
                breakdown['nursing_count'] = nursing_count
                breakdown['puppy_energy'] = round(puppy_energy, 2)
                breakdown['der_after_lactation'] = round(der, 2)
                    
            else:
                # ✅ 改进：幼年动物也应用活动系数，但调整范围
                activity_factor = cls.get_activity_factor(
                    age_months, 
                    activity_level, 
                    is_young
                )
                
                breakdown['activity_factor_base'] = activity_factor
                
                # 绝育调整
                if reproductive_status == ReproductiveStatus.NEUTERED:
                    activity_factor = max(
                        1.0, 
                        activity_factor - EnergyConstants.NEUTERED_REDUCTION
                    )
                    breakdown['neutered_adjustment'] = -EnergyConstants.NEUTERED_REDUCTION
                
                # 老年调整
                if age_months > senior_month:
                    activity_factor = max(
                        1.0, 
                        activity_factor - EnergyConstants.SENIOR_REDUCTION
                    )
                    breakdown['senior_adjustment'] = -EnergyConstants.SENIOR_REDUCTION
                    warnings.append(f"老年宠物（{age_months}月龄），能量需求降低")
                
                breakdown['activity_factor_final'] = activity_factor
                
                # 品种体型调整
                breed_factor = cls.get_breed_size_factor(weight_kg, breed)
                breakdown['breed_factor'] = breed_factor
                
                der = base_der * activity_factor * breed_factor
                breakdown['der_final'] = round(der, 2)

            # ========== 7. 返回结果 ==========
            return EnergyCalculationResult(
                resting_energy_kcal=round(rer, 1),
                daily_energy_kcal=round(der, 1),
                life_stage=life_stage.value,
                model_version=cls.VERSION,
                calculation_breakdown=breakdown,
                warnings=warnings
            )
        
        except ValueError as e:
            logger.error(f"能量计算参数错误: {e}")
            raise
        
        except Exception as e:
            logger.error(f"能量计算失败: {e}", exc_info=True)
            raise RuntimeError(f"能量计算过程中发生错误: {str(e)}") from e
