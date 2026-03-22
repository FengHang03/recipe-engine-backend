// src/components/Recipe/RecipeDetail.tsx
// 单个食谱详情页
// 演示版：从 sessionStorage 读取数据，三部分展示

import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft, Scale, Beef, Droplets, Wheat,
  CheckCircle, XCircle,
} from "lucide-react";
import { SESSION_KEY_DETAIL } from "../../hooks/useRecipeGeneration";
import type { RecipeResult } from "../../types/pet";

// ── 颜色工具 ─────────────────────────────────────────────────
const pctColor = (pct: number | null) => {
  if (pct == null) return "text-gray-400";
  if (pct < 80)   return "text-red-600 font-semibold";
  if (pct < 100)  return "text-yellow-600 font-semibold";
  return "text-green-600";
};

const fmt = (v: number | null | undefined, dp = 1) =>
  v != null ? v.toFixed(dp) : "—";

// ============================================================
// 组件
// ============================================================

const RecipeDetailPage: React.FC = () => {
  const { rank } = useParams<{ rank: string }>();
  const navigate  = useNavigate();

  const [recipe, setRecipe] = useState<RecipeResult | null>(null);
  const [error, setError]   = useState("");

  // 从 sessionStorage 读取
  useEffect(() => {
    const raw = sessionStorage.getItem(SESSION_KEY_DETAIL);
    if (!raw) {
      setError("找不到食谱数据，请返回重新选择");
      return;
    }
    try {
      setRecipe(JSON.parse(raw) as RecipeResult);
    } catch {
      setError("食谱数据解析失败");
    }
  }, []);

  if (error || !recipe) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-500 mb-4">{error || "加载中..."}</p>
          <button
            onClick={() => navigate("/recipes/result")}
            className="text-green-600 underline text-sm"
          >
            Back to list
          </button>
        </div>
      </div>
    );
  }

  // 营养素查询表
  const nMap = Object.fromEntries(
    recipe.nutrient_analysis.map((n) => [n.nutrient_id, n])
  );

  // Ca:P 比值
  const ca  = nMap["calcium"]?.value;
  const p   = nMap["phosphorus"]?.value;
  const caP = ca != null && p != null && p > 0 ? (ca / p).toFixed(2) : "—";

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50">

      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center gap-3">
          <button
            onClick={() => navigate("/recipes/result")}
            className="text-gray-400 hover:text-green-600 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Recipe {rank}</h1>
            <p className="text-xs text-gray-400">
              Total {recipe.total_weight_grams.toFixed(0)} g
            </p>
          </div>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-4 py-6 space-y-5">

        {/* ================================================ */}
        {/* ① 食材列表                                       */}
        {/* ================================================ */}
        <section className="bg-white rounded-xl shadow-sm overflow-hidden">
          <SectionHeader icon={<Scale className="w-4 h-4 text-green-600" />} title="Ingredients" />
          <div className="divide-y divide-gray-50">
            {recipe.weights.map((w) => (
              <div key={w.ingredient_id} className="flex items-center justify-between px-5 py-3">
                <div>
                  <p className="font-medium text-gray-900 text-sm">{w.ingredient_name}</p>
                  {w.is_supplement && (
                    <span className="text-xs text-purple-600 bg-purple-50 px-1.5 py-0.5 rounded">
                      Supplement
                    </span>
                  )}
                </div>
                <div className="text-right">
                  <p className="font-semibold text-gray-900 text-sm">
                    {w.weight_grams.toFixed(1)} g
                  </p>
                  <div className="flex items-center gap-1.5 mt-1">
                    <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-green-500 rounded-full"
                        style={{ width: `${Math.min(w.percentage, 100)}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-400">{w.percentage.toFixed(1)}%</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ================================================ */}
        {/* ② 重要营养素摘要                                 */}
        {/* ================================================ */}
        <section className="bg-white rounded-xl shadow-sm p-5">
          <SectionHeader
            icon={<Beef className="w-4 h-4 text-red-500" />}
            title="Key Nutrients"
          />
          <div className="grid grid-cols-2 gap-3 mt-4">
            <MacroCard
              label="Protein"
              value={nMap["protein"]?.value}
              unit={nMap["protein"]?.unit ?? "g"}
              color="bg-red-50 border-red-100 text-red-700"
              icon={<Beef className="w-4 h-4" />}
            />
            <MacroCard
              label="Fat"
              value={nMap["fat"]?.value}
              unit={nMap["fat"]?.unit ?? "g"}
              color="bg-yellow-50 border-yellow-100 text-yellow-700"
              icon={<Droplets className="w-4 h-4" />}
            />
            <MacroCard
              label="Carbohydrate"
              value={nMap["carbohydrate"]?.value}
              unit={nMap["carbohydrate"]?.unit ?? "g"}
              color="bg-blue-50 border-blue-100 text-blue-700"
              icon={<Wheat className="w-4 h-4" />}
            />
            {/* Ca:P ratio */}
            <div className="flex items-center gap-3 p-4 rounded-xl border bg-green-50 border-green-100 text-green-700">
              <span className="text-lg">🦴</span>
              <div>
                <p className="text-xs opacity-70">Ca : P Ratio</p>
                <p className="text-xl font-bold leading-tight">{caP}</p>
              </div>
            </div>
          </div>
        </section>

        {/* ================================================ */}
        {/* ③ AAFCO 完整营养素表格                           */}
        {/* ================================================ */}
        <section className="bg-white rounded-xl shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-900">AAFCO Nutrient Analysis</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              % of Min = value ÷ min_required × 100%
            </p>
          </div>

          {/* 表头 */}
          <div className="grid grid-cols-6 gap-1 px-5 py-2 bg-gray-50 text-xs font-medium text-gray-500 border-b border-gray-100">
            <span className="col-span-2">Nutrient</span>
            <span className="text-right">Min</span>
            <span className="text-right">Max</span>
            <span className="text-right">Value</span>
            <span className="text-right">% of Min</span>
          </div>

          {/* 数据行 */}
          <div className="divide-y divide-gray-50 max-h-[520px] overflow-y-auto">
            {recipe.nutrient_analysis.map((n) => {
              // 前端计算 % of min
              const pct =
                n.value != null && n.min_required != null && n.min_required > 0
                  ? (n.value / n.min_required) * 100
                  : null;

              return (
                <div
                  key={n.nutrient_id}
                  className="grid grid-cols-6 gap-1 px-5 py-2.5 text-xs items-center hover:bg-gray-50"
                >
                  <div className="col-span-2 flex items-center gap-1.5">
                    <StatusIcon meetsMin={n.meets_min} meetsMax={n.meets_max} />
                    <div>
                      <p className="text-gray-900 font-medium leading-tight">
                        {n.nutrient_name}
                      </p>
                      <p className="text-gray-400">{n.unit ?? ""}</p>
                    </div>
                  </div>
                  <span className="text-right text-gray-500">{fmt(n.min_required)}</span>
                  <span className="text-right text-gray-500">{fmt(n.max_allowed)}</span>
                  <span className="text-right text-gray-900 font-medium">{fmt(n.value)}</span>
                  <span className={`text-right ${pctColor(pct)}`}>
                    {pct != null ? `${pct.toFixed(1)}%` : "—"}
                  </span>
                </div>
              );
            })}
          </div>
        </section>

      </div>
    </div>
  );
};

// ── 辅助组件 ──────────────────────────────────────────────────

const SectionHeader = ({
  icon, title,
}: {
  icon: React.ReactNode;
  title: string;
}) => (
  <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
    {icon}
    <h2 className="font-semibold text-gray-900">{title}</h2>
  </div>
);

const MacroCard = ({
  label, value, unit, color, icon,
}: {
  label: string;
  value: number | null | undefined;
  unit:  string;
  color: string;
  icon:  React.ReactNode;
}) => (
  <div className={`flex items-center gap-3 p-4 rounded-xl border ${color}`}>
    <div className="opacity-70">{icon}</div>
    <div>
      <p className="text-xs opacity-70">{label}</p>
      <p className="text-xl font-bold leading-tight">
        {value != null ? value.toFixed(1) : "—"}
        <span className="text-sm font-normal ml-1">{unit}</span>
      </p>
    </div>
  </div>
);

const StatusIcon = ({
  meetsMin, meetsMax,
}: {
  meetsMin: boolean;
  meetsMax: boolean;
}) => {
  if (!meetsMin) return <XCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />;
  if (!meetsMax) return <XCircle className="w-3.5 h-3.5 text-orange-400 flex-shrink-0" />;
  return <CheckCircle className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />;
};

export default RecipeDetailPage;
