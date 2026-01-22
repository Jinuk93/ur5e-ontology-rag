# Main-F0: 환경 점검 및 Foundation 코드 리뷰

> **Phase**: Main-F0 (Foundation 개선 Phase 0)
> **목표**: Foundation 코드 리뷰 + Main 버전 환경 준비
> **상태**: 진행 중

---

## 1. 개요

### 1.1 Main-F0란?

Main-F0는 **Foundation(Phase 0-10) 완료 후, Main 버전을 시작하기 전 환경을 점검하는 단계**입니다.

Foundation에서 새로 환경을 구축했다면, Main-F0에서는:
1. 기존 환경이 정상 동작하는지 확인
2. Foundation 코드 리뷰 및 이슈 정리
3. Main 버전에 필요한 추가 패키지 설치
4. 센서 데이터 폴더 구조 생성

### 1.2 Foundation vs Main-F0 비교

| 항목 | Foundation Phase 0 | Main-F0 |
|------|-------------------|---------|
| **목적** | 환경 구축 (처음부터) | 환경 점검 + 확장 |
| **Python** | 설치 | 확인만 |
| **가상환경** | 생성 | 확인만 |
| **패키지** | 기본 설치 | **추가 설치** (센서용) |
| **Docker** | Neo4j 실행 | 확인만 |
| **코드 리뷰** | - | **Foundation 전체 리뷰** |
| **폴더 구조** | 기본 | **센서 폴더 추가** |

### 1.3 이 Phase의 핵심 산출물

1. **Foundation 코드 리뷰 체크리스트** - Spec vs 실제 구현 비교
2. **Main 환경 검증** - 추가 패키지, 센서 폴더
3. **이슈 목록** - Main에서 개선할 항목 정리

---

## 2. Foundation 코드 리뷰

### 2.1 Spec vs 실제 구현 비교

#### 2.1.1 폴더 구조

| 항목 | Foundation Spec | 실제 구현 | 상태 |
|------|----------------|-----------|------|
| API 서버 | `apps/api/` | `src/api/` | **불일치** |
| UI | `apps/ui/` | `src/dashboard/` | **불일치** |
| 파이프라인 | `pipelines/` | `src/ingestion/` | **불일치** |
| 온톨로지 | `src/ontology/` | `src/ontology/` | 일치 |
| RAG | `src/rag/` | `src/rag/` | 일치 |

**결론**: Main__Spec.md에서 실제 `src/` 중심 구조로 재정비 완료

#### 2.1.2 온톨로지 관계

| 관계 | Foundation Spec | 실제 구현 | 상태 |
|------|----------------|-----------|------|
| 에러→조치 | `FIXED_BY` | `RESOLVED_BY` | **불일치** |
| 에러→원인 | `MAY_CAUSE` | `CAUSED_BY` | **불일치** |
| 부품→에러 | `HAS_ERROR` | `HAS_ERROR` | 일치 |
| 문서 참조 | `REFERS_TO` | 미구현 | **누락** |

**결론**: Main__Spec.md에서 실제 구현 기준으로 문서화

#### 2.1.3 Entity Linker

| 항목 | Foundation Spec | 실제 구현 | 상태 |
|------|----------------|-----------|------|
| 방식 | Lexicon + Rules + Embedding | 단순 정규식만 | **미흡** |
| lexicon.yaml | 필요 | 미구현 | **누락** |
| rules.yaml | 필요 | 미구현 | **누락** |

**결론**: Main-F1에서 개선 예정

#### 2.1.4 Trace 시스템

| 항목 | Foundation Spec | 실제 구현 | 상태 |
|------|----------------|-----------|------|
| audit_trail.jsonl | 필요 | 미구현 | **누락** |
| trace_id 추적 | 필요 | 로그에만 남음 | **불완전** |
| /evidence API | 필요 | 부분 구현 | **불완전** |

**결론**: Main-F2에서 완성 예정

### 2.2 Foundation 이슈 요약

| 이슈 ID | 영역 | 설명 | 해결 Phase |
|---------|------|------|------------|
| F-001 | 폴더 구조 | Spec과 실제 불일치 | Main__Spec 재정비 완료 |
| F-002 | Entity Linker | 단순 정규식만 구현 | **Main-F1** |
| F-003 | Trace 시스템 | audit_trail 미구현 | **Main-F2** |
| F-004 | 메타데이터 | sources.yaml 미구현 | **Main-F3** |
| F-005 | 메타데이터 | chunk_manifest 미구현 | **Main-F3** |
| F-006 | 온톨로지 | 관계 명칭 불일치 | Main__Spec 재정비 완료 |

---

## 3. Main 환경 준비

### 3.1 추가 패키지 설치

Main 버전에서 센서 데이터를 다루기 위해 추가 패키지가 필요합니다.

