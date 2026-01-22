'use client';

import { useState, useEffect } from 'react';
import { RiskAlertBar } from './RiskAlertBar';
import { ObjectCard } from './ObjectCard';
import { RealtimeChart } from './RealtimeChart';
import { EventList, EventItem } from './EventList';
import { useUIStore } from '@/stores/uiStore';
import type { EntityInfo, RiskAlert, SensorReading } from '@/types/api';

// Mock data for demonstration
const mockEntities: EntityInfo[] = [
  {
    id: 'ur5e',
    name: 'UR5e',
    type: 'ROBOT',
    state: 'normal',
  },
  {
    id: 'axia80',
    name: 'Axia80',
    type: 'SENSOR',
    state: 'warning',
  },
  {
    id: 'fz',
    name: 'Fz',
    type: 'MEASUREMENT_AXIS',
    state: 'warning',
    currentValue: -180,
    unit: 'N',
    normalRange: [-60, 0],
  },
  {
    id: 'fx',
    name: 'Fx',
    type: 'MEASUREMENT_AXIS',
    state: 'normal',
    currentValue: -5,
    unit: 'N',
    normalRange: [-10, 10],
  },
  {
    id: 'fy',
    name: 'Fy',
    type: 'MEASUREMENT_AXIS',
    state: 'normal',
    currentValue: 3,
    unit: 'N',
    normalRange: [-10, 10],
  },
];

const mockAlerts: RiskAlert[] = [
  {
    id: '1',
    severity: 'warning',
    title: 'Fz 경고 상태',
    timestamp: new Date(Date.now() - 10 * 60000).toISOString(),
    entityId: 'fz',
    count: 2,
  },
  {
    id: '2',
    severity: 'info',
    title: '정상 동작',
    timestamp: new Date().toISOString(),
    count: 42,
  },
];

const mockEvents: EventItem[] = [
  {
    id: '1',
    timestamp: new Date(Date.now() - 3 * 60000).toISOString(),
    type: 'warning',
    message: 'Fz 경고 상태 진입 (-180N)',
    entityId: 'fz',
  },
  {
    id: '2',
    timestamp: new Date(Date.now() - 8 * 60000).toISOString(),
    type: 'info',
    message: '정상 복귀',
  },
  {
    id: '3',
    timestamp: new Date(Date.now() - 15 * 60000).toISOString(),
    type: 'critical',
    message: '충돌 감지 (PAT_COLLISION)',
    entityId: 'fz',
  },
];

// Generate mock sensor data
function generateMockSensorData(count: number): SensorReading[] {
  const data: SensorReading[] = [];
  const now = Date.now();

  for (let i = count - 1; i >= 0; i--) {
    const timestamp = new Date(now - i * 60000).toISOString();
    data.push({
      timestamp,
      Fx: -5 + Math.random() * 10 - 5,
      Fy: 3 + Math.random() * 6 - 3,
      Fz: -50 - Math.random() * 150 - (i < 5 ? 100 : 0), // Spike in recent data
      Tx: 0.1 + Math.random() * 0.4 - 0.2,
      Ty: -0.1 + Math.random() * 0.4 - 0.2,
      Tz: 0.05 + Math.random() * 0.3 - 0.15,
    });
  }

  return data;
}

export function LiveView() {
  const { selectedEntity, setSelectedEntity, setGraphCenterNode, setCurrentView } = useUIStore();
  const [sensorData, setSensorData] = useState<SensorReading[]>([]);

  // Initialize mock data
  useEffect(() => {
    setSensorData(generateMockSensorData(30));

    // Simulate real-time updates
    const interval = setInterval(() => {
      setSensorData((prev) => {
        const newReading: SensorReading = {
          timestamp: new Date().toISOString(),
          Fx: -5 + Math.random() * 10 - 5,
          Fy: 3 + Math.random() * 6 - 3,
          Fz: -50 - Math.random() * 150,
          Tx: 0.1 + Math.random() * 0.4 - 0.2,
          Ty: -0.1 + Math.random() * 0.4 - 0.2,
          Tz: 0.05 + Math.random() * 0.3 - 0.15,
        };
        return [...prev.slice(1), newReading];
      });
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const handleEntityClick = (entity: EntityInfo) => {
    setSelectedEntity(entity);
  };

  const handleAlertClick = (alert: RiskAlert) => {
    if (alert.entityId) {
      const entity = mockEntities.find((e) => e.id === alert.entityId);
      if (entity) {
        setSelectedEntity(entity);
      }
    }
  };

  const handleEventClick = (event: EventItem) => {
    if (event.entityId) {
      setGraphCenterNode(event.entityId);
      setCurrentView('graph');
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Alert Bar */}
      <RiskAlertBar alerts={mockAlerts} onAlertClick={handleAlertClick} />

      {/* Main Content */}
      <div className="flex-1 p-4 overflow-auto">
        {/* Entity Cards */}
        <div className="mb-6">
          <h2 className="text-sm font-medium text-slate-400 mb-3">모니터링 객체</h2>
          <div className="flex flex-wrap gap-3">
            {mockEntities.map((entity) => (
              <ObjectCard
                key={entity.id}
                entity={entity}
                isSelected={selectedEntity?.id === entity.id}
                onClick={() => handleEntityClick(entity)}
              />
            ))}
          </div>
        </div>

        {/* Chart */}
        <div className="mb-6">
          <RealtimeChart
            data={sensorData}
            axis="Fz"
            title="Fz (힘 Z축) 실시간 모니터링"
            thresholds={{
              warning: -60,
              critical: -200,
            }}
          />
        </div>

        {/* Events */}
        <EventList
          events={mockEvents}
          onEventClick={handleEventClick}
          maxHeight="200px"
        />
      </div>
    </div>
  );
}
