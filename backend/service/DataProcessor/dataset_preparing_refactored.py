"""
营养数据集处理系统 - 重构版
主要改进：
1. 提取常量到配置类
2. 拆分大函数为小函数
3. 统一错误处理
4. 改进代码注释
"""

import pandas as pd
import numpy as np
import uuid
import re
import logging
from pathlib import Path
from enum import Enum
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field

# ============================================
# 配置和初始化
# ============================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 常量定义
class Constants:
    """系统常量"""
    EPSILON = 1e-6  # 数值比较的极小值
    FAT_LEAN_THRESHOLD = 10.0  # 瘦肉脂肪阈值
    FAT_MODERATE_THRESHOLD = 15.0  # 中脂肉阈值
    DEFAULT_CATEGORY_ID = 999  # 未知分类的默认ID

class TagTypes:
    """标签类型常量"""
    ROLE = 'role'
    RISK = 'risk'
    DIVERSITY = 'diversity'
    REPEAT = 'repeat_policy'
    NOTE = 'note'

# ============================================
# 核心数据类
# ============================================

class NutrientGroup(Enum):
    """营养素分组"""
    PROTEIN = 'protein_amino'
    FAT = 'fat_fatty_acid'
    MINERALS = 'minerals'
    VITAMINS_OTHER = 'vitamins_other'

    @classmethod
    def get_name(cls, group_name: str) -> str:
        try:
            return cls(group_name).name.lower().replace('_', ' ')
        except ValueError:
            return f"ingredient group {group_name}"


