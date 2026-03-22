// src/components/Dashboard/Dashboard.tsx
// 演示版：Generate Recipe 按钮触发同步请求，顶部加上 AppHeader

import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus, Edit, Trash2, Activity,
  ChefHat, Loader2, AlertTriangle,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { getUserPets, deletePet } from '../../lib/api';
import { useRecipeGeneration } from '../../hooks/useRecipeGeneration';
import AppHeader from '../ui/AppHeader';
import type { Pet } from '../../types/pet';

const Dashboard: React.FC = () => {
  const { currentUser } = useAuth();
  const navigate = useNavigate();

  const [pets, setPets]       = useState<Pet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');
  const [activePetId, setActivePetId] = useState<string | null>(null);

  const recipeGen = useRecipeGeneration();

  useEffect(() => { loadPets(); }, []);

  const loadPets = async () => {
    setLoading(true);
    setError('');
    try {
      const userPets = await getUserPets();
      setPets(userPets);
    } catch (err: any) {
      setError('Failed to load pets: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateRecipe = async (pet: Pet) => {
    if (!pet.daily_calories_kcal || pet.daily_calories_kcal <= 0) {
      alert('Please complete pet info (daily calorie calculation required) before generating a recipe');
      return;
    }
    setActivePetId(pet.id ?? null);
    recipeGen.reset();
    await recipeGen.generate(pet, navigate);
  };

  const handleDeletePet = async (petId: string) => {
    if (!window.confirm('Are you sure you want to delete this pet?')) return;
    try {
      await deletePet(petId);
      setPets(pets.filter(p => p.id !== petId));
    } catch (err: any) {
      alert('Failed to delete pet: ' + err.message);
    }
  };

  // ── Generate Recipe 按钮 ────────────────────────────────────
  const GenerateButton = ({ pet }: { pet: Pet }) => {
    const isThis = activePetId === pet.id;
    const isGenerating = isThis && recipeGen.status === 'generating';

    if (isGenerating) {
      return (
        <button disabled className="flex-1 flex items-center justify-center gap-2 py-2 bg-green-100 text-green-700 rounded-lg text-sm cursor-not-allowed">
          <Loader2 className="w-4 h-4 animate-spin" />
          {recipeGen.elapsedSeconds}s
        </button>
      );
    }
    return (
      <button
        onClick={() => handleGenerateRecipe(pet)}
        disabled={recipeGen.status === 'generating'}
        className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
      >
        <ChefHat className="w-4 h-4" /> Generate Recipe
      </button>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50">

      {/* 共享导航栏 */}
      <AppHeader />

      {/* 全局 Loading 遮罩（生成食谱期间） */}
      {recipeGen.status === 'generating' && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-white rounded-2xl shadow-2xl p-8 text-center max-w-xs w-full mx-4">
            <Loader2 className="w-12 h-12 animate-spin text-green-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-1">Generating Recipe</h3>
            <p className="text-sm text-gray-500 mb-4">Optimizing nutrition plan for your pet...</p>
            <p className="text-3xl font-bold text-green-600">{recipeGen.elapsedSeconds}s</p>
            <p className="text-xs text-gray-400 mt-1">This may take 1–3 minutes</p>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {/* 用户欢迎信息 */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">My Pets</h1>
          <p className="text-sm text-gray-500">Welcome, {currentUser?.email ?? 'Guest'}</p>
        </div>

        {/* 加载错误 */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm">
            {error}
          </div>
        )}

        {/* 食谱生成错误 */}
        {recipeGen.status === 'error' && recipeGen.errorMessage && (
          <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex items-start justify-between">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-yellow-600 flex-shrink-0 mt-0.5" />
              <p className="text-yellow-800 text-sm">{recipeGen.errorMessage}</p>
            </div>
            <button onClick={recipeGen.reset} className="text-yellow-600 text-sm underline ml-4 flex-shrink-0">
              Dismiss
            </button>
          </div>
        )}

        {/* Add Pet 按钮 */}
        <div className="mb-6">
          <button
            onClick={() => navigate('/add-pet')}
            disabled={recipeGen.status === 'generating'}
            className="flex items-center gap-2 bg-green-600 text-white px-5 py-2.5 rounded-lg hover:bg-green-700 transition-colors font-medium disabled:opacity-50"
          >
            <Plus className="w-4 h-4" /> Add New Pet
          </button>
        </div>

        {/* 宠物列表 */}
        {loading ? (
          <div className="text-center py-16">
            <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-green-500 border-t-transparent" />
            <p className="mt-3 text-gray-500 text-sm">Loading pets...</p>
          </div>
        ) : pets.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm p-12 text-center">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Plus className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No pets yet</h3>
            <p className="text-gray-500 text-sm mb-6">
              Add your first pet to start generating personalized recipes
            </p>
            <button
              onClick={() => navigate('/add-pet')}
              className="inline-flex items-center gap-2 bg-green-600 text-white px-5 py-2.5 rounded-lg hover:bg-green-700 transition-colors font-medium"
            >
              <Plus className="w-4 h-4" /> Add Your First Pet
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {pets.map(pet => (
              <div key={pet.id} className="bg-white rounded-xl shadow-sm hover:shadow-md transition-shadow overflow-hidden">

                {/* Card Header */}
                <div className="bg-gradient-to-r from-green-500 to-blue-500 p-4 text-white">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-bold">{pet.name}</h3>
                    <span className="text-2xl">🐕</span>
                  </div>
                  <p className="text-sm opacity-80 mt-0.5">{pet.breed || 'Mixed breed'}</p>
                </div>

                {/* Card Body */}
                <div className="p-4 space-y-2">
                  <Row label="Age"      value={`${pet.age_months} months (${pet.life_stage})`} />
                  <Row label="Weight"   value={`${pet.weight_kg} kg`} />
                  <Row label="Size"     value={pet.size_class ?? 'N/A'} capitalize />
                  <Row label="Activity" value={(pet.activity_level ?? '').replace('_', ' ')} capitalize />

                  {pet.daily_calories_kcal ? (
                    <div className="mt-3 p-3 bg-green-50 rounded-lg flex items-center justify-between">
                      <span className="text-sm text-gray-600 flex items-center gap-1">
                        <Activity className="w-3.5 h-3.5" /> Daily Calories
                      </span>
                      <span className="font-bold text-green-600">
                        {pet.daily_calories_kcal.toFixed(0)} kcal
                      </span>
                    </div>
                  ) : (
                    <div className="mt-3 p-3 bg-yellow-50 rounded-lg">
                      <p className="text-xs text-yellow-700 text-center">
                        Complete pet info to calculate calories
                      </p>
                    </div>
                  )}
                </div>

                {/* Card Actions */}
                <div className="border-t border-gray-100 p-4 flex gap-2">
                  <GenerateButton pet={pet} />
                  <button
                    onClick={() => navigate(`/edit-pet/${pet.id}`)}
                    disabled={recipeGen.status === 'generating'}
                    className="flex items-center justify-center p-2 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDeletePet(pet.id!)}
                    disabled={recipeGen.status === 'generating'}
                    className="flex items-center justify-center p-2 bg-red-500 text-white rounded-lg hover:bg-red-600 disabled:opacity-50"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const Row = ({
  label, value, capitalize,
}: {
  label: string;
  value: string;
  capitalize?: boolean;
}) => (
  <div className="flex items-center justify-between text-sm">
    <span className="text-gray-500">{label}:</span>
    <span className={`font-medium text-gray-800 ${capitalize ? 'capitalize' : ''}`}>{value}</span>
  </div>
);

export default Dashboard;
