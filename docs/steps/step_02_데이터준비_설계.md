# Step 02: 데이터 준비 - 설계서

## 1. 개요

### 1.1 Phase 정보
- **Phase 번호**: 02
- **Phase 명**: 데이터 준비 (Data Preparation)
- **Stage**: Stage 1 - 데이터 기반 (Data Foundation)
- **목표**: 원천 데이터 확보 및 전처리

### 1.2 Phase 목표 (Unified_ROADMAP.md 기준)
- PDF 문서 3종 확보 (완료됨)
- PDF → 텍스트 청킹 (완료됨: 722 chunks)
- 센서 데이터 확인 (완료됨: 7일, 604,800 레코드)
- 메타데이터 검증 및 manifest.json 생성
- 재현 가능한 ingestion 코드 작성

### 1.3 핵심 산출물
- `data/processed/chunks/*.json` (722 chunks)
- `data/sensor/raw/axia80_week_01.parquet` (604,800 records)
- `data/processed/metadata/manifest.json`
- `src/ingestion/` 모듈 (재현 가능한 코드)

---

## 2. 다룰 파일

### 2.1 핵심 구현 파일

| 파일 경로 | 역할 | 상태 |
|-----------|------|------|
| `src/ingestion/__init__.py` | 패키지 초기화 | 작성 필요 |
| `src/ingestion/models.py` | Document, Chunk 데이터 모델 | 신규 작성 |
| `src/ingestion/pdf_parser.py` | PDF 텍스트 추출 | 신규 작성 |
| `src/ingestion/chunker.py` | 문서 청킹 | 신규 작성 |
| `scripts/run_ingestion.py` | 데이터 수집 스크립트 | 신규 작성 |

### 2.2 데이터 파일 (기존)

| 파일 경로 | 설명 | 상태 |
|-----------|------|------|
| `data/raw/pdf/710-965-00_UR5e_User_Manual_en_Global.pdf` | UR5e 사용자 매뉴얼 | 존재 |
| `data/raw/pdf/e-Series_Service_Manual_en.pdf` | 서비스 매뉴얼 | 존재 |
| `data/raw/pdf/ErrorCodes.pdf` | 에러 코드 디렉토리 | 존재 |
| `data/processed/chunks/user_manual_chunks.json` | 426 chunks | 존재 |
| `data/processed/chunks/service_manual_chunks.json` | 197 chunks | 존재 |
| `data/processed/chunks/error_codes_chunks.json` | 99 chunks | 존재 |
| `data/sensor/raw/axia80_week_01.parquet` | 604,800 records | 존재 |

### 2.3 메타데이터 파일

| 파일 경로 | 역할 | 상태 |
|-----------|------|------|
| `data/processed/metadata/manifest.json` | 문서 메타데이터 | 신규 작성 |

---

## 3. 설계 상세

### 3.1 데이터 파이프라인 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                   Data Ingestion Pipeline                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   data/raw/pdf/                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │  user_manual.pdf  service_manual.pdf  error_codes.pdf│  │
│   └──────────────────────────┬──────────────────────────┘  │
│                              │                              │
│                              ▼                              │
│   ┌─────────────────────────────────────────────────────┐  │
│   │              src/ingestion/pdf_parser.py             │  │
│   │                                                      │  │
│   │   PyMuPDF (fitz)를 사용하여 PDF → 텍스트 추출       │  │
│   │   - 페이지별 텍스트 추출                            │  │
│   │   - 메타데이터 추출 (제목, 페이지 수 등)            │  │
│   └──────────────────────────┬──────────────────────────┘  │
│                              │                              │
│                              ▼                              │
│   ┌─────────────────────────────────────────────────────┐  │
│   │              src/ingestion/chunker.py                │  │
│   │                                                      │  │
│   │   텍스트를 의미 있는 청크로 분할                    │  │
│   │   - chunk_size: 512 (settings.yaml)                 │  │
│   │   - chunk_overlap: 50 (settings.yaml)               │  │
│   │   - 섹션/챕터 기반 분할 우선                        │  │
│   └──────────────────────────┬──────────────────────────┘  │
│                              │                              │
│                              ▼                              │
│   data/processed/chunks/                                    │
│   ┌─────────────────────────────────────────────────────┐  │
│   │  user_manual_chunks.json (426)                       │  │
│   │  service_manual_chunks.json (197)                    │  │
│   │  error_codes_chunks.json (99)                        │  │
│   │                                                      │  │
│   │  Total: 722 chunks                                   │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 데이터 모델 (models.py)

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime

