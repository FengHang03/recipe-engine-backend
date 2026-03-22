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

@dataclass
class NutrientID:
    """营养素ID常量定义"""
    ENERGY          = 1008  # 能量 (kcal)
    CARBOHYDRATE    = 1005  # 碳水化合物 (g)
    FIBER           = 1079  # 纤维 (g)
    # WATER = 1051          # 水分 (g)

    PROTEIN         = 1003  # 蛋白质 (g)
    ARGININE        = 1220  # 精氨酸 (g)
    HISTIDINE       = 1221  # 组氨酸 (g)
    ISOLEUCINE      = 1212  # 异亮氨酸 (g)
    LEUCINE         = 1213  # 亮氨酸 (g)
    LYSINE          = 1214  # 赖氨酸 (g)
    METHIONINE      = 1215  # 肌氨酸 (g)
    CYSTINE         = 1216  # 胱氨酸 (g)
    PHENYLALANINE   = 1217  # 苯丙氨酸 (g)
    TYROSINE        = 1218  # 酪氨酸 (g)
    THREONINE       = 1211  # 苏氨酸 (g)
    TRYPTOPHAN      = 1210  # 色氨酸 (g)
    VALINE          = 1219  # 缬氨酸 (g)
    
    FAT             = 1004  # 脂肪 (g)
    # LA = 1316             # 亚油酸 (g) PUFA 18:2 n-6 c,c
    PUFA_18_2       = 1269  # PUFA 18:2 n-6 c,c
    ALA             = 1404  # α-亚麻酸 (g) PUFA 18:3 n-3 c,c,c (ALA)
    # PUFA_18_3 = 1270      # PUFA 18:3 if no data in 1404
    PUFA_20_4       = 1271  # PUFA 20:4 Arachidonic
    DHA             = 1272  # 二十二碳六烯酸 (g)
    EPA             = 1278  # 二十碳五烯酸 (g)

    CALCIUM          = 1087 # 钙 (mg)
    PHOSPHORUS       = 1091 # 磷 (mg)
    POTASSIUM        = 1092 # 钾 (mg)
    SODIUM           = 1093 # 钠 (mg)
    CHLORIDE         = 1088 # 氯 (mg)
    MAGNESIUM        = 1090 # 镁 (mg)
    IRON             = 1089 # 铁 (mg)
    COPPER           = 1098 # 铜 (mg)
    MANGANESE        = 1101 # 锰 (mg)
    ZINC             = 1095 # 锌 (mg)
    IODINE           = 1100 # 碘 (μg)
    SELENIUM         = 1103 # 硒 (μg)

    VITAMIN_A        = 1104 # 维生素A (IU)
    VITAMIN_D        = 1110 # 维生素D (IU)
    VITAMIN_E        = 1109 # 维生素E (mg)
    THIAMIN          = 1165 # 硫胺素 (mg)
    RIBOFLAVIN       = 1166 # 核黄素 (mg)
    PANTOTHENIC_ACID = 1170 # 泛酸 (mg)
    NIACIN           = 1167 # 烟酸 (mg)
    PYRIDOXINE       = 1175 # 吡哆醇 (mg) Vitamin B-6
    FOLIC_ACID       = 1186 # 叶酸 (μg)
    VITAMIN_B12      = 1178 # 维生素B12 (μg)
    CHOLINE          = 1180 # 胆碱 (mg)

    # === 2. 定义分组映射 使用 Set 提高查找速度 ===
    _GROUPS = {
        NutrientGroup.PROTEIN: {
            ARGININE, HISTIDINE, ISOLEUCINE, LEUCINE, LYSINE, METHIONINE, CYSTINE,
            PHENYLALANINE, TYROSINE, THREONINE, TRYPTOPHAN, VALINE, PROTEIN
        },
        NutrientGroup.FAT: {
            PUFA_18_2, ALA, PUFA_20_4, DHA, EPA, FAT
        },
        NutrientGroup.MINERALS: {
            CALCIUM, PHOSPHORUS, POTASSIUM, SODIUM, CHLORIDE, MAGNESIUM, IRON, 
            COPPER, MANGANESE, ZINC, IODINE, SELENIUM
        },
        # VITAMINS_OTHER 可以作为 fallback，或者显式定义
        # 这里为了演示，显式定义一部分，逻辑中处理剩余的
        NutrientGroup.VITAMINS_OTHER: {
            VITAMIN_A, VITAMIN_D, VITAMIN_E, VITAMIN_B12, RIBOFLAVIN, THIAMIN, 
            NIACIN, PANTOTHENIC_ACID, PYRIDOXINE, FOLIC_ACID, CHOLINE, FIBER, 
            CARBOHYDRATE, ENERGY
        }
    }

    # === 3. 缓存 (性能优化) ===
    _ID_TO_NAME_CACHE = {}
    _ID_TO_GROUP_CACHE = {}
    _ID_TO_UNIT_CACHE = {}

    @classmethod
    def _initialize_caches(cls):
        """initialization caches"""
        if cls._ID_TO_NAME_CACHE:
            return

        # 1. ID -> Name
        for attr, value in cls.__dict__.items():
            if not attr.startswith('__') and isinstance(value, int):
                cls._ID_TO_NAME_CACHE[value] = attr.lower().replace('_', ' ')
        # 2. ID -> Group Name
        for group_enum, ids in cls._GROUPS.items():
            for nid in ids:
                cls._ID_TO_GROUP_CACHE[nid] = group_enum.value

    @classmethod
    def load_metadata(cls, nutrient_csv_path: str):
        """load data from 'nutrient_new.csv' """
        try:
            # 读取 CSV
            df = pd.read_csv(nutrient_csv_path, usecols=['nutrient_id', 'name', 'unit_name'])
            
            # 清洗数据：确保 ID 是 int
            df['nutrient_id'] = pd.to_numeric(df['nutrient_id'], errors='coerce').fillna(0).astype(int)
            df = df[df['nutrient_id'] > 0]

            # 1. 填充 ID -> Name 缓存 (如果你想用 CSV 里的名字而不是代码里的变量名)
            # cls._ID_TO_NAME_CACHE = dict(zip(df['nutrient_id'], df['name']))
            
            # 2. 填充 ID -> Unit 缓存
            # 这里的逻辑是做一些标准化，比如 'MG' -> 'mg', 'IU' -> 'IU'
            def clean_unit(u):
                if not isinstance(u, str): return ''
                u = u.strip()
                if u.upper() == 'IU': return 'IU'
                return u.lower() # 其他的转小写，如 kcal, g, mg, ug

            unit_map = dict(zip(df['nutrient_id'], df['unit_name'].apply(clean_unit)))
            cls._ID_TO_UNIT_CACHE.update(unit_map)
            
            # 初始化原有缓存（代码中定义的常量名）
            cls._initialize_caches()
            
            print(f"Nutrient metadata loaded: {len(cls._ID_TO_UNIT_CACHE)} units.")

        except Exception as e:
            print(f"Error loading nutrient metadata: {e}")
            raise e 

    @classmethod
    def get_group_map(cls) -> Dict[int, str]:
        cls._initialize_caches()
        return cls._ID_TO_GROUP_CACHE

    @classmethod
    def get_name(cls, nutrient_id: int) -> str:
        """根据ID获取营养素名称"""
        cls._initialize_caches()
        return cls._ID_TO_NAME_CACHE.get(nutrient_id, f"unknown nutrient {nutrient_id}")

    @classmethod
    def get_unit(cls, nutrient_id: int) -> str:
        return cls._ID_TO_UNIT_CACHE.get(nutrient_id, '')

    @classmethod
    def _get_defined_ids_in_order(cls) -> List[int]:
        """acquire all ID and align to the order of NutrientID"""
        return [
            v for k, v in cls.__dict__.items() if not k.startswith('__') and isinstance(v, int)
        ]
    
    @classmethod
    def sort_nutrient_ids(cls, id_list: Optional[List[int]] = None) -> List[int]:
        raw_order = cls._get_defined_ids_in_order()
        
        # 置顶逻辑
        priority_items = [cls.ENERGY, cls.FIBER]
        
        # 构建基础顺序列表
        base_order = list(priority_items)
        seen = set(priority_items)
        
        for nid in raw_order:
            if nid not in seen:
                base_order.append(nid)
                seen.add(nid)

        if id_list is None:
            return base_order

        # 优化排序查找速度
        rank_lookup = {nid: i for i, nid in enumerate(base_order)}
        
        # 将未知ID排在最后
        max_rank = len(base_order) + 1
        
        return sorted(id_list, key=lambda x: rank_lookup.get(x, max_rank + x)) # 未知ID按大小排

    @classmethod
    def get_ranked_map(cls, start_index: int = 1) -> Dict[int, int]:
        ordered_ids = cls.sort_nutrient_ids()
        return {nid: i + start_index for i, nid in enumerate(ordered_ids)}