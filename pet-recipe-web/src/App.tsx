// src/App.tsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Homepage from './components/Homepage/Homepage';
import LoginPage from './components/Auth/LoginPage';
import Dashboard from './components/Dashboard/Dashboard';
import AddPetForm from './components/Pet/AddPetForm';
import RecipeResultPage from "./components/Recipe/RecipeResult";
import RecipeDetailPage from "./components/Recipe/RecipeDetail";

// 受保护的路由组件
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { currentUser, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-green-500 border-t-transparent"></div>
      </div>
    );
  }

  if (!currentUser) {
    return <Navigate to="/login" />;
  }

  return <>{children}</>;
};

// App 路由配置
const AppRoutes: React.FC = () => {
  const { currentUser } = useAuth();
  return (
    <Routes>
      {/* 首页 */}
      <Route path="/" element={<Homepage />} />

      {/* 登录/注册 */}
      <Route path="/login" element={currentUser ? <Navigate to="/dashboard" replace /> : <LoginPage />} />

      {/* 仪表板 (受保护) */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />

      {/* 添加宠物 (受保护) */}
      <Route
        path="/add-pet"
        element={
          <ProtectedRoute>
            <AddPetForm />
          </ProtectedRoute>
        }
      />

      <Route path="/edit-pet/:petId" element={<ProtectedRoute><AddPetForm /></ProtectedRoute>} />
      {/* 同步版食谱路由（无 run_id） */}
      <Route path="/recipes/result"        element={<ProtectedRoute><RecipeResultPage /></ProtectedRoute>} />
      <Route path="/recipes/detail/:rank"  element={<ProtectedRoute><RecipeDetailPage /></ProtectedRoute>} />
      
      {/* 404 */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

function App() {
  return (
    <Router>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </Router>
  );
}

export default App;