@dataclass
class DocumentMetadata:
    """문서 메타데이터"""
    source: str              # 원본 파일명
    doc_type: str           # user_manual, service_manual, error_codes
    total_pages: int        # 총 페이지 수
    created_at: datetime    # 처리 시간

@dataclass
class ChunkMetadata:
    """청크 메타데이터"""
    source: str             # 원본 파일명
    page: int               # 페이지 번호
    doc_type: str           # 문서 타입
    section: Optional[str]  # 섹션명
    chapter: Optional[str]  # 챕터명
    error_code: Optional[str]  # 에러 코드 (error_codes 문서용)
    extra: Dict[str, Any]   # 추가 필드 (확장성)

@dataclass
class Chunk:
    """문서 청크"""
    id: str                 # 청크 ID (user_manual_000)
    content: str            # 청크 텍스트
    metadata: ChunkMetadata # 메타데이터

@dataclass
class Document:
    """처리된 문서"""
    id: str                    # 문서 ID
    metadata: DocumentMetadata # 문서 메타데이터
    chunks: List[Chunk]        # 청크 목록
```

### 3.3 청크 구조 (기존 데이터 형식)

```json
{
  "id": "user_manual_000",
  "content": "1. Preface\nIntroduction\nCongratulations on...",
  "metadata": {
    "source": "710-965-00_UR5e_User_Manual_en_Global.pdf",
    "page": 1,
    "doc_type": "user_manual",
    "section": "Preface",
    "chapter": "1."
  }
}
```

### 3.4 manifest.json 구조

```json
{
  "version": "1.0",
  "created_at": "2026-01-22T00:00:00",
  "documents": {
    "user_manual": {
      "source": "710-965-00_UR5e_User_Manual_en_Global.pdf",
      "chunks_file": "user_manual_chunks.json",
      "chunk_count": 426,
      "total_pages": 248,
      "doc_type": "user_manual",
      "topics": ["safety", "operation", "installation"]
    },
    "service_manual": {
      "source": "e-Series_Service_Manual_en.pdf",
      "chunks_file": "service_manual_chunks.json",
      "chunk_count": 197,
      "total_pages": 120,
      "doc_type": "service_manual",
      "topics": ["maintenance", "repair", "troubleshooting"]
    },
    "error_codes": {
      "source": "ErrorCodes.pdf",
      "chunks_file": "error_codes_chunks.json",
      "chunk_count": 99,
      "total_pages": 45,
      "doc_type": "error_codes",
      "topics": ["error_codes", "diagnostics"]
    }
  },
  "totals": {
    "documents": 3,
    "chunks": 722
  },
  "settings": {
    "chunk_size": 512,
    "chunk_overlap": 50
  }
}
```

---

## 4. 온톨로지 연결

### 4.1 Knowledge Domain 연결

Phase 2에서 생성된 청크는 Knowledge Domain의 Document 엔티티와 연결됩니다.

```yaml
Document:
  instances:
    - id: "user_manual"
      source: "710-965-00_UR5e_User_Manual_en_Global.pdf"
      chunk_count: 426
      topics: [safety, operation, installation]

    - id: "service_manual"
      source: "e-Series_Service_Manual_en.pdf"
      chunk_count: 197
      topics: [maintenance, repair, troubleshooting]

    - id: "error_codes"
      source: "ErrorCodes.pdf"
      chunk_count: 99
      topics: [error_codes, diagnostics]
