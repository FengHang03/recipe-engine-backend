from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .nutrient_ids import NutrientID, TagRule, ThresholdValue


@dataclass
class AutoTagConfig:
    use_percentiles: bool = True
    percentile: float = 0.70

    CATS_ANIMAL = [1, 5, 10, 13, 15, 17]
    CATS_FAT_SOURCES = [1, 4, 5, 10, 12, 13, 15, 16, 17]
    CATS_PLANT_ONLY = [9, 11, 12, 16, 20]
    CATS_SUPPLEMENT = [21]

    ca_p_ratio_threshold: float = 1.5

    role_rules: Dict[int, List[TagRule]] = field(default_factory=lambda: {
        NutrientID.PUFA_18_2: [
            TagRule(
                threshold=ThresholdValue(value=4000.0, unit="mg/1000kcal"),
                tag_name="role_omega6_la",
                min_raw_value=1.6,
                allowed_categories=AutoTagConfig.CATS_FAT_SOURCES + AutoTagConfig.CATS_SUPPLEMENT,
            )
        ],
        NutrientID.ALA: [
            TagRule(
                threshold=ThresholdValue(value=800.0, unit="mg/1000kcal"),
                tag_name="role_omega3_ala",
                min_raw_value=0.5,
                allowed_categories=AutoTagConfig.CATS_FAT_SOURCES + AutoTagConfig.CATS_SUPPLEMENT,
            )
        ],
        NutrientID.EPA: [
            TagRule(
                threshold=ThresholdValue(value=1000.0, unit="mg/1000kcal"),
                tag_name="role_omega3_lc",
                min_raw_value=0.05,
                allowed_categories=[15, 4, 21],
            ),
            TagRule(
                threshold=ThresholdValue(value=2500.0, unit="mg/1000kcal"),
                tag_name="role_omega3_lc",
                source_type="SUM_EPA_DHA",
                min_raw_value=0.06,
                allowed_categories=[15, 4, 21],
            ),
        ],
        NutrientID.DHA: [
            TagRule(
                threshold=ThresholdValue(value=1000.0, unit="mg/1000kcal"),
                tag_name="role_omega3_lc",
                min_raw_value=0.5,
                allowed_categories=[15, 4, 21],
            )
        ],
        NutrientID.CALCIUM: [
            TagRule(
                threshold=ThresholdValue(value=3000.0, unit="mg/1000kcal"),
                tag_name="role_calcium_source",
                requires_ca_p_balance=True,
                min_raw_value=100.0,
                excluded_categories=[2, 11],
            )
        ],
        NutrientID.IRON: [
            TagRule(
                threshold=ThresholdValue(value=14.4, unit="mg/1000kcal"),
                tag_name="role_iron",
                min_raw_value=0.5,
                allowed_categories=AutoTagConfig.CATS_ANIMAL + AutoTagConfig.CATS_SUPPLEMENT,
            )
        ],
        NutrientID.VITAMIN_B12: [
            TagRule(
                threshold=ThresholdValue(value=10.0, unit="μg/1000kcal"),
                tag_name="role_vit_b12",
                allowed_categories=AutoTagConfig.CATS_ANIMAL + AutoTagConfig.CATS_SUPPLEMENT,
            )
        ],
        NutrientID.FIBER: [
            TagRule(
                threshold=ThresholdValue(value=3.0, unit="g/1000kcal"),
                tag_name="role_fiber_source",
                min_raw_value=1.0,
                allowed_categories=AutoTagConfig.CATS_PLANT_ONLY + AutoTagConfig.CATS_SUPPLEMENT,
            )
        ],
        NutrientID.VITAMIN_A: [
            TagRule(
                threshold=ThresholdValue(value=5000.0, unit="IU/1000kcal"),
                tag_name="role_vita",
                min_raw_value=2000.0,
                excluded_categories=[2],
            )
        ],
        NutrientID.VITAMIN_D: [
            TagRule(
                threshold=ThresholdValue(value=150.0, unit="IU/1000kcal"),
                tag_name="role_vit_d",
                min_raw_value=10.0,
                allowed_categories=[1, 4, 5, 10, 13, 15, 17, 21],
            )
        ],
        NutrientID.THIAMIN: [
            TagRule(
                threshold=ThresholdValue(value=1.5, unit="mg/1000kcal"),
                tag_name="role_thiamine",
                min_raw_value=0.1,
                allowed_categories=[1, 5, 10, 13, 15, 17, 20, 21],
            )
        ],
        NutrientID.CHOLINE: [
            TagRule(
                threshold=ThresholdValue(value=500.0, unit="mg/1000kcal"),
                tag_name="role_choline",
                min_raw_value=40.0,
                allowed_categories=[1, 5, 10, 13, 15, 17, 21],
            )
        ],
    })

    risk_rules: Dict[int, List[TagRule]] = field(default_factory=lambda: {
        NutrientID.COPPER: [
            TagRule(
                threshold=ThresholdValue(value=10.0, unit="mg/1000kcal"),
                tag_name="risk_high_copper",
                min_raw_value=1.0,
            )
        ],
        NutrientID.IODINE: [
            TagRule(
                threshold=ThresholdValue(value=3.0, unit="mg/100g"),
                tag_name="risk_high_iodine",
            ),
            TagRule(
                threshold=ThresholdValue(value=1000.0, unit="mg/100g"),
                tag_name="risk_high_iodine",
                allowed_categories=[15],
                name_regex=r"(?i)(cod|salmon|mackerel|sardine|tuna|herring|pollock|haddock|whiting)",
            ),
        ],
        NutrientID.SELENIUM: [
            TagRule(
                threshold=ThresholdValue(value=0.6, unit="mg/1000kcal"),
                tag_name="risk_high_selenium",
                min_raw_value=130.0,
            )
        ],
        NutrientID.SODIUM: [
            TagRule(
                threshold=ThresholdValue(value=1500.0, unit="mg/100g"),
                tag_name="risk_high_sodium",
            )
        ],
        NutrientID.VITAMIN_A: [
            TagRule(
                threshold=ThresholdValue(value=30000.0, unit="IU/1000kcal"),
                tag_name="risk_high_vit_a",
                allowed_categories=[4, 10, 13, 15, 17],
                min_raw_value=5000.0,
            )
        ],
        NutrientID.VITAMIN_D: [
            TagRule(
                threshold=ThresholdValue(value=2000.0, unit="IU/1000kcal"),
                tag_name="risk_high_vit_d",
                min_raw_value=100.0,
                allowed_categories=[1, 4, 5, 10, 13, 15, 17],
            )
        ],
    })

    category_limits_config: Dict[str, Tuple[float | None, float | None]] = field(default_factory=lambda: {
        "meat_lean": (None, 0.80),
        "meat_moderate": (None, 0.70),
        "meat_fat": (None, 0.30),
        "fish_lean": (None, 0.80),
        "fish_oily": (10.0, 0.25),
        "organ_liver": (1.0, 0.05),
        "organ_secreting_other": (2.0, 0.10),
        "organ_muscular": (None, 0.20),
        "egg": (5.0, 0.15),
        "carb_grain": (None, 0.40),
        "carb_tuber": (None, 0.40),
        "carb_other": (None, 0.15),
        "vegetable": (5.0, 0.15),
        "fruit": (2.0, 0.05),
        "fish_shellfish": (0.5, 0.03),
        "fat_animal": (2.0, 0.15),
        "oil_omega6_la": (1.0, 0.10),
        "oil_omega3_lc": (0.2, 0.05),
        "supplement_calcium": (1.0, None),
        "supplement_iodine": (0.1, None),
        "supplement_omega3_lc": (0.5, 0.10),
        "supplement_mineral": (0.05, 0.00),
        "supplement_multivitamin": (0.5, 0.00),
        "fiber": (0.5, 0.05),
        "supplement_functional": (0.2, 0.00),
        "OTHER": (None, None),
    })

    risk_nutrients: List[str] = field(default_factory=lambda: [
        "calcium",
        "phosphorus",
        "Ca_P_ratio",
        "iodine",
        "vitamin A",
        "vitamin D",
    ])

    def get_ca_p_threshold(self) -> float:
        return self.ca_p_ratio_threshold