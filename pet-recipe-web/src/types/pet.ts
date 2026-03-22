// src/types/pet.ts

export type Species = "dog" | "cat";
export const Species = {
  DOG: "dog" as const,
  CAT: "cat" as const,
} as const;

// ✅ 已与后端 ActivityLevel 枚举对齐
export type ActivityLevel = "sedentary" | "low" | "moderate" | "high" | "extreme";
export const ActivityLevel = {
  SEDENTARY: "sedentary" as const,
  LOW:       "low"       as const,
  MODERATE:  "moderate"  as const,
  HIGH:      "high"      as const,
  EXTREME:   "extreme"   as const,
} as const;

export type ReproductiveStatus = "intact" | "neutered";
export const ReproductiveStatus = {
  INTACT:   "intact"   as const,
  NEUTERED: "neutered" as const,
} as const;

export type ReproState = "none" | "pregnant" | "lactating";
export const ReproState = {
  NONE:       "none"       as const,
  PREGNANT:   "pregnant"   as const,
  LACTATING:  "lactating"  as const,
} as const;

export type SizeClass = "toy" | "small" | "medium" | "large" | "giant";
export const SizeClass = {
  TOY:    "toy"    as const,
  SMALL:  "small"  as const,
  MEDIUM: "medium" as const,
  LARGE:  "large"  as const,
  GIANT:  "giant"  as const,
} as const;

// 前端用于显示和逻辑判断的 LifeStage
export type LifeStage = "puppy" | "adult" | "senior" | "kitten";
export const LifeStage = {
  PUPPY:  "puppy"  as const,
  ADULT:  "adult"  as const,
  SENIOR: "senior" as const,
  KITTEN: "kitten" as const,
} as const;

// PhysiologicalStatus（仅用于旧版兼容，内部转换用）
export type PhysiologicalStatus = "intact" | "neutered" | "pregnant" | "lactating";
export const PhysiologicalStatus = {
  INTACT:     "intact"     as const,
  NEUTERED:   "neutered"   as const,
  PREGNANT:   "pregnant"   as const,
  LACTATING:  "lactating"  as const,
} as const;
  
// ── 能量计算 ──────────────────────────────────────────────────

export interface EnergyCalculationResult {
  resting_energy_kcal:   number;
  daily_energy_kcal:     number;
  life_stage:            string;
  model_version:         string;
  calculation_breakdown: Record<string, number>;
  warnings:              string[];
}

// 前端发给后端的能量计算请求
export interface EnergyCalculationRequest {
  weight_kg:           number;
  species:             Species;
  age_months:          number;
  activity_level:      ActivityLevel;
  reproductive_status: ReproductiveStatus;
  repro_state:         ReproState;
  breed?:              string;
  lactation_week?:     number;
  nursing_count?:      number;
  senior_month?:       number;
}

export interface EnergyCalculationResponse {
  success: boolean;
  data?:   EnergyCalculationResult;
  error?:  string;
}

// ── 宠物数据 ──────────────────────────────────────────────────

export interface Pet {
  id?:                  string;
  owner_uid:            string;
  name:                 string;
  species:              Species;
  breed?:               string;
  size_class?:          SizeClass;
  birth_date?:          string;
  age_months?:          number;
  weight_kg:            number;
  activity_level:       ActivityLevel;
  reproductive_status:  ReproductiveStatus;
  repro_state:          ReproState;
  life_stage:           LifeStage;
  lactation_week?:      number;
  nursing_count?:       number;
  health_conditions?:   Record<string, any>;
  allergies?:           Record<string, any>;
  daily_calories_kcal?: number;
  created_at?:          string;
  updated_at?:          string;
}

// 前端表单数据（与 Pet 分离，方便表单处理）
export interface PetFormData {
  name:                string;
  species:             Species;
  breed?:              string;
  size_class?:         SizeClass;
  birth_date?:         string;
  age_months?:         number;
  weight_kg:           number;
  activity_level:      ActivityLevel;
  reproductive_status: ReproductiveStatus;
  repro_state:         ReproState;
  lactation_week?:     number;
  nursing_count?:      number;
  health_conditions:   string[];
  allergies:           string[];
}
  
// ── 食谱生成 ──────────────────────────────────────────────────

export interface OptimizedWeight {
  ingredient_id:   string;
  ingredient_name: string;
  weight_grams:    number;
  percentage:      number;   // 占总重量百分比，后端已计算
  is_supplement:   boolean;
}

export interface NutrientAnalysis {
  nutrient_id:          string;   // 小写字符串，如 "protein"
  nutrient_name:        string;
  value:                number | null;
  unit:                 string | null;
  min_required:         number | null;
  max_allowed:          number | null;
  ideal_target:         number | null;
  meets_min:            boolean;
  meets_max:            boolean;
  deviation_from_ideal: number | null;
}

export interface RecipeResult {
  rank:               number;
  combination_id:     string;
  total_weight_grams: number;
  objective_value:    number | null;
  used_supplements:   string[];
  weights:            OptimizedWeight[];
  nutrient_analysis:  NutrientAnalysis[];
}

export interface TaskStatus {
  run_id:  string;
  status:  "pending" | "running" | "done" | "error";
  message: string | null;
  recipes: RecipeResult[] | null;
}
