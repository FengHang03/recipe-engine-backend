from unicodedata import category
from sqlalchemy.sql.functions import rank
import pandas as pd
import numpy as np
import uuid
import re
import math
import datetime
import logging
from pathlib import Path
from enum import Enum, unique
from typing import List, Dict, Set, Optional, Tuple, Union, Any
from dataclasses import dataclass, field

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TAG_TYPES = {
    'ROLE': 'role',
    'RISK': 'risk',
    'DIVERSITY': 'diversity',
    'REPEAT': 'repeat_policy',
    'NOTE': 'note'
}

RISK_TAGS = [
    'risk_calcium',
    'risk_phosphorus',
    'risk_iodine',
    'risk_vit_a',
    'risk_vit_d',
]

class NutrientGroup(Enum):
    PROTEIN = 'protein_amino'
    FAT = 'fat_fatty_acid'
    MINERALS = 'minerals'
    VITAMINS_OTHER = 'vitamins_other'

    @classmethod
    def get_name(cls, group_name: str) -> str:
        """根据名称获取营养素组名称"""
        try:
            return cls(group_name).name.lower().replace('_', ' ')
        except ValueError:
            return f"ingredient group {group_name}"

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

class IdentityTagger:
    """
    负责基于文本描述和分类ID生成 Diversity, Repeat 和 Safety 标签
    """
    # --- 安全黑名单 (Safety Blacklist) ---
    TOXIC = re.compile(r'\b(grape|raisin|sultana|currant|onion|garlic|leek|chive|chocolate|cacao|cocoa|xylitol|alcohol|macadamia|avocado|caffeine|theobromine|hops)\b', re.IGNORECASE)

    ORGAN_PATTERNS = [

    ]
    # --- 1. 动物蛋白正则 (Tuple: Regex, Div_Tag, Repeat_Base) ---
    ANIMAL_PATTERNS = [
        # 特种/低敏
        (re.compile(r'\b(rabbit|hare)\b', re.IGNORECASE), "div_protein_exotic", "repeat_rabbit"),
        (re.compile(r'\b(kangaroo|wallaby)\b', re.IGNORECASE), "div_protein_exotic", "repeat_kangaroo"),
        (re.compile(r'\b(venison|deer|elk|moose)\b', re.IGNORECASE), "div_protein_ruminant", "repeat_venison"),
        # 水禽
        (re.compile(r'\b(duck)\b', re.IGNORECASE), "div_protein_waterfowl", "repeat_duck"),
        (re.compile(r'\b(goose|geese)\b', re.IGNORECASE), "div_protein_waterfowl", "repeat_goose"),
        # 陆禽
        (re.compile(r'\b(turkey)\b', re.IGNORECASE), "div_protein_poultry", "repeat_turkey"),
        (re.compile(r'\b(quail)\b', re.IGNORECASE), "div_protein_poultry", "repeat_quail"),
        (re.compile(r'\b(chicken|hen|rooster|broiler|fryer)\b', re.IGNORECASE), "div_protein_poultry", "repeat_chicken"),
        (re.compile(r'\b(egg|yolk|white)\b', re.IGNORECASE), "div_protein_poultry", "repeat_egg"),
        # 反刍
        (re.compile(r'\b(beef|cow|veal|calf|ox|bison|buffalo)\b', re.IGNORECASE), "div_protein_ruminant", "repeat_beef"),
        (re.compile(r'\b(lamb|mutton|sheep|goat)\b', re.IGNORECASE), "div_protein_ruminant", "repeat_lamb"),
        # 猪
        (re.compile(r'\b(pork|pig|ham|bacon|swine|boar)\b', re.IGNORECASE), "div_protein_pork", "repeat_pork"),
        # 海鲜 (补充了 anchovy, catfish, bass)
        (re.compile(r'\b(shrimp|prawn|crab|lobster|crayfish|clam|mussel|oyster|scallop|squid)\b', re.IGNORECASE), "div_protein_shellfish", "repeat_shellfish"),
        (re.compile(r'\b(salmon|trout|sardine|mackerel|herring|cod|tuna|tilapia|pollock|fish|anchovy|catfish|bass|whitefish)\b', re.IGNORECASE), "div_protein_fish", "repeat_fish"),
        # 乳制品 (新增) - 归类为 animal_product 但通常作为 booster
        (re.compile(r'\b(milk|yogurt|cheese|curd|kefir|whey|casein)\b', re.IGNORECASE), "div_protein_dairy", "repeat_dairy"),
    ]

    # --- 2. 植物正则 ---
    PLANT_PATTERNS = [
        # --- 谷物 (Grains) ---
        # 匹配常见谷物：大米、燕麦、大麦、藜麦、小米、小麦、玉米、高粱、黑麦、荞麦
        (re.compile(r'\b(rice|oat[s]?|barley|quinoa|millet|wheat|corn|sorghum|rye|buckwheat)\b', re.IGNORECASE),
        "div_carb_grain", "repeat_grain"),
        # --- 豆类 (Legumes) ---
        # 匹配干豆类：扁豆、豌豆、鹰嘴豆、大豆、豆腐、毛豆
        # 注意：排除了 'green bean' (四季豆)，它通常被视为绿色蔬菜而不是淀粉豆类
        (re.compile(r'\b(lentil[s]?|bean[s]?(?!.*green)|pea[s]?(?!.*pod)|chickpea[s]?|soy|tofu|edamame|garbanzo[s]?|fava[s]?)\b', re.IGNORECASE),
        "div_carb_legume", "repeat_legume"),
        # 2. 功能性纤维 (Functional Fibers)
        # 匹配：车前子、纤维素、菊粉、甜菜粕、南瓜粉(强调纤维时)、亚麻籽、奇亚籽、麸皮
        (re.compile(r'\b(psyllium|cellulose|inulin|chicory|beet\s?pulp|fiber|bran|pomace|flax|chia)\b', re.IGNORECASE),
        "div_fiber_plant", "repeat_fiber"),
        # --- 第二层：颜色/功能 ---
        # --- 橙/红/黄色 (Beta-Carotene / Vitamin A) ---
        # 匹配：胡萝卜、南瓜、红薯、南瓜属、木瓜、番茄、西瓜、哈密瓜、杏、红/黄椒
        (re.compile(r'\b(carrot[s]?|pumpkin[s]?|sweet\s?potato[es]?|squash[es]?|papaya[s]?|tomato[es]?|watermelon[s]?|cantaloupe[s]?|apricot[s]?|yam[s]?|peach[es]?|nectarine[s]?|mango[eo]s?)\b|pepper.*(red|orange|yellow|bell)', re.IGNORECASE),
        "div_plant_orange", "repeat_color_orange"),
        # --- 绿色 (Chlorophyll / Lutein) ---
        # 匹配：菠菜、羽衣甘蓝、西兰花、抱子甘蓝、四季豆、西葫芦、芦笋、欧芹、海带、海藻、螺旋藻、青菜、生菜、卷心菜(非紫)、黄瓜、芹菜
        (re.compile(r'\b(spinach[s]?|kale|broccoli[s]?|brussels\s?sprout[s]?|green\s?bean[s]?|zucchini[s]?|asparagus|parsley|basil|kelp|seaweed|algae|spirulina|bok\s?choy[s]?|collard[s]?|chard|lettuce|cabbage[s]?(?!.*(red|purple))|celery|cucumber[s]?|arugula)\b', re.IGNORECASE),
        "div_plant_green", "repeat_color_green"),
        # --- 蓝/紫色 (Anthocyanins / Antioxidants) ---
        # 匹配：蓝莓、黑莓、树莓、蔓越莓、草莓、甜菜根、紫甘蓝、茄子、巴西莓、李子、樱桃、石榴
        (re.compile(r'\b(blueberr(?:y|ies)|blackberr(?:y|ies)|raspberr(?:y|ies)|cranberr(?:y|ies)|strawberr(?:y|ies)|beet[s]?|cabbage[s]?.*(red|purple)|eggplant[s]?|acai|pomegranate[s]?|plum[s]?|cher(?:y|ries)|prune[s]?)\b', re.IGNORECASE),
        "div_plant_blue", "repeat_color_blue"),
        # --- 白色/浅色 (Flavonoids / Potassium) ---
        # 匹配：花菜、蘑菇、苹果、梨、香蕉、防风草、芜菁、豆薯、椰子、普通土豆(非红薯)
        # 注意：排除了葱蒜洋葱 (Onion/Garlic)，因为对猫狗有毒，不建议打上通用蔬菜标签
        (re.compile(r'\b(cauliflower[s]?|mushroom[s]?|apple[s]?|pear[s]?|banana[s]?|parsnip[s]?|turnip[s]?|jicama|coconut[s]?|potato[es]?(?!.*sweet))\b', re.IGNORECASE),
        "div_plant_white", "repeat_color_white"),
    ]

    @staticmethod
    def get_tags(description, category_id):
        """
        输入: 食材描述, Category ID
        输出: (diversity_tags_str, repeat_tags_str, safety_tags_str)
        """
        div_tags, rep_tags, safe_tags = set(), set(), set()
        desc = str(description)

        # 1. Safety Check (启用!)
        if IdentityTagger.TOXIC.search(desc):
            safe_tags.add("risk_toxic")

        # 2. 动物蛋白匹配逻辑 
        # Categories: 1=Dairy, 5=Poultry, 7=Sausage, 10=Pork, 13=Beef, 15=Fish, 17=Lamb
        if category_id in [1, 5, 7, 10, 13, 15, 17]:
            for pattern, div, rep in IdentityTagger.ANIMAL_PATTERNS:
                if pattern.search(desc):
                    div_tags.add(div)
                    rep_tags.add(rep)

            # 兜底逻辑
            if not div_tags:
                if category_id == 10: rep_tags.add("repeat_pork"); div_tags.add("div_protein_pork")
                elif category_id == 13: rep_tags.add("repeat_beef"); div_tags.add("div_protein_ruminant")
                elif category_id == 5: rep_tags.add("repeat_poultry"); div_tags.add("div_protein_poultry")
                elif category_id == 1: rep_tags.add("repeat_dairy"); div_tags.add("div_protein_dairy")
                elif category_id == 15: rep_tags.add("repeat_fish"); div_tags.add("div_protein_fish")

        # 3. 植物匹配逻辑 
        # Categories: 9=Fruit, 11=Veg, 12=Nut, 16=Legume, 20=Grain
        elif category_id in [9, 11, 12, 16, 20]:
            for pattern, div, rep in IdentityTagger.PLANT_PATTERNS:
                if pattern.search(desc):
                    div_tags.add(div)
                    rep_tags.add(rep)
            
            # 兜底逻辑
            if not div_tags:
                if category_id == 11: div_tags.add("div_plant_other")
                elif category_id == 9: div_tags.add("div_plant_other")
                elif category_id == 20: div_tags.add("div_carb_grain"); rep_tags.add("repeat_grain") # 兜底谷物
                elif category_id == 16: div_tags.add("div_plant_legume"); rep_tags.add("repeat_legume") # 兜底豆类
        
        # 排序并返回
        return ",".join(sorted(div_tags)), ",".join(sorted(rep_tags)), ",".join(sorted(safe_tags))

