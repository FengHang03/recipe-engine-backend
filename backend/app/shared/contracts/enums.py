"""
@author: <NAME>
path: /backend/app/shared/contracts/enums.py
"""
from enum import Enum, IntEnum, unique

@unique
class NutrientID(IntEnum):
    """
    营养素 ID 定义 (USDA 标准 ID)
    保持纯净，只做标识符
    """
    # === 基础 ===
    ENERGY           = 1008
    WATER            = 1051
    ASH              = 1007
    
    # === 宏量 ===
    PROTEIN          = 1003
    FAT              = 1004
    CARBOHYDRATE     = 1005
    FIBER            = 1079
    
    # === 氨基酸 ===
    ARGININE         = 1220
    HISTIDINE        = 1221
    ISOLEUCINE       = 1212
    LEUCINE          = 1213
    LYSINE           = 1214
    METHIONINE       = 1215
    CYSTINE          = 1216
    PHENYLALANINE    = 1217
    TYROSINE         = 1218
    THREONINE        = 1211
    TRYPTOPHAN       = 1210
    VALINE           = 1219
    
    # === 脂肪酸 ===
    LA               = 1269 # Linoleic 18:2 n-6
    ALA              = 1404 # Alpha-Linolenic 18:3 n-3
    ARA              = 1271 # Arachidonic 20:4
    EPA              = 1278
    DHA              = 1272
    
    # === 矿物质 ===
    CALCIUM          = 1087
    PHOSPHORUS       = 1091
    POTASSIUM        = 1092
    SODIUM           = 1093
    CHLORIDE         = 1088
    MAGNESIUM        = 1090
    IRON             = 1089
    COPPER           = 1098
    MANGANESE        = 1101
    ZINC             = 1095
    IODINE           = 1100
    SELENIUM         = 1103

    # === 维生素 ===
    VITAMIN_A        = 1104
    VITAMIN_D        = 1110
    VITAMIN_E        = 1109
    THIAMIN          = 1165
    RIBOFLAVIN       = 1166
    NIACIN           = 1167
    PANTOTHENIC_ACID = 1170
    PYRIDOXINE       = 1175
    VITAMIN_B12      = 1178
    FOLIC_ACID       = 1186
    CHOLINE          = 1180

