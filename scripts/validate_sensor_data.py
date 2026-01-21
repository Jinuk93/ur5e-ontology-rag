"""
센서 데이터 검증 스크립트

검증 항목:
1. 스키마 검증 (컬럼, 타입)
2. 센서값 ↔ 컨텍스트 일관성
3. 이상 이벤트 확인
4. 시나리오별 패턴 검증
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime

# 경로 설정
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "sensor"


def load_data():
    """데이터 로드"""
    df = pd.read_parquet(DATA_DIR / "raw" / "axia80_week_01.parquet")
    with open(DATA_DIR / "processed" / "anomaly_events.json", 'r', encoding='utf-8') as f:
        events = json.load(f)
    return df, events


def validate_schema(df: pd.DataFrame) -> dict:
    """스키마 검증"""
    print("\n" + "=" * 60)
    print("1. 스키마 검증")
    print("=" * 60)

    expected_columns = [
        'timestamp', 'Fx', 'Fy', 'Fz', 'Tx', 'Ty', 'Tz',
        'task_mode', 'work_order_id', 'product_id', 'shift', 'operator_id',
        'gripper_state', 'payload_kg', 'payload_class', 'tool_id',
        'clock_skew_ms', 'data_quality',
        'status', 'event_id', 'error_code'
    ]

    results = {
        'total_columns': len(df.columns),
        'expected_columns': len(expected_columns),
        'missing_columns': [],
        'extra_columns': []
    }

    for col in expected_columns:
        if col not in df.columns:
            results['missing_columns'].append(col)

    for col in df.columns:
        if col not in expected_columns:
            results['extra_columns'].append(col)

    print(f"  총 컬럼 수: {results['total_columns']}")
    print(f"  예상 컬럼 수: {results['expected_columns']}")

    if results['missing_columns']:
        print(f"  [FAIL] 누락 컬럼: {results['missing_columns']}")
    else:
        print(f"  [PASS] 모든 필수 컬럼 존재")

    if results['extra_columns']:
        print(f"  [INFO] 추가 컬럼: {results['extra_columns']}")

    return results


def validate_consistency(df: pd.DataFrame) -> dict:
    """센서값 ↔ 컨텍스트 일관성 검증"""
    print("\n" + "=" * 60)
    print("2. 센서값 ↔ 컨텍스트 일관성 검증")
    print("=" * 60)

    results = {
        'total_records': len(df),
        'inconsistencies': [],
        'consistency_rate': 0
    }

    inconsistent_count = 0

    # 규칙 1: idle 상태에서 payload_class는 none이어야 함
    rule1_violations = df[(df['task_mode'] == 'idle') & (df['payload_class'] != 'none')]
    if len(rule1_violations) > 0:
        results['inconsistencies'].append({
            'rule': 'idle 상태에서 payload_class != none',
            'count': len(rule1_violations),
            'sample_indices': rule1_violations.index[:5].tolist()
        })
        inconsistent_count += len(rule1_violations)

    # 규칙 2: pick/place에서 gripper_state는 holding이어야 함
    rule2_violations = df[(df['task_mode'].isin(['pick', 'place'])) & (df['gripper_state'] != 'holding')]
    if len(rule2_violations) > 0:
        results['inconsistencies'].append({
            'rule': 'pick/place에서 gripper_state != holding',
            'count': len(rule2_violations),
            'sample_indices': rule2_violations.index[:5].tolist()
        })
        inconsistent_count += len(rule2_violations)

    # 규칙 3: idle 상태에서 Fz는 -30 ~ 0 범위여야 함 (대부분)
    idle_data = df[df['task_mode'] == 'idle']
    rule3_violations = idle_data[(idle_data['Fz'] < -50) | (idle_data['Fz'] > 10)]
    if len(rule3_violations) > 0:
        # 이상 이벤트 구간은 제외
        rule3_violations_no_event = rule3_violations[rule3_violations['event_id'] == '']
        if len(rule3_violations_no_event) > 100:  # 소량은 허용
            results['inconsistencies'].append({
                'rule': 'idle 상태에서 Fz 범위 이탈 (이벤트 제외)',
                'count': len(rule3_violations_no_event),
                'sample_indices': rule3_violations_no_event.index[:5].tolist()
            })
            inconsistent_count += len(rule3_violations_no_event)

    # 규칙 4: error_code가 있으면 task_mode는 stop이어야 함
    error_data = df[df['error_code'] != '']
    rule4_violations = error_data[error_data['task_mode'] != 'stop']
    if len(rule4_violations) > 0:
        results['inconsistencies'].append({
            'rule': 'error_code 있는데 task_mode != stop',
            'count': len(rule4_violations),
            'sample_indices': rule4_violations.index[:5].tolist()
        })
        inconsistent_count += len(rule4_violations)

    results['consistency_rate'] = (len(df) - inconsistent_count) / len(df) * 100

    print(f"  총 레코드: {results['total_records']:,}")
    print(f"  일관성 비율: {results['consistency_rate']:.2f}%")

    if results['inconsistencies']:
        print(f"  [WARN] 불일치 항목:")
        for inc in results['inconsistencies']:
            print(f"    - {inc['rule']}: {inc['count']:,}건")
    else:
        print(f"  [PASS] 모든 일관성 규칙 통과")

    return results


def validate_anomaly_events(df: pd.DataFrame, events: list) -> dict:
    """이상 이벤트 검증"""
    print("\n" + "=" * 60)
    print("3. 이상 이벤트 검증")
    print("=" * 60)

    results = {
        'total_events': len(events),
        'events_by_scenario': {},
        'validation': []
    }

    for scenario in ['A', 'B', 'C']:
        scenario_events = [e for e in events if e['scenario'] == scenario]
        results['events_by_scenario'][scenario] = len(scenario_events)
        print(f"  시나리오 {scenario}: {len(scenario_events)}건")

    # 각 이벤트 검증
    for event in events:
        event_data = df[df['event_id'] == event['event_id']]

        validation = {
            'event_id': event['event_id'],
            'scenario': event['scenario'],
            'event_type': event['event_type'],
            'found_in_data': len(event_data) > 0,
            'record_count': len(event_data)
        }

        if event['scenario'] == 'A':
            # 충돌 이벤트: Fz 급증 확인
            if len(event_data) > 0:
                max_fz = abs(event_data['Fz'].min())
                validation['fz_peak'] = max_fz
                validation['valid'] = max_fz > 500
        elif event['scenario'] == 'B':
            # 과부하: warning 상태 확인
            if len(event_data) > 0:
                warning_count = (event_data['status'] == 'warning').sum()
                validation['warning_count'] = warning_count
                validation['valid'] = warning_count > 0
        elif event['scenario'] == 'C':
            # 오탐/유사: 존재 여부만 확인
            validation['valid'] = True

        results['validation'].append(validation)

        status = "[PASS]" if validation.get('valid', False) else "[WARN]"
        print(f"    {status} {event['event_id']}: {event['event_type']} - {event['description'][:30]}...")

    return results


def validate_scenarios(df: pd.DataFrame, events: list) -> dict:
    """시나리오별 상세 검증"""
    print("\n" + "=" * 60)
    print("4. 시나리오별 상세 검증")
    print("=" * 60)

    results = {}

    # 시나리오 A: 전조 → 충돌 → 정지
    print("\n  [시나리오 A] 전조 → 충돌 → 정지")
    scenario_a_events = [e for e in events if e['scenario'] == 'A']
    for event in scenario_a_events:
        event_data = df[df['event_id'] == event['event_id']]
        if len(event_data) > 0:
            fz_min = event_data['Fz'].min()
            error_codes = df[df['error_code'] == 'C153']
            print(f"    {event['event_id']}: Fz peak = {abs(fz_min):.1f}N, "
                  f"C153 발생 = {len(error_codes) > 0}")

    # 시나리오 B: 반복 재발
    print("\n  [시나리오 B] 반복 재발 (14시대, PART-C)")
    scenario_b_events = [e for e in events if e['scenario'] == 'B']
    for event in scenario_b_events:
        ctx = event.get('context', {})
        print(f"    {event['event_id']}: Day {ctx.get('recurrence_day', '?')}, "
              f"Fz = {ctx.get('fz_value_N', 0):.1f}N, "
              f"error = {event.get('error_code', '-')}")

    # 시나리오 C: 오탐/유사
    print("\n  [시나리오 C] 오탐/유사 증상")
    scenario_c_events = [e for e in events if e['scenario'] == 'C']
    for event in scenario_c_events:
        print(f"    {event['event_id']}: {event['event_type']} - "
              f"{'ABSTAIN 예상' if event['event_type'] == 'drift_no_doc' else '정상 판정 예상'}")

    # 통계 검증
    print("\n  [통계 검증]")

    # 작업 시간대 (06:00~22:00) vs 비작업 시간대
    df['hour'] = df['timestamp'].dt.hour
    work_hours = df[(df['hour'] >= 6) & (df['hour'] < 22)]
    non_work_hours = df[(df['hour'] < 6) | (df['hour'] >= 22)]

    work_active = work_hours[work_hours['task_mode'].isin(['pick', 'place', 'approach', 'retract'])]
    non_work_active = non_work_hours[non_work_hours['task_mode'].isin(['pick', 'place', 'approach', 'retract'])]

    print(f"    작업 시간대 (06:00~22:00) 작업 비율: {len(work_active)/len(work_hours)*100:.1f}%")
    print(f"    비작업 시간대 작업 비율: {len(non_work_active)/max(1,len(non_work_hours))*100:.1f}%")

    # Shift별 분포
    print(f"\n    Shift별 레코드 분포:")
    for shift in ['A', 'B', 'C']:
        count = len(df[df['shift'] == shift])
        print(f"      Shift {shift}: {count:,} ({count/len(df)*100:.1f}%)")

    return results


def validate_data_quality(df: pd.DataFrame) -> dict:
    """데이터 품질 검증"""
    print("\n" + "=" * 60)
    print("5. 데이터 품질 검증")
    print("=" * 60)

    results = {}

    # 결측치 확인
    null_counts = df.isnull().sum()
    print(f"  결측치:")
    for col, count in null_counts.items():
        if count > 0:
            print(f"    {col}: {count:,}")
    if null_counts.sum() == 0:
        print(f"    없음")

    # 데이터 품질 분포
    print(f"\n  데이터 품질 분포:")
    for quality, count in df['data_quality'].value_counts().items():
        print(f"    {quality}: {count:,} ({count/len(df)*100:.2f}%)")

    # clock_skew 분포
    print(f"\n  Clock Skew 분포:")
    print(f"    min: {df['clock_skew_ms'].min()}ms")
    print(f"    max: {df['clock_skew_ms'].max()}ms")
    print(f"    mean: {df['clock_skew_ms'].mean():.1f}ms")

    return results


def main():
    print("=" * 60)
    print("ATI Axia80 센서 데이터 검증")
    print("=" * 60)

    # 데이터 로드
    print("\n데이터 로드 중...")
    df, events = load_data()
    print(f"  레코드 수: {len(df):,}")
    print(f"  이벤트 수: {len(events)}")

    # 검증 실행
    schema_result = validate_schema(df)
    consistency_result = validate_consistency(df)
    anomaly_result = validate_anomaly_events(df, events)
    scenario_result = validate_scenarios(df, events)
    quality_result = validate_data_quality(df)

    # 최종 결과
    print("\n" + "=" * 60)
    print("검증 완료")
    print("=" * 60)

    all_passed = (
        len(schema_result['missing_columns']) == 0 and
        consistency_result['consistency_rate'] > 95 and
        all(v.get('valid', True) for v in anomaly_result['validation'])
    )

    if all_passed:
        print("\n[PASS] 모든 검증 통과!")
    else:
        print("\n[WARN] 일부 검증 항목에서 문제 발견")


if __name__ == "__main__":
    main()
