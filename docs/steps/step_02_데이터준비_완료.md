# Step 02: 데이터 준비 - 완료 보고서

## 1. 요약

| 항목 | 내용 |
|------|------|
| Phase | 02 - 데이터 준비 (Data Preparation) |
| 상태 | **완료** |
| 시작일 | 2026-01-22 |
| 완료일 | 2026-01-22 |
| 리팩토링일 | 2026-01-22 |
| 작업자 | Claude Code |

---

## 2. 완료된 작업

### 2.1 구현 파일 목록

| 파일 | 라인 수 | 상태 | 설명 |
|------|--------|------|------|
| `src/ingestion/__init__.py` | 130 | 신규 작성 | 패키지 초기화 및 유틸리티 |
| `src/ingestion/models.py` | 130 | 신규 작성 | Chunk, Document, Manifest 모델 |
| `src/ingestion/pdf_parser.py` | 145 | 신규 작성 | PDF 텍스트 추출 |
| `src/ingestion/chunker.py` | 140 | 신규 작성 | 텍스트 청킹 |
| `data/processed/metadata/manifest.json` | - | 신규 생성 | 문서 메타데이터 |

### 2.2 기존 데이터 확인

| 파일 | 내용 | 상태 |
|------|------|------|
| `data/raw/pdf/*.pdf` | 원본 PDF 3종 | 존재 확인 |
| `data/processed/chunks/user_manual_chunks.json` | 426 chunks | 존재 확인 |
| `data/processed/chunks/service_manual_chunks.json` | 197 chunks | 존재 확인 |
| `data/processed/chunks/error_codes_chunks.json` | 99 chunks | 존재 확인 |
| `data/sensor/raw/axia80_week_01.parquet` | 604,800 records | 존재 확인 |

### 2.3 테스트 결과

```python
>>> from src.ingestion import load_all_chunks, load_manifest
>>> chunks = load_all_chunks()
>>> print(f'Total chunks: {len(chunks)}')
Total chunks: 722

>>> manifest = load_manifest()
>>> print(manifest.totals)
{'documents': 3, 'chunks': 722}
```

---

## 3. 구현 상세

### 3.1 데이터 모델 (models.py)

```python
@dataclass
class ChunkMetadata:
    source: str           # 원본 파일명
    page: int             # 페이지 번호
    doc_type: str         # 문서 타입
    section: Optional[str]     # 섹션명
    chapter: Optional[str]     # 챕터명
    error_code: Optional[str]  # 에러 코드 (error_codes용)
    extra: Dict[str, Any]      # 추가 필드

@dataclass
class Chunk:
    id: str               # 청크 ID
    content: str          # 청크 텍스트
    metadata: ChunkMetadata

@dataclass
class Manifest:
    version: str
    created_at: str
    documents: Dict[str, Dict]
    totals: Dict[str, int]
    settings: Dict[str, Any]
```

### 3.2 PDF 파서 (pdf_parser.py)

- PyMuPDF (fitz) 기반 텍스트 추출
- 문서 타입 자동 감지 (user_manual, service_manual, error_codes)
- 섹션/챕터 정보 추출

### 3.3 청커 (chunker.py)

- 설정 기반 청크 크기/오버랩 (settings.yaml)
- 문장 경계 인식 분할
- 메타데이터 자동 부여

### 3.4 manifest.json 구조