class RegexPatterns:
    # 1. exceptions: 必须最先检查的特例
    EXCEPTIONS = {
        "cod liver oil": "FAT_OIL", # 明确归类
        "fish oil": "FAT_OIL",
        "peanut butter": "FAT_OIL", # 也可以算 NUT
        "coconut milk": "FAT_OIL",  # 高脂
        "fish sauce": "PROCESSED",
        "beef broth": "PROCESSED",
        "bone broth": "PROCESSED",
    }
    # 2. PROCESSED: 优先排除干扰项
    PROCESSED = re.compile(r'\b(sauce|broth|stock|soup|stew|gravy|seasoning|powder|extract|flavor|bouillon|salt|sugar|syrup|honey|molasses)\b', re.IGNORECASE)
    
    # 3. FAT_OIL: 必须在 MEAT 之前检查 (防止 "Chicken fat" 被当成 Chicken)
    FAT_OIL = re.compile(r'\b(fish oil|cod liver oil|salmon oil|sardine oil|anchovy oil|herring oil|olive oil|canola oil|coconut oil|peanut oil|sunflower oil|soybean oil|corn oil|sesame oil|safflower oil|grapeseed oil|fat|tallow|lard|ghee)\b', re.IGNORECASE)
    
    # 4. ORGAN: 必须在 MEAT 之前检查 (防止 "Beef liver" 被当成 Beef)
    ORGAN = re.compile(r'\b(liver|kidney|kidneys|heart|spleen|brain|tongue|giblet|gizzard|tripe|stomach|lung|pancreas|thymus|testicle)\b', re.IGNORECASE)
    # 5. SHELLFISH (Mineral Type): 必须在 FISH_LEAN 之前或单独处理
    PROTEIN_SHELLFISH = re.compile(r'\b(cockle|scallop|snail|squid|shrimp|prawn|crab|lobster|crayfish|octopus|calamari)\b', re.IGNORECASE)
    MINERAL_SHELLFISH = re.compile(r'\b(oyster|mussel|clam)\b', re.IGNORECASE)

    # 6. FISH (分为 Oily 和 Lean)
    # Lean 包含了虾蟹鱿鱼 (Protein Type Shellfish)
    FISH_OILY = re.compile(r'\b(salmon|tuna|sardine|mackerel|herring|anchovy|trout|sprat|smelt|pilchard)\b', re.IGNORECASE)
    FISH_LEAN = re.compile(r'\b(cod|haddock|tilapia|catfish|carp|pollock|flounder|halibut|sole|snapper)\b', re.IGNORECASE)

    # 7. EGG
    EGG = re.compile(r'\b(egg|eggs|egg white|egg yolk)\b', re.IGNORECASE)
    SUPPLEMENT_CALCIUM = re.compile(r'\b(calcium|carbonate|citrate|gluconate|lactate|phosphate|egg-shell)\b')
    
    # 8. MEAT (最后检查，作为兜底)
    MEAT = re.compile(r'\b(chicken|beef|pork|lamb|mutton|turkey|duck|goose|rabbit|quail|veal|venison|bison|buffalo|goat)\b', re.IGNORECASE)

    # 9. CARB
    CARB_TUBER = re.compile(r'\b(potato|sweet potato|yam|cassava|taro|yuca|tapioca|jerusalem artichoke)\b', re.IGNORECASE)
    # 增加了一些常见的面粉词
    CARB_GRAIN = re.compile(r'\b(rice|oat|oatmeal|wheat|corn|barley|sorghum|maize|millet|rye|buckwheat|quinoa|amaranth|teff|kamut|spelt|farro|pasta|macaroni|spaghetti|noodle|bread|flour|bran|germ|couscous|semolina|bulgur|biscuit|cracker)\b', re.IGNORECASE)
    # 豆类 (Legumes) 通常也算 CARB_OTHER 或 VEG，建议单独列出或归入 CARB
    LEGUME = re.compile(r'\b(bean|pea|lentil|chickpea|soy|tofu|edamame)\b', re.IGNORECASE)

    VEGETABLE = re.compile(r'\b(carrots|broccoli|spinach|kale|cabbage|lettuce|celery|pepper|asparagus|zucchini|cucumber|pumpkin|squash|cauliflower|bean sprout|alfalfa|beet|turnip|parsnip|radish|mushroom|kelp|seaweed|algae)\b', re.IGNORECASE)
    FIBER = re.compile(r'\b(psyllium|flax|chia|hemp seed)\b', re.IGNORECASE)
    BERRY = re.compile(r'\b(blueberries|cranberry|strawberry|raspberry|blackberry|acai|currant|mulberry|pomegranate|cherry)\b', re.IGNORECASE)
    FRUIT_ORANGE = re.compile(r'\b(peach|apricot|nectarine|plum|mango|papaya|cantaloupe|persimmon)\b', re.IGNORECASE)
    # === 剧毒/危险食材黑名单 ===
    TOXIC = re.compile(r'\b(grape|raisin|currant|sultana|macadamia|chocolate|cacao|cocoa|xylitol|avocado|guacamole|onion|garlic|leek|chive)\b', re.IGNORECASE)

    # 11. SUPPLEMENT
    SUPPLEMENT = re.compile(r'\b(calcium|carbonate|citrate|gluconate|lactate|phosphate|shell|vitamin|mineral|glucosamine|chondroitin|msm|probiotic)\b', re.IGNORECASE)

@dataclass
class TargetConfigure:
    """目标食材与营养配置"""
    target_nutrients: List[int] = field(default_factory=lambda:
                            [1008, 1005, 1079,
                            1003, 1220, 1221, 1212, 1213, 1214, 1215, 1216, 1217, 1218, 1211, 1210, 1219,   # Crude Protein
                            1004, 1316, 1269, 1404, 1272, 1278,                                  # Crude Fat 1316 LA alternate
                            1087, 1088, 1089, 1090, 1091, 1092, 1093, 1095, 1098, 1100, 1101, 1103, # Minerals
                            1104, 1110, 1109, 1165, 1166, 1170, 1167, 1175, 1186, 1178, 1180,       # Vitamins & Others
                            ])
    nutrient_ids_ordered: List[int] = field(default_factory=lambda:[
        1008, 1005, 1079,
        1003, 1220, 1221, 1212, 1213, 1214, 1215, 1216, 1217, 1218, 1211, 1210, 1219,
        1004, 1269, 1404, 1271, 1272, 1278,
        1087, 1091, 1092, 1093, 1088, 1090, 1089, 1098, 1101, 1095, 1100, 1103,
        1104, 1110, 1109, 1165, 1166, 1170, 1167, 1175, 1186, 1178, 1180
    ])
    target_food_category: List[int] = field(default_factory=lambda: [6, 7, 9, 11, 13, 14, 15, 17, 18, 19, 20, 21, 22, 25])

    protein_target: List[int] = field(default_factory=lambda: [174032, 171478, 171492, 171117, 171494, 173424, 171956, 
                    175177, 175178, 175117, 174233, 175120, 173719, 175168, 175180, 173613, 
                    172389, 173626, 172377, 172411, 172409, 173618, 172381, 171205, 169486, 
                    170209, 174004, 174250, 175173, 174217, 171975, 174422, 168303, 169192])
    # 174032: beef  171140: chicken breast  171492: herring  171117: mackerel  171494: salmon  173424: egg  171140: turkey breast skinless  172411: duck  172409: duck with skin  171478: breast  173618: leg with skin  172381: leg
    # 171956: cod  175178: herring  175117: mackerel  174233: salmon  175120: salmon  173719: salmon  175168: salmon  175180: salmon  173613: drumstick with skin  172377: drumstick  172389: thigh  173626: thigh with skin
    # 171205: Beef, chuck for stew  169486: beef 1/8 fat  170209: beef 0 lean  174004: beef tenderloin 174250: Mollusks oyster 174217: mussel 171975: clam
    # 168303: pork lion centre, 169192: pork ground 84%
    vegetable_target: List[int] = field(default_factory=lambda: [168463, 169211, 168568, 169292, 170394, 170407, 169225, 169283, 169967, 168390, 168484])
    # 168568: carrot baby  168463: spinach  169211: 竹笋  169292: 西葫芦   170394: carrot

    shellfish_target: List[int] = field(default_factory=lambda: [174250])
    fruits_target: List[int] = field(default_factory=lambda: [])

    fat_target: List[int] = field(default_factory=lambda: [171016, 173578, 167702, 173577, 172343, 172336, 171025, 171027, 171025])
    # 植物油 171016: sesame  172336: 菜籽油  172343: salmon

    carb_target: List[int] = field(default_factory=lambda: [168875, 168484, 169704, 170072, 170490, 169999, 170285, 168917,  168873, 168449, 170440, 168433])
    # 168484: sweet potato  168875: 糙米 中粒  169704: 糙米中粒   170072: 燕麦

    organ_target: List[int] = field(default_factory=lambda: [171485, 171487, 171059, 171061, 169448, 168626, 172528, 172532, 168268, 169450, 174355, 167860])

    protein_target: List[int] = field(default_factory=lambda: [169192, 171791, 175168, 171956, 173424])
    shellfish_target: List[int] = field(default_factory=lambda: [175180, 174250])
    fat_target: List[int] = field(default_factory=lambda: [167702, 173577, 746775, 1742558, 2375721, 171025])
    carb_target: List[int] = field(default_factory=lambda: [169704])
    vegetable_target: List[int] = field(default_factory=lambda: [168568, 171711, 170407])
    organ_target: List[int] = field(default_factory=lambda: [168626, 171061, 169450])
    # 746775 salt iodine; 1742558 PSYLLIUM HUSK POWDER; 2375721 eggshell powder

    @classmethod
    def get_all_fdc_id(cls, unique: bool = True):
        """
        获取所有目标食材的FDC ID列表
        :param unique: 是否返回唯一值（默认True）
        :return: 合并后的FDC ID列表
        """
        instance = cls()
        target = (  instance.protein_target + instance.vegetable_target + instance.shellfish_target +
                    instance.fruits_target + instance.fat_target + instance.carb_target + instance.organ_target
        )
        if unique:
            target = list(dict.fromkeys(target))
        return target
    
    @classmethod
    def get_all_nut_id(cls, unique: bool = True):
        """获取所有目标营养素ID"""
        instance = cls()
        target = instance.nutrient_ids_ordered

        if unique:
            target = list(dict.fromkeys(target))
        return target 

@dataclass
class ThresholdValue:
    """阈值配置类，包含数值和单位"""
    value: float
    unit: str
    
    def __str__(self):
        return f"{self.value} {self.unit}"
    
    def __float__(self):
        return self.value

@dataclass
class TagRule:
    threshold: ThresholdValue    # 1. 密度阈值 (例如 4000 mg/1000kcal)
    tag_name: str                # 2. 标签名
    
    # --- 新增：安保措施 ---
    min_raw_value: float = 0.0   # 3. 绝对含量门槛 (例如 1.0 g/100g)
    allowed_categories: Optional[List[int]] = None # 4. 分类白名单 (只允许某些分类)
    excluded_categories: Optional[List[int]] = None # 5. 分类黑名单 (例如排除香料)
    # 新增 02.04 正则匹配模式
    name_regex: Optional[str] = None
    # 辅助信息
    source_type: str = 'DIRECT'  # 'DIRECT' 或 'SUM_EPA_DHA'
    requires_ca_p_balance: bool = False # 钙专用

