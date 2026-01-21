"""
ATI Axia80 센서 시뮬레이션 데이터 생성 스크립트
버전: v2.0 (데모 퍼포먼스 중심)

생성 데이터:
- 7일치 센서 데이터 (604,800 레코드)
- 센서 측정값 + 작업 컨텍스트 + 데이터 품질
- 3가지 이상 시나리오 포함

사용법:
    python scripts/generate_sensor_data.py
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import json
import yaml
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
import random

# 시드 고정 (재현성)
np.random.seed(42)
random.seed(42)

# 경로 설정
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "sensor"
CONFIG_PATH = DATA_DIR / "metadata" / "sensor_config.yaml"


@dataclass
class AnomalyEvent:
    """이상 이벤트 기록"""
    event_id: str
    scenario: str  # A, B, C
    event_type: str  # collision, overload, vibration, tool_change, etc.
    start_time: datetime
    end_time: datetime
    duration_s: float
    error_code: Optional[str]
    description: str
    context: Dict


class SensorDataGenerator:
    """센서 데이터 생성기"""

    def __init__(self, config_path: Path = CONFIG_PATH):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.start_date = datetime.strptime(
            self.config['generation']['start_date'], "%Y-%m-%d"
        )
        self.days = self.config['generation']['days']
        self.total_seconds = self.days * 24 * 60 * 60

        # 이상 이벤트 기록
        self.anomaly_events: List[AnomalyEvent] = []
        self.event_counter = 0

        # 현재 상태
        self.current_tool = "GRIPPER-01"
        self.current_tool_weight = 1.5
        self.baseline_offset = 0  # 캘리브레이션/툴교체로 인한 오프셋

    def generate(self) -> pd.DataFrame:
        """전체 데이터 생성"""
        print(f"=== ATI Axia80 센서 데이터 생성 시작 ===")
        print(f"기간: {self.start_date} ~ {self.start_date + timedelta(days=self.days)}")
        print(f"총 레코드: {self.total_seconds:,}")

        # 1. 시간축 생성
        print("\n[1/6] 시간축 생성...")
        timestamps = pd.date_range(
            start=self.start_date,
            periods=self.total_seconds,
            freq='1s'
        )

        # 2. 기본 데이터프레임 생성
        print("[2/6] 기본 구조 생성...")
        df = pd.DataFrame({'timestamp': timestamps})

        # 3. 작업 컨텍스트 생성
        print("[3/6] 작업 컨텍스트 생성...")
        df = self._generate_context(df)

        # 4. 센서 측정값 생성 (컨텍스트 기반)
        print("[4/6] 센서 측정값 생성...")
        df = self._generate_sensor_values(df)

        # 5. 이상 패턴 주입
        print("[5/6] 이상 패턴 주입...")
        df = self._inject_anomalies(df)

        # 6. 데이터 품질 이슈 추가
        print("[6/6] 데이터 품질 이슈 추가...")
        df = self._add_quality_issues(df)

        print(f"\n=== 생성 완료 ===")
        print(f"총 레코드: {len(df):,}")
        print(f"이상 이벤트: {len(self.anomaly_events)}개")

        return df

    def _generate_context(self, df: pd.DataFrame) -> pd.DataFrame:
        """작업 컨텍스트 생성"""
        n = len(df)

        # 초기화
        df['task_mode'] = 'idle'
        df['work_order_id'] = ''
        df['product_id'] = ''
        df['shift'] = ''
        df['operator_id'] = ''
        df['gripper_state'] = 'open'
        df['payload_kg'] = 0.0
        df['payload_class'] = 'none'
        df['tool_id'] = self.current_tool
        df['status'] = 'normal'
        df['event_id'] = ''
        df['error_code'] = ''

        # Shift 할당
        df['shift'] = df['timestamp'].apply(self._get_shift)

        # Operator 할당 (shift별)
        operators = self.config['context']['operators']
        df['operator_id'] = df['shift'].map({
            'A': operators[0],
            'B': operators[1],
            'C': operators[2]
        })

        # 작업 사이클 생성
        work_start = 6  # 06:00
        work_end = 22   # 22:00

        products = self.config['context']['products']
        cycle_config = self.config['work_cycle']['cycle_duration']

        idx = 0
        work_order_num = 0
        current_day = -1

        while idx < n:
            ts = df.loc[idx, 'timestamp']
            hour = ts.hour
            day = ts.day

            # 새로운 날이면 work_order 리셋
            if day != current_day:
                current_day = day
                work_order_num = 0

            # 작업 시간 외 = idle
            if hour < work_start or hour >= work_end:
                # idle 상태 유지
                idx += 1
                continue

            # 작업 사이클 실행
            product = random.choice(products)
            work_order_num += 1
            work_order_id = f"WO-{ts.strftime('%Y%m%d')}-{work_order_num:03d}"

            # 사이클: idle -> approach -> pick -> place -> retract -> idle
            cycle_sequence = [
                ('idle', cycle_config['idle'], 'open', 'none', 0.0),
                ('approach', cycle_config['approach'], 'open', 'none', 0.0),
                ('pick', cycle_config['pick'], 'holding', product['class'], product['payload_kg']),
                ('place', cycle_config['place'], 'holding', product['class'], product['payload_kg']),
                ('retract', cycle_config['retract'], 'open', 'none', 0.0),
            ]

            for mode, duration, gripper, payload_class, payload_kg in cycle_sequence:
                for _ in range(duration):
                    if idx >= n:
                        break
                    df.loc[idx, 'task_mode'] = mode
                    df.loc[idx, 'work_order_id'] = work_order_id
                    df.loc[idx, 'product_id'] = product['id']
                    df.loc[idx, 'gripper_state'] = gripper
                    df.loc[idx, 'payload_class'] = payload_class
                    df.loc[idx, 'payload_kg'] = payload_kg
                    idx += 1

            # 사이클 간 대기
            inter_cycle = random.randint(
                self.config['work_cycle']['inter_cycle_idle']['min'],
                self.config['work_cycle']['inter_cycle_idle']['max']
            )
            idx += inter_cycle

        return df

    def _get_shift(self, ts: pd.Timestamp) -> str:
        """시간대별 Shift 반환"""
        hour = ts.hour
        if 6 <= hour < 14:
            return 'A'
        elif 14 <= hour < 22:
            return 'B'
        else:
            return 'C'

    def _generate_sensor_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """센서 측정값 생성 (컨텍스트 기반)"""
        n = len(df)
        params = self.config['normal_params']

        # 기본값 (idle)
        df['Fx'] = np.random.normal(params['idle']['Fx']['mean'], params['idle']['Fx']['std'], n)
        df['Fy'] = np.random.normal(params['idle']['Fy']['mean'], params['idle']['Fy']['std'], n)
        df['Fz'] = np.random.normal(params['idle']['Fz']['mean'], params['idle']['Fz']['std'], n)
        df['Tx'] = np.random.normal(params['idle']['Tx']['mean'], params['idle']['Tx']['std'], n)
        df['Ty'] = np.random.normal(params['idle']['Ty']['mean'], params['idle']['Ty']['std'], n)
        df['Tz'] = np.random.normal(params['idle']['Tz']['mean'], params['idle']['Tz']['std'], n)

        # 작업 중 (pick, place)일 때 값 조정
        work_mask = df['task_mode'].isin(['pick', 'place'])
        work_indices = df[work_mask].index

        for idx in work_indices:
            payload_class = df.loc[idx, 'payload_class']
            if payload_class in ['light', 'normal', 'heavy']:
                fz_params = params['work'][payload_class]['Fz']
                df.loc[idx, 'Fz'] = np.random.normal(fz_params['mean'], fz_params['std'])

            # 수평축 노이즈 증가
            df.loc[idx, 'Fx'] = np.random.normal(params['work']['Fx']['mean'], params['work']['Fx']['std'])
            df.loc[idx, 'Fy'] = np.random.normal(params['work']['Fy']['mean'], params['work']['Fy']['std'])
            df.loc[idx, 'Tx'] = np.random.normal(params['work']['Tx']['mean'], params['work']['Tx']['std'])
            df.loc[idx, 'Ty'] = np.random.normal(params['work']['Ty']['mean'], params['work']['Ty']['std'])
            df.loc[idx, 'Tz'] = np.random.normal(params['work']['Tz']['mean'], params['work']['Tz']['std'])

        return df

    def _inject_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """이상 패턴 주입"""
        # 시나리오 A: 전조 → 충돌 → 정지 (2회)
        df = self._inject_scenario_a(df)

        # 시나리오 B: 반복 재발 (1세트, 4일 연속)
        df = self._inject_scenario_b(df)

        # 시나리오 C: 오탐/유사 증상 (4회)
        df = self._inject_scenario_c(df)

        return df

    def _inject_scenario_a(self, df: pd.DataFrame) -> pd.DataFrame:
        """시나리오 A: 전조 → 충돌 → 정지"""
        config = self.config['anomaly_patterns']['scenario_a']
        count = config['count_per_week']

        # 작업 시간 중 랜덤 선택 (Day 2, Day 5)
        target_days = [2, 5]

        for day_offset in target_days[:count]:
            # 해당 날의 작업 시간 중 랜덤 시점
            base_time = self.start_date + timedelta(days=day_offset, hours=random.randint(8, 18))
            collision_idx = df[df['timestamp'] >= base_time].index[0]

            # 1. 전조 (20분 전부터 진동 증가)
            precursor_start = collision_idx - 20 * 60
            precursor_end = collision_idx
            vibration_increase = config['precursor']['vibration_increase_pct'] / 100

            for idx in range(max(0, precursor_start), precursor_end):
                # Tx, Ty 노이즈 점진적 증가
                progress = (idx - precursor_start) / (precursor_end - precursor_start)
                noise_mult = 1 + vibration_increase * progress
                df.loc[idx, 'Tx'] *= noise_mult
                df.loc[idx, 'Ty'] *= noise_mult
                df.loc[idx, 'status'] = 'warning' if progress > 0.7 else 'normal'

            # 2. 충돌 (순간 Fz 급증)
            collision_duration = random.randint(
                config['collision']['duration_ms']['min'] // 1000 + 1,
                config['collision']['duration_ms']['max'] // 1000 + 1
            )
            fz_peak = random.uniform(
                config['collision']['Fz_peak']['min'],
                config['collision']['Fz_peak']['max']
            )

            event_id = self._get_event_id()
            collision_end = min(collision_idx + collision_duration, len(df) - 1)

            for idx in range(collision_idx, collision_end):
                df.loc[idx, 'Fz'] = -fz_peak
                df.loc[idx, 'status'] = 'anomaly'
                df.loc[idx, 'event_id'] = event_id

            # 3. Safety Stop
            df.loc[collision_end, 'task_mode'] = 'stop'
            df.loc[collision_end, 'error_code'] = config['error_code']

            # 정지 후 10초간 idle
            for idx in range(collision_end + 1, min(collision_end + 11, len(df))):
                df.loc[idx, 'task_mode'] = 'idle'
                df.loc[idx, 'gripper_state'] = 'open'
                df.loc[idx, 'payload_class'] = 'none'
                df.loc[idx, 'payload_kg'] = 0.0

            # 이벤트 기록
            self.anomaly_events.append(AnomalyEvent(
                event_id=event_id,
                scenario='A',
                event_type='collision',
                start_time=df.loc[precursor_start, 'timestamp'].to_pydatetime(),
                end_time=df.loc[collision_end, 'timestamp'].to_pydatetime(),
                duration_s=(collision_end - precursor_start),
                error_code=config['error_code'],
                description="전조(진동 증가 20분) → 충돌(Fz 급증) → Safety Stop",
                context={
                    'precursor_duration_min': 20,
                    'fz_peak_N': fz_peak,
                    'shift': df.loc[collision_idx, 'shift'],
                    'product': df.loc[collision_idx, 'product_id']
                }
            ))

        return df

    def _inject_scenario_b(self, df: pd.DataFrame) -> pd.DataFrame:
        """시나리오 B: 반복 재발 (특정 시간대, 특정 제품)"""
        config = self.config['anomaly_patterns']['scenario_b']

        # Day 1, 2, 3, 4 연속 14:00~15:00 사이
        target_days = [1, 2, 3, 4]
        target_product = config['target_product']

        for i, day_offset in enumerate(target_days):
            # 14:00 ~ 15:00 사이 랜덤
            hour = 14
            minute = random.randint(10, 50)
            base_time = self.start_date + timedelta(days=day_offset, hours=hour, minutes=minute)

            # 해당 시점 찾기
            target_idx = df[df['timestamp'] >= base_time].index[0]

            # 과부하 주입
            overload_duration = random.randint(
                config['overload']['duration_s']['min'],
                config['overload']['duration_s']['max']
            )
            fz_value = random.uniform(
                config['overload']['Fz_value']['min'],
                config['overload']['Fz_value']['max']
            )

            event_id = self._get_event_id()
            overload_end = min(target_idx + overload_duration, len(df) - 1)

            for idx in range(target_idx, overload_end):
                df.loc[idx, 'Fz'] = -fz_value
                df.loc[idx, 'product_id'] = target_product
                df.loc[idx, 'payload_class'] = 'heavy'
                df.loc[idx, 'status'] = 'warning'
                df.loc[idx, 'event_id'] = event_id

            # Day 4에만 Safety Stop
            if i == 3:
                df.loc[overload_end, 'task_mode'] = 'stop'
                df.loc[overload_end, 'error_code'] = config['final_error_code']
                df.loc[overload_end, 'status'] = 'anomaly'

            # 이벤트 기록
            self.anomaly_events.append(AnomalyEvent(
                event_id=event_id,
                scenario='B',
                event_type='overload',
                start_time=df.loc[target_idx, 'timestamp'].to_pydatetime(),
                end_time=df.loc[overload_end, 'timestamp'].to_pydatetime(),
                duration_s=overload_duration,
                error_code=config['final_error_code'] if i == 3 else None,
                description=f"반복 재발 ({i+1}/4일차) - 14시대 PART-C 과부하",
                context={
                    'fz_value_N': fz_value,
                    'shift': 'B',
                    'product': target_product,
                    'recurrence_day': i + 1
                }
            ))

        return df

    def _inject_scenario_c(self, df: pd.DataFrame) -> pd.DataFrame:
        """시나리오 C: 오탐/유사 증상"""
        config = self.config['anomaly_patterns']['scenario_c']

        # 타입별 이벤트 생성
        events = [
            ('tool_change', 1),      # 툴 교체 2회
            ('tool_change', 3),
            ('recalibration', 2),    # 캘리브레이션 1회
            ('no_doc_match', 6),     # 문서 매칭 없는 드리프트 1회
        ]

        for event_type, day_offset in events:
            base_time = self.start_date + timedelta(days=day_offset, hours=random.randint(9, 17))
            target_idx = df[df['timestamp'] >= base_time].index[0]

            event_id = self._get_event_id()

            if event_type == 'tool_change':
                # 툴 교체: baseline 이동
                new_tool = "GRIPPER-02" if self.current_tool == "GRIPPER-01" else "GRIPPER-01"
                weight_diff = 0.7 if new_tool == "GRIPPER-02" else -0.7

                # 교체 시점부터 Fz baseline 이동
                for idx in range(target_idx, len(df)):
                    df.loc[idx, 'tool_id'] = new_tool
                    df.loc[idx, 'Fz'] += weight_diff * -10  # 무게 차이만큼 Fz 이동

                self.current_tool = new_tool

                self.anomaly_events.append(AnomalyEvent(
                    event_id=event_id,
                    scenario='C',
                    event_type='tool_change',
                    start_time=df.loc[target_idx, 'timestamp'].to_pydatetime(),
                    end_time=df.loc[target_idx, 'timestamp'].to_pydatetime(),
                    duration_s=0,
                    error_code=None,
                    description=f"툴 교체 ({self.current_tool}) - 정상 운영, Fz baseline 이동",
                    context={
                        'old_tool': "GRIPPER-01" if new_tool == "GRIPPER-02" else "GRIPPER-02",
                        'new_tool': new_tool,
                        'fz_shift_N': weight_diff * -10
                    }
                ))

            elif event_type == 'recalibration':
                # 캘리브레이션: 전체 값 점프
                offset = random.uniform(-5, 5)

                for idx in range(target_idx, len(df)):
                    df.loc[idx, 'Fz'] += offset

                self.anomaly_events.append(AnomalyEvent(
                    event_id=event_id,
                    scenario='C',
                    event_type='recalibration',
                    start_time=df.loc[target_idx, 'timestamp'].to_pydatetime(),
                    end_time=df.loc[target_idx, 'timestamp'].to_pydatetime(),
                    duration_s=0,
                    error_code=None,
                    description="센서 캘리브레이션 - 정상 운영, 값 점프",
                    context={
                        'offset_N': offset
                    }
                ))

            elif event_type == 'no_doc_match':
                # 드리프트: 문서에 조치 없음
                drift_duration = 4 * 60 * 60  # 4시간
                drift_end = min(target_idx + drift_duration, len(df) - 1)

                for idx in range(target_idx, drift_end):
                    progress = (idx - target_idx) / drift_duration
                    df.loc[idx, 'Fz'] += progress * 15  # 점진적 drift
                    df.loc[idx, 'status'] = 'warning' if progress > 0.5 else 'normal'
                    df.loc[idx, 'event_id'] = event_id

                self.anomaly_events.append(AnomalyEvent(
                    event_id=event_id,
                    scenario='C',
                    event_type='drift_no_doc',
                    start_time=df.loc[target_idx, 'timestamp'].to_pydatetime(),
                    end_time=df.loc[drift_end, 'timestamp'].to_pydatetime(),
                    duration_s=drift_duration,
                    error_code=None,
                    description="드리프트 패턴 - 문서에 해당 조치 없음 (ABSTAIN 예상)",
                    context={
                        'drift_amount_N': 15,
                        'duration_hours': 4
                    }
                ))

        return df

    def _add_quality_issues(self, df: pd.DataFrame) -> pd.DataFrame:
        """데이터 품질 이슈 추가"""
        n = len(df)
        config = self.config['data_quality']

        # 기본값
        df['clock_skew_ms'] = np.random.randint(
            config['clock_skew_ms']['min'],
            config['clock_skew_ms']['max'] + 1,
            n
        )
        df['data_quality'] = 'good'

        # 지연 데이터 (1%)
        delayed_count = int(n * config['delayed_ratio'])
        delayed_indices = np.random.choice(n, delayed_count, replace=False)
        df.loc[delayed_indices, 'data_quality'] = 'delayed'
        df.loc[delayed_indices, 'clock_skew_ms'] = np.random.randint(30, 100, delayed_count)

        # 결측 구간 (0.5%, 10-15초 단위)
        missing_count = int(n * config['missing_ratio'])
        drop_starts = np.random.choice(n - 15, missing_count // 10, replace=False)

        for start in drop_starts:
            duration = random.randint(
                config['drop_duration_s']['min'],
                config['drop_duration_s']['max']
            )
            end = min(start + duration, n)
            df.loc[start:end, 'data_quality'] = 'missing'
            # 결측 구간은 NaN 또는 이전 값 보간
            df.loc[start:end, ['Fx', 'Fy', 'Fz', 'Tx', 'Ty', 'Tz']] = np.nan

        # 보간 데이터 (결측 후 선형 보간)
        df[['Fx', 'Fy', 'Fz', 'Tx', 'Ty', 'Tz']] = df[['Fx', 'Fy', 'Fz', 'Tx', 'Ty', 'Tz']].interpolate()

        # 보간된 구간 표시
        interpolated_mask = df['data_quality'] == 'missing'
        df.loc[interpolated_mask, 'data_quality'] = 'interpolated'

        return df

    def _get_event_id(self) -> str:
        """이벤트 ID 생성"""
        self.event_counter += 1
        return f"EVT-{self.event_counter:03d}"

    def save(self, df: pd.DataFrame):
        """데이터 저장"""
        # Parquet 저장
        parquet_path = DATA_DIR / "raw" / "axia80_week_01.parquet"
        df.to_parquet(parquet_path, index=False, compression='snappy')
        print(f"\n데이터 저장: {parquet_path}")
        print(f"파일 크기: {parquet_path.stat().st_size / 1024 / 1024:.2f} MB")

        # 이상 이벤트 JSON 저장
        events_path = DATA_DIR / "processed" / "anomaly_events.json"
        events_data = [asdict(e) for e in self.anomaly_events]
        # datetime, numpy 타입 직렬화
        for e in events_data:
            e['start_time'] = e['start_time'].isoformat()
            e['end_time'] = e['end_time'].isoformat()
            # numpy int/float -> python int/float
            e['duration_s'] = int(e['duration_s']) if isinstance(e['duration_s'], (np.integer, np.floating)) else e['duration_s']
            if e['context']:
                for k, v in e['context'].items():
                    if isinstance(v, (np.integer,)):
                        e['context'][k] = int(v)
                    elif isinstance(v, (np.floating,)):
                        e['context'][k] = float(v)

        with open(events_path, 'w', encoding='utf-8') as f:
            json.dump(events_data, f, indent=2, ensure_ascii=False)
        print(f"이벤트 저장: {events_path}")

    def print_summary(self, df: pd.DataFrame):
        """생성 결과 요약"""
        print("\n" + "=" * 60)
        print("생성 결과 요약")
        print("=" * 60)

        print(f"\n[기본 정보]")
        print(f"  기간: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
        print(f"  총 레코드: {len(df):,}")

        print(f"\n[컬럼 수]")
        print(f"  센서: 6개 (Fx, Fy, Fz, Tx, Ty, Tz)")
        print(f"  컨텍스트: 7개")
        print(f"  품질: 2개")
        print(f"  상태: 3개")
        print(f"  총: {len(df.columns)}개")

        print(f"\n[Task Mode 분포]")
        for mode, count in df['task_mode'].value_counts().items():
            print(f"  {mode}: {count:,} ({count/len(df)*100:.1f}%)")

        print(f"\n[Status 분포]")
        for status, count in df['status'].value_counts().items():
            print(f"  {status}: {count:,} ({count/len(df)*100:.2f}%)")

        print(f"\n[데이터 품질 분포]")
        for quality, count in df['data_quality'].value_counts().items():
            print(f"  {quality}: {count:,} ({count/len(df)*100:.2f}%)")

        print(f"\n[이상 이벤트]")
        for scenario in ['A', 'B', 'C']:
            events = [e for e in self.anomaly_events if e.scenario == scenario]
            print(f"  시나리오 {scenario}: {len(events)}건")
            for e in events:
                print(f"    - {e.event_id}: {e.event_type} ({e.description[:40]}...)")

        print(f"\n[센서값 통계]")
        for col in ['Fx', 'Fy', 'Fz', 'Tx', 'Ty', 'Tz']:
            print(f"  {col}: mean={df[col].mean():.2f}, std={df[col].std():.2f}, "
                  f"min={df[col].min():.2f}, max={df[col].max():.2f}")


def main():
    generator = SensorDataGenerator()
    df = generator.generate()
    generator.save(df)
    generator.print_summary(df)

    print("\n" + "=" * 60)
    print("데이터 생성 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
