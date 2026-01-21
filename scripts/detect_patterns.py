"""
배치 패턴 감지 스크립트

Main-S2: 센서 데이터에서 이상 패턴을 감지하고 결과를 저장합니다.

Usage:
    python scripts/detect_patterns.py
    python scripts/detect_patterns.py --validate
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from src.sensor.pattern_detector import PatternDetector, DetectedPattern
from src.sensor.sensor_store import SensorStore


def load_expected_events() -> list[dict]:
    """S1에서 주입한 예상 이벤트 로드"""
    events_path = project_root / "data" / "sensor" / "processed" / "anomaly_events.json"

    if not events_path.exists():
        print(f"Warning: Expected events file not found: {events_path}")
        return []

    with open(events_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_detection(
    detected: list[DetectedPattern],
    expected: list[dict]
) -> dict:
    """감지 결과와 예상 이벤트를 비교하여 검증"""

    results = {
        "total_expected": len(expected),
        "total_detected": len(detected),
        "matched": [],
        "missed": [],
        "false_positives": [],
        "precision": 0.0,
        "recall": 0.0,
        "f1_score": 0.0
    }

    # 이벤트 타입 매핑 (S1 이벤트 타입 → 감지 패턴 타입)
    type_mapping = {
        "collision": "collision",
        "overload": "overload",
        "tool_change": None,  # 정상 운영, 감지하지 않아야 함
        "recalibration": None,  # 정상 운영
        "drift_no_doc": "drift"  # 드리프트는 감지되어야 함
    }

    # 예상 이벤트를 시간 기반으로 매칭
    matched_detected_ids = set()

    for exp in expected:
        exp_type = exp["event_type"]
        expected_pattern_type = type_mapping.get(exp_type)

        # 정상 운영 이벤트 (tool_change, recalibration)는 스킵
        if expected_pattern_type is None:
            continue

        exp_start = datetime.fromisoformat(exp["start_time"])
        exp_end = datetime.fromisoformat(exp["end_time"])

        # 시간 범위가 겹치는 감지 패턴 찾기
        matched = False
        for det in detected:
            if det.pattern_type != expected_pattern_type:
                continue

            # 감지 패턴의 시간 범위 계산
            det_start = pd.Timestamp(det.timestamp)
            det_end = det_start + pd.Timedelta(milliseconds=det.duration_ms)

            # 확장된 시간 범위로 매칭 (30초 여유)
            if (det_start <= exp_end + pd.Timedelta(seconds=30) and
                det_end >= exp_start - pd.Timedelta(seconds=30)):
                matched = True
                matched_detected_ids.add(id(det))
                results["matched"].append({
                    "expected_event_id": exp["event_id"],
                    "expected_type": exp_type,
                    "detected_pattern_id": det.pattern_id,
                    "detected_type": det.pattern_type,
                    "confidence": det.confidence
                })
                break

        if not matched:
            results["missed"].append({
                "event_id": exp["event_id"],
                "event_type": exp_type,
                "start_time": str(exp_start),
                "description": exp["description"]
            })

    # False Positives: 매칭되지 않은 감지 패턴
    for det in detected:
        if id(det) not in matched_detected_ids:
            results["false_positives"].append({
                "pattern_id": det.pattern_id,
                "pattern_type": det.pattern_type,
                "start_time": str(det.timestamp),
                "confidence": det.confidence
            })

    # 메트릭 계산
    # 실제 감지 대상 이벤트 수 (정상 운영 제외)
    target_events = [e for e in expected if type_mapping.get(e["event_type"]) is not None]
    tp = len(results["matched"])
    fp = len(results["false_positives"])
    fn = len(results["missed"])

    if tp + fp > 0:
        results["precision"] = tp / (tp + fp)
    if tp + fn > 0:
        results["recall"] = tp / (tp + fn)
    if results["precision"] + results["recall"] > 0:
        results["f1_score"] = 2 * (results["precision"] * results["recall"]) / (results["precision"] + results["recall"])

    return results


def print_detection_summary(patterns: list[DetectedPattern]):
    """감지 결과 요약 출력"""
    print("\n" + "=" * 60)
    print("패턴 감지 결과 요약")
    print("=" * 60)

    # 패턴 유형별 집계
    by_type = {}
    for p in patterns:
        by_type.setdefault(p.pattern_type, []).append(p)

    print(f"\n총 감지된 패턴: {len(patterns)}개")
    print("-" * 40)

    for ptype, plist in sorted(by_type.items()):
        print(f"\n[{ptype.upper()}] {len(plist)}건")
        for p in plist:
            error_str = f" (에러: {', '.join(p.related_error_codes)})" if p.related_error_codes else ""
            ts = pd.Timestamp(p.timestamp)
            print(f"  - {p.pattern_id}: {ts.strftime('%Y-%m-%d %H:%M')} "
                  f"(신뢰도: {p.confidence:.2f}){error_str}")


def print_validation_results(results: dict):
    """검증 결과 출력"""
    print("\n" + "=" * 60)
    print("검증 결과")
    print("=" * 60)

    print(f"\n정확도 메트릭:")
    print(f"  - Precision: {results['precision']:.2%}")
    print(f"  - Recall: {results['recall']:.2%}")
    print(f"  - F1 Score: {results['f1_score']:.2%}")

    print(f"\n매칭 결과:")
    print(f"  - 매칭 성공: {len(results['matched'])}건")
    print(f"  - 미감지 (missed): {len(results['missed'])}건")
    print(f"  - 오탐 (false positive): {len(results['false_positives'])}건")

    if results["matched"]:
        print("\n[매칭된 이벤트]")
        for m in results["matched"]:
            print(f"  - {m['expected_event_id']} ({m['expected_type']}) "
                  f"→ {m['detected_pattern_id']} (신뢰도: {m['confidence']:.2f})")

    if results["missed"]:
        print("\n[미감지 이벤트]")
        for m in results["missed"]:
            print(f"  - {m['event_id']} ({m['event_type']}): {m['description']}")

    if results["false_positives"]:
        print("\n[오탐 패턴] (정상 운영 패턴일 수 있음)")
        for fp in results["false_positives"][:10]:  # 최대 10개만 출력
            print(f"  - {fp['pattern_id']} ({fp['pattern_type']}): {fp['start_time']}")
        if len(results["false_positives"]) > 10:
            print(f"  ... 외 {len(results['false_positives']) - 10}건")


def main():
    parser = argparse.ArgumentParser(description="센서 데이터 패턴 감지")
    parser.add_argument("--validate", action="store_true",
                       help="S1 예상 이벤트와 비교 검증")
    parser.add_argument("--output", type=str, default=None,
                       help="결과 저장 경로 (기본: data/sensor/processed/detected_patterns.json)")
    args = parser.parse_args()

    print("=" * 60)
    print("Main-S2: 배치 패턴 감지")
    print("=" * 60)

    # 1. 센서 데이터 로드
    print("\n[1/4] 센서 데이터 로드...")
    store = SensorStore()

    try:
        store.load_data()
    except Exception as e:
        print(f"Error: 센서 데이터 로드 실패 - {e}")
        sys.exit(1)

    df = store.get_data()
    print(f"  - 로드된 레코드: {len(df):,}개")
    print(f"  - 기간: {df['timestamp'].min()} ~ {df['timestamp'].max()}")

    # 2. 패턴 감지 실행
    print("\n[2/4] 패턴 감지 실행...")
    detector = PatternDetector()

    patterns = detector.detect(df)
    print(f"  - 감지된 패턴: {len(patterns)}개")

    # 3. 결과 저장
    print("\n[3/4] 결과 저장...")

    output_path = args.output
    if output_path is None:
        output_path = project_root / "data" / "sensor" / "processed" / "detected_patterns.json"
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    patterns_data = [p.to_dict() for p in patterns]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(patterns_data, f, ensure_ascii=False, indent=2, default=str)

    print(f"  - 저장 완료: {output_path}")

    # 결과 요약 출력
    print_detection_summary(patterns)

    # 4. 검증 (옵션)
    if args.validate:
        print("\n[4/4] S1 이벤트와 검증...")
        expected = load_expected_events()

        if expected:
            validation_results = validate_detection(patterns, expected)
            print_validation_results(validation_results)

            # 검증 결과도 저장
            validation_path = output_path.parent / "validation_results.json"
            with open(validation_path, "w", encoding="utf-8") as f:
                json.dump(validation_results, f, ensure_ascii=False, indent=2)
            print(f"\n검증 결과 저장: {validation_path}")
        else:
            print("  - 예상 이벤트 없음, 검증 스킵")
    else:
        print("\n[4/4] 검증 스킵 (--validate 옵션으로 활성화)")

    print("\n" + "=" * 60)
    print("완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