@dataclass
class AutoTagConfig:
    # 是否按数据集"分位数"自校准；True 则优先使用分位阈值（并且不会低于固定工程下限）
    use_percentiles: bool = True
    percentile: float = 0.70  # P70 以上才算"强载体"

    # 定义常用的分类组，方便引用 注：需加上补剂
    CATS_ANIMAL = [1, 5, 10, 13, 15, 17]      # 蛋奶, 禽, 猪, 牛, 鱼, 羊
    CATS_FAT_SOURCES = [1, 4, 5, 10, 12, 13, 15, 16, 17] # 加上油脂(4), 坚果(12), 大豆(16)
    CATS_PLANT_ONLY = [9, 11, 12, 16, 20]     # 水果, 蔬菜, 坚果, 豆类, 谷物
    CATS_SUPPLEMENT = [21]

    ca_p_ratio_threshold: float = 1.5

    role_rules: Dict[int, List[TagRule]] = field(default_factory=lambda: {
        # 1. 脂肪酸 (必须加 min_raw_value 防竹笋)
        NutrientID.PUFA_18_2: [
            TagRule(
                threshold=ThresholdValue(4000.0, "mg/1000kcal"), 
                tag_name="role_omega6_la",
                min_raw_value=1.6,  # 每100g必须有1g
                allowed_categories=AutoTagConfig.CATS_FAT_SOURCES + AutoTagConfig.CATS_SUPPLEMENT # <--- 核心修改：排除谷物/蔬菜
            )],
        NutrientID.ALA: [
            TagRule(
                threshold=ThresholdValue(800.0, "mg/1000kcal"), 
                tag_name="role_omega3_ala",
                min_raw_value=0.5,  # ALA 含量通常较低，0.1g 门槛足够过滤噪音
                allowed_categories=AutoTagConfig.CATS_FAT_SOURCES + AutoTagConfig.CATS_SUPPLEMENT
            )],
        # EPA: 聚合逻辑
        NutrientID.EPA: [
            # 单项 EPA
            TagRule(
                threshold=ThresholdValue(1000.0, "mg/1000kcal"), 
                tag_name="role_omega3_lc",
                min_raw_value=0.05,
                allowed_categories=[15, 4, 21] # 允许鱼类 (Cat 15, 4)
            ),
            # EPA + DHA 总和
            TagRule(
                threshold=ThresholdValue(2500.0, "mg/1000kcal"), 
                tag_name="role_omega3_lc",
                source_type='SUM_EPA_DHA',
                min_raw_value=0.06,
                allowed_categories=[15, 4, 21] # 允许鱼类
            )],
        NutrientID.DHA: [
            TagRule(
                threshold=ThresholdValue(1000.0, "mg/1000kcal"), 
                tag_name="role_omega3_lc",
                min_raw_value=0.5,
                allowed_categories=[15, 4, 21]
            )],

        # 2. 矿物质 (必须防香料和生物利用率)
        # 钙：统一用 /1000kcal 密度 + 比例约束
        NutrientID.CALCIUM: [
            TagRule(
                threshold=ThresholdValue(3000.0, "mg/1000kcal"), # 密度阈值
                tag_name="role_calcium_source",
                requires_ca_p_balance=True, # 必须 Ca:P > 1.5
                min_raw_value=100.0,         # 物理含量至少 20mg (防极低热量噪音)
                # 不限制 Category，因为要允许 蛋壳粉(1), 骨头(5,10,13), 甚至碳酸钙
                excluded_categories=[2, 11] # 排除香料(2) 和 蔬菜(11, 如菠菜)
            )],
        
        # 铁/锌：优先动物来源，或者设置较高门槛
        NutrientID.IRON: [
            TagRule(
                threshold=ThresholdValue(14.4, "mg/1000kcal"), 
                tag_name="role_iron",
                min_raw_value=0.5,
                allowed_categories=AutoTagConfig.CATS_ANIMAL + AutoTagConfig.CATS_SUPPLEMENT
            )],

        # 3. 维生素 (必须防 B12/D 假阳性)
        NutrientID.VITAMIN_B12: [
            TagRule(
                threshold=ThresholdValue(10.0, "μg/1000kcal"), 
                tag_name="role_vit_b12",
                allowed_categories=AutoTagConfig.CATS_ANIMAL + AutoTagConfig.CATS_SUPPLEMENT # <--- 核心：只许动物
            )],
        
        # 纤维：绝对禁止动物来源 (防脏数据)
        NutrientID.FIBER: [
            TagRule(
                threshold=ThresholdValue(3.0, "g/1000kcal"), 
                tag_name="role_fiber_source",
                min_raw_value=1.0, # 0.01g 门槛足够过滤噪音
                allowed_categories=AutoTagConfig.CATS_PLANT_ONLY + AutoTagConfig.CATS_SUPPLEMENT # <--- 核心：只许植物
            )],

        # 维A：防辣椒粉
        NutrientID.VITAMIN_A: [
            TagRule(
                threshold=ThresholdValue(5000.0, "IU/1000kcal"), 
                tag_name="role_vita",
                min_raw_value=2000,     # 排除低热量食物
                excluded_categories=[2] # 排除香料
            )],

        NutrientID.VITAMIN_D: [
            TagRule(
                threshold=ThresholdValue(150.0, "IU/1000kcal"),
                tag_name="role_vit_d",
                # 这是一个很低的门槛，但足以过滤掉牛肉和鸡肉（通常是 0）。
                min_raw_value=10.0, 
                allowed_categories=[1, 4, 5, 10, 13, 15, 17, 21] 
            )
        ],
        
        NutrientID.THIAMIN: [
            TagRule(
                # 它能过滤掉大部分普通鸡肉/牛肉肌肉（逼迫算法去找猪肉或内脏）
                threshold=ThresholdValue(1.5, "mg/1000kcal"), 
                tag_name="role_thiamine",
                min_raw_value=0.1,                 
                # 允许：蛋奶(1), 禽(5), 猪(10-重点), 牛(13), 鱼(15), 羊(17), 谷物(20)
                # 猪肉(10)是 B1 之王，心脏和肝脏也是好来源
                allowed_categories=[1, 5, 10, 13, 15, 17, 20, 21]
            )
        ],

        NutrientID.CHOLINE: [
            TagRule(
                # 设定为 500.0，寻找优质来源
                threshold=ThresholdValue(500.0, "mg/1000kcal"), 
                tag_name="role_choline",
                min_raw_value=40.0, 
                # 允许：蛋奶(1-重点), 禽(5), 猪(10), 牛(13), 鱼(15), 羊(17)
                allowed_categories=[1, 5, 10, 13, 15, 17, 21]
            )
        ],
    })

    risk_rules: Dict[int, List[TagRule]] = field(default_factory=lambda: {
        # 1. 矿物质 
        NutrientID.COPPER: [
            TagRule(
                threshold=ThresholdValue(10.0, "mg/1000kcal"), 
                tag_name="risk_high_copper",
                min_raw_value=1.0,
            )
        ],
        NutrientID.IODINE: [
            TagRule(
                threshold=ThresholdValue(3.0, "mg/100g"), 
                tag_name="risk_high_iodine",
            ),
            TagRule(
                threshold=ThresholdValue(1000.0, "mg/100g"),
                tag_name="risk_high_iodine",
                allowed_categories=[15], 
                # 包含: 鳕鱼(cod), 三文鱼(salmon), 鲭鱼(mackerel), 沙丁鱼(sardine), 金枪鱼(tuna), 鲱鱼(herring), 鲽鱼(pollock/flatfish)
                name_regex=r"(?i)(cod|salmon|mackerel|sardine|tuna|herring|pollock|haddock|whiting)"
            )
        ],
        NutrientID.SELENIUM: [
            TagRule(
                threshold=ThresholdValue(0.6, "mg/1000kcal"), 
                tag_name="risk_high_selenium",
                min_raw_value=130,
            )
        ],
        NutrientID.SODIUM: [
            TagRule(
                threshold=ThresholdValue(1500.0, "mg/100g"), 
                tag_name="risk_high_sodium",
            )
        ],

        # 3. 维生素 
        # 维A：防辣椒粉
        NutrientID.VITAMIN_A: [
            TagRule(
                threshold=ThresholdValue(30000.0, "IU/1000kcal"), 
                tag_name="risk_high_vit_a",
                allowed_categories=[4, 10, 13, 15, 17],
                min_raw_value=5000.0 # IU/100g
            )
        ],
        NutrientID.VITAMIN_D: [
            TagRule(
                threshold=ThresholdValue(2000.0, "IU/1000kcal"), 
                tag_name="risk_high_vit_d",
                min_raw_value=100.0,
                allowed_categories=[1, 4, 5, 10, 13, 15, 17] # <--- 核心：只许动物
            )
        ],
    })

    # Role 阈值配置表
    role_thresholds: Dict[int, Tuple[ThresholdValue, str]] = field(default_factory=lambda: {
        # --- 脂肪酸 ---
        NutrientID.PUFA_18_2:    (ThresholdValue(4000.0, "mg/1000kcal"), "role_omega6_la"),
        NutrientID.ALA:          (ThresholdValue(200.0,  "mg/1000kcal"), "role_omega3_ala"),
        NutrientID.EPA:          (ThresholdValue(800.0,  "mg/1000kcal"), "role_omega3_lc"),
        NutrientID.DHA:          (ThresholdValue(300.0,  "mg/1000kcal"), "role_omega3_lc"),
        
        # --- 矿物质 ---
        # 钙 - Support (普通含量) -> 对应标准 ID
        NutrientID.CALCIUM:      (ThresholdValue(3000.0, "mg/100g"), "role_calcium"),
        
        NutrientID.IRON:         (ThresholdValue(20.0, "mg/1000kcal"), "role_iron"),
        NutrientID.ZINC:         (ThresholdValue(30.0, "mg/1000kcal"), "role_zinc"),
        NutrientID.IODINE:       (ThresholdValue(0.5,  "mg/1000kcal"), "role_iodine"),

        # --- 维生素 & 其他 ---
        NutrientID.FIBER:       (ThresholdValue(3.0, "g/1000kcal"),    "role_fiber_source"),
        NutrientID.THIAMIN:     (ThresholdValue(1.5, "mg/1000kcal"),   "role_vit_b1"),
        # 注意：这里把 B12 阈值统一了，之前你有 0.018 和 20 两个，建议用微克统一逻辑
        NutrientID.VITAMIN_B12: (ThresholdValue(20.0, "μg/1000kcal"), "role_vit_b12"),
        NutrientID.CHOLINE:     (ThresholdValue(1000.0, "mg/1000kcal"), "role_choline"),
        
        NutrientID.VITAMIN_A:   (ThresholdValue(5000.0, "IU/1000kcal"), "role_vita"),
        NutrientID.VITAMIN_D:   (ThresholdValue(250.0,  "IU/1000kcal"), "role_vitd"),
    })

    # Risk 阈值配置表
    risk_thresholds: Dict[int, Tuple[ThresholdValue, str]] = field(default_factory=lambda: {
        NutrientID.COPPER:    (ThresholdValue(10.0, "mg/1000kcal"), "risk_high_copper"),
        NutrientID.IODINE:    (ThresholdValue(5.0,  "mg/1000kcal"), "risk_high_iodine"),
        NutrientID.SELENIUM:  (ThresholdValue(0.6, "mg/1000kcal"), "risk_high_selenium"),
        NutrientID.SODIUM:    (ThresholdValue(1500.0, "mg/1000kcal"), "risk_high_sodium"),
        NutrientID.VITAMIN_A: (ThresholdValue(30000.0, "IU/1000kcal"), "risk_high_vit_a"),
        NutrientID.VITAMIN_D: (ThresholdValue(750.0, "IU/1000kcal"),   "risk_high_vit_d"),
    })

    CATEGORY_LIMITS_CONFIG = {
        # --- 1. 核心肉类 (宽松) ---
        'meat_lean':     (None, 0.80),  # 瘦肉：不限重，热量占比最高80%
        'meat_moderate': (None, 0.70),  # 中脂肉
        'meat_fat':      (None, 0.30),  # 肥肉：限制热量占比，防止胰腺炎
        'fish_lean':     (None, 0.80),  # 瘦鱼/虾/鱿鱼
        'fish_oily':     (10.0, 0.25),  # 油性鱼：限制重量(防重金属/维D)，限制热量

        # --- 2. 内脏 (严格) ---
        'organ_liver':           (1.0, 0.05),  # 肝脏：维A毒性，极大限制
        'organ_secreting_other': (2.0, 0.10),  # 脾/肾：防腹泻
        'organ_muscular':        (None, 0.20), # 心/胗：作为肉类补充

        # --- 3. 蛋类 ---
        'egg': (5.0, 0.15),  # 鸡蛋

        # --- 4. 碳水与蔬菜 ---
        'carb_grain': (None, 0.40), 
        'carb_tuber': (None, 0.40),
        'carb_other': (None, 0.15), # 豆类：限制 DCM 风险
        'vegetable':  (5.0,  0.15), # 蔬菜：纤维限制
        'fruit':      (2.0,  0.05), # 水果：糖分限制

        # --- 5. 补充剂与特殊 ---
        'fish_shellfish': (0.5, 0.03), # 牡蛎：极严格，锌/钠限制
        'fat_animal':     (2.0, 0.15), # 动物油
        'oil_omega6_la':  (1.0, 0.10), 
        'oil_omega3_lc':  (0.2, 0.05), # 鱼油
        'supplement_calcium':   (1.0, None),
        'supplement_iodine':    (0.1, None),
        'supplement_omega3_lc': (0.5, 0.10),
        'supplement_mineral':   (0.05, 0.00),
        'supplement_multivitamin':  (0.5, 0.00),
        'fiber':                    (0.5, 0.05),
        'supplement_functional':    (0.2, 0.00),
        
        # --- 默认 ---
        'OTHER': (None, None)
    }

    risk_nutrient: List[str] = field(default_factory=lambda: ["calcium","phosphorus", "Ca_P_ratio", "iodine", "vitamin A", "vitamin D"])

    # 风险词典（名称匹配）
    risk_goitrogenic: List[str] = field(default_factory=lambda: ["kale","羽衣甘蓝","broccoli","西兰花","cabbage","卷心菜"])
    risk_oxalate: List[str] = field(default_factory=lambda: ["spinach","菠菜","beet greens","甜菜叶"])
    risk_thiaminase_fish: List[str] = field(default_factory=lambda: ["smelt","capelin","herring","carp","anchovy","沙丁"])  # 熟喂影响小
    risk_mercury: List[str] = field(default_factory=lambda: ["tuna","金枪鱼","swordfish","旗鱼"])

    def get_ca_p_threshold(self) -> float:
        return self.ca_p_ratio_threshold