class NutrientID:
    """营养素ID定义和管理"""
    
    # 基础营养素
    ENERGY = 1008
    CARBOHYDRATE = 1005
    FIBER = 1079
    PROTEIN = 1003
    FAT = 1004
    
    # 氨基酸
    ARGININE = 1220
    HISTIDINE = 1221
    ISOLEUCINE = 1212
    LEUCINE = 1213
    LYSINE = 1214
    METHIONINE = 1215
    CYSTINE = 1216
    PHENYLALANINE = 1217
    TYROSINE = 1218
    THREONINE = 1211
    TRYPTOPHAN = 1210
    VALINE = 1219
    
    # 脂肪酸
    PUFA_18_2 = 1269
    ALA = 1404
    PUFA_20_4 = 1271
    DHA = 1272
    EPA = 1278
    
    # 矿物质
    CALCIUM = 1087
    PHOSPHORUS = 1091
    POTASSIUM = 1092
    SODIUM = 1093
    CHLORIDE = 1088
    MAGNESIUM = 1090
    IRON = 1089
    COPPER = 1098
    MANGANESE = 1101
    ZINC = 1095
    IODINE = 1100
    SELENIUM = 1103
    
    # 维生素
    VITAMIN_A = 1104
    VITAMIN_D = 1110
    VITAMIN_E = 1109
    THIAMIN = 1165
    RIBOFLAVIN = 1166
    PANTOTHENIC_ACID = 1170
    NIACIN = 1167
    PYRIDOXINE = 1175
    FOLIC_ACID = 1186
    VITAMIN_B12 = 1178
    CHOLINE = 1180
    
    # 分组映射
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
        NutrientGroup.VITAMINS_OTHER: {
            VITAMIN_A, VITAMIN_D, VITAMIN_E, VITAMIN_B12, RIBOFLAVIN, THIAMIN,
            NIACIN, PANTOTHENIC_ACID, PYRIDOXINE, FOLIC_ACID, CHOLINE, FIBER,
            CARBOHYDRATE, ENERGY
        }
    }
    
    # 缓存
    _ID_TO_NAME_CACHE = {}
    _ID_TO_GROUP_CACHE = {}
    _ID_TO_UNIT_CACHE = {}
    
    @classmethod
    def _initialize_caches(cls):
        """初始化缓存"""
        if cls._ID_TO_NAME_CACHE:
            return
        
        # ID -> Name
        for attr, value in cls.__dict__.items():
            if not attr.startswith('_') and isinstance(value, int):
                cls._ID_TO_NAME_CACHE[value] = attr.lower().replace('_', ' ')
        
        # ID -> Group
        for group_enum, ids in cls._GROUPS.items():
            for nid in ids:
                cls._ID_TO_GROUP_CACHE[nid] = group_enum.value
    
    @classmethod
    def load_metadata(cls, nutrient_csv_path: str):
        """从CSV加载营养素元数据"""
        try:
            df = pd.read_csv(nutrient_csv_path, usecols=['nutrient_id', 'name', 'unit_name'])
            df['nutrient_id'] = pd.to_numeric(df['nutrient_id'], errors='coerce').fillna(0).astype(int)
            df = df[df['nutrient_id'] > 0]
            
            def clean_unit(u):
                if not isinstance(u, str):
                    return ''
                u = u.strip()
                return 'IU' if u.upper() == 'IU' else u.lower()
            
            unit_map = dict(zip(df['nutrient_id'], df['unit_name'].apply(clean_unit)))
            cls._ID_TO_UNIT_CACHE.update(unit_map)
            cls._initialize_caches()
            
            logging.info(f"加载营养素元数据: {len(cls._ID_TO_UNIT_CACHE)} 个单位")
        except Exception as e:
            logging.error(f"加载营养素元数据失败: {e}")
            raise
    
    @classmethod
    def get_name(cls, nutrient_id: int) -> str:
        cls._initialize_caches()
        return cls._ID_TO_NAME_CACHE.get(nutrient_id, f"unknown nutrient {nutrient_id}")
    
    @classmethod
    def get_unit(cls, nutrient_id: int) -> str:
        return cls._ID_TO_UNIT_CACHE.get(nutrient_id, '')
    
    @classmethod
    def get_group_map(cls) -> Dict[int, str]:
        cls._initialize_caches()
        return cls._ID_TO_GROUP_CACHE
    
    @classmethod
    def sort_nutrient_ids(cls, id_list: Optional[List[int]] = None) -> List[int]:
        """排序营养素ID，能量和纤维置顶"""
        raw_order = [v for k, v in cls.__dict__.items() 
                     if not k.startswith('_') and isinstance(v, int)]
        
        priority_items = [cls.ENERGY, cls.FIBER]
        base_order = list(priority_items)
        seen = set(priority_items)
        
        for nid in raw_order:
            if nid not in seen:
                base_order.append(nid)
                seen.add(nid)
        
        if id_list is None:
            return base_order
        
        rank_lookup = {nid: i for i, nid in enumerate(base_order)}
        max_rank = len(base_order) + 1
        return sorted(id_list, key=lambda x: rank_lookup.get(x, max_rank + x))


@dataclass
class ThresholdValue:
    """阈值配置"""
    value: float
    unit: str
    
    def __post_init__(self):
        if self.value < 0:
            raise ValueError(f"阈值不能为负数: {self.value}")


@dataclass
class TagRule:
    """标签规则"""
    tag_name: str
    threshold: ThresholdValue
    source_type: str = "DIRECT"
    min_raw_value: float = 0.0
    allowed_categories: Optional[Set[int]] = None
    excluded_categories: Optional[Set[int]] = None
    requires_ca_p_balance: bool = False


