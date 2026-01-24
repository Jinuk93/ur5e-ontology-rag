'use client';

import { useEffect, useRef, useCallback } from 'react';
import { toast } from 'sonner';
import { AlertTriangle, AlertCircle, Info, XCircle, CheckCircle } from 'lucide-react';
import { createElement } from 'react';
import type { IntegratedStreamData, ScenarioType, RiskLevel } from '@/types/api';
import {
  useAlertStore,
  shouldAlert,
  createEventFromStreamData,
  getScenarioName,
  getRiskLevelName,
} from '@/stores/alertStore';
import { useAlertSound } from './useAlertSound';

/**
 * 이상 감지 알림 훅
 *
 * IntegratedStreamData를 모니터링하여:
 * 1. 시나리오 변경 감지
 * 2. 이벤트 기록 저장
 * 3. Toast 알림 표시
 * 4. 경고음 재생
 */
export function useAnomalyAlert(latestData: IntegratedStreamData | null) {
  const { playAlert } = useAlertSound();
  const {
    settings,
    addEvent,
    resolveActiveEvent,
    updateActiveEvent,
    activeEvent,
    setLastAlertTime,
    lastAlertTime,
  } = useAlertStore();

  const prevScenarioRef = useRef<ScenarioType | null>(null);
  const prevRiskLevelRef = useRef<RiskLevel | null>(null);

  // Toast 표시 함수
  const showToast = useCallback(
    (scenario: ScenarioType, riskLevel: RiskLevel, data: IntegratedStreamData) => {
      const riskName = getRiskLevelName(riskLevel);

      // 빨간색 아이콘으로 통일
      const icons: Record<RiskLevel, React.ReactNode> = {
        low: createElement(Info, { className: 'w-4 h-4 text-blue-400' }),
        medium: createElement(AlertCircle, { className: 'w-4 h-4 text-red-400' }),
        high: createElement(AlertTriangle, { className: 'w-4 h-4 text-red-400' }),
        critical: createElement(XCircle, { className: 'w-4 h-4 text-red-400' }),
      };

      const toastType: Record<RiskLevel, 'info' | 'warning' | 'error'> = {
        low: 'info',
        medium: 'error',
        high: 'error',
        critical: 'error',
      };

      const messages: Record<ScenarioType, string> = {
        normal: '정상',
        collision: `충돌 ${data.axia80.Fz.toFixed(0)}N`,
        overload: `과부하 ${data.axia80.force_magnitude.toFixed(0)}N`,
        wear: `마모 감지`,
        risk_approach: `위험 ${(data.risk.contact_risk_score * 100).toFixed(0)}%`,
      };

      const type = toastType[riskLevel];
      const message = messages[scenario];

      toast[type](message, {
        description: riskName,
        icon: icons[riskLevel],
        duration: riskLevel === 'critical' ? 5000 : 3000,
      });
    },
    []
  );

  // 정상 복귀 Toast (초록색 아이콘)
  const showRecoveryToast = useCallback((prevScenario: ScenarioType) => {
    toast.success(`${getScenarioName(prevScenario)} 해제`, {
      description: '정상 복귀',
      duration: 2000,
      icon: createElement(CheckCircle, { className: 'w-4 h-4 text-green-400' }),
    });
  }, []);

  // 데이터 변경 감지 및 알림 처리
  useEffect(() => {
    if (!latestData) return;

    const currentScenario = latestData.scenario.current;
    const currentRiskLevel = latestData.risk.risk_level;
    const prevScenario = prevScenarioRef.current;

    // 시나리오가 변경된 경우
    if (prevScenario !== null && prevScenario !== currentScenario) {
      // 비정상 → 정상으로 변경 (복귀)
      if (currentScenario === 'normal' && prevScenario !== 'normal') {
        // 활성 이벤트 종료
        resolveActiveEvent();

        // 복귀 알림
        if (settings.toastEnabled) {
          showRecoveryToast(prevScenario);
        }
      }
      // 정상 → 비정상으로 변경 (이상 감지)
      else if (currentScenario !== 'normal') {
        // 새 이벤트 생성
        const newEvent = createEventFromStreamData(latestData, prevScenario);
        if (newEvent) {
          addEvent(newEvent);
        }

        // 알림 조건 확인
        const now = Date.now();
        const shouldTrigger = shouldAlert(currentScenario, currentRiskLevel, settings);
        const minInterval = 2000; // 최소 2초 간격

        if (shouldTrigger && now - lastAlertTime > minInterval) {
          setLastAlertTime(now);

          // Toast 알림
          if (settings.toastEnabled) {
            showToast(currentScenario, currentRiskLevel, latestData);
          }

          // 사운드 알림
          if (settings.soundEnabled) {
            playAlert(currentRiskLevel);
          }
        }
      }
    }

    // 활성 이벤트 업데이트 (최대 힘, 위험도 등)
    if (activeEvent && currentScenario !== 'normal') {
      const newMaxForce = Math.max(activeEvent.maxForce, latestData.axia80.force_magnitude);
      const newMaxRisk = Math.max(
        activeEvent.maxRiskScore,
        latestData.risk.contact_risk_score,
        latestData.risk.collision_risk_score
      );

      if (newMaxForce > activeEvent.maxForce || newMaxRisk > activeEvent.maxRiskScore) {
        updateActiveEvent({
          maxForce: newMaxForce,
          maxRiskScore: newMaxRisk,
          duration: latestData.scenario.elapsed_sec,
          details: {
            contactRiskScore: Math.max(
              activeEvent.details.contactRiskScore,
              latestData.risk.contact_risk_score
            ),
            collisionRiskScore: Math.max(
              activeEvent.details.collisionRiskScore,
              latestData.risk.collision_risk_score
            ),
            tcpSpeed: Math.max(activeEvent.details.tcpSpeed, latestData.ur5e.tcp_speed),
            protectiveStop: activeEvent.details.protectiveStop || latestData.ur5e.protective_stop,
          },
        });
      }
    }

    // 위험 레벨이 상승한 경우 추가 알림
    if (
      prevRiskLevelRef.current !== null &&
      currentScenario !== 'normal' &&
      isRiskEscalation(prevRiskLevelRef.current, currentRiskLevel)
    ) {
      const now = Date.now();
      if (now - lastAlertTime > 3000) {
        // 3초 간격
        setLastAlertTime(now);

        if (settings.toastEnabled) {
          toast.error(`위험↑ ${getRiskLevelName(currentRiskLevel)}`, {
            description: getScenarioName(currentScenario),
            duration: 3000,
          });
        }

        if (settings.soundEnabled) {
          playAlert(currentRiskLevel);
        }
      }
    }

    // 이전 상태 저장
    prevScenarioRef.current = currentScenario;
    prevRiskLevelRef.current = currentRiskLevel;
  }, [
    latestData,
    settings,
    activeEvent,
    lastAlertTime,
    addEvent,
    resolveActiveEvent,
    updateActiveEvent,
    setLastAlertTime,
    showToast,
    showRecoveryToast,
    playAlert,
  ]);
}

/**
 * 위험 레벨이 상승했는지 확인
 */
function isRiskEscalation(prev: RiskLevel, current: RiskLevel): boolean {
  const order: RiskLevel[] = ['low', 'medium', 'high', 'critical'];
  return order.indexOf(current) > order.indexOf(prev);
}

export default useAnomalyAlert;