class DiversityPatterns:
    # 1. 蛋白质组 (Protein Group) - 生物科属
    
    # 反刍类 (Ruminant): 牛, 羊, 鹿, 骆驼, 水牛
    RUMINANT = re.compile(r'\b(beef|cow|veal|calf|bison|buffalo|lamb|mutton|sheep|goat|venison|deer|elk|camel|moose)\b', re.IGNORECASE)
    # 猪 (Pork): 单独一类
    PORK = re.compile(r'\b(pork|pig|ham|bacon|swine|boar)\b', re.IGNORECASE)
    # 水禽 (Waterfowl): 鸭, 鹅 (凉性/低敏)
    WATERFOWL = re.compile(r'\b(duck|goose|geese)\b', re.IGNORECASE)
    # 陆禽 (Poultry): 鸡, 火鸡, 鹌鹑, 雉鸡 (常见过敏原)
    POULTRY = re.compile(r'\b(chicken|hen|rooster|broiler|fryer|turkey|quail|pheasant|guinea fowl|egg)\b', re.IGNORECASE)
    # 甲壳/软体 (Shellfish): 虾, 蟹, 贝, 鱿鱼 (矿物质)，在 Fish 之前匹配
    SHELLFISH = re.compile(r'\b(shrimp|prawn|crab|lobster|crayfish|clam|mussel|oyster|scallop|squid|octopus|calamari|snail|whelk)\b', re.IGNORECASE)
    # 鱼类 (Fish): 广义鱼类
    FISH = re.compile(r'\b(fish|salmon|tuna|cod|sardine|mackerel|herring|trout|tilapia|pollock|haddock|anchovy|catfish|bass|snapper|halibut|sole|flounder)\b', re.IGNORECASE)
    # 特种/低敏 (Exotic): 兔, 袋鼠, 鳄鱼
    EXOTIC = re.compile(r'\b(rabbit|hare|kangaroo|wallaby|crocodile|alligator|emu|ostrich)\b', re.IGNORECASE)
    # 2. 植物组 (Plant Group) - 颜色/功能
    # 浆果 (Berry): 花青素 (紫/黑/蓝)，在 Fruit 之前匹配
    BERRY = re.compile(r'\b(blueberry|cranberry|strawberry|raspberry|blackberry|mulberry|acai|currant)\b', re.IGNORECASE)
    # 绿叶菜 (Leafy): 叶酸/维K (绿)
    LEAFY = re.compile(r'\b(spinach|kale|lettuce|chard|cabbage|bok choy|greens|arugula|collard|watercress|endive|romaine)\b', re.IGNORECASE)
    # 十字花科 (Cruciferous): 抗癌，注意：Broccoli, Cauliflower
    CRUCIFEROUS = re.compile(r'\b(broccoli|cauliflower|brussels sprout|kohlrabi|radish|turnip|rutabaga)\b', re.IGNORECASE)
    # 橙/黄/红 (Orange): 胡萝卜素
    ORANGE = re.compile(r'\b(carrot|pumpkin|squash|sweet potato|yam|papaya|cantaloupe|apricot|mango|persimmon)\b', re.IGNORECASE)
    # (re.compile(r'\b(carrot|pumpkin|sweet\s?potato|squash|papaya|tomato|watermelon|cantaloupe|apricot)\b|pepper.*(red|orange|bell)', re.IGNORECASE), "div_plant_orange", "repeat_color_orange"),
    # (re.compile(r'\b(spinach|kale|broccoli|brussels\s?sprout|green\s?bean|zucchini|asparagus|parsley|basil|kelp|seaweed|algae|bok\s?choy|collard|chard|lettuce|cabbage(?!.*(red|purple)))\b', re.IGNORECASE), "div_plant_green", "repeat_color_green"),
    # (re.compile(r'\b(blueberr|blackberr|raspberr|cranberr|strawberr|beet|cabbage.*(red|purple)|eggplant|acai)\b', re.IGNORECASE), "div_plant_blue", "repeat_color_blue"),
    # 普通水果 (Fruit): 果糖/适口性
    FRUIT = re.compile(r'\b(apple|pear|banana|watermelon|melon|peach|plum|nectarine|pineapple|coconut|fig|date|kiwi)\b', re.IGNORECASE)
    # 其他蔬菜 (Other): 填充/补水
    OTHER_VEG = re.compile(r'\b(zucchini|cucumber|celery|asparagus|green bean|string bean|snap pea|mushroom|eggplant|pepper|bell pepper|okra|tomatillo|tomato)\b', re.IGNORECASE)

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
    def parse_unit_string(unit_str: str):
        """
        解析配置字符串，如 "mg/1000kcal" -> ('mg', '1000kcal')
        """
        if '/' in unit_str:
            numerator, denominator = unit_str.split('/', 1)
        else:
            numerator, denominator = unit_str, '100g' # 默认分母
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

def _get_diversity_tag(row: pd.Series):
    desc = str(row.get('description', '')).lower()
    cat_id = row.get('food_category_id')
    # 1. 快速排除 (Fast Fail)
    # 这些类别不需要 Diversity Tag (由 Role Tag 或 Subgroup 管理)
    # 4: Fats, 12: Nuts, 16: Legumes, 20: Grains
    if cat_id in [4, 12, 16, 20]:
        return None

    # 2. 动物蛋白组逻辑 (Animal Group)
    
    # --- ID 13: Beef Products (牛肉) ---
    if cat_id == 13:
        # 99% 是反刍，直接返回
        return 'div_protein_ruminant'

    # --- ID 5: Poultry Products (禽类) ---
    if cat_id == 5:
        # 区分水禽(凉性)和陆禽(热性/易敏)
        if DiversityPatterns.WATERFOWL.search(desc):
            return 'div_protein_waterfowl'
        return 'div_protein_poultry' # 默认为鸡/火鸡

    # --- ID 15: Finfish and Shellfish (鱼贝) ---
    if cat_id == 15:
        # 区分甲壳/软体 和 鱼
        if DiversityPatterns.SHELLFISH.search(desc):
            return 'div_protein_marine_shellfish'
        return 'div_protein_marine_fish' # 默认为鱼

    # --- ID 17: Lamb, Veal, and Game (羊/小牛/野味) ---
    if cat_id == 17:
        # 这一组比较杂，需要细分
        if DiversityPatterns.PORK.search(desc): # 防止有些野猪肉混进来
            return 'div_protein_pork'
        if DiversityPatterns.EXOTIC.search(desc): # 兔、鹿、袋鼠
            # 注意：鹿(Venison)在生物学上也是反刍，把鹿归为 ruminant，兔归为 exotic
            if 'rabbit' in desc or 'hare' in desc or 'kangaroo' in desc:
                return 'div_protein_exotic'
            return 'div_protein_ruminant' # 鹿、野牛都算反刍
        
        # 剩下的 Lamb, Veal, Goat 都是反刍
        return 'div_protein_ruminant'

    # --- ID 1: Dairy and Egg (奶蛋) ---
    if cat_id == 1:
        # 只关心蛋，奶制品(Dairy)通常不算蛋白质多样性轮换的主力(或者是零食)
        if DiversityPatterns.EGG.search(desc):
            return 'div_protein_poultry' # 蛋归为禽类蛋白
        return None # 奶酪/牛奶返回 None (或者你可以设为 div_protein_ruminant，看需求)

    # --- ID 10: Pork Products (猪肉 - USDA标准ID) ---
    # 虽然你列表里没给10，但如果有的话
    if cat_id == 10:
        return 'div_protein_pork'

    # 3. 植物组逻辑 (Plant Group)
    # --- ID 9: Fruits (水果) ---
    if cat_id == 9:
        # 区分高价值浆果 和 普通水果
        if DiversityPatterns.BERRY.search(desc):
            return 'div_plant_berry'
        return 'div_plant_fruit'

    # --- ID 11: Vegetables (蔬菜) ---
    if cat_id == 11:
        # 优先级匹配
        if DiversityPatterns.LEAFY.search(desc):
            return 'div_plant_leafy'
        if DiversityPatterns.CRUCIFEROUS.search(desc):
            return 'div_plant_cruciferous'
        if DiversityPatterns.ORANGE.search(desc):
            return 'div_plant_orange'
        
        # 剩下的 (西葫芦, 黄瓜, 芹菜等)
        return 'div_plant_other'

    return None

