// src/types/pet.ts

export type Species = "dog" | "cat";

export const Species = {
  DOG: "dog" as const,
  CAT: "cat" as const,
} as const;

export type ActivityLevel = "sedentary" | "light_active" | "moderate_active" | "very_active" | "extremely_active";

export const ActivityLevel = {
  SEDENTARY: "sedentary" as const,
  LIGHT_ACTIVE: "light_active" as const,
  MODERATE_ACTIVE: "moderate_active" as const,
  VERY_ACTIVE: "very_active" as const,
  EXTREMELY_ACTIVE: "extremely_active" as const,
} as const;

export type PhysiologicalStatus = "intact" | "neutered" | "pregnant" | "lactating";

export const PhysiologicalStatus = {
  INTACT: "intact" as const,
  NEUTERED: "neutered" as const,
  PREGNANT: "pregnant" as const,
  LACTATING: "lactating" as const,
} as const;

export type ReproductiveStatus = "intact" | "neutered";

export const ReproductiveStatus = {
  INTACT: "intact" as const,
  NEUTERED: "neutered" as const,
} as const;

export type ReproState = "none" | "pregnant" | "lactating";

export const ReproState = {
  NONE: "none" as const,
  PREGNANT: "pregnant" as const,
  LACTATING: "lactating" as const,
} as const;

export type SizeClass = "toy" | "small" | "medium" | "large" | "giant";

export const SizeClass = {
  TOY: "toy" as const,
  SMALL: "small" as const,
  MEDIUM: "medium" as const,
  LARGE: "large" as const,
  GIANT: "giant" as const,
} as const;

export type LifeStage = "puppy" | "adult" | "senior" | "kitten";

export const LifeStage = {
  PUPPY: "puppy" as const,
  ADULT: "adult" as const,
  SENIOR: "senior" as const,
  KITTEN: "kitten" as const,
} as const;
  
  // 能量计算结果
  export interface EnergyCalculationResult {
    resting_energy_kcal: number;
    daily_energy_kcal: number;
    life_stage: string;
    model_version: string;
    calculation_breakdown: Record<string, number>;
    warnings: string[];
  }
  
  // 宠物信息接口（与数据库模型对应）
  export interface Pet {
    id?: string;
    owner_uid: string;
    name: string;
    species: Species;
    breed?: string;
    size_class?: SizeClass;
    birth_date?: string; // ISO date string
    age_months?: number;
    weight_kg: number;
    activity_level: ActivityLevel;
    reproductive_status: ReproductiveStatus;
    repro_state: ReproState;
    life_stage: LifeStage;
    lactation_week?: number;
    nursing_count?: number;
    health_conditions?: Record<string, any>;
    allergies?: Record<string, any>;
    daily_calories_kcal?: number;
    created_at?: string;
    updated_at?: string;
  }
  
  // 前端表单数据
  export interface PetFormData {
    name: string;
    species: Species;
    breed?: string;
    size_class?: SizeClass;
    birth_date?: string;
    age_months?: number;
    weight_kg: number;
    activity_level: ActivityLevel;
    reproductive_status: ReproductiveStatus;
    repro_state: ReproState;
    lactation_week?: number;
    nursing_count?: number;
    health_conditions: string[];
    allergies: string[];
  }
  
  // Cloud Run API 请求参数
  export interface EnergyCalculationRequest {
    weight_kg: number;
    species: Species;
    age_months: number;
    activity_level: ActivityLevel;
    physiological_status: PhysiologicalStatus;
    breed?: string;
    lactation_week?: number;
    nursing_count?: number;
    senior_month?: number;
    energy_requirement?: number;
  }
  
  // Cloud Run API 响应
  export interface EnergyCalculationResponse {
    success: boolean;
    data?: EnergyCalculationResult;
    error?: string;
  }