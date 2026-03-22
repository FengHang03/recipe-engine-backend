// src/components/Pet/AddPetForm.tsx
// 修改点：handleGenerateRecipe 去掉 createPet，直接构建临时 Pet 对象传给 recipeGen.generate

import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Save, Loader, AlertCircle,
  Calendar, Weight, Activity, Heart, Zap, ChefHat,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { calculateDailyEnergy, createPet } from '../../lib/api';
import { useRecipeGeneration } from '../../hooks/useRecipeGeneration';
import AppHeader from '../ui/AppHeader';
import type { PetFormData, EnergyCalculationRequest, Pet } from '../../types/pet';
import {
  Species, ActivityLevel, ReproductiveStatus,
  ReproState, SizeClass, LifeStage,
} from '../../types/pet';

// ── 默认值 ────────────────────────────────────────────────────
const DEFAULT_FORM: PetFormData = {
  name:                'Dog',
  species:             Species.DOG,
  breed:               '',
  size_class:          SizeClass.MEDIUM,
  birth_date:          '',
  age_months:          12,
  weight_kg:           20,
  activity_level:      ActivityLevel.MODERATE,
  reproductive_status: ReproductiveStatus.INTACT,
  repro_state:         ReproState.NONE,
  lactation_week:      4,
  nursing_count:       1,
  health_conditions:   [],
  allergies:           [],
};

// ── LifeStage 推算 ─────────────────────────────────────────────
const inferLifeStage = (f: PetFormData): LifeStage => {
  const months = f.age_months ?? 12;
  const sc = f.size_class ?? SizeClass.MEDIUM;
  const adultAt:  Record<SizeClass, number> = { toy: 10, small: 12, medium: 12, large: 15, giant: 18 };
  const seniorAt: Record<SizeClass, number> = { toy: 120, small: 120, medium: 96, large: 84, giant: 72 };
  if (months < adultAt[sc])  return LifeStage.PUPPY;
  if (months >= seniorAt[sc]) return LifeStage.SENIOR;
  return LifeStage.ADULT;
};

// ── senior_month 推算 ──────────────────────────────────────────
const inferSeniorMonth = (f: PetFormData): number => {
  const seniorAt: Record<SizeClass, number> = { toy: 120, small: 120, medium: 96, large: 84, giant: 72 };
  return seniorAt[f.size_class ?? SizeClass.MEDIUM];
};

// ============================================================
// 组件
// ============================================================

