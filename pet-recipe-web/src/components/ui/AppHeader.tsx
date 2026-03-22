// src/components/ui/AppHeader.tsx
// 全站共享导航栏，与 Homepage nav 完全一致
// 在 Homepage、Dashboard、AddPetForm 中复用

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { LogIn, UserPlus } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';

const AppHeader: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser } = useAuth();

  return (
    <nav className="bg-white shadow-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">

          {/* Logo — 点击跳回首页 */}
          <div
            className="flex items-center cursor-pointer"
            onClick={() => navigate('/')}
          >
            <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center mr-3">
              <svg className="w-6 h-6 text-green-600" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2L13.5 7L18 7L14.5 10L16 15L12 12L8 15L9.5 10L6 7L10.5 7L12 2Z"/>
              </svg>
            </div>
            <span className="text-xl font-bold text-gray-900">Pet Recipe</span>
          </div>

          {/* 中间导航链接（仅首页可用，其他页面隐藏） */}
          <div className="hidden md:flex items-center space-x-8">
            <a href="/#features"      className="text-gray-600 hover:text-gray-900 font-medium">Features</a>
            <a href="/#how-it-works"  className="text-gray-600 hover:text-gray-900 font-medium">How It Works</a>
            <a href="/#testimonials"  className="text-gray-600 hover:text-gray-900 font-medium">Testimonials</a>
          </div>

          {/* 右侧按钮 */}
          <div className="flex items-center space-x-4">
            {currentUser ? (
              <button
                onClick={() => navigate('/dashboard')}
                className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 transition-colors font-medium"
              >
                Dashboard
              </button>
            ) : (
              <>
                <button
                  onClick={() => navigate('/login')}
                  className="text-gray-700 hover:text-gray-900 font-medium flex items-center"
                >
                  <LogIn className="w-4 h-4 mr-2" />
                  Sign In
                </button>
                <button
                  onClick={() => navigate('/login')}
                  className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 transition-colors font-medium flex items-center"
                >
                  <UserPlus className="w-4 h-4 mr-2" />
                  Get Started
                </button>
              </>
            )}
          </div>

        </div>
      </div>
    </nav>
  );
};

export default AppHeader;