# 静态元数据定义 (比运行时加载 CSV 更快更稳)
# 如果你需要多语言支持或动态配置，才建议保留 CSV 加载逻辑
NUTRIENT_METADATA = {
    NutrientID.PROTEIN: {'name': 'Protein', 'unit_name': 'G'},
    NutrientID.FAT: {'name': 'Total lipid (fat)', 'unit_name': 'G'},
    NutrientID.CARBOHYDRATE: {'name': 'Carbohydrate, by difference', 'unit_name': 'G'},
    NutrientID.ASH: {'name': 'Ash', 'unit_name': 'G'},
    NutrientID.ENERGY: {'name': 'Energy', 'unit_name': 'KCAL'},
    NutrientID.WATER: {'name': 'Water', 'unit_name': 'G'},
    NutrientID.FIBER: {'name': 'Fiber, total dietary', 'unit_name': 'G'},
    NutrientID.CALCIUM: {'name': 'Calcium, Ca', 'unit_name': 'MG'},
    NutrientID.CHLORIDE: {'name': 'Chlorine, Cl', 'unit_name': 'MG'},
    NutrientID.IRON: {'name': 'Iron, Fe', 'unit_name': 'MG'},
    NutrientID.MAGNESIUM: {'name': 'Magnesium, Mg', 'unit_name': 'MG'},
    NutrientID.PHOSPHORUS: {'name': 'Phosphorus, P', 'unit_name': 'MG'},
    NutrientID.POTASSIUM: {'name': 'Potassium, K', 'unit_name': 'MG'},
    NutrientID.SODIUM: {'name': 'Sodium, Na', 'unit_name': 'MG'},
    NutrientID.ZINC: {'name': 'Zinc, Zn', 'unit_name': 'MG'},
    NutrientID.COPPER: {'name': 'Copper, Cu', 'unit_name': 'MG'},
    NutrientID.IODINE: {'name': 'Iodine, I', 'unit_name': 'UG'},
    NutrientID.MANGANESE: {'name': 'Manganese, Mn', 'unit_name': 'MG'},
    NutrientID.SELENIUM: {'name': 'Selenium, Se', 'unit_name': 'UG'},
    NutrientID.VITAMIN_A: {'name': 'Vitamin A, IU', 'unit_name': 'IU'},
    NutrientID.VITAMIN_E: {'name': 'Vitamin E (alpha-tocopherol)', 'unit_name': 'MG'},
    NutrientID.VITAMIN_D: {'name': 'Vitamin D (D2 + D3), International Units', 'unit_name': 'IU'},
    NutrientID.THIAMIN: {'name': 'Thiamin', 'unit_name': 'MG'},
    NutrientID.RIBOFLAVIN: {'name': 'Riboflavin', 'unit_name': 'MG'},
    NutrientID.NIACIN: {'name': 'Niacin', 'unit_name': 'MG'},
    NutrientID.PANTOTHENIC_ACID: {'name': 'Pantothenic acid', 'unit_name': 'MG'},
    NutrientID.PYRIDOXINE: {'name': 'Vitamin B-6', 'unit_name': 'MG'},
    NutrientID.VITAMIN_B12: {'name': 'Vitamin B-12', 'unit_name': 'UG'},
    NutrientID.CHOLINE: {'name': 'Choline, total', 'unit_name': 'MG'},
    NutrientID.FOLIC_ACID: {'name': 'Folic acid', 'unit_name': 'UG'},
    NutrientID.TRYPTOPHAN: {'name': 'Tryptophan', 'unit_name': 'G'},
    NutrientID.THREONINE: {'name': 'Threonine', 'unit_name': 'G'},
    NutrientID.ISOLEUCINE: {'name': 'Isoleucine', 'unit_name': 'G'},
    NutrientID.LEUCINE: {'name': 'Leucine', 'unit_name': 'G'},
    NutrientID.LYSINE: {'name': 'Lysine', 'unit_name': 'G'},
    NutrientID.METHIONINE: {'name': 'Methionine', 'unit_name': 'G'},
    NutrientID.CYSTINE: {'name': 'Cystine', 'unit_name': 'G'},
    NutrientID.PHENYLALANINE: {'name': 'Phenylalanine', 'unit_name': 'G'},
    NutrientID.TYROSINE: {'name': 'Tyrosine', 'unit_name': 'G'},
    NutrientID.VALINE: {'name': 'Valine', 'unit_name': 'G'},
    NutrientID.ARGININE: {'name': 'Arginine', 'unit_name': 'G'},
    NutrientID.HISTIDINE: {'name': 'Histidine', 'unit_name': 'G'},
    NutrientID.LA: {'name': 'PUFA 18:2', 'unit_name': 'G'},
    NutrientID.ARA: {'name': 'PUFA 20:4', 'unit_name': 'G'},
    NutrientID.DHA: {'name': 'PUFA 22:6 n-3 (DHA)', 'unit_name': 'G'},
    NutrientID.EPA: {'name': 'PUFA 20:5 n-3 (EPA)', 'unit_name': 'G'},
    NutrientID.ALA: {'name': 'PUFA 18:3 n-3 c,c,c (ALA)', 'unit_name': 'G'},
    "CA_P_RATIO": {"name": "Calcium:Phosphorus Ratio", "unit": "ratio"},
    "N6_N3_RATIO": {"name": "Omega-6:Omega-3 Ratio", "unit": "ratio"},
    "EPA_DHA_SUM": {"name": "EPA + DHA", "unit": "G"},
}

class FoodGroup(str, Enum):
    """食材大类"""
    PROTEIN_MEAT = "PROTEIN_MEAT"
    PROTEIN_FISH = "PROTEIN_FISH"
    PROTEIN_EGG = "PROTEIN_EGG"
    PROTEIN_SHELLFISH = "PROTEIN_SHELLFISH"
    MINERAL_SHELLFISH = "MINERAL_SHELLFISH"
    
    # 内脏 (3个组)
    ORGAN = "ORGAN"
    
    CARB_GRAIN = "CARB_GRAIN"
    CARB_TUBER = "CARB_TUBER"
    CARB_LEGUME = "CARB_LEGUME"
    CARB_OTHER = "CARB_OTHER"
    PLANT_ANTIOXIDANT = "PLANT_ANTIOXIDANT"
    FAT_OIL = "FAT_OIL"
    FIBER = "FIBER"
    SUPPLEMENT = "SUPPLEMENT"
    TREAT = "TREAT"
    DAIRY = "DAIRY"

