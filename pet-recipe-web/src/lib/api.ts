import { auth } from "./firebase";
import axios from 'axios';
import type {
  Pet,
  EnergyCalculationRequest,
  EnergyCalculationResponse,
  EnergyCalculationResult
} from '../types/pet';

// TODO: 替换为你的 Cloud Run 服务 URL
const CLOUD_RUN_BASE_URL = 'https://YOUR-SERVICE-URL.run.app';

// TODO: 替换为你的后端 API URL（用于与 Cloud SQL 交互）
const BACKEND_API_URL = 'https://YOUR-BACKEND-API-URL.run.app';


const API_BASE = (import.meta.env.VITE_API_BASE_URL as string) ?? "";

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const user = auth.currentUser;
  const token = user ? await user.getIdToken(/* forceRefresh */ false) : null;

  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }

  // 兼容空 body
  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("application/json")) return (undefined as T);
  return (await res.json()) as T;
}

  // 调用 Cloud Run 计算能量需求
export const calculateDailyEnergy = async (
  request: EnergyCalculationRequest
): Promise<EnergyCalculationResult> => {
  try {
    const response = await axios.post<EnergyCalculationResponse>(
      
      `${CLOUD_RUN_BASE_URL}/api/calculate-energy`,
      request,
      {
        headers: {
          'Content-Type': 'application/json',
        }
      }
    );

    if (response.data.success && response.data.data) {
      return response.data.data;
    } else {
      throw new Error(response.data.error || 'Failed to calculate energy');
    }
  } catch (error) {
    console.error('Error calculating energy:', error);
    throw error;
  }
};

// 创建宠物记录到 Cloud SQL
export const createPet = async (
  pet: Omit<Pet, 'id' | 'created_at' | 'updated_at'>,
  authToken: string
): Promise<Pet> => {
  try {
    const response = await axios.post<Pet>(
      `${BACKEND_API_URL}/api/pets`,
      pet,
      {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        }
      }
    );
    return response.data;
  } catch (error) {
    console.error('Error creating pet:', error);
    throw error;
  }
};

  // 获取用户的所有宠物
export const getUserPets = async (
  ownerUid: string,
  authToken: string
): Promise<Pet[]> => {
  try {
    const response = await axios.get<Pet[]>(
      `${BACKEND_API_URL}/api/pets/user/${ownerUid}`,
      {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      }
    );
    return response.data;
  } catch (error) {
    console.error('Error fetching pets:', error);
    throw error;
  }
};

  // 更新宠物信息
export const updatePet = async (
  petId: string,
  updates: Partial<Pet>,
  authToken: string
): Promise<Pet> => {
  try {
    const response = await axios.put<Pet>(
      `${BACKEND_API_URL}/api/pets/${petId}`,
      updates,
      {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        }
      }
    );
    return response.data;
  } catch (error) {
    console.error('Error updating pet:', error);
    throw error;
  }
};

// 删除宠物记录
export const deletePet = async (
  petId: string,
  authToken: string
): Promise<void> => {
  try {
    await axios.delete(
      `${BACKEND_API_URL}/api/pets/${petId}`,
      {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      }
    );
  } catch (error) {
    console.error('Error deleting pet:', error);
    throw error;
  }
};
// 获取单个宠物详情
export const getPetById = async (
  petId: string,
  authToken: string
): Promise<Pet> => {
  try {
    const response = await axios.get<Pet>(
      `${BACKEND_API_URL}/api/pets/${petId}`,
      {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      }
    );
    return response.data;
  } catch (error) {
    console.error('Error fetching pet:', error);
    throw error;
  }
};