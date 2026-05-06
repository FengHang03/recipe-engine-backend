# Ingerdient tag interpretation
## Enums
    ### FoodGroup
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
    ### FoodSubgroup
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

    ### SlotType
        class SlotType(StrEnum):
            """食材槽位类型 (Slot Names Enum)"""
            MAIN_PROTEIN = "Main Protein Slot"
            SHELLFISH_PROTEIN = "Shellfish Protein"
            EGG = "Egg"
            CALCIUM = "Calcium Slot"
            MINERAL_SHELLFISH = "Mineral Shellfish"
            ORGAN_LIVER = "Organ Liver Slot"
            ORGAN_SECRETING = "Organ Secreting Slot"
            ORGAN_MUSCULAR = "Organ Muscular Slot"
            VEGETABLE = "Vegetable Slot"
            OMEGA3_LC = "Omega3 LC Slot"
            OMEGA6_LA = "Omega6 LA Slot"
            CARBOHYDRATE = "Carbohydrate Slot"
            IODINE = "Iodine Slot"
            FIBER = "Fiber Slot"
            OPTIONAL_INGREDIENTS = "Optional Ingredients Slot"

## database schema
    ### Table ingredients
        CREATE TABLE IF NOT EXISTS ingredients (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

        -- USDA FDC（built-in 才有；用户自定义可空）
        fdc_id INTEGER,

        source ingredient_source NOT NULL DEFAULT 'built_in',
        owner_uid VARCHAR(128) REFERENCES users(uid) ON DELETE CASCADE,

        description TEXT NOT NULL,
        short_name TEXT,
        food_category_id INTEGER,
        food_category_label TEXT,

        food_group TEXT,        -- 例如 meat_lean / fish_oily / oil_omega6_la
        #  diversity_cluster TEXT,        -- 例如 oil_cluster / poultry_cluster

        -- 数据质量：用户输入不全时非常重要
        #  quality_tier ingredient_quality_tier NOT NULL DEFAULT 't3',
        #  derived_from_ingredient_id UUID REFERENCES ingredients(id) ON DELETE SET NULL,
        #  match_confidence NUMERIC(4,3),  -- 0~1

        -- 食材级上限（可空；为空则走策略层默认值）
        max_g_per_kg_bw NUMERIC(8,3),
        max_pct_kcal NUMERIC(6,3),

        -- 状态
        is_active BOOLEAN NOT NULL DEFAULT TRUE,

        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

        -- 约束：built_in 必须 owner_uid 为 NULL；user 必须 owner_uid 非 NULL
        CONSTRAINT chk_ingredient_owner
        CHECK (
            (source = 'built_in' AND owner_uid IS NULL)
            OR
            (source = 'user' AND owner_uid IS NOT NULL)
        ),

        -- 约束：match_confidence 合法范围
        CONSTRAINT chk_match_confidence
        CHECK (match_confidence IS NULL OR (match_confidence >= 0 AND match_confidence <= 1))
        );

        -- built_in 的 fdc_id 应尽量唯一（允许 NULL 给 user）
        CREATE UNIQUE INDEX IF NOT EXISTS uq_ingredients_fdc_id
        ON ingredients(fdc_id)
        WHERE fdc_id IS NOT NULL;

        -- 用户自定义食材：同一用户下名字可做弱唯一（可选）
        CREATE INDEX IF NOT EXISTS idx_ingredients_owner ON ingredients(owner_uid);
        CREATE INDEX IF NOT EXISTS idx_ingredients_source_active ON ingredients(source, is_active);
        CREATE INDEX IF NOT EXISTS idx_ingredients_food_group ON ingredients(food_group);
        CREATE INDEX IF NOT EXISTS idx_ingredients_diversity_cluster ON ingredients(diversity_cluster);

    ### Table ingredient_tags
        DO $$ BEGIN
        CREATE TYPE ingredient_tag_type AS ENUM (
            'role',             -- 功能层
            'risk',             -- 风险层
            'diversity',        -- 多样性层
            'repeat_policy',    -- 多日复用/频次默认策略
            'note'              -- 其它备注
        );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;

        CREATE TABLE IF NOT EXISTS ingredient_tags (
        ingredient_id UUID NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
        food_subgroup TEXT NOT NULL,
        tag_type ingredient_tag_type NOT NULL,
        tag TEXT NOT NULL,         

        source VARCHAR(32) NOT NULL DEFAULT 'system',
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

        PRIMARY KEY (ingredient_id, tag_type, tag)
        );

        CREATE INDEX IF NOT EXISTS idx_ingtags_type_tag ON ingredient_tags(tag_type, tag);
        CREATE INDEX IF NOT EXISTS idx_ingtags_ing ON ingredient_tags(ingredient_id);

        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
        NEW."updated_at" = now();
        RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS trg_ingredients_updated_at ON ingredients;

        CREATE TRIGGER trg_ingredients_updated_at
        BEFORE UPDATE ON ingredients
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();

## Tag determined algorithm
    ### diversity tags
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
    ### role & risk tags
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
