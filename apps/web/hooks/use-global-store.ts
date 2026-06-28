import { create } from "zustand";
import { persist } from "zustand/middleware";

interface GlobalState {
  activeCompanyId: string | null;
  activeCompanyName: string | null;
  setActiveCompany: (id: string, name: string) => void;
  clearActiveCompany: () => void;
}

export const useGlobalStore = create<GlobalState>()(
  // 使用 persist 中间件，自动将状态持久化到 localStorage
  persist(
    (set) => ({
      activeCompanyId: "c_001", // 默认设置一个，比如 Aya Cloud 的 ID
      activeCompanyName: "Aya Cloud",
      
      setActiveCompany: (id, name) => 
        set({ activeCompanyId: id, activeCompanyName: name }),
        
      clearActiveCompany: () => 
        set({ activeCompanyId: null, activeCompanyName: null }),
    }),
    {
      name: "ai-bos-global-storage", // 存在 localStorage 里的 key
    }
  )
);