def _percentile(values: List[float], p: float) -> float:
    vals = sorted(v for v in values if v is not None and v > 0)
    if not vals:
        return 0.0
    k = int(math.ceil(p * len(vals))) - 1
    return vals[max(0, min(k, len(vals)-1))]

def _thr(th: Any, level: str = "support", fallback: float = None) -> float:
    """
    读取阈值：
    - 若 th 是数值：直接返回
    - 若 th 是 dict：优先取 dict[level]，否则取 'value' 或任一数字
    - fallback 可覆盖默认
    """
    if isinstance(th, (int, float)):
        return float(th)
    if isinstance(th, dict):
        for k in (level, "value", "threshold", "min"):
            if k in th and isinstance(th[k], (int, float)):
                return float(th[k])
        # 随便取一个数字键
        for v in th.values():
            if isinstance(v, (int, float)):
                return float(v)
    if fallback is not None:
        return float(fallback)
    raise ValueError(f"Bad threshold spec: {th}")

def _contains_word(text: str, word: str) -> bool:
    """
    检查文本中是否包含指定的单词（作为独立单词）
    
    参数:
    text: str - 要检查的文本
    word: str - 要查找的单词
    
    返回:
    bool - 是否包含该单词
    """
    import re
    # 使用正则表达式进行全词匹配
    pattern = r'\b' + re.escape(word) + r'\b'
    return bool(re.search(pattern, text))

def _infer_food_category(description: str, category_id: int | None = None, fat_g_100g: float | None = None) -> str:
    """
    根据食物描述、category_id和脂肪含量推断食物类别
    
    参数:
    description: str - 食物描述
    category_id: int | None - USDA food category id，用于辅助判断
    fat_g_100g: float | None - 每100g的脂肪含量（克），用于肉类脂肪含量分类
    
    返回:
    str - 推断的食物类别
    """
    try:
        # 首先根据category_id进行主要分类
        if category_id is not None:
            hint = _get_category_hint_from_id(category_id, description, fat_g_100g)
            if hint: return hint

        desc_lower = description.lower()
        
        # 2. 文本匹配逻辑
        for k, v in RegexPatterns.EXCEPTIONS.items():
            if k in desc_lower: return v

        # Level 1: 排除加工食品/干扰项
        if RegexPatterns.PROCESSED.search(desc_lower): return "SUPPLEMENT"
        if RegexPatterns.SUPPLEMENT.search(desc_lower): return "SUPPLEMENT"
        if RegexPatterns.SUPPLEMENT_CALCIUM.search(desc_lower): return 'SUPPLEMENT'
        
        # Level 2: 优先检查脂肪 (防止 Chicken Fat 被归为 Meat)
        if RegexPatterns.FAT_OIL.search(desc_lower): return "FAT_OIL"

        # Level 3: 内脏 (防止 Beef Liver 被归为 Meat)
        if RegexPatterns.ORGAN.search(desc_lower): return 'ORGAN'
        # Level 4: 蛋类
        if RegexPatterns.EGG.search(desc_lower): return 'PROTEIN_EGG'
        
        # Level 5: 鱼类和贝类
        if RegexPatterns.PROTEIN_SHELLFISH.search(desc_lower): return "PROTEIN_SHELLFISH" # 矿物型和虾蟹
        if RegexPatterns.MINERAL_SHELLFISH.search(desc_lower): return "MINERAL_SHELLFISH"
        if RegexPatterns.FISH_OILY.search(desc_lower): return "PROTEIN_FISH"
        if RegexPatterns.FISH_LEAN.search(desc_lower): return "PROTEIN_FISH" # 不包含虾蟹

        # Level 6: 肉类 (兜底)
        if RegexPatterns.MEAT.search(desc_lower): return "PROTEIN_MEAT"

        # Level 7: 碳水和蔬菜
        if RegexPatterns.CARB_TUBER.search(desc_lower): return "CARB_TUBER"
        if RegexPatterns.CARB_GRAIN.search(desc_lower): return "CARB_GRAIN"
        if RegexPatterns.LEGUME.search(desc_lower): return "CARB_OTHER" # 或者是 VEGETABLE，看你的营养策略
        if RegexPatterns.FIBER.search(desc_lower): return "FIBER"
        if RegexPatterns.VEGETABLE.search(desc_lower): return "PLANT_ANTIOXIDANT"
        if RegexPatterns.BERRY.search(desc_lower): return "PLANT_ANTIOXIDANT"

        return 'OTHER'
        
    except Exception as e:
        logging.warning(f"Error inferring food category for '{description}': {str(e)}")
        return 'OTHER'

def _get_category_hint_from_id(category_id: int, description: str, fat_g_100g: float | None = None) -> str | None:
    """
    根据category_id、描述和脂肪含量提供分类提示
    
    参数:
    category_id: int - USDA food category id
    description: str - 食物描述（小写）
    fat_g_100g: float | None - 每100g的脂肪含量（克）
    
    返回:
    str | None - 分类提示，如果没有匹配则返回None
    """
    try:
        if not isinstance(description, str) or description.strip() == '':
            return None
        desc_lower = description.strip().lower()
        
        if category_id == 1: # Dairy & Egg
            return 'PROTEIN_EGG' if 'egg' in desc_lower else 'DAIRY'
        elif category_id == 4: return 'FAT_OIL'
        elif category_id in (5, 13, 17, 10): # Meat/Poultry
            return 'ORGAN' if RegexPatterns.ORGAN.search(desc_lower) else 'PROTEIN_MEAT'
        elif category_id == 11:
            return 'CARB_TUBER' if RegexPatterns.CARB_TUBER.search(desc_lower) else 'PLANT_ANTIOXIDANT'
        elif category_id == 12: return 'TREATS'
        elif category_id == 15: # Fish
            if RegexPatterns.MINERAL_SHELLFISH.search(desc_lower):
                return 'MINERAL_SHELLFISH' 
            elif RegexPatterns.PROTEIN_SHELLFISH.search(desc_lower):
                return 'PROTEIN_SHELLFISH'
            elif RegexPatterns.FISH_OILY.search(desc_lower) or RegexPatterns.FISH_LEAN.search(desc_lower):
                return 'PROTEIN_FISH'
        elif category_id == 16:
            if RegexPatterns.LEGUME.search(desc_lower):
                return 'CARB_LEGUME' # Legumes
        elif category_id == 20: 
            if RegexPatterns.CARB_GRAIN.search(desc_lower):
                return 'CARB_GRAIN'
        elif category_id == 21: return 'SUPPLEMENT'
        
        return None

    except Exception as e:
        logging.warning(f"Error in _get_category_hint_from_id for category_id {category_id}: {str(e)}")
        return None

def table_nutrients_generation(input_file_path: str, output_file_path: str='././data/nutrients_out.csv'):
    try:
        # read the nutrients.csv file and select the columns id, name, unit_name
        input_file_path = Path(input_file_path)
        output_file_path = Path(output_file_path)

        # 1. read and clean data
        df = pd.read_csv(input_file_path, usecols=['id', 'name', 'unit_name'])

        # translate the type of id column to int
        df['id'] = pd.to_numeric(df['id'], errors='coerce')
        df = df.dropna(subset=['id'])
        df['id'] = df['id'].astype(int)

        # filter data 
        target_ids = set(NutrientID.sort_nutrient_ids())
        df = df[df['id'].isin(target_ids)]
        
        # rename and drop duplicates
        df = df.rename(columns={'id': 'nutrient_id'})
        df = df.drop_duplicates(subset=['nutrient_id'])

        # modify the new csv file to have the columns nutrient_id, name, unit_name, is_key. group name and display_order
        key_nutrients_id = [NutrientID.PROTEIN, NutrientID.FAT, NutrientID.CARBOHYDRATE, NutrientID.ENERGY]
        
        rank_map = NutrientID.get_ranked_map(start_index=1)
        group_map = NutrientID.get_group_map()

        # assignment of the columns is_key and group_name
        df['is_key'] = df['nutrient_id'].isin(key_nutrients_id)

        df['group_name'] = df['nutrient_id'].map(group_map).fillna(NutrientGroup.VITAMINS_OTHER.value)

        # assigne the display_order make sure nutrient_id is int type
        df['display_order'] = df['nutrient_id'].map(rank_map).fillna(9999).astype(int)

        output_file_path.parent.mkdir(parents=True, exist_ok=True)

        # df.to_csv(output_file_path, index=False)

        logging.info(f"Nutrients table generated successfully: {output_file_path}")
        return df
        
    except Exception as e:
        logging.error(f"Error generating nutrients table: {e}")
        raise e

def _get_short_name(description: str) -> str:
    """Create ingredient short name from description, remove the descriptor of cooking method and process"""
    if not description or pd.isna(description):
            return ""
    try:
        # 定义要去除的烹饪方式和处理方式关键词
        cooking_keywords = [
            'cooked', 'boiled', 'drained', 'steamed', 'raw', 'without skin',
            'braised', 'simmered', 'baked', 'fried', 'grilled', 'roasted', 'roast'
            'sauteed', 'stir-fried', 'poached', 'smoked', 'cured', 'pickled',
            'canned', 'frozen', 'fresh', 'dried', 'dehydrated', 'powdered', 'crumbles'
            'minced', 'chopped', 'sliced', 'diced', 'shredded', 'ground', 'domesticated', 
            'whole', 'peeled', 'unpeeled', 'conventional', 'fortified', 'enriched', 'natural', 'artificial',
            'dry', 'heat', 'broiled', 'stewed', 'includes', 'patty', 'farmed', 
            'without salt', 'with salt', 'salt', 'dry heat', 'cold pressed', 'variety meats and by-products',
            'mollusks', 'crustaceans', 'fish', 'mixed species', 'broilers or fryers',
            'composite of trimmed retail cuts', 'trimmed to 1/8" fat', 'choice', 'trimmed to 0" fat', 
            'pearled', 'all varieties', 'salad or cooking', '(approx. 65%)', '(approx. 75%)', '(approx. 85%)', '(approx. 95%)',
            'linoleic', 'high oleic', 'pan-browned', 'chuck for stew', 'all classes', 'Crustaceans', 
            'Atlantic', 'Pacific', 'grades', 'tenderloin'
        ]

        keep_terms = {
            'sweet potato', 
            'sweet corn', 
            'sweet pepper',
            'sweet onion',
            'blue crab',       # 保护 blue
            'blue mussels',    # 保护 blue
            'yellow squash',   # 保护 yellow
            'yellow corn'      # 保护 yellow
        }
        
        # 按逗号分割，处理每个部分
        parts = [part.strip() for part in description.split(',')]
        filtered_parts = []
        
        for part in parts:
            # 转换为小写
            part_lower = part.lower()
            # 检查这个部分是否包含任何烹饪关键词
            is_protected = any(term in part_lower for term in keep_terms)
            if is_protected:
                filtered_parts.append(part)
                continue  # 跳过后续步骤，直接处理下一个 part

            contains_cooking_keyword = any(keyword in part_lower for keyword in cooking_keywords)
            
            # 如果不包含烹饪关键词，保留这个部分
            if not contains_cooking_keyword:
                filtered_parts.append(part)
        
        # 重新组合成简称
        short_name = ' '.join(filtered_parts)
        
        # 首字母大写
        short_name = short_name.title()
        
        return short_name

    except Exception as e:
        logging.error(f"Error generate short name: {e}")

