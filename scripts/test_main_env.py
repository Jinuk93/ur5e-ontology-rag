"""
Main 버전 환경 검증 스크립트

검증 항목:
1. Foundation 환경 (기존)
2. 센서 처리 패키지 (추가)
3. 센서 폴더 구조 (추가)
4. 센서 데이터 파일 (추가)
"""

import sys
from pathlib import Path


def check_sensor_packages():
    """센서 처리 패키지 확인"""
    print("\n" + "=" * 50)
    print("[Main-1] Sensor Packages Check")
    print("=" * 50)

    packages = [
        ("pandas", "pandas"),
        ("pyarrow", "pyarrow"),
        ("duckdb", "duckdb"),
        ("scipy", "scipy"),
        ("plotly", "plotly"),
    ]

    all_ok = True
    for import_name, package_name in packages:
        try:
            __import__(import_name)
            print(f"[OK] {package_name}")
        except ImportError:
            print(f"[FAIL] {package_name} - pip install {package_name}")
            all_ok = False

    return all_ok


def check_sensor_folders():
    """센서 폴더 구조 확인"""
    print("\n" + "=" * 50)
    print("[Main-2] Sensor Folders Check")
    print("=" * 50)

    base_dir = Path(__file__).parent.parent
    folders = [
        "data/sensor/raw",
        "data/sensor/processed",
        "data/sensor/metadata",
    ]

    all_ok = True
    for folder in folders:
        path = base_dir / folder
        if path.exists():
            print(f"[OK] {folder}")
        else:
            print(f"[FAIL] {folder} - mkdir -p {folder}")
            all_ok = False

    return all_ok


def check_sensor_data():
    """센서 데이터 파일 확인"""
    print("\n" + "=" * 50)
    print("[Main-3] Sensor Data Check")
    print("=" * 50)

    base_dir = Path(__file__).parent.parent
    files = {
        "data/sensor/raw/axia80_week_01.parquet": "센서 데이터",
        "data/sensor/processed/anomaly_events.json": "이상 이벤트",
        "data/sensor/metadata/sensor_config.yaml": "센서 설정",
    }

    all_ok = True
    for file_path, desc in files.items():
        path = base_dir / file_path
        if path.exists():
            size_mb = path.stat().st_size / 1024 / 1024
            print(f"[OK] {desc}: {file_path} ({size_mb:.2f} MB)")
        else:
            print(f"[WARN] {desc}: {file_path} (Main-S1에서 생성)")
            # 데이터 파일은 아직 없어도 됨

    return True  # 데이터 파일은 경고만


def check_sensor_data_integrity():
    """센서 데이터 무결성 검증"""
    print("\n" + "=" * 50)
    print("[Main-4] Sensor Data Integrity Check")
    print("=" * 50)

    base_dir = Path(__file__).parent.parent
    parquet_path = base_dir / "data/sensor/raw/axia80_week_01.parquet"

    if not parquet_path.exists():
        print("[SKIP] 센서 데이터 없음 (Main-S1 완료 후 다시 검증)")
        return True

    try:
        import pandas as pd

        df = pd.read_parquet(parquet_path)

        # 기본 검증
        print(f"[OK] 레코드 수: {len(df):,}")
        print(f"[OK] 컬럼 수: {len(df.columns)}")

        # 필수 컬럼 확인
        required_columns = ['timestamp', 'Fx', 'Fy', 'Fz', 'Tx', 'Ty', 'Tz',
                           'task_mode', 'status']
        missing = [c for c in required_columns if c not in df.columns]
        if missing:
            print(f"[FAIL] 누락 컬럼: {missing}")
            return False
        else:
            print(f"[OK] 필수 컬럼 모두 존재")

        return True

    except Exception as e:
        print(f"[FAIL] 데이터 로드 실패: {e}")
        return False


def main():
    print("=" * 50)
    print("Main 버전 환경 검증")
    print("=" * 50)

    results = []

    results.append(("Sensor Packages", check_sensor_packages()))
    results.append(("Sensor Folders", check_sensor_folders()))
    results.append(("Sensor Data Files", check_sensor_data()))
    results.append(("Sensor Data Integrity", check_sensor_data_integrity()))

    # 결과 요약
    print("\n" + "=" * 50)
    print("[SUMMARY] Main Environment Results")
    print("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n*** Main environment ready! ***")
    else:
        print("\n*** Some checks failed ***")

    return all_passed


if __name__ == "__main__":
    main()