@dataclass
class UnitConverter:
    """单位转换工具"""
    
    MAGNITUDE_MAP = {
        'kg': 1000.0,
        'g': 1.0,
        'mg': 0.001,
        'ug': 0.000001,
        'mcg': 0.000001,
        'iu': 1.0,
        'kcal': 1.0
    }
    
    VITAMIN_CONVERSION_MAP = {
        NutrientID.VITAMIN_A: 0.0003,
        NutrientID.VITAMIN_D: 0.000025,
        NutrientID.VITAMIN_E: 0.67,
    }
    
    @staticmethod
    def parse_unit_string(unit_str: str) -> Tuple[str, str]:
        """解析单位字符串，如 'mg/1000kcal' -> ('mg', '1000kcal')"""
        if '/' in unit_str:
            numerator, denominator = unit_str.split('/', 1)
        else:
            numerator, denominator = unit_str, '100g'
        return numerator.strip().lower(), denominator.strip().lower()
    
    @classmethod
    def get_unit_factor(cls, nutrient_id: int, nutrient_unit: str, 
                       threshold_unit: str) -> float:
        """计算单位转换系数"""
        threshold_num, _ = cls.parse_unit_string(threshold_unit)
        nut_unit = nutrient_unit.lower().strip()
        threshold_num = threshold_num.lower().strip()
        
        mag_factor = 1.0
        is_vitamin_special = nutrient_id in cls.VITAMIN_CONVERSION_MAP
        
        if is_vitamin_special:
            conversion_rate = cls.VITAMIN_CONVERSION_MAP[nutrient_id]
            
            if nut_unit == 'iu' and threshold_num != 'iu':
                weight_adjustment = cls.MAGNITUDE_MAP['mg'] / cls.MAGNITUDE_MAP[threshold_num]
                mag_factor = conversion_rate * weight_adjustment
            elif nut_unit != 'iu' and threshold_num == 'iu':
                source_mag = cls.MAGNITUDE_MAP.get(nut_unit, 1.0)
                to_mg_factor = source_mag / cls.MAGNITUDE_MAP['mg']
                mag_factor = to_mg_factor * (1.0 / conversion_rate)
            elif nut_unit == threshold_num:
                mag_factor = 1.0
            elif nut_unit in cls.MAGNITUDE_MAP and threshold_num in cls.MAGNITUDE_MAP:
                mag_factor = cls.MAGNITUDE_MAP[nut_unit] / cls.MAGNITUDE_MAP[threshold_num]
        elif nut_unit in cls.MAGNITUDE_MAP and threshold_num in cls.MAGNITUDE_MAP:
            mag_factor = cls.MAGNITUDE_MAP[nut_unit] / cls.MAGNITUDE_MAP[threshold_num]
        
        return mag_factor
    
    @classmethod
    def get_base_factor(cls, energy_series: pd.Series, threshold_unit: str) -> pd.Series:
        """根据能量计算基准系数"""
        _, threshold_denom = cls.parse_unit_string(threshold_unit)
        
        if '1000kcal' in threshold_denom:
            safe_energy = energy_series.replace(0, np.nan)
            return 1000.0 / safe_energy
        elif '100g' in threshold_denom:
            return pd.Series(1.0, index=energy_series.index)
        else:
            return pd.Series(1.0, index=energy_series.index)


# ============================================
# 标签生成器
# ============================================

