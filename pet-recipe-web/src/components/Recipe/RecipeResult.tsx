// src/components/Recipe/RecipeResult.tsx
// 食谱结果列表页
// 演示版：从 sessionStorage 读取数据，不再调用后端

import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ChevronRight, BookOpen, Scale } from "lucide-react";
import { SESSION_KEY_RECIPES, SESSION_KEY_DETAIL } from "../../hooks/useRecipeGeneration";
import type { RecipeResult } from "../../types/pet";

// ── 营养知识内容 ──────────────────────────────────────────────
const NUTRITION_TIPS = [
  {
    icon: "🥩",
    title: "Protein First",
    text: "Dogs and cats need high-quality animal protein as the foundation of every meal. It supports muscle maintenance, immune function, and energy.",
  },
  {
    icon: "🦴",
    title: "Calcium : Phosphorus Balance",
    text: "A Ca:P ratio between 1:1 and 2:1 is essential. Imbalances can cause bone disease, especially in growing puppies.",
  },
  {
    icon: "🐟",
    title: "Essential Fatty Acids",
    text: "Omega-3 (EPA & DHA) supports brain health, coat quality, and reduces inflammation. Aim for fish or fish oil as a source.",
  },
  {
    icon: "🌿",
    title: "AAFCO Standards",
    text: "All recipes are optimized to meet or exceed AAFCO nutrient profiles, the gold standard for pet nutrition in North America.",
  },
];

// ============================================================
// 组件
// ============================================================

const RecipeResultPage: React.FC = () => {
  const navigate = useNavigate();
  const [recipes, setRecipes] = useState<RecipeResult[]>([]);
  const [error, setError]     = useState("");

  // 从 sessionStorage 读取数据
  useEffect(() => {
    const raw = sessionStorage.getItem(SESSION_KEY_RECIPES);
    if (!raw) {
      setError("找不到食谱数据，请返回重新生成");
      return;
    }
    try {
      const data = JSON.parse(raw) as RecipeResult[];
      setRecipes(data);
    } catch {
      setError("食谱数据解析失败，请返回重新生成");
    }
  }, []);

  // 点击某行：存详情到 sessionStorage，跳转详情页
  const handleSelectRecipe = (recipe: RecipeResult) => {
    sessionStorage.setItem(SESSION_KEY_DETAIL, JSON.stringify(recipe));
    navigate(`/recipes/detail/${recipe.rank}`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50">

      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center gap-3">
          <button
            onClick={() => navigate("/dashboard")}
            className="text-gray-400 hover:text-green-600 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Recipe Results</h1>
            <p className="text-xs text-gray-400">
              {recipes.length} optimized recipe{recipes.length !== 1 ? "s" : ""} found
            </p>
          </div>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">

        {/* 错误提示 */}
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
            <p className="text-red-700 text-sm">{error}</p>
            <button
              onClick={() => navigate("/dashboard")}
              className="mt-2 text-red-500 text-sm underline"
            >
              Return to Dashboard
            </button>
          </div>
        )}

        {/* ── 营养知识块 ─────────────────────────────────── */}
        {recipes.length > 0 && (
          <section className="bg-white rounded-xl shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-green-600" />
              <h2 className="font-semibold text-gray-900">Nutrition Insights</h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-gray-100">
              {NUTRITION_TIPS.map((tip) => (
                <div key={tip.title} className="p-4">
                  <p className="text-xl mb-1">{tip.icon}</p>
                  <p className="font-medium text-gray-900 text-sm mb-1">{tip.title}</p>
                  <p className="text-gray-500 text-xs leading-relaxed">{tip.text}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ── 食谱列表 ───────────────────────────────────── */}
        {recipes.length > 0 ? (
          <section>
            <p className="text-sm text-gray-500 mb-3">
              Tap a recipe to view detailed ingredient list and nutrient analysis
            </p>
            <div className="space-y-3">
              {recipes.map((recipe, index) => (
                <RecipeCard
                  key={recipe.combination_id}
                  recipe={recipe}
                  index={index}
                  onSelect={handleSelectRecipe}
                />
              ))}
            </div>
          </section>
        ) : !error ? (
          <div className="bg-white rounded-xl p-12 text-center">
            <p className="text-gray-400">No recipes available</p>
          </div>
        ) : null}

      </div>
    </div>
  );
};

// ── 单个食谱卡片 ──────────────────────────────────────────────
const RecipeCard = ({
  recipe, index, onSelect,
}: {
  recipe: RecipeResult;
  index:  number;
  onSelect: (r: RecipeResult) => void;
}) => {
  const nMap = Object.fromEntries(
    recipe.nutrient_analysis.map((n) => [n.nutrient_id, n.value])
  );
  const protein = nMap["protein"];
  const fat     = nMap["fat"];
  const carb    = nMap["carbohydrate"];

  const ingredientNames = recipe.weights
    .slice(0, 4)
    .map((w) => w.ingredient_name)
    .filter(Boolean);

  const rankLabel = ["🥇", "🥈", "🥉"][index] ?? `#${recipe.rank}`;

  return (
    <div
      onClick={() => onSelect(recipe)}
      className="bg-white rounded-xl shadow-sm hover:shadow-md border border-gray-100 hover:border-green-300 transition-all cursor-pointer p-5"
    >
      <div className="flex items-start justify-between gap-4">
        {/* 左侧 */}
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <div className={`w-9 h-9 rounded-full flex items-center justify-center text-lg flex-shrink-0
            ${index === 0 ? "bg-yellow-100" : index === 1 ? "bg-gray-100" : index === 2 ? "bg-amber-100" : "bg-green-100"}`}>
            {rankLabel}
          </div>
          <div className="min-w-0">
            <p className="font-semibold text-gray-900 text-sm mb-1">Recipe {recipe.rank}</p>
            <p className="text-xs text-gray-400 truncate mb-2">
              {ingredientNames.join(" · ")}
              {recipe.weights.length > 4 ? ` +${recipe.weights.length - 4} more` : ""}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {protein != null && <Tag label={`Protein ${protein.toFixed(1)}g`} color="bg-red-50 text-red-600" />}
              {fat     != null && <Tag label={`Fat ${fat.toFixed(1)}g`}         color="bg-yellow-50 text-yellow-600" />}
              {carb    != null && <Tag label={`Carb ${carb.toFixed(1)}g`}        color="bg-blue-50 text-blue-600" />}
            </div>
          </div>
        </div>

        {/* 右侧 */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <div className="text-right">
            <div className="flex items-center gap-1 text-gray-500 text-xs">
              <Scale className="w-3 h-3" />
              <span>{recipe.total_weight_grams.toFixed(0)}g</span>
            </div>
          </div>
          <ChevronRight className="w-4 h-4 text-gray-300" />
        </div>
      </div>
    </div>
  );
};

const Tag = ({ label, color }: { label: string; color: string }) => (
  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${color}`}>{label}</span>
);

export default RecipeResultPage;
