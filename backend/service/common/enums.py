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
    NutrientID.ENERGY: {"name": "Energy", "unit": "kcal"},
    NutrientID.PROTEIN: {"name": "Protein", "unit": "g"},
    NutrientID.CALCIUM: {"name": "Calcium", "unit": "mg"},
    NutrientID.VITAMIN_A: {"name": "Vitamin A", "unit": "IU"},
    # ... 其他项 ...
}

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

class Species(str, Enum):
    DOG = "dog"
    CAT = "cat"

class LifeStage(Enum):
    """生命阶段"""
    DOG_ADULT = "adult"
    DOG_PUPPY = "puppy"
    DOG_SENIOR = "senior"

    def to_aafco_standard(self):
        """映射回 AAFCO 标准"""
        if self == LifeStage.SENIOR:
            return LifeStage.ADULT
        return self

class ActivityLevel(str,Enum):
    SEDENTARY = "sedentary"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"

class ReproductiveStatus(str, Enum):
    INTACT = "intact"
    NEUTERED = "neutered"

class ReproState(str, Enum):
    NONE = "none"
    PREGNANT = "pregnant"
    LACTATING = "lactating"

# === L1 & L2 ===
class SlotType(Enum):
    """食材槽位类型"""
    MAIN_PROTEIN = "main_protein"
    ORGAN_LIVER = "organ_liver"
    ORGAN_SECRETING = "organ_secreting"
    ORGAN_MUSCULAR = "organ_muscular"
    MINERAL_SHELLFISH = "mineral_shellfish"
    VEGETABLE = "vegetable"
    CARBOHYDRATE = "carbohydrate"
    OMEGA3_LC = "omega3_lc"
    OMEGA6_LA = "omega6_la"
    SUPPLEMENT = "supplement"
    SUPPLEMENT_CALCIUM = "supplement_calcium"
    IODINE = "iodine"