class IdentityTagger:
    """食材身份标签生成器"""
    
    # 有毒食材
    TOXIC = re.compile(
        r'\b(grape|raisin|sultana|currant|onion|garlic|leek|chive|chocolate|'
        r'cacao|cocoa|xylitol|alcohol|macadamia|avocado|caffeine|theobromine|hops)\b',
        re.IGNORECASE
    )
    
    # 动物蛋白模式: (正则, diversity标签, repeat标签)
    ANIMAL_PATTERNS = [
        (re.compile(r'\b(rabbit|hare)\b', re.I), "div_protein_exotic", "repeat_rabbit"),
        (re.compile(r'\b(kangaroo|wallaby)\b', re.I), "div_protein_exotic", "repeat_kangaroo"),
        (re.compile(r'\b(venison|deer|elk|moose)\b', re.I), "div_protein_ruminant", "repeat_venison"),
        (re.compile(r'\b(duck)\b', re.I), "div_protein_waterfowl", "repeat_duck"),
        (re.compile(r'\b(goose|geese)\b', re.I), "div_protein_waterfowl", "repeat_goose"),
        (re.compile(r'\b(turkey)\b', re.I), "div_protein_poultry", "repeat_turkey"),
        (re.compile(r'\b(quail)\b', re.I), "div_protein_poultry", "repeat_quail"),
        (re.compile(r'\b(chicken|hen|rooster|broiler|fryer)\b', re.I), "div_protein_poultry", "repeat_chicken"),
        (re.compile(r'\b(egg|yolk|white)\b', re.I), "div_protein_poultry", "repeat_egg"),
        (re.compile(r'\b(beef|cow|veal|calf|ox|bison|buffalo)\b', re.I), "div_protein_ruminant", "repeat_beef"),
        (re.compile(r'\b(lamb|mutton|sheep|goat)\b', re.I), "div_protein_ruminant", "repeat_lamb"),
        (re.compile(r'\b(pork|pig|ham|bacon|swine|boar)\b', re.I), "div_protein_pork", "repeat_pork"),
        (re.compile(r'\b(shrimp|prawn|crab|lobster|crayfish|clam|mussel|oyster|scallop|squid)\b', re.I), 
         "div_protein_shellfish", "repeat_shellfish"),
        (re.compile(r'\b(salmon|trout|sardine|mackerel|herring|cod|tuna|tilapia|pollock|fish|anchovy|catfish|bass|whitefish)\b', re.I), 
         "div_protein_fish", "repeat_fish"),
        (re.compile(r'\b(milk|yogurt|cheese|curd|kefir|whey|casein)\b', re.I), "div_protein_dairy", "repeat_dairy"),
    ]
    
    # 植物模式
    PLANT_PATTERNS = [
        (re.compile(r'\b(rice|oat|barley|quinoa|millet|wheat|corn|sorghum)\b', re.I), 
         "div_carb_grain", "repeat_grain"),
        (re.compile(r'\b(lentil|bean|pea|chickpea|soy|tofu|edamame)\b', re.I), 
         "div_plant_legume", "repeat_legume"),
        (re.compile(r'\b(blueberry|cranberry|strawberry|raspberry|blackberry)\b', re.I), 
         "div_plant_berry", "repeat_berry"),
        (re.compile(r'\b(broccoli|cauliflower|brussels sprout|kale|cabbage|bok choy|collard|mustard greens)\b', re.I), 
         "div_plant_cruciferous", "repeat_cruciferous"),
        (re.compile(r'\b(spinach|lettuce|chard|greens|arugula)\b', re.I), 
         "div_plant_leafy", "repeat_leafy"),
        (re.compile(r'\b(carrot|pumpkin|sweet\s?potato|squash|papaya|tomato|watermelon|cantaloupe|apricot)\b|pepper.*(red|orange|bell)', re.I), 
         "div_plant_orange", "repeat_color_orange"),
    ]
    
    @staticmethod
    def get_tags(description: str, category_id: int) -> Tuple[str, str]:
        """
        生成identity标签
        返回: (diversity_tags_str, repeat_tags_str)
        """
        div_tags, rep_tags = set(), set()
        desc = str(description)
        
        # 动物蛋白类别
        if category_id in [1, 5, 7, 10, 13, 15, 17]:
            for pattern, div, rep in IdentityTagger.ANIMAL_PATTERNS:
                if pattern.search(desc):
                    div_tags.add(div)
                    rep_tags.add(rep)
            
            # 兜底逻辑
            if not div_tags:
                fallback_map = {
                    10: ("div_protein_pork", "repeat_pork"),
                    13: ("div_protein_ruminant", "repeat_beef"),
                    5: ("div_protein_poultry", "repeat_poultry"),
                    1: ("div_protein_dairy", "repeat_dairy"),
                    15: ("div_protein_fish", "repeat_fish"),
                }
                if category_id in fallback_map:
                    div, rep = fallback_map[category_id]
                    div_tags.add(div)
                    rep_tags.add(rep)
        
        # 植物类别
        elif category_id in [9, 11, 12, 16, 20]:
            for pattern, div, rep in IdentityTagger.PLANT_PATTERNS:
                if pattern.search(desc):
                    div_tags.add(div)
                    rep_tags.add(rep)
            
            # 兜底逻辑
            if not div_tags:
                fallback_map = {
                    11: "div_plant_other",
                    9: "div_plant_fruit",
                    20: "div_carb_grain",
                    16: "div_plant_legume",
                }
                if category_id in fallback_map:
                    div_tags.add(fallback_map[category_id])
                    if category_id in [20, 16]:
                        rep_tags.add("repeat_grain" if category_id == 20 else "repeat_legume")
        
        return ",".join(sorted(div_tags)), ",".join(sorted(rep_tags))


