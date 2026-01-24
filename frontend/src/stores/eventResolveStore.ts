import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface EventResolveState {
  // 해결된 이벤트 ID 목록
  resolvedEventIds: Set<string>;

  // Actions
  resolveEvent: (eventId: string) => void;
  unresolveEvent: (eventId: string) => void;
  toggleResolve: (eventId: string) => void;
  isResolved: (eventId: string) => boolean;
  clearResolved: () => void;
}

export const useEventResolveStore = create<EventResolveState>()(
  persist(
    (set, get) => ({
      resolvedEventIds: new Set<string>(),

      resolveEvent: (eventId) =>
        set((state) => ({
          resolvedEventIds: new Set([...state.resolvedEventIds, eventId]),
        })),

      unresolveEvent: (eventId) =>
        set((state) => {
          const newSet = new Set(state.resolvedEventIds);
          newSet.delete(eventId);
          return { resolvedEventIds: newSet };
        }),

      toggleResolve: (eventId) => {
        const isCurrentlyResolved = get().resolvedEventIds.has(eventId);
        if (isCurrentlyResolved) {
          get().unresolveEvent(eventId);
        } else {
          get().resolveEvent(eventId);
        }
      },

      isResolved: (eventId) => get().resolvedEventIds.has(eventId),

      clearResolved: () => set({ resolvedEventIds: new Set<string>() }),
    }),
    {
      name: 'event-resolve-storage',
      // Set을 JSON으로 변환
      storage: {
        getItem: (name) => {
          const str = localStorage.getItem(name);
          if (!str) return null;
          const parsed = JSON.parse(str);
          return {
            ...parsed,
            state: {
              ...parsed.state,
              resolvedEventIds: new Set(parsed.state.resolvedEventIds || []),
            },
          };
        },
        setItem: (name, value) => {
          const toStore = {
            ...value,
            state: {
              ...value.state,
              resolvedEventIds: [...value.state.resolvedEventIds],
            },
          };
          localStorage.setItem(name, JSON.stringify(toStore));
        },
        removeItem: (name) => localStorage.removeItem(name),
      },
    }
  )
);
