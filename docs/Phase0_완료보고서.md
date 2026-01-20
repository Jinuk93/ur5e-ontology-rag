# Phase 0: 개발 환경 설정 - 완료 보고서

> **작성일:** 2025-01-20
> **상태:** ✅ 완료
> **목표:** 코드를 실행할 수 있는 개발 환경을 구축한다.

---

## 목차

1. [개요](#1-개요)
2. [기획 vs 실제 구현 비교](#2-기획-vs-실제-구현-비교)
3. [생성된 파일 전체 목록](#3-생성된-파일-전체-목록)
4. [파일별 상세 설명](#4-파일별-상세-설명)
5. [코드 분석: test_env.py](#5-코드-분석-test_envpy)
6. [실행 결과](#6-실행-결과)
7. [배운 점 정리](#7-배운-점-정리)

---

## 1. 개요

### 1.1 Phase 0이란?

Phase 0은 **개발을 시작하기 전에 필요한 환경을 준비하는 단계**입니다.
코드를 작성해도 실행할 환경이 없으면 아무 의미가 없기 때문에,
모든 프로젝트의 가장 첫 단계입니다.

### 1.2 이 Phase의 목표

```
[목표]
프로젝트 코드를 실행할 수 있는 환경을 구축한다.

[구체적으로]
1. Python 가상환경 설정
2. 필요한 패키지 설치
3. 환경변수 설정 (API 키, DB 접속 정보)
4. 데이터베이스(Neo4j) 실행
5. 환경이 제대로 동작하는지 검증
```

### 1.3 왜 이 순서인가?

```
코드 작성 → 실행 → 에러 발생 → "환경 문제인가? 코드 문제인가?" 혼란
                    ↓
        디버깅 시간 낭비

vs.

환경 먼저 검증 → 코드 작성 → 실행 → 에러 발생 → "코드 문제임" 확신
                                      ↓
                            빠른 디버깅
```

---

## 2. 기획 vs 실제 구현 비교

### 2.1 전체 비교표

| 항목 | 기획 (Phase0_환경설정.md) | 실제 구현 | 차이점 |
|------|---------------------------|-----------|--------|
| Python 버전 | 3.10 이상 | 3.11.9 | 기획보다 높은 버전 사용 |
| 가상환경 | venv 사용 | venv 사용 | 동일 |
| Neo4j | Docker로 실행 | Docker로 실행 (v5.15.0) | 동일 |
| ChromaDB | Docker로 실행 | Python 패키지로 사용 | **변경** - 서버 없이 로컬로 |
| 환경 검증 | 간단한 스크립트 | 5단계 검증 스크립트 | **확장** - 더 상세한 검증 |
| 패키지 관리 | requirements.txt 1개 | requirements.txt 3개 | **확장** - 역할별 분리 |

### 2.2 변경된 부분 상세

#### ChromaDB 실행 방식 변경

| 구분 | 기획 | 실제 |
|------|------|------|
| 실행 방식 | Docker 컨테이너 | Python 패키지 (로컬 파일) |
| 이유 | - | 개인 프로젝트에서는 서버 없이 더 간단함 |
| docker-compose.yaml | chromadb 서비스 포함 | 주석 처리됨 |

#### 환경 검증 스크립트 확장

| 구분 | 기획 | 실제 |
|------|------|------|
| 검증 항목 | 패키지 설치, 환경변수 | Python 버전, 패키지, 환경변수, Neo4j 연결, OpenAI API |
| 파일 위치 | 문서 내 예시 코드 | `scripts/test_env.py` (독립 파일) |
| 출력 형식 | 간단한 print | 섹션별 구분, 최종 요약 포함 |

---

## 3. 생성된 파일 전체 목록

### 3.1 환경 설정 파일

| 경로 | 역할 | Git 포함 |
|------|------|----------|
| `.env.example` | 환경변수 템플릿 | ✅ 포함 |
| `.env` | 실제 환경변수 (API 키 등) | ❌ 제외 |
| `.gitignore` | Git 무시 목록 | ✅ 포함 |

### 3.2 의존성 파일

| 경로 | 역할 | 패키지 수 |
|------|------|----------|
| `requirements.txt` | 전체 공통 패키지 | 14개 |
| `apps/api/requirements.txt` | API 서버 전용 | 10개 |
| `apps/ui/requirements.txt` | UI 대시보드 전용 | 7개 |

### 3.3 인프라 설정

| 경로 | 역할 |
|------|------|
| `docker-compose.yaml` | Neo4j 컨테이너 정의 |
| `configs/settings.yaml` | 프로젝트 설정값 |

### 3.4 스크립트

| 경로 | 역할 |
|------|------|
| `scripts/test_env.py` | 환경 검증 스크립트 |

### 3.5 폴더 구조 유지용

| 경로 | 역할 |
|------|------|
| `data/raw/pdf/.gitkeep` | PDF 저장 폴더 |
| `stores/chroma/.gitkeep` | ChromaDB 저장 폴더 |
| `stores/neo4j/.gitkeep` | Neo4j 데이터 폴더 |
| `stores/audit/.gitkeep` | 감사 로그 폴더 |

---

## 4. 파일별 상세 설명

### 4.1 `.env.example`

**경로:** `.env.example`

**역할:** 환경변수의 "템플릿" 파일. 어떤 환경변수가 필요한지 알려줌.

**구조:**
```bash
# ============================================================
# .env.example - 환경변수 템플릿 파일
# ============================================================

# [1] OpenAI API 설정
OPENAI_API_KEY=sk-xxxxxxxx        # OpenAI API 키

# [2] Neo4j 설정 (그래프 데이터베이스)
NEO4J_URI=bolt://localhost:7687   # 접속 주소
NEO4J_USER=neo4j                  # 사용자명
NEO4J_PASSWORD=your-password      # 비밀번호

# [3] ChromaDB 설정 (벡터 데이터베이스)
CHROMA_PERSIST_DIR=./stores/chroma

# [4] 파일 경로 설정
DATA_RAW_DIR=./data/raw/pdf
DATA_PROCESSED_DIR=./data/processed
AUDIT_LOG_DIR=./stores/audit

# [5] 로깅 설정
LOG_LEVEL=INFO
```

**왜 이렇게 작성했는가:**
- 섹션별로 구분하여 가독성 향상
- 각 변수 옆에 주석으로 용도 설명
- 실제 값 대신 placeholder (`sk-xxxxxxxx`) 사용

---

### 4.2 `.gitignore`

**경로:** `.gitignore`

**역할:** Git이 추적하지 않을 파일/폴더 목록

**핵심 섹션:**
```bash
# [1] 환경변수 / 비밀 정보 (가장 중요!)
.env                    # API 키, 비밀번호 포함
!.env.example           # 템플릿은 포함

# [2] Python 관련
venv/                   # 가상환경 (용량 큼)
__pycache__/            # 캐시 파일

# [5] 데이터 파일 (용량 큼)
data/raw/pdf/*.pdf      # PDF 원본

# [6] 데이터베이스 / 스토어
stores/chroma/          # 벡터 인덱스
stores/neo4j/           # Neo4j 데이터
```

**왜 이 파일들을 무시하는가:**

| 파일/폴더 | 무시 이유 |
|-----------|----------|
| `.env` | API 키, 비밀번호 노출 방지 |
| `venv/` | 용량 큼 + 각자 PC에서 생성 |
| `*.pdf` | 용량 큼 + 저작권 이슈 가능 |
| `stores/` | 용량 큼 + 각자 생성 |

---

### 4.3 `requirements.txt` (루트)

**경로:** `requirements.txt`

**역할:** 프로젝트 전체에서 공통으로 사용하는 패키지

**구조:**
```txt
# [1] 환경 설정 관련
python-dotenv>=1.0.0    # .env 파일 로드
pyyaml>=6.0             # YAML 파일 읽기

# [2] PDF 처리 관련
pymupdf>=1.23.0         # PDF 텍스트 추출

# [3] AI/LLM 관련
openai>=1.0.0           # OpenAI API
tiktoken>=0.5.0         # 토큰 계산

# [4] 벡터 DB 관련
chromadb>=0.4.0         # 벡터 검색

# [5] 그래프 DB 관련
neo4j>=5.0.0            # Neo4j 드라이버

# [6] 웹 프레임워크 관련
fastapi>=0.100.0        # API 서버
uvicorn>=0.23.0         # ASGI 서버
pydantic>=2.0.0         # 데이터 검증

# [7] UI 관련
streamlit>=1.28.0       # 대시보드

# [8] 유틸리티
requests>=2.31.0        # HTTP 요청
tqdm>=4.66.0            # 진행 표시줄

# [9] 개발/테스트 도구
pytest>=7.4.0           # 테스트
black>=23.0.0           # 코드 포맷터
```

**왜 버전을 `>=`로 지정했는가:**
- `==`: 정확히 그 버전만 (너무 제한적)
- `>=`: 그 버전 이상 (호환성 유지하면서 유연)
- 개인 프로젝트에서는 `>=`가 적절

---

### 4.4 `docker-compose.yaml`

**경로:** `docker-compose.yaml`

**역할:** Neo4j 데이터베이스를 Docker 컨테이너로 실행

**전체 구조:**
```yaml
version: "3.8"

services:
  # Neo4j 컨테이너 정의
  neo4j:
    image: neo4j:5.15.0              # 사용할 이미지
    container_name: ur5e-neo4j       # 컨테이너 이름

    ports:
      - "7474:7474"                  # 웹 UI
      - "7687:7687"                  # Bolt 프로토콜

    environment:
      - NEO4J_AUTH=neo4j/password123 # 인증 정보
      - NEO4J_PLUGINS=["apoc"]       # 플러그인

    volumes:
      - ./stores/neo4j/data:/data    # 데이터 영속화
      - ./stores/neo4j/logs:/logs    # 로그

    restart: unless-stopped          # 재시작 정책
```

**포트 설명:**

| 포트 | 용도 | 접속 방법 |
|------|------|----------|
| 7474 | 웹 브라우저 UI | http://localhost:7474 |
| 7687 | Bolt 프로토콜 | Python 코드에서 연결 |

**volumes가 필요한 이유:**
```
컨테이너 삭제 → 데이터도 삭제됨 (기본)

volumes 사용 시:
컨테이너 삭제 → 데이터는 로컬에 유지됨
```

---

### 4.5 `configs/settings.yaml`

**경로:** `configs/settings.yaml`

**역할:** 프로젝트 설정값을 코드와 분리하여 관리

**핵심 설정:**
```yaml
# [1] 문서 처리 설정
document:
  chunk_size: 512       # 청크 크기 (글자 수)
  chunk_overlap: 50     # 청크 간 겹침

# [2] 검색 설정
retrieval:
  top_k: 5              # 검색 결과 개수
  similarity_threshold: 0.7  # 유사도 임계값

# [3] LLM 설정
llm:
  model: "gpt-4o-mini"  # 사용할 모델
  temperature: 0.0      # 응답 일관성 (0=일관)

# [4] Verifier 설정
verifier:
  require_citation_for_action: true  # 조치에 근거 필수
```

**왜 설정 파일로 분리했는가:**
```python
# 나쁜 예: 코드에 하드코딩
chunk_size = 512  # 바꾸려면 코드 수정 필요

# 좋은 예: 설정 파일에서 읽기
config = load_yaml("configs/settings.yaml")
chunk_size = config["document"]["chunk_size"]
# → 설정만 바꾸면 됨, 코드 수정 불필요
```

---

## 5. 코드 분석: test_env.py

### 5.1 파일 개요

**경로:** `scripts/test_env.py`

**역할:** Phase 0에서 설정한 환경이 제대로 동작하는지 검증

**검증 항목:**
1. Python 버전 (3.10 이상)
2. 필수 패키지 설치 여부
3. 환경변수 설정 여부
4. Neo4j 연결 가능 여부
5. OpenAI API 연결 가능 여부

### 5.2 전체 구조 (탑다운)

```
test_env.py
│
├── main()                    # 진입점: 모든 검증 실행
│   ├── check_python_version()
│   ├── check_packages()
│   ├── check_env_variables()
│   ├── check_neo4j_connection()
│   └── check_openai_api()
│
├── check_python_version()    # Python 버전 확인
├── check_packages()          # 패키지 설치 확인
├── check_env_variables()     # 환경변수 확인
├── check_neo4j_connection()  # Neo4j 연결 확인
└── check_openai_api()        # OpenAI API 확인
```

### 5.3 함수별 상세 분석

#### 5.3.1 `main()` - 메인 함수

```python
def main():
    """
    메인 함수 - 모든 검증 실행
    """
    print("\n[*] Starting environment verification...\n")

    results = []  # 각 검증 결과를 저장할 리스트

    # 5가지 검증 순차 실행
    results.append(("Python Version", check_python_version()))
    results.append(("Packages", check_packages()))
    results.append(("Env Variables", check_env_variables()))
    results.append(("Neo4j Connection", check_neo4j_connection()))
    results.append(("OpenAI API", check_openai_api()))

    # 최종 결과 출력
    print("\n" + "=" * 50)
    print("[SUMMARY] Final Results")
    print("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {name}")
        if not passed:
            all_passed = False

    # 최종 메시지
    if all_passed:
        print("\n*** All checks passed! ***")
    else:
        print("\n*** Some checks failed ***")

    return all_passed
```

**흐름도:**
```
main() 시작
    │
    ├─▶ check_python_version() ──▶ 결과 저장
    ├─▶ check_packages() ──▶ 결과 저장
    ├─▶ check_env_variables() ──▶ 결과 저장
    ├─▶ check_neo4j_connection() ──▶ 결과 저장
    ├─▶ check_openai_api() ──▶ 결과 저장
    │
    └─▶ 결과 종합 출력
```

---

#### 5.3.2 `check_python_version()` - Python 버전 확인

```python
def check_python_version():
    """
    Python 버전 확인
    최소 3.10 이상이어야 함
    """
    print("=" * 50)
    print("[1] Python Version Check")
    print("=" * 50)

    version = sys.version_info  # (major=3, minor=11, micro=9, ...)
    print(f"Current: Python {version.major}.{version.minor}.{version.micro}")

    # 3.10 이상인지 확인
    if version.major >= 3 and version.minor >= 10:
        print("[OK] Python version OK")
        return True
    else:
        print("[FAIL] Python 3.10+ required")
        return False
```

**라인별 설명:**

| 라인 | 코드 | 설명 |
|------|------|------|
| 1 | `version = sys.version_info` | Python 버전 정보를 가져옴 |
| 2 | `version.major` | 메이저 버전 (예: **3**.11.9의 3) |
| 3 | `version.minor` | 마이너 버전 (예: 3.**11**.9의 11) |
| 4 | `if version.major >= 3 and version.minor >= 10` | 3.10 이상인지 조건 확인 |

---

#### 5.3.3 `check_packages()` - 패키지 설치 확인

```python
def check_packages():
    """
    필수 패키지 설치 확인
    """
    print("\n" + "=" * 50)
    print("[2] Package Check")
    print("=" * 50)

    # 확인할 패키지 목록 (import 이름, 패키지 이름)
    packages = [
        ("dotenv", "python-dotenv"),  # import dotenv / pip install python-dotenv
        ("yaml", "pyyaml"),
        ("fitz", "pymupdf"),          # pymupdf는 fitz로 import
        ("openai", "openai"),
        ("chromadb", "chromadb"),
        ("neo4j", "neo4j"),
        ("fastapi", "fastapi"),
        ("streamlit", "streamlit"),
    ]

    all_ok = True
    for import_name, package_name in packages:
        try:
            __import__(import_name)   # 동적으로 import 시도
            print(f"[OK] {package_name}")
        except ImportError:
            print(f"[FAIL] {package_name}")
            all_ok = False

    return all_ok
```

**왜 `__import__`를 사용했는가:**
```python
# 일반적인 import (정적)
import openai  # 코드 작성 시점에 패키지명 고정

# __import__ (동적)
__import__("openai")  # 문자열로 패키지명 전달 가능
# → 반복문에서 여러 패키지를 확인할 때 유용
```

**주의: import 이름 ≠ 패키지 이름**

| pip install | import |
|-------------|--------|
| `python-dotenv` | `dotenv` |
| `pyyaml` | `yaml` |
| `pymupdf` | `fitz` |

---

#### 5.3.4 `check_env_variables()` - 환경변수 확인

```python
def check_env_variables():
    """
    환경변수 확인 (.env 파일)
    """
    import os
    from dotenv import load_dotenv

    load_dotenv()  # .env 파일을 읽어서 환경변수로 등록

    # 확인할 환경변수 목록
    env_vars = [
        "OPENAI_API_KEY",
        "NEO4J_URI",
        "NEO4J_USER",
        "NEO4J_PASSWORD",
        "CHROMA_PERSIST_DIR",
    ]

    all_ok = True
    for var in env_vars:
        value = os.getenv(var)  # 환경변수 값 가져오기
        if value:
            # API 키는 앞 10자만 표시 (보안)
            if "KEY" in var or "PASSWORD" in var:
                display = value[:10] + "..."
            else:
                display = value
            print(f"[OK] {var} = {display}")
        else:
            print(f"[FAIL] {var} - not set")
            all_ok = False

    return all_ok
```

**load_dotenv() 동작 원리:**
```
.env 파일:
OPENAI_API_KEY=sk-12345

load_dotenv() 실행 후:
os.getenv("OPENAI_API_KEY") → "sk-12345"
```

**왜 API 키를 일부만 표시하는가:**
```
전체 표시: sk-proj-MgUkZwaoVp4jacaA1TtLxa7B...
→ 화면 캡처, 로그 유출 시 위험

일부만 표시: sk-proj-Mg...
→ 설정됨을 확인 가능 + 보안 유지
```

---

#### 5.3.5 `check_neo4j_connection()` - Neo4j 연결 확인

```python
def check_neo4j_connection():
    """
    Neo4j 연결 확인
    """
    import os
    from dotenv import load_dotenv

    load_dotenv()

    try:
        from neo4j import GraphDatabase

        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER")
        password = os.getenv("NEO4J_PASSWORD")

        # Neo4j 드라이버 생성
        driver = GraphDatabase.driver(uri, auth=(user, password))

        # 연결 확인 (실제로 접속 시도)
        driver.verify_connectivity()

        # 연결 종료
        driver.close()

        print(f"[OK] Neo4j connected ({uri})")
        return True

    except Exception as e:
        print(f"[FAIL] Neo4j connection failed: {e}")
        return False
```

**연결 흐름:**
```
1. 환경변수에서 접속 정보 로드
   uri = "bolt://localhost:7687"
   user = "neo4j"
   password = "password123"

2. 드라이버 생성
   driver = GraphDatabase.driver(uri, auth=(user, password))

3. 연결 확인
   driver.verify_connectivity()  # 실제 접속 시도

4. 연결 종료
   driver.close()  # 리소스 해제
```

---

#### 5.3.6 `check_openai_api()` - OpenAI API 확인

```python
def check_openai_api():
    """
    OpenAI API 연결 확인
    """
    import os
    from dotenv import load_dotenv

    load_dotenv()

    try:
        from openai import OpenAI

        # 클라이언트 생성 (환경변수에서 자동으로 키 로드)
        client = OpenAI()

        # 간단한 테스트: 모델 목록 조회
        models = client.models.list()

        print("[OK] OpenAI API connected")
        return True

    except Exception as e:
        print(f"[FAIL] OpenAI API failed: {e}")
        return False
```

**OpenAI 클라이언트가 API 키를 찾는 순서:**
```
1. 생성자 인자: OpenAI(api_key="sk-...")
2. 환경변수: OPENAI_API_KEY
3. 없으면 에러 발생
```

---

## 6. 실행 결과

### 6.1 검증 스크립트 실행

**명령어:**
```bash
cd ur5e-ontology-rag
.\venv\Scripts\activate
python scripts/test_env.py
```

### 6.2 출력 결과

```
[*] Starting environment verification...

==================================================
[1] Python Version Check
==================================================
Current: Python 3.11.9
[OK] Python version OK

==================================================
[2] Package Check
==================================================
[OK] python-dotenv
[OK] pyyaml
[OK] pymupdf
[OK] openai
[OK] chromadb
[OK] neo4j
[OK] fastapi
[OK] streamlit

==================================================
[3] Environment Variables Check
==================================================
[OK] OPENAI_API_KEY = sk-proj-Mg...
[OK] NEO4J_URI = bolt://localhost:7687
[OK] NEO4J_USER = neo4j
[OK] NEO4J_PASSWORD = password12...
[OK] CHROMA_PERSIST_DIR = ./stores/chroma

==================================================
[4] Neo4j Connection Check
==================================================
[OK] Neo4j connected (bolt://localhost:7687)

==================================================
[5] OpenAI API Check
==================================================
[OK] OpenAI API connected

==================================================
[SUMMARY] Final Results
==================================================
[PASS] Python Version
[PASS] Packages
[PASS] Env Variables
[PASS] Neo4j Connection
[PASS] OpenAI API
==================================================

*** All checks passed! ***
Ready to proceed to Phase 1!
```

### 6.3 결과 해석

| 항목 | 결과 | 의미 |
|------|------|------|
| Python Version | PASS | 3.11.9 ≥ 3.10 조건 충족 |
| Packages | PASS | 8개 필수 패키지 모두 설치됨 |
| Env Variables | PASS | 5개 환경변수 모두 설정됨 |
| Neo4j Connection | PASS | Docker 컨테이너 정상 실행 중 |
| OpenAI API | PASS | API 키 유효, 네트워크 정상 |

---

## 7. 배운 점 정리

### 7.1 개념 정리

| 개념 | 한 줄 정의 | 이 프로젝트에서의 용도 |
|------|-----------|---------------------|
| 가상환경 | 프로젝트별 독립된 Python 환경 | 패키지 버전 충돌 방지 |
| 환경변수 | 프로그램 외부에서 주입하는 설정값 | API 키, 비밀번호 보호 |
| Docker | 앱을 컨테이너로 패키징하는 기술 | Neo4j를 간편하게 실행 |
| YAML | 사람이 읽기 쉬운 설정 파일 형식 | 프로젝트 설정 관리 |

### 7.2 명령어 정리

| 작업 | 명령어 |
|------|--------|
| 가상환경 생성 | `python -m venv venv` |
| 가상환경 활성화 (Windows) | `.\venv\Scripts\activate` |
| 패키지 설치 | `pip install -r requirements.txt` |
| Docker 컨테이너 실행 | `docker-compose up -d` |
| 실행 중 컨테이너 확인 | `docker ps` |
| 환경 검증 | `python scripts/test_env.py` |

### 7.3 면접 예상 질문

**Q: 왜 .env 파일을 Git에 올리면 안 되나요?**
> API 키, 비밀번호 등 민감 정보가 포함되어 있어서 공개되면 보안 문제가 발생합니다. `.gitignore`에 추가해서 Git 추적에서 제외합니다.

**Q: requirements.txt를 왜 여러 개로 분리했나요?**
> 역할별로 분리하면 Docker 빌드 시 필요한 패키지만 설치할 수 있어서 이미지 크기가 줄고 빌드 시간이 단축됩니다.

**Q: Docker를 사용하는 이유는?**
> Neo4j 같은 데이터베이스를 직접 설치하면 Java 설치, 설정 파일 수정 등 복잡합니다. Docker는 한 줄 명령어로 실행 가능하고, 어떤 환경에서든 동일하게 동작합니다.

---

## 8. 다음 단계 (Phase 1 미리보기)

**Phase 1: 데이터 탐색**에서는:

1. `data/raw/pdf/` 폴더에 UR5e PDF 문서 3개 넣기
2. PDF 내용 직접 열어보고 구조 파악
3. 추출할 정보 (에러코드, 증상, 조치) 식별
4. 샘플 질문-답변 쌍 만들어보기