```json
{
  "version": "1.0",
  "created_at": "2026-01-22T...",
  "documents": {
    "user_manual": {
      "source": "710-965-00_UR5e_User_Manual_en_Global.pdf",
      "chunks_file": "user_manual_chunks.json",
      "chunk_count": 426,
      "total_pages": 248,
      "topics": ["safety", "operation", "installation"]
    },
    "service_manual": {...},
    "error_codes": {...}
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

## 4. 데이터 통계

### 4.1 문서별 청크 수

| 문서 | 청크 수 | 비율 |
|------|--------|------|
| user_manual | 426 | 59.0% |
| service_manual | 197 | 27.3% |
| error_codes | 99 | 13.7% |
| **합계** | **722** | **100%** |

### 4.2 센서 데이터

| 항목 | 값 |
|------|-----|
| 기간 | 7일 (604,800초) |
| 레코드 수 | 604,800 |
| 샘플링 | 1 Hz (1초 평균) |
| 파일 형식 | Parquet |
| 파일 크기 | 34.15 MB |

---

## 5. 아키텍처 정합성

### 5.1 Unified_ROADMAP.md 충족 사항

| ROADMAP 요구사항 | 구현 내용 | 상태 |
|-----------------|----------|------|
| PDF 3종 확보 | data/raw/pdf/*.pdf | O |
| 722 chunks | 426 + 197 + 99 = 722 | O |
| 센서 데이터 7일 | 604,800 records | O |
| 메타데이터 검증 | manifest.json 생성 | O |

### 5.2 Unified_Spec.md 충족 사항

| Spec 요구사항 | 구현 내용 | 상태 |
|--------------|----------|------|
| 문서 인덱싱용 청크 | JSON 형식 저장 | O |
| 메타데이터 포함 | source, page, doc_type | O |
| Knowledge Domain 연결 | Document 엔티티 정의 가능 | O |

### 5.3 온톨로지 스키마 연결점

```
Chunk.metadata.doc_type → Knowledge Domain: Document
Chunk.metadata.error_code → Knowledge Domain: ErrorCode
Chunk.id → DOCUMENTED_IN 관계 target
```

---

## 6. 폴더 구조

```
ur5e-ontology-rag/
├── data/
│   ├── raw/
│   │   └── pdf/
│   │       ├── 710-965-00_UR5e_User_Manual_en_Global.pdf
│   │       ├── e-Series_Service_Manual_en.pdf
│   │       └── ErrorCodes.pdf
│   │
│   ├── processed/
│   │   ├── chunks/
│   │   │   ├── user_manual_chunks.json (426)
│   │   │   ├── service_manual_chunks.json (197)
│   │   │   └── error_codes_chunks.json (99)
│   │   │
│   │   └── metadata/
│   │       └── manifest.json [신규]
│   │
│   └── sensor/
│       └── raw/
│           └── axia80_week_01.parquet (604,800)
│
└── src/
    └── ingestion/
        ├── __init__.py [신규]
        ├── models.py [신규]
        ├── pdf_parser.py [신규]
        └── chunker.py [신규]
```

---

## 7. 다음 단계 준비

### Phase 03 (문서 인덱싱)과의 연결

Phase 2 산출물이 Phase 3에서 사용되는 방식:

| Phase 2 산출물 | Phase 3 사용처 |
|---------------|---------------|
| `*_chunks.json` | ChromaDB 임베딩 대상 |
| `manifest.json` | 문서 목록 조회 |
| `Chunk.metadata` | ChromaDB 메타데이터 |

### 준비 사항

```python
# Phase 3에서 사용할 코드
from src.ingestion import load_all_chunks
from src.config import get_settings

settings = get_settings()
chunks = load_all_chunks()

# 임베딩 생성 대상
for chunk in chunks:
    text = chunk.content
    metadata = chunk.metadata.to_dict()
    # → OpenAI embedding 생성
    # → ChromaDB 저장
```

---

## 8. 이슈 및 참고사항

### 8.1 해결된 이슈

1. **ChunkMetadata 필드 불일치**: 기존 청크에 `error_code` 필드가 있어 모델에 추가
2. **extra 필드 추가**: 알 수 없는 추가 필드 처리를 위해 extra 딕셔너리 추가

### 8.2 권장 사항

1. **재처리 시**: `scripts/run_ingestion.py --force` 옵션으로 기존 청크 덮어쓰기 가능
2. **청크 설정 변경 시**: `configs/settings.yaml`의 `document.chunk_size/overlap` 수정 후 재처리

---

## 9. 리팩토링 수행 내역

### 9.1 설계서 업데이트 (v1.0 → v2.0)

| 추가/변경 섹션 | 내용 |
|---------------|------|
| 구현 상태 업데이트 | "신규 작성" → "완료됨" 상태 반영 |
| ChunkMetadata 필드 | `error_code`, `extra` 필드 추가 |
| 검증 명령어 수정 | 실제 테스트 코드와 일치하도록 수정 |
| 온톨로지 연결 상세화 | Knowledge Domain 연결점 명시 |

### 9.2 코드 업데이트

| 파일 | 변경 내용 |
|------|----------|
| `src/ingestion/__init__.py` | `load_manifest`, `save_manifest`를 `__all__`에 추가 |

### 9.3 검증 결과

```python
>>> from src.ingestion import load_all_chunks, load_manifest
>>> chunks = load_all_chunks()
>>> print(f'Total chunks: {len(chunks)}')
Total chunks: 722

>>> manifest = load_manifest()
>>> print(f'Version: {manifest.version}')
Version: 1.0
>>> print(f'Totals: {manifest.totals}')
Totals: {'documents': 3, 'chunks': 722}
```

모든 검증 테스트 통과 확인.

---

## 10. 문서 정보

| 항목 | 값 |
|------|---|
| 문서 버전 | v2.0 (리팩토링 완료) |
| 작성일 | 2026-01-22 |
| 리팩토링일 | 2026-01-22 |
| 설계서 참조 | [step_02_데이터준비_설계.md](step_02_데이터준비_설계.md) |
| ROADMAP 섹션 | A.2 Phase 2 |
| Spec 섹션 | Section 8 |

---

*Phase 02 완료. Phase 03 (문서 인덱싱)으로 진행합니다.*
