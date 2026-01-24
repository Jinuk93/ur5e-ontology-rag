'use client';

import { useCallback, useRef } from 'react';
import type { RiskLevel } from '@/types/api';

/**
 * 알림 사운드 훅
 *
 * Web Audio API를 사용하여 위험 레벨에 따라 다른 경고음을 생성합니다.
 * - low: 짧은 단일 비프음
 * - medium: 중간 비프음 (2회)
 * - high: 높은 비프음 (3회)
 * - critical: 연속 경고음
 */
export function useAlertSound() {
  const audioContextRef = useRef<AudioContext | null>(null);
  const isPlayingRef = useRef(false);

  // AudioContext 초기화 (user interaction 후에만 가능)
  const getAudioContext = useCallback(() => {
    if (!audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
    }
    return audioContextRef.current;
  }, []);

  // 단일 비프음 재생
  const playBeep = useCallback(
    (frequency: number, duration: number, volume: number = 0.3): Promise<void> => {
      return new Promise((resolve) => {
        try {
          const audioContext = getAudioContext();

          const oscillator = audioContext.createOscillator();
          const gainNode = audioContext.createGain();

          oscillator.connect(gainNode);
          gainNode.connect(audioContext.destination);

          oscillator.frequency.value = frequency;
          oscillator.type = 'sine';

          // 부드러운 시작/종료
          gainNode.gain.setValueAtTime(0, audioContext.currentTime);
          gainNode.gain.linearRampToValueAtTime(volume, audioContext.currentTime + 0.01);
          gainNode.gain.linearRampToValueAtTime(0, audioContext.currentTime + duration);

          oscillator.start(audioContext.currentTime);
          oscillator.stop(audioContext.currentTime + duration);

          setTimeout(resolve, duration * 1000);
        } catch (e) {
          console.warn('Audio playback failed:', e);
          resolve();
        }
      });
    },
    [getAudioContext]
  );

  // 위험 레벨에 따른 알림음 재생
  const playAlert = useCallback(
    async (riskLevel: RiskLevel) => {
      // 이미 재생 중이면 무시
      if (isPlayingRef.current) return;
      isPlayingRef.current = true;

      try {
        switch (riskLevel) {
          case 'low':
            // 단일 낮은 비프음
            await playBeep(440, 0.15, 0.2);
            break;

          case 'medium':
            // 2회 중간 비프음
            await playBeep(660, 0.15, 0.3);
            await new Promise((r) => setTimeout(r, 100));
            await playBeep(660, 0.15, 0.3);
            break;

          case 'high':
            // 3회 높은 비프음
            for (let i = 0; i < 3; i++) {
              await playBeep(880, 0.12, 0.4);
              if (i < 2) await new Promise((r) => setTimeout(r, 80));
            }
            break;

          case 'critical':
            // 연속 경고음 (상승하는 톤)
            for (let i = 0; i < 4; i++) {
              await playBeep(800 + i * 100, 0.1, 0.5);
              await new Promise((r) => setTimeout(r, 50));
            }
            await playBeep(1200, 0.2, 0.5);
            break;
        }
      } finally {
        isPlayingRef.current = false;
      }
    },
    [playBeep]
  );

  // 간단한 클릭음 (UI 피드백용)
  const playClick = useCallback(async () => {
    await playBeep(1000, 0.05, 0.1);
  }, [playBeep]);

  // 성공음
  const playSuccess = useCallback(async () => {
    await playBeep(523, 0.1, 0.2); // C5
    await new Promise((r) => setTimeout(r, 50));
    await playBeep(659, 0.1, 0.2); // E5
    await new Promise((r) => setTimeout(r, 50));
    await playBeep(784, 0.15, 0.2); // G5
  }, [playBeep]);

  return {
    playAlert,
    playClick,
    playSuccess,
    playBeep,
  };
}

export default useAlertSound;