**추가 패키지:**
```txt
# 센서 데이터 처리
pandas>=2.0.0
pyarrow>=14.0.0
duckdb>=0.9.0

# 신호 처리 (패턴 감지)
scipy>=1.11.0

# 시각화
plotly>=5.18.0
```

**설치 명령:**
```bash
# 가상환경 활성화
.\venv\Scripts\activate

# 추가 패키지 설치
pip install pandas pyarrow duckdb scipy plotly
```

### 3.2 센서 폴더 구조 생성

```
data/sensor/
├── raw/                    # 원본 센서 데이터
│   └── axia80_week_01.parquet  ← Main-S1에서 생성
├── processed/              # 처리된 데이터
│   └── anomaly_events.json     ← Main-S1에서 생성
└── metadata/               # 설정 파일
    └── sensor_config.yaml      ← Main-S1에서 생성
```

**생성 명령:**
```bash
mkdir -p data/sensor/raw data/sensor/processed data/sensor/metadata
```

### 3.3 requirements.txt 업데이트

**현재 requirements.txt에 추가:**
```txt
# ============================================================
# [Main 추가] 센서 데이터 처리
# ============================================================

# 데이터 처리
pandas>=2.0.0
pyarrow>=14.0.0         # Parquet 파일 지원
duckdb>=0.9.0           # 빠른 SQL 조회

# 신호 처리
scipy>=1.11.0           # FFT, 신호 분석

# 시각화
plotly>=5.18.0          # 센서 차트
```

---

## 4. 환경 검증

### 4.1 Foundation 환경 검증 (기존)

기존 `scripts/test_env.py`로 Foundation 환경이 정상인지 확인:

```bash
python scripts/test_env.py
```

**예상 결과:**
```
[PASS] Python Version
[PASS] Packages
[PASS] Env Variables
[PASS] Neo4j Connection
[PASS] OpenAI API

*** All checks passed! ***
```

### 4.2 Main 추가 환경 검증

**검증 스크립트:** `scripts/test_main_env.py`

```python
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
```

---

## 5. Main-F0 체크리스트

### 5.1 Foundation 환경 확인

- [x] Python 3.10+ 확인
- [x] 가상환경 활성화 확인
- [x] 기존 패키지 설치 확인
- [x] Neo4j 연결 확인
- [x] OpenAI API 연결 확인

### 5.2 Foundation 코드 리뷰

- [x] 폴더 구조 Spec vs 실제 비교
- [x] 온톨로지 관계 Spec vs 실제 비교
- [x] Entity Linker 구현 상태 확인
- [x] Trace 시스템 구현 상태 확인
- [x] 이슈 목록 정리

### 5.3 Main 환경 준비

- [x] 센서 처리 패키지 설치 (pandas, pyarrow, duckdb, scipy, plotly)
- [x] 센서 폴더 구조 생성
- [x] requirements.txt 업데이트
- [x] Main 환경 검증 스크립트 작성

### 5.4 센서 데이터 (Main-S1 완료 후)

- [x] axia80_week_01.parquet 생성
- [x] anomaly_events.json 생성
- [x] sensor_config.yaml 생성
- [x] 데이터 검증 통과

---

## 6. Main-F0 실행 결과

### 6.1 Foundation 환경 검증

```bash
python scripts/test_env.py
```

```
[PASS] Python Version - 3.11.9
[PASS] Packages - 8개 모두 설치됨
[PASS] Env Variables - 5개 모두 설정됨
[PASS] Neo4j Connection
[PASS] OpenAI API

*** All checks passed! ***
```

### 6.2 Main 환경 검증

```bash
python scripts/test_main_env.py
```

```
[PASS] Sensor Packages - 5개 모두 설치됨
[PASS] Sensor Folders - 3개 폴더 존재
[PASS] Sensor Data Files - 3개 파일 존재 (34.15 MB)
[PASS] Sensor Data Integrity - 604,800 레코드, 21 컬럼

*** Main environment ready! ***
```

---

## 7. 다음 단계

### 7.1 Main Phase 진행 순서

```
Main-F0 (환경 점검) ← 현재
    │
    ├── Main-F1: Entity Linker 개선
    ├── Main-F2: Trace 시스템 완성
    └── Main-F3: 메타데이터 정비
    │
Main-S1 (센서 데이터 생성) ← 완료
    │
    ├── Main-S2: 패턴 감지
    ├── Main-S3: Context Enricher
    ├── Main-S4: 온톨로지 확장
    ├── Main-S5: Verifier 확장
    └── Main-S6: API/UI 확장
```

### 7.2 참조 문서

- [Main__Spec.md](Main__Spec.md) - 기술 설계서
- [Main__ROADMAP.md](Main__ROADMAP.md) - 개발 로드맵
- [Main_S1_센서데이터생성.md](Main_S1_센서데이터생성.md) - 센서 데이터 문서

---

**작성일**: 2024-01-21
**참조**: Foundation_Phase0_환경설정.md, Foundation_Phase0_완료보고서.md
