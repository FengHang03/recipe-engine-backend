import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple, Union, Any

from app.common.enums import NutrientID, NutrientGroup

@dataclass
class UnitConverter:
    # 定义基础量级 (统一换算为 'g' 或 'IU' 进行中间过渡)
    MAGNITUDE_MAP = {
        'kg': 1000.0,
        'g': 1.0,
        'mg': 0.001,
        'ug': 0.000001,
        'mcg': 0.000001,
        'iu': 1.0,   # IU 不涉及重量换算，保持原样
        'kcal': 1.0
    }
    VITAMIN_CONVERSION_MAP = {
        NutrientID.VITAMIN_A: 0.0003, 
        NutrientID.VITAMIN_D: 0.000025, 
        NutrientID.VITAMIN_E: 0.67,
    }

    @staticmethod
    def parse_unit_string(unit_str: str, default_denom: str = '1000kcal'):
        """
        解析配置字符串，如 "mg/1000kcal" -> ('mg', '1000kcal')
        """
        if '/' in unit_str:
                numerator, denominator = unit_str.split('/', 1)
        else:
            if default_denom == '1000kcal':
                numerator, denominator = unit_str, '1000kcal' # 默认分母 02.09 改
            else:
                numerator, denominator = unit_str, '100g' # 默认分母 02.09 改 

        return numerator.strip().lower(), denominator.strip().lower()

    @classmethod
    def get_unit_factor(cls, nutrient_id: int, nutrient_unit: str, threshold_unit: str, energy_series: pd.Series = None):
        """
        核心函数：计算转换系数
        :param source_unit: 数据的原始单位 (如 'mg')
        :param target_unit_str: 配置的目标单位 (如 'g/1000kcal')
        :param energy_series: 热量列 (kcal/100g)，当目标分母为 kcal 时必须提供
        :return: 一个系数 (float) 或者 一个 Series (向量)
        """
        # 1. 解析目标单位
        threshold_num, _ = cls.parse_unit_string(threshold_unit)
        nut_unit = nutrient_unit.lower().strip()
        threshold_num = threshold_num.lower().strip()

        # 2. 计算【分子】系数 (Magnitude Factor)
        mag_factor = 1.0
        is_vitamin_special = nutrient_id in cls.VITAMIN_CONVERSION_MAP
        # 目标 = 原始 * (原始量级 / 目标量级)
        if is_vitamin_special:
            conversion_rate = cls.VITAMIN_CONVERSION_MAP[nutrient_id]
            # 情况 A: 源是 IU -> 目标是 重量 (mg, ug, g)
            if nut_unit == 'iu' and threshold_num != 'iu':
                weight_adjustment = cls.MAGNITUDE_MAP['mg'] / cls.MAGNITUDE_MAP[threshold_num]
                mag_factor = conversion_rate * weight_adjustment
            
            # 情况 B: 源是 重量 -> 目标是 IU
            elif nut_unit != 'iu' and threshold_num == 'iu':
                source_mag = cls.MAGNITUDE_MAP.get(nut_unit, 1.0)
                to_mg_factor = source_mag / cls.MAGNITUDE_MAP['mg']
                mag_factor = to_mg_factor * (1.0 / conversion_rate)
                
            # 情况 C: 单位相同 (IU -> IU) 或 (mg -> mg)
            elif nut_unit == threshold_num:
                mag_factor = 1.0
            
            # 情况 D: 重量转重量 (Fallback 到下面逻辑)
            elif nut_unit in cls.MAGNITUDE_MAP and threshold_num in cls.MAGNITUDE_MAP:
                mag_factor = cls.MAGNITUDE_MAP[nut_unit] / cls.MAGNITUDE_MAP[threshold_num]

        # --- 普通单位处理 ---
        elif nut_unit in cls.MAGNITUDE_MAP and threshold_num in cls.MAGNITUDE_MAP:
            mag_factor = cls.MAGNITUDE_MAP[nut_unit] / cls.MAGNITUDE_MAP[threshold_num]
        
        # --- 兜底 (Ratio 或 无单位) ---
        else:
            # 如果找不到单位映射，默认返回 1.0 (保持原值)
            mag_factor = 1.0

        return mag_factor

    @classmethod
    def get_base_factor(cls, energy_series: pd.Series, threshold_unit: str) -> pd.Series:
        """
        根据能量列计算基准系数 (向量化版本)
        
        参数:
        energy_series: pd.Series - 包含所有食材每100g能量值的列 (kcal/100g)
        threshold_unit: str - 阈值单位字符串 (如 'mg/1000kcal')
        
        返回:
        pd.Series - 每一行对应的转换系数
        """
        # 1. 解析单位 (提取分母)
        _, threshold_denom = cls.parse_unit_string(threshold_unit)

        # 2. 场景 A: 目标是 /1000kcal (计算密度)
        if '1000kcal' in threshold_denom:
            # 核心逻辑: Factor = 1000 / Energy
            
            # 将 0 替换为 NaN，防止 "ZeroDivisionError" 或产生 "inf" (无穷大)，任何数除以 NaN 还是 NaN
            safe_energy = energy_series.replace(0, np.nan)
            # 向量化除法 (整列一起算，速度极快)
            return 1000.0 / safe_energy

        # 3. 场景 B: 目标是 /100g (无需转换)
        elif '100g' in threshold_denom:
            # 返回一个全是 1.0 的 Series，长度和索引与输入一致
            return pd.Series(1.0, index=energy_series.index)

        # 4. 其他情况 (如 kg)
        else:
            return pd.Series(1.0, index=energy_series.index)

    @classmethod
    def get_base_factor_value(cls, energy_series: float, threshold_unit: str) -> float:
        """
        根据能量列计算基准系数 (向量化版本)
        
        参数:
        energy_series: pd.Series - 包含所有食材每100g能量值的列 (kcal/100g)
        threshold_unit: str - 阈值单位字符串 (如 'mg/1000kcal')
        
        返回:
        pd.Series - 每一行对应的转换系数
        """
        # 1. 解析单位 (提取分母)
        _, threshold_denom = cls.parse_unit_string(threshold_unit)

        # 2. 场景 A: 目标是 /1000kcal (计算密度)
        if '1000kcal' in threshold_denom:
            # 核心逻辑: Factor = 1000 / Energy
            safe_energy = np.nan if energy_series == 0 else energy_series
            
            # 避免除以nan/0导致inf，兜底返回1.0
            if pd.isna(safe_energy) or safe_energy == 0:
                return 1.0
            
            # 计算核心系数：1000 / 热量值
            factor = 1000.0 / safe_energy
            # 防止极端值（如热量值极小导致系数过大），可选限制范围
            return factor if 0 < factor < 1e6 else 1.0

        # 3. 场景 B: 目标是 /100g (无需转换)
        elif '100g' in threshold_denom:
            # 返回一个全是 1.0 的 Series，长度和索引与输入一致
            return 1.0

        # 4. 其他情况 (如 kg)
        else:
            return 1.0