class FoodSubgroup(str, Enum):
    """食材子类"""
    # 肉类
    MEAT_LEAN = "meat_lean"
    MEAT_MODERATE = "meat_moderate"
    MEAT_FAT = "meat_fat"
    
    # 鱼类
    FISH_LEAN = "fish_lean"
    FISH_OILY = "fish_oily"
    
    # 内脏 - 3-subgroup 方案
    # === ORGAN_LIVER 组 ===
    LIVER = "organ_liver"  # 肝脏 (鸡肝、牛肝、猪肝)
    
    # === ORGAN_SECRETING 组 ===
    KIDNEY = "organ_kidney"              # 肾脏
    SPLEEN = "organ_spleen"              # 脾脏
    BRAIN = "organ_brain"                # 脑花
    ORGAN_SECRETING = "organ_secreting"  # 胰腺、睾丸等
    
    # === ORGAN_MUSCULAR 组 ===
    HEART = "heart"                     # 心脏
    GIZZARD = "gizzard"                 # 胗 (鸡胗、鸭胗)
    ORGAN_MUSCULAR = "organ_muscular"   # 舌、肺、肚
    
    # 碳水
    CARB_GRAIN = "carb_grain"
    CARB_TUBER = "carb_tuber"
    CARB_LEGUME = "carb_legume"
    
    # 蔬菜
    PLANT_ORANGE = "plant_orange"  # 红/橙/黄色蔬菜
    PLANT_GREEN = "plant_green"    # 绿叶蔬菜
    PLANT_BLUE = "plant_blue"      # 蓝/紫色蔬菜
    PLANT_WHITE = "plant_white"    # 白色蔬菜
    PLANT_OTHER = "plant_other"
    
    # 其他
    FIBER_PLANT = "fiber_plant"
    FIBER_SUPPLEMENT = "supplement_fiber"
    OIL_OMEGA3_LC = "oil_omega3_lc"
    OIL_OMEGA6_LA = "oil_omega6_la"
    MINERAL_SHELLFISH = "mineral_shellfish"
    PROTEIN_SHELLFISH = "protein_shellfish"
    EGG = "egg"
    DAIRY = "dairy"
    SUPPLEMENT_CALCIUM = "supplement_calcium"
    SUPPLEMENT_IODINE = "supplement_iodine"
    SUPPLEMENT_OMEGA3 = "supplement_omega3_lc"
    SUPPLEMENT_OTHER = "supplement_other"

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

# 分组映射
NUTRIENT_GROUPS = {
    NutrientGroup.MINERALS: {
        NutrientID.CALCIUM, NutrientID.PHOSPHORUS, NutrientID.ZINC, # ...
    },
    NutrientGroup.PROTEIN: {
        NutrientID.ARGININE, NutrientID.LYSINE, # ...
    }
}



class Species(str, Enum):
    DOG = "dog"
    CAT = "cat"

class LifeStage(str,Enum):
    """生命阶段"""
    DOG_ADULT = "adult"
    DOG_PUPPY = "puppy"
    DOG_SENIOR = "senior"

    def to_aafco_standard(self):
        """映射回 AAFCO 标准"""
        if self == LifeStage.DOG_SENIOR:
            return LifeStage.DOG_ADULT
        return self

class SizeClass(str,Enum):
    TOY     = "toy"
    SMALL   = "small"
    MEDIUM  = "medium"
    LARGE   = "large"
    GIANT   = "giant"

class ActivityLevel(str,Enum):
    SEDENTARY = "sedentary"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"

class SterilizationStatus(str, Enum):
    INTACT = "intact"
    NEUTERED = "neutered"


class ReproductiveStage(str, Enum):
    NONE = "none"
    PREGNANT = "pregnant"
    LACTATING = "lactating"


class BodyConditionGoal(str, Enum):
    MAINTAIN = "maintain"
    LOSE = "lose"
    GAIN = "gain"


class AdultEnergyProfile(str, Enum):
    LOW_ACTIVITY = "low_activity_adult"
    MODERATE_ACTIVITY = "moderate_activity_adult"
    ACTIVE = "active_adult"


class EstimateConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# === L1 & L2 ===
class SlotType(str, Enum):
    """槽位类型（值用 snake_case，作为字典 key 和 slot_name 字符串）"""
    MAIN_PROTEIN         = "main_protein"
    SHELLFISH_PROTEIN    = "shellfish_protein"
    EGG                  = "egg"
    CALCIUM              = "calcium"
    MINERAL_SHELLFISH    = "mineral_shellfish"
    ORGAN_LIVER          = "organ_liver"
    ORGAN_SECRETING      = "organ_secreting"
    ORGAN_MUSCULAR       = "organ_muscular"
    VEGETABLE            = "vegetable"
    OMEGA3_LC            = "omega3_lc"
    OMEGA6_LA            = "omega6_la"
    CARBOHYDRATE         = "carbohydrate"
    IODINE               = "iodine"
    FIBER                = "fiber"
    SUPPLEMENT           = "supplement"
    SUPPLEMENT_CALCIUM   = "supplement_calcium"
    OPTIONAL_INGREDIENTS = "optional_ingredients"
