// src/components/Pet/AddPetForm.tsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  Save, 
  Loader, 
  AlertCircle,
  Calendar,
  Weight,
  Activity,
  Heart
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { calculateDailyEnergy, createPet } from '../../lib/api';
import type {
    PetFormData,
    EnergyCalculationRequest,
} from '../../types/pet';
import {
  Species,
  ActivityLevel,
  ReproductiveStatus,
  ReproState,
  SizeClass,
  LifeStage,
  PhysiologicalStatus,
} from '../../types/pet';

const AddPetForm: React.FC = () => {
  const { currentUser, getAuthToken } = useAuth();
  const navigate = useNavigate();

  const [formData, setFormData] = useState<PetFormData>({
    name: '',
    species: Species.DOG,
    breed: '',
    size_class: SizeClass.MEDIUM,
    birth_date: '',
    age_months: 12,
    weight_kg: 10,
    activity_level: ActivityLevel.MODERATE_ACTIVE,
    reproductive_status: ReproductiveStatus.NEUTERED,
    repro_state: ReproState.NONE,
    lactation_week: 4,
    nursing_count: 1,
    health_conditions: [],
    allergies: []
  });

  const [calculatedEnergy, setCalculatedEnergy] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  // 根据体型和物种计算生命阶段
  const calculateLifeStage = (): LifeStage => {
    const { species, age_months, size_class } = formData;

    if (species === Species.CAT) {
      if (age_months! < 12) return LifeStage.KITTEN;
      if (age_months! >= 84) return LifeStage.SENIOR; // 7 years
      return LifeStage.ADULT;
    }

    // Dog
    if (!size_class) return LifeStage.ADULT;

    const adultMonths: Record<SizeClass, number> = {
      [SizeClass.TOY]: 10,
      [SizeClass.SMALL]: 12,
      [SizeClass.MEDIUM]: 12,
      [SizeClass.LARGE]: 15,
      [SizeClass.GIANT]: 18
    };

    const seniorMonths: Record<SizeClass, number> = {
      [SizeClass.TOY]: 120,
      [SizeClass.SMALL]: 120,
      [SizeClass.MEDIUM]: 96,
      [SizeClass.LARGE]: 84,
      [SizeClass.GIANT]: 72
    };

    if (age_months! < adultMonths[size_class]) return LifeStage.PUPPY;
    if (age_months! >= seniorMonths[size_class]) return LifeStage.SENIOR;
    return LifeStage.ADULT;
  };

  // 计算高级月龄（用于能量计算）
  const calculateSeniorMonth = (): number => {
    const { species, size_class } = formData;

    if (species === Species.CAT) return 84; // 7 years

    if (!size_class) return 84;

    const seniorMonths: Record<SizeClass, number> = {
      [SizeClass.TOY]: 120,
      [SizeClass.SMALL]: 120,
      [SizeClass.MEDIUM]: 96,
      [SizeClass.LARGE]: 84,
      [SizeClass.GIANT]: 72
    };

    return seniorMonths[size_class];
  };

  // 将 ReproductiveStatus + ReproState 转换为 PhysiologicalStatus
  const getPhysiologicalStatus = (): PhysiologicalStatus => {
    if (formData.repro_state === ReproState.PREGNANT) {
      return PhysiologicalStatus.PREGNANT;
    }
    if (formData.repro_state === ReproState.LACTATING) {
      return PhysiologicalStatus.LACTATING;
    }
    if (formData.reproductive_status === ReproductiveStatus.NEUTERED) {
      return PhysiologicalStatus.NEUTERED;
    }
    return PhysiologicalStatus.INTACT;
  };

  // 计算能量需求
  const handleCalculateEnergy = async () => {
    setError('');
    setLoading(true);

    try {
      const request: EnergyCalculationRequest = {
        weight_kg: formData.weight_kg,
        species: formData.species,
        age_months: formData.age_months || 12,
        activity_level: formData.activity_level,
        physiological_status: getPhysiologicalStatus(),
        breed: formData.breed || undefined,
        lactation_week: formData.lactation_week,
        nursing_count: formData.nursing_count,
        senior_month: calculateSeniorMonth()
      };

      const result = await calculateDailyEnergy(request);
      setCalculatedEnergy(result.daily_energy_kcal);
      
      // 显示警告信息
      if (result.warnings && result.warnings.length > 0) {
        console.warn('Energy calculation warnings:', result.warnings);
      }
    } catch (err: any) {
      console.error('Energy calculation error:', err);
      setError('Failed to calculate energy requirement: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // 提交表单
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (!currentUser) {
      setError('You must be logged in to add a pet');
      setLoading(false);
      return;
    }

    try {
      const token = await getAuthToken();
      if (!token) {
        throw new Error('Failed to get authentication token');
      }

      // 构建宠物数据
      const petData = {
        owner_uid: currentUser.uid,
        name: formData.name,
        species: formData.species,
        breed: formData.breed || undefined,
        size_class: formData.size_class,
        birth_date: formData.birth_date || undefined,
        age_months: formData.age_months,
        weight_kg: formData.weight_kg,
        activity_level: formData.activity_level,
        reproductive_status: formData.reproductive_status,
        repro_state: formData.repro_state,
        life_stage: calculateLifeStage(),
        lactation_week: formData.lactation_week,
        nursing_count: formData.nursing_count,
        health_conditions: formData.health_conditions.reduce((acc, condition) => {
          acc[condition] = true;
          return acc;
        }, {} as Record<string, any>),
        allergies: formData.allergies.reduce((acc, allergy) => {
          acc[allergy] = true;
          return acc;
        }, {} as Record<string, any>),
        daily_calories_kcal: calculatedEnergy || undefined
      };

      await createPet(petData, token);
      setSuccess(true);
      
      // 延迟后跳转
      setTimeout(() => {
        navigate('/dashboard');
      }, 1500);
    } catch (err: any) {
      console.error('Error saving pet:', err);
      setError('Failed to save pet: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 p-4 md:p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            Back to Dashboard
          </button>
          <h1 className="text-3xl font-bold text-gray-900">Add New Pet</h1>
          <p className="text-gray-600 mt-2">
            Enter your pet's information to calculate daily calorie needs
          </p>
        </div>

        {/* Success Message */}
        {success && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-green-800 font-medium">
              ✓ Pet added successfully! Redirecting...
            </p>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start">
            <AlertCircle className="w-5 h-5 text-red-600 mr-3 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-md p-6 space-y-8">
          {/* Basic Information */}
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Basic Information</h2>
            
            {/* Pet Name */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Pet Name *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                placeholder="e.g., Max"
                required
              />
            </div>

            {/* Species */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Species *
              </label>
              <div className="grid grid-cols-2 gap-4">
                <button
                  type="button"
                  onClick={() => setFormData({ ...formData, species: Species.DOG })}
                  className={`p-4 border-2 rounded-lg transition-all ${
                    formData.species === Species.DOG
                      ? 'border-green-500 bg-green-50'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  <div className="text-center">
                    <div className="text-3xl mb-2">🐕</div>
                    <span className="font-medium">Dog</span>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => setFormData({ ...formData, species: Species.CAT })}
                  className={`p-4 border-2 rounded-lg transition-all ${
                    formData.species === Species.CAT
                      ? 'border-green-500 bg-green-50'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  <div className="text-center">
                    <div className="text-3xl mb-2">🐱</div>
                    <span className="font-medium">Cat</span>
                  </div>
                </button>
              </div>
            </div>

            {/* Breed */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Breed (Optional)
              </label>
              <input
                type="text"
                value={formData.breed}
                onChange={(e) => setFormData({ ...formData, breed: e.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                placeholder="e.g., Golden Retriever"
              />
            </div>

            {/* Size Class (only for dogs) */}
            {formData.species === Species.DOG && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Size Class *
                </label>
                <select
                  value={formData.size_class}
                  onChange={(e) => setFormData({ ...formData, size_class: e.target.value as SizeClass })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  required
                >
                  <option value={SizeClass.TOY}>Toy (&lt;5 kg)</option>
                  <option value={SizeClass.SMALL}>Small (5-10 kg)</option>
                  <option value={SizeClass.MEDIUM}>Medium (10-25 kg)</option>
                  <option value={SizeClass.LARGE}>Large (25-45 kg)</option>
                  <option value={SizeClass.GIANT}>Giant (&gt;45 kg)</option>
                </select>
              </div>
            )}
          </div>

          {/* Physical Information */}
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
              <Weight className="w-5 h-5 mr-2 text-green-600" />
              Physical Information
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Age */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  <Calendar className="w-4 h-4 inline mr-1" />
                  Age (months) *
                </label>
                <input
                  type="number"
                  value={formData.age_months}
                  onChange={(e) => setFormData({ ...formData, age_months: parseInt(e.target.value) })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  min="1"
                  max="300"
                  required
                />
              </div>

              {/* Weight */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  <Weight className="w-4 h-4 inline mr-1" />
                  Weight (kg) *
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.weight_kg}
                  onChange={(e) => setFormData({ ...formData, weight_kg: parseFloat(e.target.value) })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  min="0.1"
                  max="100"
                  required
                />
              </div>
            </div>

            {/* Birth Date (Optional) */}
            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Birth Date (Optional)
              </label>
              <input
                type="date"
                value={formData.birth_date}
                onChange={(e) => setFormData({ ...formData, birth_date: e.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Activity & Status */}
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
              <Activity className="w-5 h-5 mr-2 text-green-600" />
              Activity & Status
            </h2>

            {/* Activity Level */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Activity Level *
              </label>
              <select
                value={formData.activity_level}
                onChange={(e) => setFormData({ ...formData, activity_level: e.target.value as ActivityLevel })}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                required
              >
                <option value={ActivityLevel.SEDENTARY}>Sedentary (little to no exercise)</option>
                <option value={ActivityLevel.LIGHT_ACTIVE}>Light Active (1-2 days/week)</option>
                <option value={ActivityLevel.MODERATE_ACTIVE}>Moderate Active (3-5 days/week)</option>
                <option value={ActivityLevel.VERY_ACTIVE}>Very Active (6-7 days/week)</option>
                <option value={ActivityLevel.EXTREMELY_ACTIVE}>Extremely Active (athlete/working dog)</option>
              </select>
            </div>

            {/* Reproductive Status */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Reproductive Status *
              </label>
              <select
                value={formData.reproductive_status}
                onChange={(e) => setFormData({ ...formData, reproductive_status: e.target.value as ReproductiveStatus })}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                required
              >
                <option value={ReproductiveStatus.NEUTERED}>Neutered/Spayed</option>
                <option value={ReproductiveStatus.INTACT}>Intact</option>
              </select>
            </div>

            {/* Reproductive State */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Heart className="w-4 h-4 inline mr-1" />
                Reproductive State *
              </label>
              <select
                value={formData.repro_state}
                onChange={(e) => setFormData({ ...formData, repro_state: e.target.value as ReproState })}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                required
              >
                <option value={ReproState.NONE}>None</option>
                <option value={ReproState.PREGNANT}>Pregnant</option>
                <option value={ReproState.LACTATING}>Lactating</option>
              </select>
            </div>

            {/* Lactation Details (if lactating) */}
            {formData.repro_state === ReproState.LACTATING && (
              <div className="grid grid-cols-2 gap-4 p-4 bg-pink-50 rounded-lg">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Lactation Week
                  </label>
                  <input
                    type="number"
                    value={formData.lactation_week}
                    onChange={(e) => setFormData({ ...formData, lactation_week: parseInt(e.target.value) })}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    min="1"
                    max="12"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Number of Offspring
                  </label>
                  <input
                    type="number"
                    value={formData.nursing_count}
                    onChange={(e) => setFormData({ ...formData, nursing_count: parseInt(e.target.value) })}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    min="1"
                    max="15"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Energy Calculation */}
          <div className="bg-gradient-to-r from-green-50 to-blue-50 p-6 rounded-lg">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Daily Energy Requirement
            </h2>
            
            <button
              type="button"
              onClick={handleCalculateEnergy}
              disabled={loading}
              className="w-full md:w-auto bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition-colors font-medium flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed mb-4"
            >
              {loading ? (
                <>
                  <Loader className="w-5 h-5 mr-2 animate-spin" />
                  Calculating...
                </>
              ) : (
                'Calculate Energy Requirement'
              )}
            </button>

            {calculatedEnergy !== null && (
              <div className="p-4 bg-white rounded-lg border-2 border-green-500">
                <div className="text-center">
                  <p className="text-sm text-gray-600 mb-1">Daily Calorie Requirement</p>
                  <p className="text-4xl font-bold text-green-600">
                    {calculatedEnergy.toFixed(0)}
                  </p>
                  <p className="text-sm text-gray-600 mt-1">kcal/day</p>
                </div>
              </div>
            )}

            <p className="text-xs text-gray-500 mt-3">
              * This calculation is based on AAFCO standards and your pet's specific characteristics.
            </p>
          </div>

          {/* Submit Buttons */}
          <div className="flex gap-4">
            <button
              type="submit"
              disabled={loading || !calculatedEnergy}
              className="flex-1 bg-green-600 text-white py-3 px-6 rounded-lg hover:bg-green-700 transition-colors font-medium flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="w-5 h-5 mr-2" />
              Save Pet
            </button>
            
            <button
              type="button"
              onClick={() => navigate('/dashboard')}
              className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>

          {!calculatedEnergy && (
            <p className="text-sm text-gray-500 text-center">
              Please calculate energy requirement before saving
            </p>
          )}
        </form>
      </div>
    </div>
  );
};

export default AddPetForm;
