import { create } from 'zustand';
import type { ChatResponse } from '@/types/api';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  response?: ChatResponse;
  isLoading?: boolean;
  error?: string;
}

interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;

  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => string;
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void;
  setLoading: (loading: boolean) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isLoading: false,

  addMessage: (message) => {
    const id = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    set((state) => ({
      messages: [
        ...state.messages,
        {
          ...message,
          id,
          timestamp: new Date(),
        },
      ],
    }));
    return id;
  },

  updateMessage: (id, updates) => {
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id ? { ...msg, ...updates } : msg
      ),
    }));
  },

  setLoading: (loading) => set({ isLoading: loading }),

  clearMessages: () => set({ messages: [] }),
}));