const AddPetForm: React.FC = () => {
  const { currentUser } = useAuth();
  const navigate = useNavigate();
  const recipeGen = useRecipeGeneration();

  const [formData, setFormData]                 = useState<PetFormData>(DEFAULT_FORM);
  const [calculatedEnergy, setCalculatedEnergy] = useState<number | null>(null);
  const [energyLoading, setEnergyLoading]       = useState(false);
  const [energyError, setEnergyError]           = useState('');
  const [energyWarnings, setEnergyWarnings]     = useState<string[]>([]);
  const [saving, setSaving]                     = useState(false);
  const [formError, setFormError]               = useState('');
  const [success, setSuccess]                   = useState(false);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ----------------------------------------------------------
  // 能量自动计算：直接内联在 useEffect，避免 useCallback 依赖链问题
  // 页面挂载 + 任意字段变化 → debounce 600ms → 发请求
  // ----------------------------------------------------------
  useEffect(() => {
    if (!formData.name.trim() || formData.weight_kg <= 0 || (formData.age_months ?? 0) <= 0) {
      return;
    }

    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(async () => {
      setEnergyLoading(true);
      setEnergyError('');
      setEnergyWarnings([]);

      try {
        const req: EnergyCalculationRequest = {
          weight_kg:           formData.weight_kg,
          species:             Species.DOG,
          age_months:          formData.age_months ?? 12,
          activity_level:      formData.activity_level,
          reproductive_status: formData.reproductive_status,
          repro_state:         formData.repro_state,
          breed:               formData.breed || undefined,
          lactation_week:      formData.lactation_week,
          nursing_count:       formData.nursing_count,
          senior_month:        inferSeniorMonth(formData),
        };

        const result = await calculateDailyEnergy(req);
        setCalculatedEnergy(result.daily_energy_kcal);
        if (result.warnings?.length > 0) setEnergyWarnings(result.warnings);
      } catch (err: any) {
        setEnergyError('Energy calculation failed: ' + err.message);
        setCalculatedEnergy(null);
      } finally {
        setEnergyLoading(false);
      }
    }, 600);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [formData]);

  const update = (patch: Partial<PetFormData>) =>
    setFormData(prev => ({ ...prev, ...patch }));

  // ----------------------------------------------------------
  // Save Pet（保存到数据库，流程不变）
  // ----------------------------------------------------------
  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentUser) { setFormError('You must be logged in'); return; }
    if (!calculatedEnergy) { setFormError('Please wait for energy calculation'); return; }

    setSaving(true);
    setFormError('');
    try {
      await createPet({
        owner_uid:           currentUser.uid,
        name:                formData.name,
        species:             Species.DOG,
        breed:               formData.breed || undefined,
        size_class:          formData.size_class,
        birth_date:          formData.birth_date || undefined,
        age_months:          formData.age_months,
        weight_kg:           formData.weight_kg,
        activity_level:      formData.activity_level,
        reproductive_status: formData.reproductive_status,
        repro_state:         formData.repro_state,
        life_stage:          inferLifeStage(formData),
        lactation_week:      formData.lactation_week,
        nursing_count:       formData.nursing_count,
        health_conditions:   formData.health_conditions.reduce(
          (acc, c) => ({ ...acc, [c]: true }), {} as Record<string, any>
        ),
        allergies: formData.allergies.reduce(
          (acc, a) => ({ ...acc, [a]: true }), {} as Record<string, any>
        ),
        daily_calories_kcal: calculatedEnergy,
      });
      setSuccess(true);
      setTimeout(() => navigate('/dashboard'), 1500);
    } catch (err: any) {
      setFormError('Failed to save pet: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  // ----------------------------------------------------------
  // Generate Recipe
  // 不再调用 createPet，直接用表单数据构建临时 Pet 对象
  // 传给 recipeGen.generate，generate 内部跳转到结果页
  // ----------------------------------------------------------
  const handleGenerateRecipe = async () => {
    if (!calculatedEnergy) {
      setFormError('Please wait for energy calculation to complete');
      return;
    }

    setFormError('');

    // 构建临时 Pet 对象（不写数据库，id 用空字符串占位）
    const tempPet: Pet = {
      id:                  '',             // 无需真实 id，generate 不使用
      owner_uid:           currentUser?.uid ?? 'guest',
      name:                formData.name,
      species:             Species.DOG,
      breed:               formData.breed || undefined,
      size_class:          formData.size_class,
      age_months:          formData.age_months,
      weight_kg:           formData.weight_kg,
      activity_level:      formData.activity_level,
      reproductive_status: formData.reproductive_status,
      repro_state:         formData.repro_state,
      life_stage:          inferLifeStage(formData),
      lactation_week:      formData.lactation_week,
      nursing_count:       formData.nursing_count,
      health_conditions:   formData.health_conditions.reduce(
        (acc, c) => ({ ...acc, [c]: true }), {} as Record<string, any>
      ),
      allergies: formData.allergies.reduce(
        (acc, a) => ({ ...acc, [a]: true }), {} as Record<string, any>
      ),
      daily_calories_kcal: calculatedEnergy,   // ← 关键：把计算好的能量传进去
    };

    // 直接生成，generate 内部完成后自动跳转 /recipes/result
    await recipeGen.generate(tempPet, navigate);
  };

  const isGenerating = recipeGen.status === 'generating';
  const isBusy = saving || isGenerating;

  // ----------------------------------------------------------
  // 渲染
  // ----------------------------------------------------------
  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50">

      <AppHeader />

      {/* 全局 Loading 遮罩 */}
      {isGenerating && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-white rounded-2xl shadow-2xl p-8 text-center max-w-xs w-full mx-4">
            <Loader className="w-12 h-12 animate-spin text-green-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-1">Generating Recipe</h3>
            <p className="text-sm text-gray-500 mb-4">Optimizing nutrition plan for your pet...</p>
            <p className="text-3xl font-bold text-green-600">{recipeGen.elapsedSeconds}s</p>
            <p className="text-xs text-gray-400 mt-1">This may take 1–3 minutes</p>
          </div>
        </div>
      )}

      <div className="max-w-2xl mx-auto py-8 px-4">

        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Add New Pet</h1>
          <p className="text-sm text-gray-500 mt-1">Fill in your dog's info to generate a personalized recipe</p>
        </div>

        {success && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-green-800 font-medium">✅ Pet saved! Redirecting...</p>
          </div>
        )}

        {formError && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-800">{formError}</p>
          </div>
        )}

        {recipeGen.status === 'error' && recipeGen.errorMessage && (
          <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex items-start justify-between">
            <p className="text-yellow-800 text-sm">{recipeGen.errorMessage}</p>
            <button onClick={recipeGen.reset} className="text-yellow-600 text-sm underline ml-4">Dismiss</button>
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-6">

          {/* ── 基本信息 ───────────────────────────────── */}
          <section className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Basic Info</h2>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Pet Name *</label>
              <input
                type="text"
                value={formData.name}
                onChange={e => update({ name: e.target.value })}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                placeholder="e.g. Buddy"
                required
              />
            </div>

            {/* Species 固定为 Dog，只读展示 */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Species</label>
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-50 border border-green-200 rounded-lg text-green-700 font-medium text-sm">
                🐕 Dog
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Breed (optional)</label>
                <input
                  type="text"
                  value={formData.breed}
                  onChange={e => update({ breed: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  placeholder="e.g. Labrador"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Size Class</label>
                <select
                  value={formData.size_class}
                  onChange={e => update({ size_class: e.target.value as SizeClass })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                >
                  <option value={SizeClass.TOY}>Toy (&lt;5 kg)</option>
                  <option value={SizeClass.SMALL}>Small (5–10 kg)</option>
                  <option value={SizeClass.MEDIUM}>Medium (10–25 kg)</option>
                  <option value={SizeClass.LARGE}>Large (25–45 kg)</option>
                  <option value={SizeClass.GIANT}>Giant (&gt;45 kg)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <Calendar className="w-4 h-4 inline mr-1" />Age (months) *
                </label>
                <input
                  type="number"
                  value={formData.age_months}
                  onChange={e => update({ age_months: parseInt(e.target.value) || 12 })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  min="1" max="300" required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <Weight className="w-4 h-4 inline mr-1" />Weight (kg) *
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.weight_kg}
                  onChange={e => update({ weight_kg: parseFloat(e.target.value) || 20 })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  min="0.1" max="200" required
                />
              </div>
            </div>
          </section>

          {/* ── 活动与繁殖状态 ──────────────────────── */}
          <section className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Activity className="w-4 h-4 text-green-600" />Activity & Status
            </h2>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Activity Level *</label>
              <select
                value={formData.activity_level}
                onChange={e => update({ activity_level: e.target.value as ActivityLevel })}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
              >
                <option value={ActivityLevel.SEDENTARY}>Sedentary (little/no exercise)</option>
                <option value={ActivityLevel.LOW}>Low (light activity)</option>
                <option value={ActivityLevel.MODERATE}>Moderate (regular exercise)</option>
                <option value={ActivityLevel.HIGH}>High (very active)</option>
                <option value={ActivityLevel.EXTREME}>Extreme (working/sport dog)</option>
              </select>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Reproductive Status *</label>
              <div className="flex gap-3">
                {[
                  { value: ReproductiveStatus.INTACT,   label: 'Intact' },
                  { value: ReproductiveStatus.NEUTERED, label: 'Neutered / Spayed' },
                ].map(opt => (
                  <button
                    key={opt.value} type="button"
                    onClick={() => update({ reproductive_status: opt.value })}
                    className={`flex-1 py-2.5 rounded-lg border-2 font-medium text-sm transition-colors
                      ${formData.reproductive_status === opt.value
                        ? 'border-green-500 bg-green-50 text-green-700'
                        : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                <Heart className="w-4 h-4 inline mr-1" />Reproductive State *
              </label>
              <select
                value={formData.repro_state}
                onChange={e => update({ repro_state: e.target.value as ReproState })}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
              >
                <option value={ReproState.NONE}>None</option>
                <option value={ReproState.PREGNANT}>Pregnant</option>
                <option value={ReproState.LACTATING}>Lactating</option>
              </select>
            </div>

            {formData.repro_state === ReproState.LACTATING && (
              <div className="grid grid-cols-2 gap-4 p-4 bg-pink-50 rounded-lg border border-pink-100">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Lactation Week</label>
                  <input
                    type="number"
                    value={formData.lactation_week}
                    onChange={e => update({ lactation_week: parseInt(e.target.value) || 4 })}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    min="1" max="12"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Number of Offspring</label>
                  <input
                    type="number"
                    value={formData.nursing_count}
                    onChange={e => update({ nursing_count: parseInt(e.target.value) || 1 })}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    min="1" max="15"
                  />
                </div>
              </div>
            )}
          </section>

          {/* ── 每日能量（自动计算） ─────────────────── */}
          <section className="bg-gradient-to-r from-green-50 to-blue-50 rounded-xl p-6 border border-green-100">
            <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Zap className="w-4 h-4 text-green-600" />
              Daily Energy Requirement
              <span className="text-xs font-normal text-gray-400 ml-1">(auto-calculated)</span>
            </h2>

            {energyLoading ? (
              <div className="flex items-center gap-2 text-green-700">
                <Loader className="w-4 h-4 animate-spin" />
                <span className="text-sm">Calculating...</span>
              </div>
            ) : energyError ? (
              <div className="flex items-center gap-2 text-red-600">
                <AlertCircle className="w-4 h-4" />
                <span className="text-sm">{energyError}</span>
              </div>
            ) : calculatedEnergy !== null ? (
              <div className="bg-white rounded-lg border-2 border-green-400 p-4 text-center">
                <p className="text-sm text-gray-500 mb-1">Daily Calorie Requirement</p>
                <p className="text-5xl font-bold text-green-600">{calculatedEnergy.toFixed(0)}</p>
                <p className="text-sm text-gray-500 mt-1">kcal / day</p>
              </div>
            ) : (
              <p className="text-sm text-gray-400">Calculating energy requirement...</p>
            )}

            {energyWarnings.length > 0 && (
              <div className="mt-3 space-y-1">
                {energyWarnings.map((w, i) => (
                  <p key={i} className="text-xs text-yellow-700 bg-yellow-50 px-3 py-1 rounded">⚠️ {w}</p>
                ))}
              </div>
            )}

            <p className="text-xs text-gray-400 mt-3">
              * Based on AAFCO standards. Updates automatically when you change any field.
            </p>
          </section>

          {/* ── 按钮区 ──────────────────────────────── */}
          <div className="flex flex-col gap-3">

            {/* Generate Recipe（不保存，直接生成） */}
            <button
              type="button"
              onClick={handleGenerateRecipe}
              disabled={isBusy || !calculatedEnergy}
              className="w-full bg-green-600 text-white py-3 px-6 rounded-lg hover:bg-green-700 transition-colors font-medium flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isGenerating
                ? <><Loader className="w-5 h-5 animate-spin" /> Generating... {recipeGen.elapsedSeconds}s</>
                : <><ChefHat className="w-5 h-5" /> Generate Recipe</>
              }
            </button>

            {/* Save Pet（保存到数据库） */}
            <button
              type="submit"
              disabled={isBusy || !calculatedEnergy || success}
              className="w-full bg-gray-700 text-white py-3 px-6 rounded-lg hover:bg-gray-800 transition-colors font-medium flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving && !isGenerating
                ? <><Loader className="w-5 h-5 animate-spin" /> Saving...</>
                : <><Save className="w-5 h-5" /> Save Pet</>
              }
            </button>

            {/* Cancel */}
            <button
              type="button"
              onClick={() => navigate('/dashboard')}
              disabled={isBusy}
              className="w-full py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
          </div>

          {!calculatedEnergy && !energyLoading && !energyError && (
            <p className="text-sm text-gray-400 text-center">
              Energy calculation is required before generating a recipe
            </p>
          )}

        </form>
      </div>
    </div>
  );
};

export default AddPetForm;
