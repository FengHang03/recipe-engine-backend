// src/hooks/useRecipeGeneration.ts
// 演示版：同步生成，直接 await 结果
// 结果存入 sessionStorage，供 RecipeResult / RecipeDetail 页面读取

import { useState, useCallback } from "react";
import { generateRecipes } from "../lib/api";
import type { Pet, RecipeResult } from "../types/pet";
import type { GenerateRecipeRequest } from "../lib/api";

// sessionStorage 的 key 常量（集中管理，避免拼写错误）
export const SESSION_KEY_RECIPES = "recipe_results";
export const SESSION_KEY_DETAIL  = "recipe_detail";

// ── 前端 LifeStage → 后端枚举名称 ────────────────────────────
const LIFE_STAGE_MAP: Record<string, Record<string, string>> = {
  dog: { puppy: "DOG_PUPPY", adult: "DOG_ADULT", senior: "DOG_SENIOR", kitten: "DOG_ADULT" },
  cat: { kitten: "CAT_KITTEN", adult: "CAT_ADULT", senior: "CAT_SENIOR", puppy: "CAT_ADULT" },
};

// ── 状态类型 ─────────────────────────────────────────────────
export type GenerationStatus = "idle" | "generating" | "done" | "error";

// ============================================================
// Hook
// ============================================================

export function useRecipeGeneration() {
  const [status, setStatus]             = useState<GenerationStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const reset = useCallback(() => {
    setStatus("idle");
    setErrorMessage(null);
    setElapsedSeconds(0);
  }, []);

  /**
   * 主入口：构建请求 → 同步调用后端 → 存 sessionStorage → 跳转
   * navigate 由调用方传入，保持 Hook 的纯粹性
   */
  const generate = useCallback(
    async (pet: Pet, navigate: (path: string) => void) => {
      if (status === "generating") return;

      reset();
      setStatus("generating");

      // 计时器：展示已等待秒数
      const startTime = Date.now();
      const timer = setInterval(() => {
        setElapsedSeconds(Math.floor((Date.now() - startTime) / 1000));
      }, 1000);

      try {
        // 推算后端 life_stage 枚举名称
        const lifeStage =
          LIFE_STAGE_MAP[pet.species]?.[pet.life_stage] ?? "DOG_ADULT";

        const request: GenerateRecipeRequest = {
          pet_profile: {
            target_calories:    pet.daily_calories_kcal ?? 0,
            body_weight:        pet.weight_kg,
            life_stage:         lifeStage,
            allergies:          pet.allergies
              ? Object.keys(pet.allergies).filter((k) => pet.allergies![k])
              : [],
            size_class:         pet.size_class,
            activity_level:     pet.activity_level,
            health_conditions:  pet.health_conditions
              ? Object.keys(pet.health_conditions).filter((k) => pet.health_conditions![k])
              : [],
            reproductive_status: pet.reproductive_status,
          },
          top_k: 5,
        };

        // 同步调用（可能阻塞 1-3 分钟）
        const response = await generateRecipes(request);

        // 存入 sessionStorage
        sessionStorage.setItem(
          SESSION_KEY_RECIPES,
          JSON.stringify(response.recipes)
        );

        setStatus("done");
        clearInterval(timer);

        // 跳转到结果页
        navigate("/recipes/result");

      } catch (err: any) {
        clearInterval(timer);
        setStatus("error");
        setErrorMessage(err.message ?? "食谱生成失败，请重试");
      }
    },
    [status, reset]
  );

  return {
    status,
    errorMessage,
    elapsedSeconds,
    generate,
    reset,
  };
}
