"""
AAFCO 营养标准配置 (2023年标准)
AAFCO Nutritional Standards Configuration

所有营养素单位均为 per 1000 kcal ME (Metabolizable Energy)
"""

from app.common.enums import LifeStage, NutrientID
from .l2_data_models import NutrientConstraint


# ==================== AAFCO 标准 (生产级配置) ====================

AAFCO_STANDARDS = {
    LifeStage.DOG_ADULT: {
        # ===== 宏量营养素 =====
        NutrientID.PROTEIN: {
            "min": 45.0,
            "max": None,
            "unit": "G",
            "nutrient_id": NutrientID.PROTEIN,
            "priority": 1,
            "tolerance": 0.05,  # 允许 5% 误差
            "source": "AAFCO 2023"
        },

        # ===== 氨基酸 =====
        NutrientID.ARGININE: {
            "min": 1.28,
            "max": None,
            "unit": "G",
            "nutrient_id": NutrientID.ARGININE,
            "priority": 2,
            "source": "AAFCO 2023"
        },

        NutrientID.HISTIDINE: {
            "min": 0.48,
            "max": None,
            "unit": "G",
            "nutrient_id": NutrientID.HISTIDINE,
            "priority": 2,
            "source": "AAFCO 2023"
        },

        NutrientID.ISOLEUCINE: {
            "min": 0.95,
            "max": None,
            "unit": "G",
            "nutrient_id": NutrientID.ISOLEUCINE,
            "priority": 2,
            "source": "AAFCO 2023"
        },

        NutrientID.LEUCINE: {
            "min": 1.70,
            "max": None,
            "unit": "G",
            "nutrient_id": NutrientID.LEUCINE,
            "priority": 2,
            "source": "AAFCO 2023"
        },

        NutrientID.LYSINE: {
            "min": 1.58,
            "max": None,
            "unit": "G",
            "nutrient_id": NutrientID.LYSINE,
            "priority": 2,
            "source": "AAFCO 2023"
        },

        NutrientID.METHIONINE: {
            "min": 0.83,
            "max": None,
            "unit": "G",
            "nutrient_id": NutrientID.METHIONINE,
            "priority": 2,
            "source": "AAFCO 2023"
        },

        NutrientID.CYSTINE: {
            "min": 1.63,
            "max": None,
            "unit": "G",
            "nutrient_id": NutrientID.CYSTINE,
            "priority": 2,
            "source": "AAFCO 2023"
        },

        NutrientID.PHENYLALANINE: {
            "min": 1.13,
            "max": None,
            "unit": "G",
            "nutrient_id": NutrientID.PHENYLALANINE,
            "priority": 2,
            "source": "AAFCO 2023"
        },

        NutrientID.TYROSINE: {
            "min": 1.85,
            "max": None,
            "unit": "G",
            "nutrient_id": NutrientID.TYROSINE,
            "priority": 2,
            "source": "AAFCO 2023"
        },

        NutrientID.THREONINE: {
            "min": 1.20,
            "max": None,
            "unit": "G",
            "nutrient_id": NutrientID.THREONINE,
            "priority": 2,
            "source": "AAFCO 2023"
        },

        NutrientID.TRYPTOPHAN: {
            "min": 0.40,
            "max": None,
            "unit": "G",
            "nutrient_id": NutrientID.TRYPTOPHAN,
            "priority": 2,
            "source": "AAFCO 2023"
        },

        NutrientID.VALINE: {
            "min": 1.23,
            "max": None,
            "unit": "G",
            "nutrient_id": NutrientID.VALINE,
            "priority": 2,
            "source": "AAFCO 2023"
        },

        NutrientID.FAT: {
            "min": 13.8,
            "max": None,
            "unit": "G",
            "nutrient_id": NutrientID.FAT,
            "priority": 1,
            "tolerance": 0.05,
            "source": "AAFCO 2023"
        },
        
        # ===== 矿物质 (骨骼) =====
        NutrientID.CALCIUM: {
            "min": 1250,        # 1.25 g
            "max_soft": 4000,   # 4.5 g (NRC 推荐)
            "max_hard": 4500,   # 6.25 g (AAFCO 法定上限)
            "ideal": 2000,      # 理想目标
            "unit": "MG",
            "nutrient_id": NutrientID.CALCIUM,
            "priority": 0,      # P0 级别
            "source": "AAFCO 2023, NRC 2006"
        },
        
        NutrientID.PHOSPHORUS: {
            "min": 1000,        # 1.0 g
            "max": 4000,        # 4.0 g
            "unit": "MG",
            "nutrient_id": NutrientID.PHOSPHORUS,
            "priority": 0,
            "source": "AAFCO 2023"
        },
        
        "CA_P_RATIO": {
            "min": 1.0,
            "max": 2.0,
            "ideal": 1.3,       # 理想比率
            "unit": "",
            "priority": 0.05,
            "source": "AAFCO 2023"
        },
        
        # ===== 矿物质 (微量元素) =====
        # NutrientID.IRON: {
        #     "min": 10,
        #     "max": 500,         # NRC Safe Upper Limit
        #     "unit": "MG",
        #     "nutrient_id": NutrientID.IRON,
        #     "priority": 1,
        #     "source": "AAFCO 2023, NRC SUL"
        # },
        
        # NutrientID.ZINC: {
        #     "min": 20,
        #     "max": 250,         # NRC Safe Upper Limit
        #     "ideal": 30,        # 鼓励稍高于最低要求
        #     "unit": "MG",
        #     "nutrient_id": NutrientID.ZINC,
        #     "priority": 1,
        #     "penalty_type": "balance",
        #     "source": "AAFCO 2023, NRC SUL"
        # },
        
        # NutrientID.COPPER: {
        #     "min": 1.83,
        #     "max": 30,          # NRC Safe Upper Limit
        #     "ideal": 5.0,       # 理想范围: 3-8 mg
        #     "unit": "MG",
        #     "nutrient_id": NutrientID.COPPER,
        #     "priority": 1,
        #     "penalty_type": "balance",
        #     "source": "AAFCO 2023, NRC SUL"
        # },
        
        # NutrientID.MANGANESE: {
        #     "min": 1.25,
        #     "max": None,
        #     "ideal": 2.0,       # 建议有安全冗余
        #     "unit": "MG",
        #     "nutrient_id": NutrientID.MANGANESE,
        #     "priority": 1,
        #     "penalty_type": "balance",
        #     "source": "AAFCO 2023"
        # },
        
        # NutrientID.SELENIUM: {
        #     "min": 80,          # 0.08 mg = 80 µg
        #     "max": 500,         # 0.5 mg = 500 µg
        #     "safe_target": 120, # ALARA: 越低越好
        #     "warning_target": 300,
        #     "unit": "UG",
        #     "nutrient_id": NutrientID.SELENIUM,
        #     "priority": 0,      # P0 - 毒性风险
        #     "penalty_type": "alara",
        #     "source": "AAFCO 2023"
        # },
        
        # NutrientID.IODINE: {
        #     "min": 0.25,
        #     "max": 2.75,
        #     "safe_target": 0.5, # ALARA
        #     "warning_target": 1.5,
        #     "unit": "MG",
        #     "nutrient_id": NutrientID.IODINE,
        #     "priority": 0,      # P0 - 毒性风险
        #     "penalty_type": "alara",
        #     "source": "AAFCO 2023"
        # },

        NutrientID.CHLORIDE: {
            "min": 0.30,        # 1.5 g
            "max": None,
            "unit": "G",
            "nutrient_id": NutrientID.CHLORIDE,
            "priority": 2,
            "source": "AAFCO 2023"
        },
        
        # ===== 电解质 =====
        NutrientID.POTASSIUM: {
            "min": 1500,        # 1.5 g
            "max": None,
            "unit": "MG",
            "nutrient_id": NutrientID.POTASSIUM,
            "priority": 2,
            "source": "AAFCO 2023"
        },
        
        NutrientID.SODIUM: {
            "min": 200,         # 0.2 g
            "max": None,
            "unit": "MG",
            "nutrient_id": NutrientID.SODIUM,
            "priority": 2,
            "source": "AAFCO 2023"
        },
        
        NutrientID.MAGNESIUM: {
            "min": 150,         # 0.15 g
            "max": None,
            "unit": "MG",
            "nutrient_id": NutrientID.MAGNESIUM,
            "priority": 2,
            "source": "AAFCO 2023"
        },
        
        # ===== 维生素 =====
        NutrientID.VITAMIN_A: {
            "min": 1250,
            "max": 62500,
            "safe_target": 10000,    # ALARA
            "warning_target": 30000,
            "unit": "IU",
            "nutrient_id": NutrientID.VITAMIN_A,
            "priority": 0,           # P0 - 毒性风险
            "penalty_type": "alara",
            "source": "AAFCO 2023"
        },
        
        NutrientID.VITAMIN_D: {
            "min": 125,
            "max": 750,
            "safe_target": 200,      # ALARA
            "warning_target": 500,
            "unit": "IU",
            "nutrient_id": NutrientID.VITAMIN_D,
            "priority": 0,           # P0 - 毒性风险
            "penalty_type": "alara",
            "source": "AAFCO 2023"
        },
        
        NutrientID.VITAMIN_E: {
            "min": 12.5,        # 保持 IU,不转换
            "max": 1000,        # NRC Upper Limit (很难超)
            "unit": "IU",
            "nutrient_id": NutrientID.VITAMIN_E,
            "priority": 1,
            "source": "AAFCO 2023, NRC SUL"
        },
        
        NutrientID.THIAMIN: {
            "min": 0.56,
            "max": None,
            "unit": "MG",
            "nutrient_id": NutrientID.THIAMIN,
            "priority": 2,
            "source": "AAFCO 2023"
        },

        NutrientID.NIACIN: {
            "min": 3.4,
            "max": None,
            "unit": "MG",
            "nutrient_id": NutrientID.NIACIN,
            "priority": 2,
            "source": "AAFCO 2023"
        },

        NutrientID.PYRIDOXINE: {
            "min": 0.38,
            "max": None,
            "unit": "MG",
            "nutrient_id": NutrientID.NIACIN,
            "priority": 2,
            "source": "AAFCO 2023"
        },

        NutrientID.FOLIC_ACID: {
            "min": 54,
            "max": None,
            "unit": "UG",
            "nutrient_id": NutrientID.NIACIN,
            "priority": 2,
            "source": "AAFCO 2023"
        },
        
        NutrientID.CHOLINE: {
            "min": 340,
            "max": None,
            "unit": "MG",
            "nutrient_id": NutrientID.CHOLINE,
            "priority": 2,
            "source": "AAFCO 2023"
        },
        
        NutrientID.VITAMIN_B12: {
            "min": 7,           # 0.007 mg = 7 µg
            "max": None,
            "unit": "UG",
            "nutrient_id": NutrientID.VITAMIN_B12,
            "priority": 2,
            "source": "AAFCO 2023"
        },
        
        NutrientID.RIBOFLAVIN: {
            "min": 1.3,
            "max": None,
            "unit": "MG",
            "nutrient_id": NutrientID.RIBOFLAVIN,
            "priority": 2,
            "source": "AAFCO 2023"
        },

        NutrientID.PANTOTHENIC_ACID: {
            "min": 3.0,
            "max": None,
            "unit": "MG",
            "nutrient_id": NutrientID.PANTOTHENIC_ACID,
            "priority": 2,
            "source": "AAFCO 2023"
        },
        
        # ===== 脂肪酸 =====
        NutrientID.LA: {
            "min": 2.8,         # 亚油酸 (Omega-6)
            "max": None,
            "unit": "G",
            "nutrient_id": NutrientID.LA,
            "priority": 1,
            "source": "AAFCO 2023"
        },
        
        NutrientID.ALA: {
            "min": None,        # 成犬不强制
            "recommended": 0.1, # 但推荐有
            "max": None,
            "unit": "G",
            "nutrient_id": NutrientID.ALA,
            "priority": 2,
            "source": "NRC 2006"
        },

        NutrientID.ARA: {
            "min": None,
            "max": None,
            "unit": "G",
            "nutrient_id": NutrientID.ARA,
            "priority": 2
        },
        
        NutrientID.EPA: {
            "min": None,
            "max": None,
            "unit": "G",
            "nutrient_id": NutrientID.EPA,
            "priority": 2
        },
        
        NutrientID.DHA: {
            "min": None,
            "max": None,
            "unit": "G",
            "nutrient_id": NutrientID.DHA,
            "priority": 2
        },
        
        "EPA_DHA_SUM": {
            "min": None,            # 成犬不强制
            "recommended": 0.11,    # NRC 推荐
            "max": None,
            "unit": "G",
            "priority": 2,
            "source": "NRC 2006"
        },
        
        # ===== 比率约束 =====
        "N6_N3_RATIO": {
            "min": None,
            "max": 30.0,        # Omega-6 : Omega-3 不超过 30:1
            "unit": "",
            "priority": 2,
            "source": "AAFCO 2023"
        }
    },
    
    # ==================== 幼犬标准 ====================
    LifeStage.DOG_PUPPY: {
        # ===== 宏量营养素 =====
        NutrientID.PROTEIN: {
            "min": 56.3,
            "max": None,
            "unit": "G",
            "nutrient_id": NutrientID.PROTEIN,
            "priority": 1,
            "tolerance": 0.05,
            "source": "AAFCO 2023"
        },
        
        NutrientID.FAT: {
            "min": 21.3,
            "max": None,
            "unit": "G",
            "nutrient_id": NutrientID.FAT,
            "priority": 1,
            "tolerance": 0.05,
            "source": "AAFCO 2023"
        },
        
        # ===== 矿物质 (骨骼) - 幼犬要求更高 =====
        NutrientID.CALCIUM: {
            "min": 3000,        # 3.0 g (比成犬高)
            "max": 4500,        # 4.5 g (比成犬更严格!)
            "ideal": 3500,
            "unit": "MG",
            "nutrient_id": NutrientID.CALCIUM,
            "priority": 0,
            "source": "AAFCO 2023"
        },
        
        NutrientID.PHOSPHORUS: {
            "min": 2500,        # 2.5 g
            "max": 4000,
            "unit": "MG",
            "nutrient_id": NutrientID.PHOSPHORUS,
            "priority": 0,
            "source": "AAFCO 2023"
        },
        
        "CA_P_RATIO": {
            "min": 1.0,         # 更宽的范围
            "max": 2.0,
            "ideal": 1.3,
            "unit": "",
            "priority": 0,
            "source": "AAFCO 2023"
        },
        
        # # ===== 微量元素 =====
        # NutrientID.IRON: {
        #     "min": 22,          # 比成犬高
        #     "max": 500,
        #     "unit": "MG",
        #     "nutrient_id": NutrientID.IRON,
        #     "priority": 1,
        #     "source": "AAFCO 2023"
        # },
        
        # NutrientID.ZINC: {
        #     "min": 25,          # 比成犬高
        #     "max": 250,
        #     "ideal": 35,
        #     "unit": "MG",
        #     "nutrient_id": NutrientID.ZINC,
        #     "priority": 1,
        #     "penalty_type": "balance",
        #     "source": "AAFCO 2023"
        # },
        
        # NutrientID.COPPER: {
        #     "min": 3.1,         # 比成犬高
        #     "max": 30,
        #     "ideal": 6.0,
        #     "unit": "MG",
        #     "nutrient_id": NutrientID.COPPER,
        #     "priority": 1,
        #     "penalty_type": "balance",
        #     "source": "AAFCO 2023"
        # },
        
        # NutrientID.MANGANESE: {
        #     "min": 1.8,         # 比成犬高
        #     "max": None,
        #     "ideal": 2.5,
        #     "unit": "MG",
        #     "nutrient_id": NutrientID.MANGANESE,
        #     "priority": 1,
        #     "penalty_type": "balance",
        #     "source": "AAFCO 2023"
        # },
        
        # NutrientID.SELENIUM: {
        #     "min": 90,          # 修正: 90 µg (不是 500!)
        #     "max": 500,
        #     "safe_target": 150,
        #     "warning_target": 350,
        #     "unit": "UG",
        #     "nutrient_id": NutrientID.SELENIUM,
        #     "priority": 0,
        #     "penalty_type": "alara",
        #     "source": "AAFCO 2023"
        # },
        
        # NutrientID.IODINE: {
        #     "min": 0.25,
        #     "max": 2.75,
        #     "safe_target": 0.5,
        #     "warning_target": 1.5,
        #     "unit": "MG",
        #     "nutrient_id": NutrientID.IODINE,
        #     "priority": 0,
        #     "penalty_type": "alara",
        #     "source": "AAFCO 2023"
        # },

        # NutrientID.CHLORIDE: {
        #     "min": 1.10,        # 1.5 g
        #     "max": None,
        #     "unit": "G",
        #     "nutrient_id": NutrientID.CHLORIDE,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },
        
        # # ===== 电解质 =====
        # NutrientID.POTASSIUM: {
        #     "min": 1500,
        #     "max": None,
        #     "unit": "MG",
        #     "nutrient_id": NutrientID.POTASSIUM,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },
        
        # NutrientID.SODIUM: {
        #     "min": 800,         # 比成犬高
        #     "max": None,
        #     "unit": "MG",
        #     "nutrient_id": NutrientID.SODIUM,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },
        
        # NutrientID.MAGNESIUM: {
        #     "min": 140,
        #     "max": None,
        #     "unit": "MG",
        #     "nutrient_id": NutrientID.MAGNESIUM,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },
        
        # # ===== 维生素 =====
        # NutrientID.VITAMIN_A: {
        #     "min": 1250,
        #     "max": 62500,
        #     "safe_target": 10000,
        #     "warning_target": 30000,
        #     "unit": "IU",
        #     "nutrient_id": NutrientID.VITAMIN_A,
        #     "priority": 0,
        #     "penalty_type": "alara",
        #     "source": "AAFCO 2023"
        # },
        
        # NutrientID.VITAMIN_D: {
        #     "min": 125,
        #     "max": 750,
        #     "safe_target": 200,
        #     "warning_target": 500,
        #     "unit": "IU",
        #     "nutrient_id": NutrientID.VITAMIN_D,
        #     "priority": 0,
        #     "penalty_type": "alara",
        #     "source": "AAFCO 2023"
        # },
        
        # NutrientID.VITAMIN_E: {
        #     "min": 12.5,
        #     "max": 1000,
        #     "unit": "IU",
        #     "nutrient_id": NutrientID.VITAMIN_E,
        #     "priority": 1,
        #     "source": "AAFCO 2023"
        # },
        
        # NutrientID.THIAMIN: {
        #     "min": 0.56,
        #     "max": None,
        #     "unit": "MG",
        #     "nutrient_id": NutrientID.THIAMIN,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },

        # NutrientID.NIACIN: {
        #     "min": 3.4,
        #     "max": None,
        #     "unit": "MG",
        #     "nutrient_id": NutrientID.NIACIN,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },

        # NutrientID.PYRIDOXINE: {
        #     "min": 0.38,
        #     "max": None,
        #     "unit": "MG",
        #     "nutrient_id": NutrientID.NIACIN,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },

        # NutrientID.FOLIC_ACID: {
        #     "min": 54,
        #     "max": None,
        #     "unit": "UG",
        #     "nutrient_id": NutrientID.NIACIN,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },
        
        # NutrientID.VITAMIN_B12: {
        #     "min": 7,
        #     "max": None,
        #     "unit": "UG",
        #     "nutrient_id": NutrientID.VITAMIN_B12,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },
        
        # NutrientID.CHOLINE: {
        #     "min": 340,
        #     "max": None,
        #     "unit": "MG",
        #     "nutrient_id": NutrientID.CHOLINE,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },

        # NutrientID.RIBOFLAVIN: {
        #     "min": 1.3,
        #     "max": None,
        #     "unit": "MG",
        #     "nutrient_id": NutrientID.RIBOFLAVIN,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },

        # NutrientID.PANTOTHENIC_ACID: {
        #     "min": 3.0,
        #     "max": None,
        #     "unit": "MG",
        #     "nutrient_id": NutrientID.PANTOTHENIC_ACID,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },
        

        # # ===== 氨基酸 =====
        # NutrientID.ARGININE: {
        #     "min": 2.50,
        #     "max": None,
        #     "unit": "G",
        #     "nutrient_id": NutrientID.ARGININE,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },

        # NutrientID.HISTIDINE: {
        #     "min": 1.10,
        #     "max": None,
        #     "unit": "G",
        #     "nutrient_id": NutrientID.HISTIDINE,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },

        # NutrientID.ISOLEUCINE: {
        #     "min": 1.78,
        #     "max": None,
        #     "unit": "G",
        #     "nutrient_id": NutrientID.ISOLEUCINE,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },

        # NutrientID.LEUCINE: {
        #     "min": 3.23,
        #     "max": None,
        #     "unit": "G",
        #     "nutrient_id": NutrientID.LEUCINE,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },

        # NutrientID.LYSINE: {
        #     "min": 2.25,
        #     "max": None,
        #     "unit": "G",
        #     "nutrient_id": NutrientID.LYSINE,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },

        # NutrientID.METHIONINE: {
        #     "min": 0.88,
        #     "max": None,
        #     "unit": "G",
        #     "nutrient_id": NutrientID.METHIONINE,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },

        # NutrientID.CYSTINE: {
        #     "min": 1.75,
        #     "max": None,
        #     "unit": "G",
        #     "nutrient_id": NutrientID.CYSTINE,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },

        # NutrientID.PHENYLALANINE: {
        #     "min": 2.08,
        #     "max": None,
        #     "unit": "G",
        #     "nutrient_id": NutrientID.PHENYLALANINE,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },

        # NutrientID.TYROSINE: {
        #     "min": 3.25,
        #     "max": None,
        #     "unit": "G",
        #     "nutrient_id": NutrientID.TYROSINE,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },

        # NutrientID.THREONINE: {
        #     "min": 2.60,
        #     "max": None,
        #     "unit": "G",
        #     "nutrient_id": NutrientID.THREONINE,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },

        # NutrientID.TRYPTOPHAN: {
        #     "min": 0.50,
        #     "max": None,
        #     "unit": "G",
        #     "nutrient_id": NutrientID.TRYPTOPHAN,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },

        # NutrientID.VALINE: {
        #     "min": 1.70,
        #     "max": None,
        #     "unit": "G",
        #     "nutrient_id": NutrientID.VALINE,
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # },
        
        # # ===== 脂肪酸 =====
        # NutrientID.LA: {
        #     "min": 3.3,         # 比成犬高
        #     "max": None,
        #     "unit": "G",
        #     "nutrient_id": NutrientID.LA,
        #     "priority": 1,
        #     "source": "AAFCO 2023"
        # },
        
        # NutrientID.ALA: {
        #     "min": 0.2,         # 幼犬强制要求
        #     "max": None,
        #     "unit": "G",
        #     "nutrient_id": NutrientID.ALA,
        #     "priority": 1,
        #     "source": "AAFCO 2023"
        # },
        
        # NutrientID.EPA: {
        #     "min": None,
        #     "max": None,
        #     "unit": "G",
        #     "nutrient_id": NutrientID.EPA,
        #     "priority": 2
        # },
        
        # NutrientID.DHA: {
        #     "min": None,
        #     "max": None,
        #     "unit": "G",
        #     "nutrient_id": NutrientID.DHA,
        #     "priority": 2
        # },
        
        "EPA_DHA_SUM": {
            "min": 0.13,        # 幼犬强制要求! (修正为 0.13)
            "max": None,
            "unit": "G",
            "priority": 1,
            "condition": "if_no_fish",  # 如果有鱼类,可能自动满足
            "source": "AAFCO 2023"
        },
        
        # ===== 比率约束 =====
        # "N6_N3_RATIO": {
        #     "min": None,
        #     "max": 30.0,
        #     "unit": "",
        #     "priority": 2,
        #     "source": "AAFCO 2023"
        # }
    }
}