```

### 4.2 DOCUMENTED_IN 관계

에러 코드와 문서 간의 관계:

```
ErrorCode (C153) ──DOCUMENTED_IN──→ Document (user_manual#p145)
ErrorCode (C153) ──DOCUMENTED_IN──→ Document (service_manual#p67)
ErrorCode (C189) ──DOCUMENTED_IN──→ Document (service_manual#p45)
```

### 4.3 Phase 3 연결

Phase 2 청크가 Phase 3 (문서 인덱싱)에서 사용되는 방식:

```
Phase 2 청크 (.json)
        │
        ▼
Phase 3 임베딩 생성 (OpenAI text-embedding-3-small)
        │
        ▼
ChromaDB 벡터 저장 (stores/chroma/)
        │
        ▼
Phase 10-12 RAG 검색에서 활용
```

---

## 5. Unified_Spec.md 정합성 검증

### 5.1 데이터 흐름 요구사항

| Spec 요구사항 | Phase 2 구현 내용 | 충족 여부 |
|--------------|------------------|----------|
| PDF → 텍스트 추출 | PyMuPDF 사용 | O |
| 722 chunks | 426 + 197 + 99 = 722 | O |
| 메타데이터 포함 | source, page, doc_type 포함 | O |
| Knowledge Domain 연결 | Document 엔티티 정의 | O |

### 5.2 센서 데이터 요구사항

| Spec 요구사항 | Phase 2 구현 내용 | 충족 여부 |
|--------------|------------------|----------|
| 7일 데이터 | 604,800 records | O |
| Parquet 형식 | axia80_week_01.parquet | O |
| 125Hz 샘플링 | 원본 125Hz 미포함(1Hz 다운샘플/요약만 저장) | △ |

---

## 6. 구현 체크리스트

### 6.1 데이터 확인 (완료됨)

- [x] PDF 3종 존재 확인
- [x] 청크 722개 존재 확인
- [x] 센서 데이터 604,800 레코드 확인

### 6.2 코드 구현 (완료됨)

- [x] `src/ingestion/models.py` - 데이터 모델 (130줄)
- [x] `src/ingestion/pdf_parser.py` - PDF 파서 (145줄)
- [x] `src/ingestion/chunker.py` - 청커 (140줄)
- [x] `src/ingestion/__init__.py` - 패키지 초기화 (130줄)
- [x] `scripts/run_ingestion.py` - 실행 스크립트 (기존)

### 6.3 메타데이터 생성 (완료됨)

- [x] `data/processed/metadata/manifest.json`

### 6.4 검증 명령어 (ROADMAP 기준)

```python
# 청크 수 검증
from src.ingestion import load_all_chunks
chunks = load_all_chunks()
assert len(chunks) == 722  # 426 + 197 + 99

# 메타데이터 검증
from src.ingestion import load_manifest
manifest = load_manifest()
assert manifest.totals['chunks'] == 722

# 센서 데이터 검증
import pandas as pd
df = pd.read_parquet('data/sensor/raw/axia80_week_01.parquet')
assert len(df) == 604800

# (선택) 통합 검증 스크립트
# python scripts/run_ingestion.py --mode validate
```

---

## 7. 설계 결정 사항

### 7.1 PyMuPDF 선택

**결정**: PDF 파싱에 PyMuPDF (fitz) 사용

**근거**:
1. 성능: C 기반으로 빠른 처리
2. 품질: 레이아웃 보존 텍스트 추출
3. 메타데이터: 페이지, 섹션 정보 추출 용이
4. 라이선스: AGPL (오픈소스 프로젝트 호환)

### 7.2 청킹 전략

**결정**: 고정 크기 + 오버랩 + 섹션 경계 고려

**근거**:
1. chunk_size=512: 임베딩 모델 최적화
2. chunk_overlap=50: 문맥 연속성 유지
3. 섹션 경계: 의미적 단위 보존

### 7.3 JSON 저장 형식

**결정**: 청크를 JSON 배열로 저장

**근거**:
1. 가독성: 사람이 읽기 쉬움
2. 호환성: 다양한 도구에서 처리 가능
3. 메타데이터: 구조화된 메타데이터 포함 용이

---

## 8. 다음 Phase 연결

### Phase 03 (문서 인덱싱)과의 연결

Phase 2에서 생성한 청크가 Phase 3에서 사용되는 방식:

| Phase 2 산출물 | Phase 3 사용처 |
|---------------|---------------|
| `*_chunks.json` | 임베딩 생성 대상 |
| `manifest.json` | 문서 목록 조회 |
| Chunk.metadata | ChromaDB 메타데이터 |

### Phase 4-5 (온톨로지)와의 연결

| Phase 2 산출물 | Phase 4-5 사용처 |
|---------------|-----------------|
| Document 메타데이터 | Knowledge Domain Document 엔티티 |
| Chunk.doc_type | DOCUMENTED_IN 관계 생성 |

---

*작성일: 2026-01-22*
*Phase: 02 - 데이터 준비*
*문서 버전: v1.0*
