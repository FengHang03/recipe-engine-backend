// src/contexts/AuthContext.tsx
import React, { createContext, use, useContext, useEffect, useState } from 'react';
import {
  signInWithEmailAndPassword,
  signInAnonymously,
  createUserWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  GoogleAuthProvider,
  signInWithPopup,
  sendPasswordResetEmail
} from 'firebase/auth';
import { doc, setDoc, getFirestore } from 'firebase/firestore';
import type { User } from 'firebase/auth';
import { auth } from '../lib/firebase';

const db = getFirestore();

interface AuthContextType {
  currentUser: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  loginAnonymously: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  getAuthToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // 邮箱密码登录
  const login = async (email: string, password: string) => {
    await signInWithEmailAndPassword(auth, email, password);

  };

  // 邮箱密码注册
  const signup = async (email: string, password: string) => {
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    const user = userCredential.user;

    const db = getFirestore();
    await setDoc(doc(db, "users", user.uid), {
      email: user.email,
      role: 'user',
      createdAt: new Date()
      
    // 2. (可选) 如果 Cloud SQL 需要这个用户记录，调用一次你的 Cloud Run 后端 API
    // const token = await user.getIdToken();
    // await fetch('https://your-api-on-cloud-run/api/user/sync', {
    //   method: 'POST',
    //   headers: { 'Authorization': `Bearer ${token}` }
    // });
    });
  };

  // Google 登录
  const loginWithGoogle = async () => {
    const provider = new GoogleAuthProvider();
    await signInWithPopup(auth, provider);
  };

  // 登出
  const logout = async () => {
    await signOut(auth);
  };

  // 重置密码
  const resetPassword = async (email: string) => {
    await sendPasswordResetEmail(auth, email);
  };

  // 获取认证 Token
  const getAuthToken = async (forceRefresh = false): Promise<string | null> => {
    if (!auth.currentUser) return null;
    return await auth.currentUser?.getIdToken(forceRefresh);
  };

  const loginAnonymously = async () => {
    await signInAnonymously(auth);
  };

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setCurrentUser(user);
      setLoading(false);
    });

    return unsubscribe;
  }, []);

  const value: AuthContextType = {
    currentUser,
    loading,
    login,
    signup,
    logout,
    loginWithGoogle,
    loginAnonymously,
    resetPassword,
    getAuthToken
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
};
