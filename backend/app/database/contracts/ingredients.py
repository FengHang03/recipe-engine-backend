from __future__ import annotations

from enum import Enum


class FoodGroup(str, Enum):
    PROTEIN_MEAT = "PROTEIN_MEAT"
    PROTEIN_FISH = "PROTEIN_FISH"
    PROTEIN_EGG = "PROTEIN_EGG"
    PROTEIN_SHELLFISH = "PROTEIN_SHELLFISH"
    MINERAL_SHELLFISH = "MINERAL_SHELLFISH"
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
    OTHER = "OTHER"


class FoodSubgroup(str, Enum):
    MEAT_LEAN = "meat_lean"
    MEAT_MODERATE = "meat_moderate"
    MEAT_FAT = "meat_fat"

    FISH_LEAN = "fish_lean"
    FISH_OILY = "fish_oily"

    ORGAN_LIVER = "organ_liver"
    ORGAN_KIDNEY = "organ_kidney"
    ORGAN_SPLEEN = "organ_spleen"
    ORGAN_BRAIN = "organ_brain"
    ORGAN_SECRETING = "organ_secreting"
    ORGAN_MUSCULAR = "organ_muscular"
    HEART = "heart"
    GIZZARD = "gizzard"

    CARB_GRAIN = "carb_grain"
    CARB_TUBER = "carb_tuber"
    CARB_LEGUME = "carb_legume"
    CARB_OTHER = "carb_other"

    PLANT_ORANGE = "plant_orange"
    PLANT_GREEN = "plant_green"
    PLANT_BLUE = "plant_blue"
    PLANT_WHITE = "plant_white"
    PLANT_OTHER = "plant_other"

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

    OTHER = "other"


class PrepState(str, Enum):
    RAW = "raw"
    COOKED = "cooked"
    AS_IS = "as_is"


FOOD_CATEGORY_ID_TO_LABEL: dict[int, str] = {
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
    20: "Cereal Grains and Pasta",
    21: "Supplement Products",
}