# ==================== 辅助函数 ====================

def get_constraint(life_stage: LifeStage, nutrient_id) -> dict:
    """
    获取指定营养素的约束
    
    Args:
        life_stage: 生命阶段
        nutrient_id: 营养素 ID (NutrientID 枚举或字符串)
        
    Returns:
        约束字典
    """
    standards = AAFCO_STANDARDS.get(life_stage, {})
    return standards.get(nutrient_id, {})


def get_all_p0_nutrients(life_stage: LifeStage) -> list:
    """获取所有 P0 级别的营养素"""
    standards = AAFCO_STANDARDS.get(life_stage, {})
    p0_nutrients = []
    
    for nutrient_id, constraint in standards.items():
        if isinstance(constraint, dict) and constraint.get("priority") == 0:
            p0_nutrients.append(nutrient_id)
    
    return p0_nutrients


def validate_standards():
    """验证 AAFCO 标准的完整性"""
    issues = []
    
    for stage, standards in AAFCO_STANDARDS.items():
        for nutrient_id, constraint in standards.items():
            # 判断是否为比率 (将 nutrient_id 转为字符串判断是否包含 "RATIO")
            is_ratio = "RATIO" in str(nutrient_id)
            if not is_ratio and "unit" not in constraint:
                issues.append(f"{stage.value} - {nutrient_id}: missing 'unit'")
            # 检查必需字段
            if "unit" not in constraint:
                issues.append(f"{stage.value} - {nutrient_id}: missing 'unit'")
            
            if "priority" not in constraint:
                issues.append(f"{stage.value} - {nutrient_id}: missing 'priority'")
            
            # 检查逻辑一致性
            min_val = constraint.get("min")
            max_val = constraint.get("max") or constraint.get("max_hard")
            
            if min_val and max_val and min_val >= max_val:
                issues.append(f"{stage.value} - {nutrient_id}: min >= max")
    
    if issues:
        print("⚠️ AAFCO Standards Validation Issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ AAFCO Standards validated successfully!")
    
    return len(issues) == 0


# 运行验证
if __name__ == "__main__":
    validate_standards()