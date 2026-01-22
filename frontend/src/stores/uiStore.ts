import { create } from 'zustand';
import type { EntityInfo, RiskAlert } from '@/types/api';

type ViewType = 'live' | 'graph' | 'history';

interface UIState {
  // Current view
  currentView: ViewType;
  setCurrentView: (view: ViewType) => void;

  // Selected entity
  selectedEntity: EntityInfo | null;
  setSelectedEntity: (entity: EntityInfo | null) => void;

  // Risk alerts
  alerts: RiskAlert[];
  setAlerts: (alerts: RiskAlert[]) => void;
  addAlert: (alert: RiskAlert) => void;

  // Graph view center node
  graphCenterNode: string | null;
  setGraphCenterNode: (nodeId: string | null) => void;

  // Time range for history
  timeRange: '10m' | '1h' | '24h' | '7d';
  setTimeRange: (range: '10m' | '1h' | '24h' | '7d') => void;

  // Chat panel visibility (mobile)
  isChatOpen: boolean;
  setChatOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  currentView: 'live',
  setCurrentView: (view) => set({ currentView: view }),

  selectedEntity: null,
  setSelectedEntity: (entity) => set({ selectedEntity: entity }),

  alerts: [],
  setAlerts: (alerts) => set({ alerts }),
  addAlert: (alert) => set((state) => ({ alerts: [alert, ...state.alerts] })),

  graphCenterNode: null,
  setGraphCenterNode: (nodeId) => set({ graphCenterNode: nodeId }),

  timeRange: '1h',
  setTimeRange: (range) => set({ timeRange: range }),

  isChatOpen: false,
  setChatOpen: (open) => set({ isChatOpen: open }),
}));