def table_ingredients_generation(input_file_path, output_file_path, merge_strategy='update', preserve_fields=None):
    """Read food.csv and generate ingredient database data"""

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
        20: "Gereal Grains and Pasta",
        21: "Supplements Products"
    }

    try:
        target_fdc_ids = set(TargetConfigure.get_all_fdc_id())
        food_df = (pd.read_csv(input_file_path, usecols=['fdc_id', 'description', 'food_category_id'])
                .query('fdc_id in @target_fdc_ids'))

        # translate the fdc_id column to int and clean data 
        food_df['fdc_id'] = pd.to_numeric(food_df['fdc_id'], errors='coerce')
        food_df['food_category_id'] = pd.to_numeric(food_df['food_category_id'], errors='coerce')
        food_df = food_df.dropna(subset=['fdc_id'])
        food_df['fdc_id'] = food_df['fdc_id'].astype(int)
        food_df['food_category_id'] = food_df['food_category_id'].astype(int)

        # 生成新字段
        logging.info("Generating short names...")

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
        food_df['max_g_per_bg_bw'] = None   # max weight per kilogram of body weight
        food_df['max_pct_kcal'] = None      # max precent of calories from total calories
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
            existing_identity = existing_df[['fdc_id', 'id', 'created_at']].copy()
            # 为 food_df['id'] 进行赋值
            food_df = pd.merge(food_df, existing_identity, on='fdc_id', how='left')

            new_rows_mask = food_df['id'].isna()
            num_new = new_rows_mask.sum()
            
            if num_new > 0:
                logging.info(f"检测到 {num_new} 条新增食材，正在分配 ID...")
                # 为新增行生成 UUID
                food_df.loc[new_rows_mask, 'id'] = [str(uuid.uuid4()) for _ in range(num_new)]
                # 为新增行设置创建时间
                food_df.loc[new_rows_mask, 'created_at'] = now_str
            
            # for col in preserve_fields:
            #     if col in food_df.columns:
            #         # 为需要保留的字段创建新列
            #         new_values = []
            #         for fdc_id in food_df['fdc_id']:
            #             if fdc_id in existing_lookup.index:
            #                 new_values.append(existing_lookup.loc[fdc_id, col])
            #             else:
            #                 if col == 'id':
            #                     new_values.append(str(uuid.uuid4()))
            #                 elif col == 'created_at':
            #                     new_values.append(now_str)
            #                 else:
            #                     new_values.append(None)
            #         food_df[col] = new_values
            
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
        if 'created_at' in food_df.columns:
            food_df['created_at'] = food_df['created_at'].fillna(now_str)

        food_df = food_df[column_name]
        Path(output_file_path).parent.mkdir(parents=True, exist_ok=True)
        # food_df.to_csv(output_file_path, index=False, na_rep='\\N')

        logging.info(f"Ingredients table generated: {output_file_path}")

        return food_df

    except Exception as e:
        logging.error(f"Error reading food.csv: {e}")
        raise e

def                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               table_ingredient_nutrients_generation(input_food_path, input_nut_path, output_file_path):
    try:
        input_food_path = Path(input_food_path)
        input_nut_path = Path(input_nut_path)
        output_file_path = Path(output_file_path)

        logging.info('loading data...')
        # 1. 获取目标 ID 集合
        ordered_target_nut_ids = TargetConfigure.get_all_nut_id()
        target_nut_ids = set(ordered_target_nut_ids)
        target_fdc_ids = set(TargetConfigure.get_all_fdc_id())

        # 2. 读取食材表 (Food)
        food_df = pd.read_csv(input_food_path, usecols=['id', 'fdc_id'])
        food_df = food_df[food_df['fdc_id'].isin(target_fdc_ids)]
        food_df = food_df.rename(columns={'id': 'ingredient_id'})
        
        ordered_ingredients = food_df['ingredient_id'].unique()

        # 3. 读取营养素表 (Nutrient)
        nut_df = pd.read_csv(input_nut_path, usecols=['fdc_id', 'nutrient_id', 'amount'])
        nut_df = nut_df[
            (nut_df['fdc_id'].isin(target_fdc_ids)) & 
            (nut_df['nutrient_id'].isin(target_nut_ids))
        ]

        logging.info('Building skeleton and merging...')

        # 4. 数据预处理：将 UUID (ingredient_id) 映射到 营养素数据上
        actual_data = pd.merge(food_df, nut_df, on='fdc_id', how='inner')

        full_index = pd.MultiIndex.from_product(
            [ordered_ingredients, ordered_target_nut_ids],
            names=['ingredient_id', 'nutrient_id']
        )
        skeleton_df = pd.DataFrame(index=full_index).reset_index()

        # 6. 左连接补全 (Left Join)
        # 用骨架去“套”实际数据。如果骨架有(需要该营养素)但实际数据没有，就会产生 NaN
        final_df = pd.merge(
            skeleton_df, 
            actual_data[['ingredient_id', 'nutrient_id', 'amount', 'fdc_id']], # 只取需要的列合并
            on=['ingredient_id', 'nutrient_id'], 
            how='left',
        )

        final_df['amount'] = final_df['amount'].fillna(0.0)

        now_str = pd.Timestamp.now().isoformat()
        final_df['created_at'] = now_str
        final_df['data_source'] = 'usda'

        # 8. 格式化输出
        # 注意：这里去掉了 fdc_id，因为长表通常只需要 ingredient_id 关联。
        # 如果你确实需要 fdc_id，需要在 merge 后重新从 food_df 映射回来，但通常 ingredient_nutrients 表不需要 fdc_id。
        final_df = final_df[['ingredient_id', 'nutrient_id', 'amount', 'fdc_id', 'data_source', 'created_at']]
        
        # 理论行数检查
        expected_rows = len(ordered_ingredients) * len(ordered_target_nut_ids)
        logging.info(f"生成完毕: 实际 {len(final_df)} 行 / 理论 {expected_rows} 行")

        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        # final_df.to_csv(output_file_path, index=False)
        logging.info(f"Saved to: {output_file_path}")

        return final_df
    except Exception as e:
        logging.error(f"Error reading {input_food_path}: {e}")

def _get_food_subgroup(row: pd.Series) -> str:
    try:
        group = row.get('food_group', 'OTHER')
        desc = str(row.get('description', '')).lower()
        fat_val = row.get(NutrientID.FAT, 0.0)

        # 1. 蛋白质 - 肉类 (按脂肪分级)
        if group == 'PROTEIN_MEAT':
            if fat_val < 10.0:
                return 'meat_lean'
            elif fat_val < 15.0:
                return 'meat_moderate'
            else:
                return 'meat_fat'
        
        # 2. 蛋白质 - 鱼类 (按种类分级)
        if group == 'PROTEIN_FISH':
            # 常见油性鱼关键词 (富含 Omega-3)
            oily_keywords = [
                'salmon', 'mackerel', 'sardine', 'herring', 'anchovy', 
                'trout', 'sprat', 'smelt', 'pilchard', 'whitebait'
            ]
            if any(k in desc for k in oily_keywords):
                return 'fish_oily'
            return 'fish_lean' # 鳕鱼, 罗非鱼等

        if group == 'PROTEIN_SHELLFISH':
            # 定义“蛋白型贝壳类”关键词
            protein_shellfish = ['shrimp', 'prawn', 'squid', 'octopus', 'calamari', 'lobster', 'crayfish', 'crab']
            # 逻辑分流
            if any(k in desc for k in protein_shellfish):
                # 晋升为瘦鱼，参与主食蛋白竞争
                return 'protein_shellfish'
            return 'mineral_shellfish' # 贝类

        if group == 'MINERAL_SHELLFISH':
            mineral_shellfish = ['oyster', 'mussel', 'clam', 'cockle', 'scallop']

            if any(k in desc for k in mineral_shellfish):
                # 晋升为瘦鱼，参与主食蛋白竞争
                return 'mineral_shellfish'
            return 'protein_shellfish' # 贝类

        if group == 'PROTEIN_EGG':
            return 'egg'

        # 3. 内脏 (按功能解剖分级)
        if group == 'ORGAN':
            # 3.1 肝脏 (维A宝库)
            if 'liver' in desc:
                return 'organ_liver'
            
            # 3.2 分泌型内脏 (Secreting - 富含B族/矿物质)
            secreting_keywords = [
                'kidney', 'spleen', 'pancreas', 'thymus', 'sweetbread', 
                'brain', 'testicle', 'fries'
            ]
            if any(k in desc for k in secreting_keywords):
                return 'organ_secreting'
            
            # 3.3 肌肉型内脏 (Muscular - 类似瘦肉)
            muscular_keywords = [
                'heart', 'gizzard', 'tongue', 'lung', 'stomach', 'tripe', 'cheek'
            ]
            if any(k in desc for k in muscular_keywords):
                return 'organ_muscular'
                
            return 'organ_other'
        # 4. 碳水化合物
        if group == 'CARB_GRAIN':
            return 'carb_grain' # 米, 麦, 燕麦
        
        if group == 'CARB_TUBER':
            return 'carb_tuber' # 土豆, 红薯, 山药

        if group == 'CARB_LEGUME':
            return 'carb_legume'
            
        if group == 'CARB_OTHER':
            # 可能是豆类等
            return 'carb_other'

        #5. 蔬果和纤维
        if group == 'PLANT_ANTIOXIDANT':
            for pattern, div, rep in IdentityTagger.PLANT_PATTERNS:
                if pattern.search(desc):
                    if div == 'div_plant_orange':
                        return 'plant_orange'
                    elif div == 'div_plant_green':
                        return 'plant_green'
                    elif div == 'div_plant_blue':
                        return 'plant_blue'
                    elif div == 'div_plant_white':
                        return 'plant_white'
            
        if group == 'FIBER':
            return 'fiber' # 洋车前子等

        # 6. 油脂 (FAT_OIL)
        if group == 'FAT_OIL':
            # 6.1 Omega-3 (EPA/DHA)
            if any(k in desc for k in ['fish oil', 'salmon oil', 'krill', 'cod liver', 'menhaden']):
                return 'oil_omega3_lc'
                
            # 6.2 Omega-6 (亚油酸) - 植物油或禽油
            # 常见高LA油: 葵花籽, 玉米, 大豆, 核桃, 鸡油
            if any(k in desc for k in ['sunflower', 'corn', 'soy', 'safflower', 'walnut', 'hemp', 'cottonseed']):
                return 'oil_omega6_la'
                
            # 6.3 动物油 (饱和脂肪为主)
            if any(k in desc for k in ['lard', 'tallow', 'duck', 'chicken', 'suet', 'goose', 'turkey', 'beef', 'pork']):
                return 'fat_animal'
                
            return 'oil_other' # 橄榄油, 椰子油等

        # 7. 补充剂 (SUPPLEMENT)
        if group == 'SUPPLEMENT':
            if any(k in desc for k in ['calcium', 'bone meal', 'egg shell', 'carbonate']):
                return 'supplement_calcium'
                
            if any(k in desc for k in ['iodine', 'kelp', 'seaweed', 'dulse']):
                return 'supplement_iodine'
                
            if any(k in desc for k in ['fish oil', 'omega']):
                return 'supplement_omega3_lc'
                
            if any(k in desc for k in ['zinc', 'manganese', 'iron', 'copper', 'magnesium']):
                return 'supplement_mineral'
                
            if 'multi' in desc and 'vitamin' in desc:
                return 'supplement_multivitamin'
                
            if any(k in desc for k in ['glucosamine', 'chondroitin', 'probiotic']):
                return 'supplement_functional'

            return 'supplement_other'

    except Exception as e:
        logging.warning(f"Error in _get_food_subgroup: {str(e)}")
        return 'others'

