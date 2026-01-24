import { create } from 'zustand';
import type { ScenarioType, RiskLevel, IntegratedStreamData } from '@/types/api';

/**
 * 실시간 감지 이벤트
 */
export interface LiveDetectedEvent {
  id: string;
  timestamp: string;
  scenario: ScenarioType;
  riskLevel: RiskLevel;
  maxForce: number;
  maxRiskScore: number;
  duration: number; // seconds
  resolved: boolean;
  resolvedAt?: string;
  details: {
    contactRiskScore: number;
    collisionRiskScore: number;
    tcpSpeed: number;
    protectiveStop: boolean;
  };
}

/**
 * 알림 설정
 */
export interface AlertSettings {
  soundEnabled: boolean;
  toastEnabled: boolean;
  minRiskLevelForAlert: RiskLevel; // 이 레벨 이상일 때만 알림
  scenariosToAlert: ScenarioType[]; // 알림할 시나리오 타입
}

interface AlertState {
  // 감지된 이벤트 목록 (최근 100개)
  detectedEvents: LiveDetectedEvent[];

  // 현재 진행 중인 이벤트 (아직 resolved되지 않은)
  activeEvent: LiveDetectedEvent | null;

  // 알림 설정
  settings: AlertSettings;

  // 마지막 알림 시간 (중복 알림 방지)
  lastAlertTime: number;

  // Actions
  addEvent: (event: LiveDetectedEvent) => void;
  resolveActiveEvent: () => void;
  updateActiveEvent: (data: Partial<LiveDetectedEvent>) => void;
  clearEvents: () => void;
  updateSettings: (settings: Partial<AlertSettings>) => void;
  setLastAlertTime: (time: number) => void;
}

const DEFAULT_SETTINGS: AlertSettings = {
  soundEnabled: true,
  toastEnabled: true,
  minRiskLevelForAlert: 'medium',
  scenariosToAlert: ['collision', 'overload', 'wear', 'risk_approach'],
};

export const useAlertStore = create<AlertState>((set, get) => ({
  detectedEvents: [],
  activeEvent: null,
  settings: DEFAULT_SETTINGS,
  lastAlertTime: 0,

  addEvent: (event) => set((state) => ({
    detectedEvents: [event, ...state.detectedEvents].slice(0, 100),
    activeEvent: event.resolved ? state.activeEvent : event,
  })),

  resolveActiveEvent: () => set((state) => {
    if (!state.activeEvent) return state;

    const resolvedEvent: LiveDetectedEvent = {
      ...state.activeEvent,
      resolved: true,
      resolvedAt: new Date().toISOString(),
    };

    return {
      activeEvent: null,
      detectedEvents: state.detectedEvents.map((e) =>
        e.id === resolvedEvent.id ? resolvedEvent : e
      ),
    };
  }),

  updateActiveEvent: (data) => set((state) => {
    if (!state.activeEvent) return state;

    const updated = { ...state.activeEvent, ...data };

    return {
      activeEvent: updated,
      detectedEvents: state.detectedEvents.map((e) =>
        e.id === updated.id ? updated : e
      ),
    };
  }),

  clearEvents: () => set({ detectedEvents: [], activeEvent: null }),

  updateSettings: (settings) => set((state) => ({
    settings: { ...state.settings, ...settings },
  })),

  setLastAlertTime: (time) => set({ lastAlertTime: time }),
}));

/**
 * 시나리오가 알림 대상인지 확인
 */
export function shouldAlert(
  scenario: ScenarioType,
  riskLevel: RiskLevel,
  settings: AlertSettings
): boolean {
  // 정상 시나리오는 알림하지 않음
  if (scenario === 'normal') return false;

  // 설정된 시나리오 타입인지 확인
  if (!settings.scenariosToAlert.includes(scenario)) return false;

  // 위험 레벨 체크
  const riskOrder: RiskLevel[] = ['low', 'medium', 'high', 'critical'];
  const minIndex = riskOrder.indexOf(settings.minRiskLevelForAlert);
  const currentIndex = riskOrder.indexOf(riskLevel);

  return currentIndex >= minIndex;
}

/**
 * IntegratedStreamData에서 LiveDetectedEvent 생성
 */
export function createEventFromStreamData(
  data: IntegratedStreamData,
  prevScenario: ScenarioType | null
): LiveDetectedEvent | null {
  const currentScenario = data.scenario.current;

  // 시나리오가 normal이 아니고, 이전과 다른 경우에만 새 이벤트 생성
  if (currentScenario === 'normal') return null;
  if (prevScenario === currentScenario) return null;

  return {
    id: `event_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    timestamp: data.timestamp,
    scenario: currentScenario,
    riskLevel: data.risk.risk_level,
    maxForce: data.axia80.force_magnitude,
    maxRiskScore: Math.max(data.risk.contact_risk_score, data.risk.collision_risk_score),
    duration: 0,
    resolved: false,
    details: {
      contactRiskScore: data.risk.contact_risk_score,
      collisionRiskScore: data.risk.collision_risk_score,
      tcpSpeed: data.ur5e.tcp_speed,
      protectiveStop: data.ur5e.protective_stop,
    },
  };
}

/**
 * 시나리오 타입에 따른 한글 이름
 */
export function getScenarioName(scenario: ScenarioType): string {
  const names: Record<ScenarioType, string> = {
    normal: '정상',
    collision: '충돌',
    overload: '과부하',
    wear: '마모',
    risk_approach: '위험 접근',
  };
  return names[scenario] || scenario;
}

/**
 * 위험 레벨에 따른 한글 이름
 */
export function getRiskLevelName(level: RiskLevel): string {
  const names: Record<RiskLevel, string> = {
    low: '낮음',
    medium: '보통',
    high: '높음',
    critical: '위험',
  };
  return names[level] || level;
}
