# Phase 0: 개발 환경 설정

> **목표:** 코드를 실행할 수 있는 개발 환경을 구축한다.
>
> **왜 먼저?** 환경이 없으면 아무 코드도 실행할 수 없다.

---

## 0.1 이번 Phase에서 배울 것

| 개념 | 설명 | 왜 필요한가? |
|------|------|-------------|
| **Python** | 프로그래밍 언어 | AI/ML 생태계의 표준 언어 |
| **가상환경(venv)** | 프로젝트별 독립된 Python 환경 | 프로젝트마다 다른 라이브러리 버전 충돌 방지 |
| **pip** | Python 패키지 관리자 | 필요한 라이브러리 설치 |
| **Docker** | 컨테이너 기술 | Neo4j, ChromaDB 등을 쉽게 실행 |
| **환경변수(.env)** | API 키 등 민감 정보 저장 | 코드에 비밀번호 노출 방지 |

---

## 0.2 체크리스트

### Step 1: Python 설치 확인

```bash
# 터미널에서 실행
python --version
```

**기대 결과:** `Python 3.10.x` 이상

만약 설치 안 됨:
- Windows: https://www.python.org/downloads/ 에서 다운로드
- 설치 시 "Add Python to PATH" 체크 필수!

---

### Step 2: 가상환경 생성

```bash
# 프로젝트 폴더로 이동
cd c:\Users\nugikim\Desktop\ur5e-ontology-rag

# 가상환경 생성 (venv라는 폴더가 만들어짐)
python -m venv venv

# 가상환경 활성화 (Windows)
.\venv\Scripts\activate

# 활성화 확인 - 프롬프트 앞에 (venv) 표시되면 성공
# (venv) C:\Users\nugikim\Desktop\ur5e-ontology-rag>
```

**왜 가상환경을 쓰나요?**
```
프로젝트 A: numpy 1.0 필요
프로젝트 B: numpy 2.0 필요
→ 같은 컴퓨터에서 충돌!

가상환경 사용 시:
프로젝트 A의 venv: numpy 1.0 설치
프로젝트 B의 venv: numpy 2.0 설치
→ 각자 독립적으로 동작!
```

---

### Step 3: 기본 패키지 설치

```bash
# 가상환경 활성화된 상태에서
pip install --upgrade pip

# 주요 패키지들 설치
pip install python-dotenv    # 환경변수 관리
pip install pyyaml           # YAML 파일 읽기
```

---

### Step 4: Docker 설치 확인

```bash
docker --version
```

**기대 결과:** `Docker version 24.x.x` 이상

만약 설치 안 됨:
- Windows: https://docs.docker.com/desktop/install/windows-install/
- Docker Desktop 설치 후 재부팅 필요

**왜 Docker를 쓰나요?**
```
Neo4j 직접 설치하려면:
1. Java 설치
2. Neo4j 다운로드
3. 설정 파일 수정
4. 포트 설정
5. 서비스 등록
... 복잡!

Docker 사용 시:
docker run neo4j
→ 끝! 한 줄로 실행
```

---

### Step 5: 환경변수 파일 설정

프로젝트에 `.env.example` 파일이 있습니다. 이것을 복사해서 `.env` 파일을 만들어야 합니다.

```bash
# .env.example 내용 확인 후
# .env 파일에 실제 값 입력
```

**`.env` 파일 예시:**
```env
# OpenAI API 키 (https://platform.openai.com/api-keys 에서 발급)
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# Neo4j 설정 (일단 기본값 사용)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here

# ChromaDB 설정
CHROMA_PERSIST_DIR=./stores/chroma
```

**왜 .env 파일을 쓰나요?**
```python
# 나쁜 예 - 코드에 API 키 직접 작성
api_key = "sk-12345abcde"  # GitHub에 올리면 해킹당함!

# 좋은 예 - 환경변수에서 읽기
import os
api_key = os.getenv("OPENAI_API_KEY")  # .env에서 읽어옴
```

---

### Step 6: Docker Compose로 DB 실행

```bash
# 프로젝트 폴더에서
docker-compose up -d
```

이 명령은 `docker-compose.yaml`에 정의된 서비스들을 실행합니다:
- Neo4j (그래프 데이터베이스)
- ChromaDB (벡터 데이터베이스) - 필요 시

---

## 0.3 검증: 환경이 제대로 설정되었는지 확인

아래 Python 코드를 실행해서 모든 것이 제대로 되었는지 확인합니다.

```python
# test_env.py
import sys
print(f"Python 버전: {sys.version}")

# 패키지 확인
try:
    import dotenv
    print("✓ python-dotenv 설치됨")
except ImportError:
    print("✗ python-dotenv 설치 필요")

try:
    import yaml
    print("✓ pyyaml 설치됨")
except ImportError:
    print("✗ pyyaml 설치 필요")

# 환경변수 확인
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    print(f"✓ OPENAI_API_KEY 설정됨 (앞 10자: {api_key[:10]}...)")
else:
    print("✗ OPENAI_API_KEY 설정 필요")

print("\n환경 설정 검증 완료!")
```

---

## 0.4 핵심 개념 정리

### 가상환경이란?
- 프로젝트마다 **독립된 Python 환경**을 만드는 것
- 다른 프로젝트와 라이브러리 버전 충돌을 방지
- 활성화: `.\venv\Scripts\activate` (Windows)
- 비활성화: `deactivate`

### pip이란?
- Python **패키지 관리자**
- `pip install 패키지명` - 설치
- `pip list` - 설치된 패키지 목록
- `pip freeze > requirements.txt` - 현재 설치된 패키지를 파일로 저장

### Docker란?
- **컨테이너** 기술 - 앱을 "상자"에 담아서 어디서든 동일하게 실행
- 복잡한 설치 과정 없이 `docker run`으로 바로 실행
- `docker-compose` - 여러 컨테이너를 한번에 관리

### 환경변수란?
- 프로그램 **외부**에서 설정값을 주입하는 방법
- API 키, 비밀번호 등 민감 정보를 코드에 직접 쓰지 않음
- `.env` 파일은 **절대 Git에 올리면 안 됨** (`.gitignore`에 포함)

---

## 0.5 트러블슈팅

### Q: `python` 명령이 안 됨
```bash
# Windows에서 python 대신 py 사용
py --version
py -m venv venv
```

### Q: 가상환경 활성화가 안 됨 (PowerShell)
```powershell
# 실행 정책 변경 필요
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# 이후 다시 시도
.\venv\Scripts\activate
```

### Q: Docker가 실행 안 됨
1. Docker Desktop이 실행 중인지 확인
2. 시스템 트레이에서 Docker 아이콘 확인
3. WSL2가 설치되어 있는지 확인 (Windows)

---

## 0.6 이번 Phase 완료 조건

- [ ] Python 3.10+ 설치 확인
- [ ] 가상환경 생성 및 활성화
- [ ] 기본 패키지 설치 (python-dotenv, pyyaml)
- [ ] Docker 설치 확인
- [ ] `.env` 파일 생성 및 API 키 설정
- [ ] 검증 스크립트 실행 성공

---

## 0.7 다음 Phase 미리보기

**Phase 1: 데이터 탐색**에서는:
- PDF 3개를 직접 열어보고
- 어떤 정보가 어디에 있는지 파악하고
- 추출할 데이터를 계획합니다

---

*이 문서를 따라하다 막히는 부분이 있으면 바로 질문해주세요!*