# ============================================
# 配置类
# ============================================

@dataclass
class AutoTagConfig:
    """自动标签配置"""
    
    ca_p_ratio_threshold: float = 1.5
    
    # Role规则
    role_rules: Dict[int, List[TagRule]] = field(default_factory=lambda: {
        NutrientID.PUFA_18_2: [TagRule("role_omega6_la", ThresholdValue(4000.0, "mg/1000kcal"))],
        NutrientID.ALA: [TagRule("role_omega3_ala", ThresholdValue(200.0, "mg/1000kcal"))],
        NutrientID.EPA: [TagRule("role_omega3_lc", ThresholdValue(800.0, "mg/1000kcal"), source_type="SUM_EPA_DHA")],
        NutrientID.CALCIUM: [TagRule("role_calcium", ThresholdValue(3000.0, "mg/100g"))],
        NutrientID.IRON: [TagRule("role_iron", ThresholdValue(20.0, "mg/1000kcal"))],
        NutrientID.ZINC: [TagRule("role_zinc", ThresholdValue(30.0, "mg/1000kcal"))],
        NutrientID.IODINE: [TagRule("role_iodine", ThresholdValue(0.5, "mg/1000kcal"))],
        NutrientID.FIBER: [TagRule("role_fiber_source", ThresholdValue(3.0, "g/1000kcal"))],
        NutrientID.THIAMIN: [TagRule("role_vit_b1", ThresholdValue(1.5, "mg/1000kcal"))],
        NutrientID.VITAMIN_B12: [TagRule("role_vit_b12", ThresholdValue(20.0, "μg/1000kcal"))],
        NutrientID.CHOLINE: [TagRule("role_choline", ThresholdValue(1000.0, "mg/1000kcal"))],
        NutrientID.VITAMIN_A: [TagRule("role_vita", ThresholdValue(5000.0, "IU/1000kcal"))],
        NutrientID.VITAMIN_D: [TagRule("role_vitd", ThresholdValue(250.0, "IU/1000kcal"))],
    })
    
    # Risk规则
    risk_rules: Dict[int, List[TagRule]] = field(default_factory=lambda: {
        NutrientID.COPPER: [TagRule("risk_high_copper", ThresholdValue(10.0, "mg/1000kcal"))],
        NutrientID.IODINE: [TagRule("risk_high_iodine", ThresholdValue(5.0, "mg/1000kcal"))],
        NutrientID.SELENIUM: [TagRule("risk_high_selenium", ThresholdValue(0.6, "mg/1000kcal"))],
        NutrientID.SODIUM: [TagRule("risk_high_sodium", ThresholdValue(1500.0, "mg/1000kcal"))],
        NutrientID.VITAMIN_A: [TagRule("risk_high_vit_a", ThresholdValue(30000.0, "IU/1000kcal"))],
        NutrientID.VITAMIN_D: [TagRule("risk_high_vit_d", ThresholdValue(750.0, "IU/1000kcal"))],
    })
    
    def get_ca_p_threshold(self) -> float:
        return self.ca_p_ratio_threshold


# ============================================
# 辅助函数
# ============================================

def clean_tags(tag_str: str) -> str:
    """清洗标签字符串：去重、排序"""
    if not isinstance(tag_str, str) or not tag_str:
        return ""
    tags = [t.strip() for t in tag_str.split(',') if t.strip()]
    return ",".join(sorted(set(tags)))


def validate_dataframe(df: pd.DataFrame, required_cols: List[str], name: str = "DataFrame"):
    """验证DataFrame必需列"""
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"{name} 缺少必需列: {missing}")
    
    if df.empty:
        raise ValueError(f"{name} 为空")


# 此处省略其他辅助函数的实现，保持与原代码相同
# 包括: _get_short_name, _infer_food_category, _get_food_subgroup 等