def generate_role_risk_tags(df:pd.DataFrame, config: AutoTagConfig, nut_id: int):
    if df.empty:
        logging.error(f"data is empty!")
        return None

    if nut_id not in df.columns:
        logging.error(f"generate_role_risk_tags: 营养素ID {nut_id} 不在df列中")
        return pd.Series([""]*len(df), index=df.index)  # 返回空标签列

    nut_col = df[nut_id]
    tag_series = pd.Series([""]*len(df), index=df.index)

    try:
        default_th = ThresholdValue(99999999.0, 'mg/1000kcal')
        default_tag = ""
        th_config, tag_name = config.role_thresholds.get(nut_id, (default_th, default_tag))
        unit_factor = UnitConverter.get_unit_factor(nut_id, th_config.unit, pd)
        base_factor = UnitConverter.get_base_factor(nut_id, )
        nut_th_val = UnitConverter.th_config.value
        if nut_id == NutrientID.CALCIUM:
            nut_th = config.role_thresholds.get(nut_id, 20000.0)
            nut_th_val = nut_th[0].value
            Ca_P_Ratio_th = 1.5
            phosphorus_col = df[NutrientID.PHOSPHORUS]

        elif nut_id == NutrientID.EPA or nut_id == NutrientID.DHA:
            th = config.role_thresholds.get(nut_id, 600.0)
        else:
            th = config.role_thresholds.get(nut_id, 9999999.0)
    except Exception as e:
        logging.error(f"Error in generate_role_risk_tags: {str(e)}")

def _determine_repeat_policy(row, risk_tags):
    """
    根据 Subgroup 和 Risk Tags 生成频次策略。
    """
    subgroup = row.get('food_subgroup', '')
    desc = str(row.get('description', '')).lower()
    
    # =======================================================
    # 1. 风险一票否决 (Risk Veto) - 优先级最高
    # =======================================================
    # 必须微量的风险 -> policy_freq_low
    micro_risks = ['risk_high_copper', 'risk_high_iodine', 'risk_high_vit_a', 'risk_high_vit_d', 'risk_high_selenium']
    if any(r in risk_tags for r in micro_risks):
        return 'policy_freq_low'

    # 只能偶尔的风险 -> policy_freq_once (或 low)
    occasional_risks = ['risk_high_sodium', 'risk_high_mercury']
    if any(r in risk_tags for r in occasional_risks):
        return 'policy_freq_once'

    # =======================================================
    # 2. 根据 Subgroup 定性
    # =======================================================
    
    # --- A. Daily Safe (7/7) ---
    # 包含了主粮碳水、瘦肉、骨骼、钙补充剂
    # 重点：carb_grain (米饭/燕麦) 和 carb_tuber (红薯) 在这里
    daily_subgroups = [
        'meat_lean', 'meat_moderate', 
        'carb_grain', 'carb_tuber',  # <--- 碳水归为此类
        'bone_edible', 'supplement_calcium'
    ]
    if subgroup in daily_subgroups:
        return 'policy_freq_daily'

    # --- B. High Freq (4/7) ---
    # 常见蔬菜、水果(作为零食)、蛋类
    if subgroup in ['vegetable', 'fruit', 'egg']:
        # 温和蔬菜可以升级为 Daily
        if any(x in desc for x in ['pumpkin', 'squash', 'carrot', 'zucchini']):
            return 'policy_freq_daily'
        return 'policy_freq_high'

    # --- C. Medium Freq (3/7) ---
    # 豆类 (限制胀气)、油性鱼 (限制脂肪酸过载)
    if subgroup in ['carb_legume', 'fish_oily', 'fish_lean']:
        return 'policy_freq_medium'

    # --- D. Low Freq (2/7) ---
    # 内脏、油脂、普通补充剂
    if 'organ' in subgroup or 'oil' in subgroup or 'supplement' in subgroup or 'fat' in subgroup:
        return 'policy_freq_low'
        
    # --- E. Occasional (1/7) ---
    if subgroup == 'meat_fat':
        return 'policy_freq_once'

    # 默认兜底
    return 'policy_freq_medium'

def append_tag(series: pd.Series, mask: pd.Series, new_tag: str, sep: str = ",") -> pd.Series:
    """
    向满足条件的行追加标签（去重+规范分隔符）
    :param series: 原标签列
    :param mask: 布尔掩码（True=需要追加标签）
    :param new_tag: 要追加的标签名
    :param sep: 标签分隔符（默认逗号）
    :return: 更新后的标签列
    """
    # 只处理mask为True的行
    mask_rows = series[mask]
    for idx in mask_rows.index:
        current_tags = series.loc[idx].strip()
        # 1. 空值：直接赋值标签
        if not current_tags:
            series.loc[idx] = new_tag
        # 2. 已有标签：检查是否重复，不重复则追加
        elif new_tag not in current_tags.split(sep):
            series.loc[idx] = f"{current_tags}{sep}{new_tag}"
    return series

def _generate_diversity_tags(food_name, category_id):
    """
    根据 Category ID 初筛，再用 Regex 确诊
    """
    tags = []
    
    # --- A. 动物蛋白处理逻辑 ---
    # 针对: 禽(5), 猪(10), 牛(13), 鱼(15), 羊/野味(17), 蛋(1), 香肠(7)
    if category_id in [1, 5, 7, 10, 13, 15, 17]:
        
        # 1. 特种 (Exotic) - 优先检查 (Rabbit 常常混在 17 里)
        if DiversityPatterns.EXOTIC.search(food_name):
            return ["div_protein_exotic"]
            
        # 2. 贝类 (Shellfish) - 优先于鱼
        if DiversityPatterns.SHELLFISH.search(food_name):
            return ["div_protein_shellfish"]
            
        # 3. 鱼类 (Fish)
        if DiversityPatterns.FISH.search(food_name):
            return ["div_protein_fish"]
            
        # 4. 猪 (Pork) - Cat 10 或者是 Cat 7 里的 ham
        if category_id == 10 or DiversityPatterns.PORK.search(food_name):
            return ["div_protein_pork"]
            
        # 5. 反刍 (Ruminant) - Cat 13, 17
        if category_id in [13, 17] or DiversityPatterns.RUMINANT.search(food_name):
            return ["div_protein_ruminant"]
            
        # 6. 水禽 (Waterfowl) - 鸭鹅
        if DiversityPatterns.WATERFOWL.search(food_name):
            return ["div_protein_waterfowl"]
            
        # 7. 陆禽 (Poultry) - 鸡火鸡 + 蛋
        if category_id in [1, 5] or DiversityPatterns.POULTRY.search(food_name):
            return ["div_protein_poultry"]

    # --- B. 植物处理逻辑 ---
    # 针对: 蔬菜(11), 水果(9), 豆类(16)
    elif category_id in [9, 11, 16]:
        
        # 1. 浆果 (Berry)
        if DiversityPatterns.BERRY.search(food_name):
            return ["div_plant_berry"]
            
        # 2. 十字花科 (Cruciferous) - 优先级高于 Leafy
        if DiversityPatterns.CRUCIFEROUS.search(food_name):
            return ["div_plant_cruciferous"]
            
        # 3. 绿叶 (Leafy)
        if DiversityPatterns.LEAFY.search(food_name):
            return ["div_plant_leafy"]
            
        # 4. 橙/红/黄 (Orange)
        if DiversityPatterns.ORANGE.search(food_name):
            return ["div_plant_orange"]
            
        # 5. 水果 (Fruit)
        if category_id == 9 or DiversityPatterns.FRUIT.search(food_name):
            # 注意：这里可能需要防误判，比如 "Apple" 匹配到了 "Pineapple" (正则已处理边界 \b)
            # 但如果它已经是 Vegetable (11) 但被正则匹配到 Fruit，我们信任正则
            return ["div_plant_fruit"]
            
        # 6. 其他 (Other)
        if DiversityPatterns.OTHER_VEG.search(food_name):
            return ["div_plant_other"]
            
        # 兜底：如果是蔬菜分类但没匹配到正则，归为 Other
        if category_id == 11:
            return ["div_plant_other"]

    return tags

def validate_input_data(df_food, df_nut):
    """验证输入数据的完整性"""
    # 检查必需列
    required_food_cols = ['ingredient_id', 'description', 'fdc_id', 'food_subgroup']
    missing_cols = [col for col in required_food_cols if col not in df_food.columns]
    if missing_cols:
        raise ValueError(f"Missing columns in food data: {missing_cols}")
    
    # 检查数据质量
    if df_food['ingredient_id'].isna().any():
        raise ValueError("Found NaN values in ingredient_id")
    
    # 检查营养数据
    if df_nut.empty:
        raise ValueError("Nutrition data is empty")

