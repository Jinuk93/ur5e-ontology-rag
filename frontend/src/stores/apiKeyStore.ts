/**
 * OpenAI API Key Management Store
 *
 * 사용자가 직접 OpenAI API 키를 등록해서 사용하도록 함.
 * .env.local 에서 NEXT_PUBLIC_OPENAI_API_KEY 가 있으면 자동 로드.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ApiKeyState {
  apiKey: string | null;
  isKeyRegistered: boolean;
  showKeyModal: boolean;

  // Actions
  setApiKey: (key: string) => void;
  clearApiKey: () => void;
  openKeyModal: () => void;
  closeKeyModal: () => void;
  initializeFromEnv: () => void;
}

export const useApiKeyStore = create<ApiKeyState>()(
  persist(
    (set, get) => ({
      apiKey: null,
      isKeyRegistered: false,
      showKeyModal: false,

      setApiKey: (key: string) => {
        if (key && key.trim()) {
          set({ apiKey: key.trim(), isKeyRegistered: true, showKeyModal: false });
        }
      },

      clearApiKey: () => {
        set({ apiKey: null, isKeyRegistered: false });
      },

      openKeyModal: () => {
        set({ showKeyModal: true });
      },

      closeKeyModal: () => {
        set({ showKeyModal: false });
      },

      initializeFromEnv: () => {
        // .env.local의 NEXT_PUBLIC_OPENAI_API_KEY 확인
        const envKey = process.env.NEXT_PUBLIC_OPENAI_API_KEY;
        if (envKey && envKey.trim() && !get().isKeyRegistered) {
          set({ apiKey: envKey.trim(), isKeyRegistered: true });
        }
      },
    }),
    {
      name: 'openai-api-key-storage',
      // API 키는 localStorage에 저장 (보안 주의 필요)
      partialize: (state) => ({
        apiKey: state.apiKey,
        isKeyRegistered: state.isKeyRegistered,
      }),
    }
  )
);
