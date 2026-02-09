// src/components/Dashboard/Dashboard.tsx
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, LogOut, Edit, Trash2, Activity } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { getUserPets, deletePet } from '../../lib/api';
import type { Pet } from '../../types/pet';

const Dashboard: React.FC = () => {
  const { currentUser, logout, getAuthToken } = useAuth();
  const navigate = useNavigate();
  
  const [pets, setPets] = useState<Pet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadPets();
  }, []);

  const loadPets = async () => {
    if (!currentUser) return;

    setLoading(true);
    setError('');

    try {
      const token = await getAuthToken();
      if (!token) {
        throw new Error('Failed to get authentication token');
      }

      const userPets = await getUserPets(currentUser.uid, token);
      setPets(userPets);
    } catch (err: any) {
      console.error('Error loading pets:', err);
      setError('Failed to load pets: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeletePet = async (petId: string) => {
    if (!window.confirm('Are you sure you want to delete this pet?')) {
      return;
    }

    try {
      const token = await getAuthToken();
      if (!token) {
        throw new Error('Failed to get authentication token');
      }

      await deletePet(petId, token);
      setPets(pets.filter(p => p.id !== petId));
    } catch (err: any) {
      console.error('Error deleting pet:', err);
      alert('Failed to delete pet: ' + err.message);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">My Pets</h1>
            <p className="text-sm text-gray-600">
              Welcome, {currentUser?.email}
            </p>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center px-4 py-2 text-gray-700 hover:text-gray-900 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Logout
          </button>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Add Pet Button */}
        <div className="mb-6">
          <button
            onClick={() => navigate('/add-pet')}
            className="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition-colors font-medium flex items-center"
          >
            <Plus className="w-5 h-5 mr-2" />
            Add New Pet
          </button>
        </div>

        {/* Loading State */}
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-green-500 border-t-transparent"></div>
            <p className="mt-4 text-gray-600">Loading pets...</p>
          </div>
        ) : pets.length === 0 ? (
          /* Empty State */
          <div className="bg-white rounded-lg shadow-md p-12 text-center">
            <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              No pets yet
            </h3>
            <p className="text-gray-600 mb-6">
              Add your first pet to start creating personalized recipes
            </p>
            <button
              onClick={() => navigate('/add-pet')}
              className="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition-colors font-medium inline-flex items-center"
            >
              <Plus className="w-5 h-5 mr-2" />
              Add Your First Pet
            </button>
          </div>
        ) : (
          /* Pet Grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {pets.map((pet) => (
              <div
                key={pet.id}
                className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow overflow-hidden"
              >
                {/* Pet Header */}
                <div className="bg-gradient-to-r from-green-500 to-blue-500 p-4 text-white">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-xl font-bold">{pet.name}</h3>
                    <span className="text-3xl">
                      {pet.species === 'dog' ? '🐕' : '🐱'}
                    </span>
                  </div>
                  <p className="text-sm opacity-90">
                    {pet.breed || 'Mixed breed'}
                  </p>
                </div>

                {/* Pet Details */}
                <div className="p-4 space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Age:</span>
                    <span className="font-medium">
                      {pet.age_months} months ({pet.life_stage})
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Weight:</span>
                    <span className="font-medium">{pet.weight_kg} kg</span>
                  </div>

                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Size:</span>
                    <span className="font-medium capitalize">
                      {pet.size_class || 'N/A'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Activity:</span>
                    <span className="font-medium capitalize">
                      {pet.activity_level.replace('_', ' ')}
                    </span>
                  </div>

                  {/* Daily Calories */}
                  {pet.daily_calories_kcal && (
                    <div className="mt-4 p-3 bg-green-50 rounded-lg">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600 flex items-center">
                          <Activity className="w-4 h-4 mr-1" />
                          Daily Calories:
                        </span>
                        <span className="text-lg font-bold text-green-600">
                          {pet.daily_calories_kcal.toFixed(0)} kcal
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="border-t border-gray-200 p-4 flex gap-2">
                  <button
                    onClick={() => navigate(`/edit-pet/${pet.id}`)}
                    className="flex-1 flex items-center justify-center px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <Edit className="w-4 h-4 mr-2" />
                    Edit
                  </button>
                  <button
                    onClick={() => handleDeletePet(pet.id!)}
                    className="flex-1 flex items-center justify-center px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete
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

export default Dashboard;