def table_ingredient_tags_generation(
    path_food_new: str,             # food_new.csv
    path_nutrient_data: str,    # food_nutrient_new.csv
    path_nutrient_def: str,     # nutrient_new.csv
    output_path: str,
    config: AutoTagConfig):
    try:
        logging.info("1. Loading & Pivoting Data...")
        # 1. 读取食材主表
        # 假设 food_group 列存的是 'meat_lean', 'organ_liver' 等细分分类
        cols_to_use = ['id', 'food_group', 'fdc_id', 'description', 'food_category_id']
        df_food = pd.read_csv(path_food_new, usecols=cols_to_use)
        df_food.rename(columns={'id': 'ingredient_id'}, inplace=True)
        df_food.set_index('ingredient_id', inplace=True)

        # 2. 读取营养素定义 (获取单位)
        df_nut_def = pd.read_csv(path_nutrient_def, usecols=['nutrient_id', 'unit_name'])
        unit_map = dict(zip(df_nut_def['nutrient_id'], df_nut_def['unit_name']))

        # 3. 读取并透视营养素表
        df_nut_data = pd.read_csv(path_nutrient_data, usecols=['ingredient_id', 'nutrient_id', 'amount'])
        df_nut_pivot = df_nut_data.pivot(index='ingredient_id', columns='nutrient_id', values='amount').fillna(0)

        # 这一步很关键：确保 ENERGY 列存在且安全
        if NutrientID.ENERGY not in df_nut_pivot.columns:
            logging.error("Missing ENERGY column!")
            return
        energy_series = df_nut_pivot[NutrientID.ENERGY]

        logging.info("2. Applying Tag Logic (Smart Rules)...")

        df_final = df_nut_pivot.join(df_food)

        # ==========================================
        # PHASE 1: Generate Subgroup
        # ==========================================
        logging.info("2. Generating Food Subgroups...")
        # 确保计算所需的营养素列存在
        if NutrientID.FAT not in df_final.columns:
            df_final[NutrientID.FAT] = 0.0
        
        df_final['food_subgroup'] = df_final.apply(_get_food_subgroup, axis=1)
        df_food['food_subgroup'] = df_final['food_subgroup']
        df_food.to_csv('./data/new_food_data.csv', index=False, encoding='utf-8')

        # ------------------------------------------------
        # PHASE 2: Generate Tags (Role/Risk)
        # ------------------------------------------------
        logging.info("3. Calculating Role & Risk Tags...")
        df_final['role_tags'] = ""
        df_final['risk_tags'] = ""

        # 定义要处理的循环列表：(配置字典, 目标列名, 类型标识)
        loops = [
            (config.role_rules, 'role_tags', 'ROLE'),
            (config.risk_rules, 'risk_tags', 'RISK')
        ]

        audit_col_tracker = set()

        for rule_dict, target_col, tag_type in loops:
            for nut_id, rule_list in rule_dict.items():
                for rule in rule_list:

                    source_unit = unit_map.get(nut_id, 'g')
                    raw_values = None

                    # 特殊逻辑：EPA (处理 Sum)
                    if rule.source_type == 'SUM_EPA_DHA':
                        # 特殊逻辑：求和
                        val_epa = df_nut_pivot.get(NutrientID.EPA, 0)
                        val_dha = df_nut_pivot.get(NutrientID.DHA, 0)
                        raw_values = val_epa + val_dha
                        source_unit = unit_map.get(NutrientID.EPA, 'g') # 借用 EPA 单位
                    elif nut_id in df_nut_pivot.columns:
                        # 标准逻辑
                        raw_values = df_nut_pivot[nut_id]
                    else:
                        continue # 数据缺失，跳过

                    # --- B. 核心计算 ---
                    mag_factor = UnitConverter.get_unit_factor(nut_id, source_unit, rule.threshold.unit)
                    base_factor = UnitConverter.get_base_factor(energy_series, rule.threshold.unit)
                    
                    # --- B. 计算标准化数值 (Density) ---
                    norm_values = (raw_values * mag_factor * base_factor).fillna(0)
                    
                    # --- C. 阈值判断 (生成 Mask) ---
                    # a. 密度
                    mask = norm_values >= rule.threshold.value
                    
                    # b. 绝对含量门槛，避免超低热量食材
                    if rule.min_raw_value > 0:
                        is_zero_cal = energy_series <= 1.0
                        mask_floor = raw_values >= rule.min_raw_value
                        mask = (mask | is_zero_cal) & mask_floor

                    if getattr(rule, 'name_regex', None):
                        # 在 short_name 中搜索 (不区分大小写)
                        mask_regex = df_final['description'].str.contains(
                            rule.name_regex, 
                            case=False, 
                            regex=True, 
                            na=False
                        )
                        # [🟢 关键] 取并集：数值达标 OR 名字匹配
                        # 这样即使 raw_values 是 0 (数据缺失)，只要名字对，mask 也会变 True
                        mask = mask | mask_regex

                    # === 4. 公共过滤器 (Categories & Ca:P) ===
                    # c. 类型过滤，确保 df_final 中有 food_category_id 列
                    if 'food_category_id' in df_final.columns:
                        if rule.allowed_categories:
                            mask_cat = df_final['food_category_id'].isin(rule.allowed_categories)
                            mask = mask & mask_cat
                        
                        if rule.excluded_categories:
                            mask_exclude = ~df_final['food_category_id'].isin(rule.excluded_categories)
                            mask = mask & mask_exclude
                
                    if rule.requires_ca_p_balance:
                        ca = df_nut_pivot.get(NutrientID.CALCIUM, 0)
                        p = df_nut_pivot.get(NutrientID.PHOSPHORUS, 0)
                        ratios = np.divide(
                            ca, 
                            p, 
                            out=np.full_like(ca, np.inf), # 当分母为0时，填充为无穷大
                            where=(p > 1e-6)              # 仅当 P > 0 时才进行除法
                        )
                        
                        # 只需要比率 > 1.5 即可 (无穷大也满足 > 1.5)
                        # 前提是 Ca 本身要大于 0 (避免 0/0 的情况)
                        ca_p_threshold = config.get_ca_p_threshold()
                        mask_ratio = (ratios > ca_p_threshold) & (ca > 0)
                        
                        mask = mask & mask_ratio

                    # --- E. 写入标签 ---
                    if mask.any():
                        # [技巧] 前面加逗号，最后再 strip，比 if else 快
                        df_final.loc[mask, target_col] += "," + rule.tag_name

                # --- F. [关键] 生成审计检查列 (Audit Columns) ---
                audit_key = rule.tag_name
                if audit_key not in audit_col_tracker:
                    # 1. 密度值
                    df_final[f'chk_{audit_key}_val'] = norm_values.round(2)
                    # 2. 是否通过 (BOOL)
                    df_final[f'chk_{audit_key}_pass'] = mask.astype(int)
                    # 3. 原始值 (方便检查 min_raw_value 是否生效)
                    df_final[f'chk_{audit_key}_raw'] = raw_values.round(2)
                    
                    audit_col_tracker.add(audit_key)                
                
                # 4. (可选) 如果是钙，把比例也打出来
                if nut_id == NutrientID.CALCIUM:
                     df_final[f'chk_{rule.tag_name}_ratio'] = (df_nut_pivot[NutrientID.CALCIUM] / df_nut_pivot[NutrientID.PHOSPHORUS].replace(0, np.nan)).round(2)

        # ==========================================
        # PHASE 3: Identity Tags (Diversity & Repeat)
        # ==========================================
        logging.info("3. Generating Identity Tags (Diversity & Repeat)...")
        # 使用 apply 调用 IdentityTagger
        # result_type='expand' 会将返回的 tuple 拆分成多列
        identity_results = df_final.apply(
            lambda row: IdentityTagger.get_tags(row['description'], row['food_category_id']),
            axis=1, result_type='expand'
        )
        # 将结果赋值给新列
        df_final[['diversity_tags', 'repeat_tags']] = identity_results.iloc[:, :2]

        # ==========================================
        # PHASE 4: Transform Dataset Type
        # ==========================================
        logging.info("5. Transforming to DB Format (Exploding)...")
        df_final_chk = df_final.copy()
        def clean_tags(tag_str):
            if not isinstance(tag_str, str) or not tag_str: return ""
            # 分割、去空、去重、排序
            tags = [t.strip() for t in tag_str.split(',') if t.strip()]
            return ",".join(sorted(list(set(tags))))

        # 清洗所有 Tag 列
        for col in ['role_tags', 'risk_tags', 'diversity_tags', 'repeat_tags']:
            df_final_chk[col] = df_final_chk[col].apply(clean_tags)

        # 列排序优化：基础信息 -> Tags -> 审计列
        cols = list(df_final_chk.columns)
        tag_cols = ['role_tags', 'risk_tags', 'diversity_tags', 'repeat_tags']
        audit_cols = sorted([c for c in cols if isinstance(c, str) and c.startswith('chk_')])
        base_cols = [c for c in cols if c not in audit_cols and c not in tag_cols]
        
        # 将重要的 Tag 列放到最前面，方便查看
        final_col_order = base_cols + tag_cols + audit_cols
        df_final_chk = df_final_chk[final_col_order]

        df_chk_uutput_path = data_dir / 'food_tag_chk.csv'
        Path(df_chk_uutput_path).parent.mkdir(parents=True, exist_ok=True)
        df_final_chk.to_csv(df_chk_uutput_path)

        # 定义列名到 DB ENUM 的映射
        tag_mapping = {
            'role_tags': 'role',
            'risk_tags': 'risk',
            'diversity_tags': 'diversity',
            'repeat_tags': 'repeat_policy',
        }
        # 选取需要的列进行 Melt (宽变长)
        # 包含你要求的检测列：description, fdc_id
        id_vars = ['food_subgroup', 'description', 'fdc_id'] 
        value_vars = list(tag_mapping.keys())
        
        # Reset index to make ingredient_id a column
        df_reset = df_final.reset_index()
        
        # Melt 操作
        df_melted = df_reset.melt(
            id_vars=['ingredient_id'] + id_vars,
            value_vars=value_vars,
            var_name='source_col',
            value_name='tag_string'
        )

        # 过滤掉空标签
        df_melted = df_melted[df_melted['tag_string'] != ""]
        df_melted = df_melted.dropna(subset=['tag_string'])

        # 将逗号分隔的字符串炸开 (Explode)
        # 1. 拆分字符串为列表
        df_melted['tag_list'] = df_melted['tag_string'].apply(lambda x: [t.strip() for t in x.split(',') if t.strip()])
        # 2. Explode 列表
        df_exploded = df_melted.explode('tag_list')

        # ------------------------------------------------
        # PHASE 5: 最终格式化
        # ------------------------------------------------
        logging.info("6. Formatting Final Output...")
        
        # 映射 tag_type
        df_exploded['tag_type'] = df_exploded['source_col'].map(tag_mapping)
        
        # 重命名 tag 列
        df_exploded.rename(columns={'tag_list': 'tag'}, inplace=True)
        
        # 添加 source 列
        df_exploded['source'] = 'system'

        now_str = pd.Timestamp.now().isoformat()
        df_exploded['created_at'] = now_str
        
        # 选取最终列 (注意顺序，虽然 CSV 不强制，但为了清晰)
        final_cols = [
            'ingredient_id', 
            'tag_type', 
            'tag', 
            'source', 
            'created_at',       # 检测用
            'food_subgroup'
        ]
        
        df_final_export = df_exploded[final_cols].copy()
        
        # 去重 (防止同一个 Tag 在同一个 Type 下重复，虽然逻辑上不应该发生)
        df_final_export.drop_duplicates(subset=['ingredient_id', 'tag_type', 'tag'], inplace=True)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df_final_export.to_csv(output_path, index=False)
        
        logging.info(f"Done. Database import file saved to: {output_path}")
        logging.info(f"Total Rows: {len(df_final_export)}")

    except FileNotFoundError as e:
        logging.error(f"Input file not found: {e}")
        raise
    except pd.errors.ParserError as e:
        logging.error(f"CSV parsing error: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected ETL error: {e}", exc_info=True)
        raise

# if __name__ == "__main__":
#     current_file = Path(__file__).resolve()
#     project_root = current_file.parent.parent.parent

#     th_config = AutoTagConfig()

#     data_dir = project_root / 'data'
#     nutrient_input_csv = data_dir / 'nutrient.csv'
#     nutrient_output_csv = data_dir / 'nutrient_new.csv'

#     ingredient_input_csv = data_dir / 'food.csv'
#     ingredient_output_csv = data_dir / 'food_new_1.csv'

#     input_food_csv = ingredient_output_csv
#     input_nut_csv = data_dir / 'food_nutrient.csv'
#     ing_nut_output_csv = data_dir / 'food_nutrient_new.csv'

#     ing_tags_input_csv = data_dir / 'food_tag.csv'
#     ing_tags_output_csv = data_dir / 'food_tag_new.csv'

#     try:
#         nutrient_df = table_nutrients_generation(nutrient_input_csv, nutrient_output_csv)
#         ingredient_df = table_ingredients_generation(ingredient_input_csv, ingredient_output_csv)

#         ing_nut_df = table_ingredient_nutrients_generation(input_food_csv, input_nut_csv, ing_nut_output_csv)
#         ing_tag_df = table_ingredient_tags_generation(ingredient_output_csv, ing_nut_output_csv, nutrient_output_csv, ing_tags_output_csv, th_config)
#     except Exception as e:
#         logging.error(f"Error generating nutrients table: {e}")
