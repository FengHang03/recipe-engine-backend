from app.shared.contracts.enums import(
    NutrientID, LifeStage,
)
from app.domains.recipe_generation.contracts.constraints import NutrientConstraint


AAFCO_STANDARDS = {
    LifeStage.DOG_ADULT: {
        # ===== 宏量营养素 =====
        NutrientID.PROTEIN: NutrientConstraint(
            nutrient_id=NutrientID.PROTEIN,
            min=45.0,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=1,
            tolerance=0.05,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        # ===== 氨基酸 =====
        NutrientID.ARGININE: NutrientConstraint(
            nutrient_id=NutrientID.ARGININE,
            min=1.28,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.HISTIDINE: NutrientConstraint(
            nutrient_id=NutrientID.HISTIDINE,
            min=0.48,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.ISOLEUCINE: NutrientConstraint(
            nutrient_id=NutrientID.ISOLEUCINE,
            min=0.95,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.LEUCINE: NutrientConstraint(
            nutrient_id=NutrientID.LEUCINE,
            min=1.70,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.LYSINE: NutrientConstraint(
            nutrient_id=NutrientID.LYSINE,
            min=1.58,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.METHIONINE: NutrientConstraint(
            nutrient_id=NutrientID.METHIONINE,
            min=0.83,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.CYSTINE: NutrientConstraint(
            nutrient_id=NutrientID.CYSTINE,
            min=1.63,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.PHENYLALANINE: NutrientConstraint(
            nutrient_id=NutrientID.PHENYLALANINE,
            min=1.13,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.TYROSINE: NutrientConstraint(
            nutrient_id=NutrientID.TYROSINE,
            min=1.85,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.THREONINE: NutrientConstraint(
            nutrient_id=NutrientID.THREONINE,
            min=1.20,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.TRYPTOPHAN: NutrientConstraint(
            nutrient_id=NutrientID.TRYPTOPHAN,
            min=0.40,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.VALINE: NutrientConstraint(
            nutrient_id=NutrientID.VALINE,
            min=1.23,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.FAT: NutrientConstraint(
            nutrient_id=NutrientID.FAT,
            min=13.8,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=1,
            tolerance=0.05,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        # ===== 矿物质 (骨骼) =====
        NutrientID.CALCIUM: NutrientConstraint(
            nutrient_id=NutrientID.CALCIUM,
            min=1250.0,
            max=None,
            max_soft=4000.0,
            max_hard=4500.0,
            ideal=2000.0,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=0,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023, NRC 2006",
            condition=None
        ),
        
        NutrientID.PHOSPHORUS: NutrientConstraint(
            nutrient_id=NutrientID.PHOSPHORUS,
            min=1000.0,
            max=4000.0,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=0,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        "CA_P_RATIO": NutrientConstraint(
            nutrient_id="CA_P_RATIO",
            min=1.0,
            max=2.0,
            max_soft=None,
            max_hard=None,
            ideal=1.3,
            safe_target=None,
            warning_target=None,
            unit="",
            basis = "per_1000_kcal",
            priority=0,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        # ===== 矿物质 (微量元素) =====
        NutrientID.IRON: NutrientConstraint(
            nutrient_id=NutrientID.IRON,
            min=10.0,
            max=500.0,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=1,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023, NRC SUL",
            condition=None
        ),
        
        NutrientID.ZINC: NutrientConstraint(
            nutrient_id=NutrientID.ZINC,
            min=20.0,
            max=250.0,
            max_soft=None,
            max_hard=None,
            ideal=30.0,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type="balance",
            source="AAFCO 2023, NRC SUL",
            condition=None
        ),
        
        NutrientID.COPPER: NutrientConstraint(
            nutrient_id=NutrientID.COPPER,
            min=1.83,
            max=30.0,
            max_soft=None,
            max_hard=None,
            ideal=5.0,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=1,
            tolerance=None,
            penalty_type="balance",
            source="AAFCO 2023, NRC SUL",
            condition=None
        ),
        
        NutrientID.MANGANESE: NutrientConstraint(
            nutrient_id=NutrientID.MANGANESE,
            min=1.25,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=2.0,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type="balance",
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.SELENIUM: NutrientConstraint(
            nutrient_id=NutrientID.SELENIUM,
            min=80.0,
            max=500.0,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=120.0,
            warning_target=300.0,
            unit="UG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type="alara",
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.IODINE: NutrientConstraint(
            nutrient_id=NutrientID.IODINE,
            min=0.25,
            max=2.75,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=0.5,
            warning_target=1.5,
            unit="MG",
            basis = "per_1000_kcal",
            priority=0,
            tolerance=None,
            penalty_type="alara",
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.CHLORIDE: NutrientConstraint(
            nutrient_id=NutrientID.CHLORIDE,
            min=0.30,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        # ===== 电解质 =====
        NutrientID.POTASSIUM: NutrientConstraint(
            nutrient_id=NutrientID.POTASSIUM,
            min=1500.0,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.SODIUM: NutrientConstraint(
            nutrient_id=NutrientID.SODIUM,
            min=200.0,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.MAGNESIUM: NutrientConstraint(
            nutrient_id=NutrientID.MAGNESIUM,
            min=150.0,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        # ===== 维生素 =====
        NutrientID.VITAMIN_A: NutrientConstraint(
            nutrient_id=NutrientID.VITAMIN_A,
            min=1250.0,
            max=62500.0,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=10000.0,
            warning_target=30000.0,
            unit="IU",
            basis = "per_1000_kcal",
            priority=0,
            tolerance=None,
            penalty_type="alara",
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.VITAMIN_D: NutrientConstraint(
            nutrient_id=NutrientID.VITAMIN_D,
            min=125.0,
            max=750.0,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=200.0,
            warning_target=500.0,
            unit="IU",
            basis = "per_1000_kcal",
            priority=0,
            tolerance=None,
            penalty_type="alara",
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.VITAMIN_E: NutrientConstraint(
            nutrient_id=NutrientID.VITAMIN_E,
            min=12.5,
            max=1000.0,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="IU",
            basis = "per_1000_kcal",
            priority=1,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023, NRC SUL",
            condition=None
        ),
        
        NutrientID.THIAMIN: NutrientConstraint(
            nutrient_id=NutrientID.THIAMIN,
            min=0.56,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.NIACIN: NutrientConstraint(
            nutrient_id=NutrientID.NIACIN,
            min=3.4,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.PYRIDOXINE: NutrientConstraint(
            nutrient_id=NutrientID.PYRIDOXINE, 
            min=0.38,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.FOLIC_ACID: NutrientConstraint(
            nutrient_id=NutrientID.FOLIC_ACID, 
            min=54.0,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="UG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.CHOLINE: NutrientConstraint(
            nutrient_id=NutrientID.CHOLINE,
            min=340.0,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.VITAMIN_B12: NutrientConstraint(
            nutrient_id=NutrientID.VITAMIN_B12,
            min=7.0,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="UG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.RIBOFLAVIN: NutrientConstraint(
            nutrient_id=NutrientID.RIBOFLAVIN,
            min=1.3,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.PANTOTHENIC_ACID: NutrientConstraint(
            nutrient_id=NutrientID.PANTOTHENIC_ACID,
            min=3.0,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        # ===== 脂肪酸 =====
        NutrientID.LA: NutrientConstraint(
            nutrient_id=NutrientID.LA,
            min=2.8,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=1,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.ALA: NutrientConstraint(
            nutrient_id=NutrientID.ALA,
            min=None,  # 成犬不强制
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="NRC 2006",
            condition=None
        ),

        NutrientID.ARA: NutrientConstraint(
            nutrient_id=NutrientID.ARA,
            min=None,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source=None,
            condition=None
        ),
        
        NutrientID.EPA: NutrientConstraint(
            nutrient_id=NutrientID.EPA,
            min=None,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source=None,
            condition=None
        ),
        
        NutrientID.DHA: NutrientConstraint(
            nutrient_id=NutrientID.DHA,
            min=None,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source=None,
            condition=None
        ),
        
        "EPA_DHA_SUM": NutrientConstraint(
            nutrient_id="EPA_DHA_SUM",
            min=None,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="NRC 2006",
            condition=None
        ),
        
        # ===== 比率约束 =====
        "N6_N3_RATIO": NutrientConstraint(
            nutrient_id="N6_N3_RATIO",
            min=None,
            max=30.0,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        )
    },
    
    # ==================== Puppy Standard ====================
    LifeStage.DOG_PUPPY: {
        # ===== 宏量营养素 =====
        NutrientID.PROTEIN: NutrientConstraint(
            nutrient_id=NutrientID.PROTEIN,
            min=56.3,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=1,
            tolerance=0.05,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.FAT: NutrientConstraint(
            nutrient_id=NutrientID.FAT,
            min=21.3,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=1,
            tolerance=0.05,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        # ===== Mineral (骨骼) - 幼犬要求更高 =====
        NutrientID.CALCIUM: NutrientConstraint(
            nutrient_id=NutrientID.CALCIUM,
            min=3000.0,
            max=4500.0,
            max_soft=None,
            max_hard=None,
            ideal=3500.0,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=0,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.PHOSPHORUS: NutrientConstraint(
            nutrient_id=NutrientID.PHOSPHORUS,
            min=2500.0,
            max=4000.0,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=0,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        "CA_P_RATIO": NutrientConstraint(
            nutrient_id="CA_P_RATIO",
            min=1.0,
            max=2.0,
            max_soft=None,
            max_hard=None,
            ideal=1.3,
            safe_target=None,
            warning_target=None,
            unit="",
            basis = "per_1000_kcal",
            priority=0,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        # ===== Microelement =====
        NutrientID.IRON: NutrientConstraint(
            nutrient_id=NutrientID.IRON,
            min=22.0,
            max=500.0,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=1,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.ZINC: NutrientConstraint(
            nutrient_id=NutrientID.ZINC,
            min=25.0,
            max=250.0,
            max_soft=None,
            max_hard=None,
            ideal=35.0,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=1,
            tolerance=None,
            penalty_type="balance",
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.COPPER: NutrientConstraint(
            nutrient_id=NutrientID.COPPER,
            min=3.1,
            max=30.0,
            max_soft=None,
            max_hard=None,
            ideal=6.0,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=1,
            tolerance=None,
            penalty_type="balance",
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.MANGANESE: NutrientConstraint(
            nutrient_id=NutrientID.MANGANESE,
            min=1.8,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=2.5,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=1,
            tolerance=None,
            penalty_type="balance",
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.SELENIUM: NutrientConstraint(
            nutrient_id=NutrientID.SELENIUM,
            min=90.0,
            max=500.0,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=150.0,
            warning_target=350.0,
            unit="UG",
            basis = "per_1000_kcal",
            priority=0,
            tolerance=None,
            penalty_type="alara",
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.IODINE: NutrientConstraint(
            nutrient_id=NutrientID.IODINE,
            min=0.25,
            max=2.75,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=0.5,
            warning_target=1.5,
            unit="MG",
            basis = "per_1000_kcal",
            priority=0,
            tolerance=None,
            penalty_type="alara",
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.CHLORIDE: NutrientConstraint(
            nutrient_id=NutrientID.CHLORIDE,
            min=1.10,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        # ===== 电解质 =====
        NutrientID.POTASSIUM: NutrientConstraint(
            nutrient_id=NutrientID.POTASSIUM,
            min=1500.0,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.SODIUM: NutrientConstraint(
            nutrient_id=NutrientID.SODIUM,
            min=800.0,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.MAGNESIUM: NutrientConstraint(
            nutrient_id=NutrientID.MAGNESIUM,
            min=140.0,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        # ===== Vitamin =====
        NutrientID.VITAMIN_A: NutrientConstraint(
            nutrient_id=NutrientID.VITAMIN_A,
            min=1250.0,
            max=62500.0,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=10000.0,
            warning_target=30000.0,
            unit="IU",
            basis = "per_1000_kcal",
            priority=0,
            tolerance=None,
            penalty_type="alara",
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.VITAMIN_D: NutrientConstraint(
            nutrient_id=NutrientID.VITAMIN_D,
            min=125.0,
            max=750.0,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=200.0,
            warning_target=500.0,
            unit="IU",
            basis = "per_1000_kcal",
            priority=0,
            tolerance=None,
            penalty_type="alara",
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.VITAMIN_E: NutrientConstraint(
            nutrient_id=NutrientID.VITAMIN_E,
            min=12.5,
            max=1000.0,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="IU",
            basis = "per_1000_kcal",
            priority=1,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.THIAMIN: NutrientConstraint(
            nutrient_id=NutrientID.THIAMIN,
            min=0.56,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.NIACIN: NutrientConstraint(
            nutrient_id=NutrientID.NIACIN,
            min=3.4,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.PYRIDOXINE: NutrientConstraint(
            nutrient_id=NutrientID.PYRIDOXINE,
            min=0.38,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.FOLIC_ACID: NutrientConstraint(
            nutrient_id=NutrientID.FOLIC_ACID, 
            min=54.0,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="UG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.VITAMIN_B12: NutrientConstraint(
            nutrient_id=NutrientID.VITAMIN_B12,
            min=7.0,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="UG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.CHOLINE: NutrientConstraint(
            nutrient_id=NutrientID.CHOLINE,
            min=340.0,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.RIBOFLAVIN: NutrientConstraint(
            nutrient_id=NutrientID.RIBOFLAVIN,
            min=1.3,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.PANTOTHENIC_ACID: NutrientConstraint(
            nutrient_id=NutrientID.PANTOTHENIC_ACID,
            min=3.0,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="MG",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        # ===== 氨基酸 =====
        NutrientID.ARGININE: NutrientConstraint(
            nutrient_id=NutrientID.ARGININE,
            min=2.50,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.HISTIDINE: NutrientConstraint(
            nutrient_id=NutrientID.HISTIDINE,
            min=1.10,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.ISOLEUCINE: NutrientConstraint(
            nutrient_id=NutrientID.ISOLEUCINE,
            min=1.78,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.LEUCINE: NutrientConstraint(
            nutrient_id=NutrientID.LEUCINE,
            min=3.23,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.LYSINE: NutrientConstraint(
            nutrient_id=NutrientID.LYSINE,
            min=2.25,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.METHIONINE: NutrientConstraint(
            nutrient_id=NutrientID.METHIONINE,
            min=0.88,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.CYSTINE: NutrientConstraint(
            nutrient_id=NutrientID.CYSTINE,
            min=1.75,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.PHENYLALANINE: NutrientConstraint(
            nutrient_id=NutrientID.PHENYLALANINE,
            min=2.08,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.TYROSINE: NutrientConstraint(
            nutrient_id=NutrientID.TYROSINE,
            min=3.25,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.THREONINE: NutrientConstraint(
            nutrient_id=NutrientID.THREONINE,
            min=2.60,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.TRYPTOPHAN: NutrientConstraint(
            nutrient_id=NutrientID.TRYPTOPHAN,
            min=0.50,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),

        NutrientID.VALINE: NutrientConstraint(
            nutrient_id=NutrientID.VALINE,
            min=1.70,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        # ===== 脂肪酸 =====
        NutrientID.LA: NutrientConstraint(
            nutrient_id=NutrientID.LA,
            min=3.3,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=1,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.ALA: NutrientConstraint(
            nutrient_id=NutrientID.ALA,
            min=0.2,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=1,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        ),
        
        NutrientID.EPA: NutrientConstraint(
            nutrient_id=NutrientID.EPA,
            min=None,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source=None,
            condition=None
        ),
        
        NutrientID.DHA: NutrientConstraint(
            nutrient_id=NutrientID.DHA,
            min=None,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source=None,
            condition=None
        ),
        
        "EPA_DHA_SUM": NutrientConstraint(
            nutrient_id="EPA_DHA_SUM",
            min=0.13,
            max=None,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="G",
            basis = "per_1000_kcal",
            priority=1,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition="if_no_fish"
        ),
        
        # ===== 比率约束 =====
        "N6_N3_RATIO": NutrientConstraint(
            nutrient_id="N6_N3_RATIO",
            min=None,
            max=30.0,
            max_soft=None,
            max_hard=None,
            ideal=None,
            safe_target=None,
            warning_target=None,
            unit="",
            basis = "per_1000_kcal",
            priority=2,
            tolerance=None,
            penalty_type=None,
            source="AAFCO 2023",
            condition=None
        )
    }
}


# ==================== 辅助函数 ====================
def get_constraint(life_stage: LifeStage, nutrient_id) -> NutrientConstraint | None:
    """
    获取指定营养素的约束
    
    Args:
        life_stage: 生命阶段
        nutrient_id: 营养素 ID (NutrientID 枚举或字符串)
        
    Returns:
        约束对象
    """
    standards = AAFCO_STANDARDS.get(life_stage, {})
    return standards.get(nutrient_id)


def get_all_p0_nutrients(life_stage: LifeStage) -> list:
    """获取所有 P0 级别的营养素"""
    standards = AAFCO_STANDARDS.get(life_stage, {})
    p0_nutrients = []
    
    for nutrient_id, constraint in standards.items():
        if isinstance(constraint, NutrientConstraint) and constraint.priority == 0:
            p0_nutrients.append(nutrient_id)
    
    return p0_nutrients


def validate_standards():
    """验证 AAFCO 标准的完整性"""
    issues = []
    
    for stage, standards in AAFCO_STANDARDS.items():
        for nutrient_id, constraint in standards.items():
            if not isinstance(constraint, NutrientConstraint):
                issues.append(f"{stage.value} - {nutrient_id}: not a NutrientConstraint instance")
                continue
                
            # 判断是否为比率 (将 nutrient_id 转为字符串判断是否包含 "RATIO")
            is_ratio = "RATIO" in str(nutrient_id)
            
            # 检查必需字段
            if constraint.unit is None and not is_ratio:
                issues.append(f"{stage.value} - {nutrient_id}: missing 'unit'")
            
            if constraint.priority is None:
                issues.append(f"{stage.value} - {nutrient_id}: missing 'priority'")
            
            # 检查逻辑一致性
            min_val = constraint.min
            max_val = constraint.max or constraint.max_hard
            
            if min_val is not None and max_val is not None and min_val >= max_val:
                issues.append(f"{stage.value} - {nutrient_id}: min >= max")
    
    if issues:
        print("⚠️ AAFCO Standards Validation Issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ AAFCO Standards validated successfully!")
    
    return len(issues) == 0

