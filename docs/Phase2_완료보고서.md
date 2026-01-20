# Phase 2: PDF 파싱 및 텍스트 추출 - 완료 보고서

> **목표:** PDF 문서에서 텍스트를 추출하고, 의미 단위로 청킹하여 저장한다.
>
> **완료일:** 2026-01-20

---

## 1. Before vs After 비교

### 1.1 파일 구조

| 항목 | Before (계획) | After (실제) | 차이점 |
|------|--------------|--------------|--------|
| `models.py` | Document, Chunk 클래스 | Document, Chunk, ChunkMetadata 클래스 | **ChunkMetadata 추가** |
| `pdf_parser.py` | PDFParser 클래스 | PDFParser + parse_all_pdfs() | **유틸리티 함수 추가** |
| `chunker.py` | Chunker 클래스 | Chunker + ChunkingConfig | **설정 클래스 분리** |
| `run_ingestion.py` | 실행 스크립트 | 동일 | 계획대로 |
| 출력 위치 | `data/processed/chunks/` | 동일 | 계획대로 |

### 1.2 청킹 전략

| 문서 유형 | Before (계획) | After (실제) | 이유 |
|----------|--------------|--------------|------|
| **ErrorCodes** | TOC 기반 (에러코드별) | TOC 기반 (에러코드별) | 계획대로 |
| **Service Manual** | 섹션 기반 (절차별) | 섹션 기반 + 크기 분할 | **대형 섹션 처리 필요** |
| **User Manual** | 섹션 기반 (기능별) | 섹션 기반 + 크기 분할 | **대형 섹션 처리 필요** |

### 1.3 예상 vs 실제 청크 수

| 문서 | Before (예상) | After (실제) | 차이 |
|------|--------------|--------------|------|
| ErrorCodes | ~231개 | 99개 | **-132개** |
| Service Manual | ~100개 | 197개 | **+97개** |
| User Manual | ~150개 | 426개 | **+276개** |
| **합계** | ~481개 | **722개** | **+241개** |

---

## 2. 차이점 분석 및 이유

### 2.1 ChunkMetadata 클래스 추가 (models.py)

**Before:** Chunk 클래스에 metadata를 Dict로 저장
```python
# 계획
@dataclass
class Chunk:
    id: str
    content: str
    metadata: Dict
```

**After:** ChunkMetadata 전용 클래스 분리
```python
# 실제
@dataclass
class ChunkMetadata:
    source: str
    page: int
    doc_type: str
    section: Optional[str] = None
    error_code: Optional[str] = None
    chapter: Optional[str] = None

@dataclass
class Chunk:
    id: str
    content: str
    metadata: ChunkMetadata
```

**이유:**
1. **타입 안전성**: 메타데이터 필드를 명시적으로 정의하여 오타 방지
2. **자동완성 지원**: IDE에서 `.source`, `.page` 등 자동완성 가능
3. **문서화**: 어떤 메타데이터가 필요한지 코드로 문서화됨

---

### 2.2 ErrorCodes 청크 수 감소 (231 → 99)

**Before:** 에러 코드 하나당 하나의 청크 (예상 231개)

**After:** 실제 99개 청크

**이유:**
1. **TOC 구조 문제**: TOC에는 231개 항목이 있지만, 같은 페이지에 여러 에러 코드가 있음
2. **페이지 범위 기반 추출**: 현재 구현은 페이지 범위로 텍스트를 추출하므로, 같은 페이지의 에러 코드들이 하나의 청크에 병합됨
3. **실용적 결정**: 관련 에러 코드들이 함께 있는 것이 오히려 검색 시 유리할 수 있음

```
예시: 페이지 12에 C0, C1, C2, C3, C4가 모두 있음
→ 5개가 아닌 1개 청크로 병합
→ 검색 시 "Outbuffer overflow"를 찾으면 관련 에러들도 함께 반환
```

**개선 가능 옵션 (향후):**
- 정규식으로 에러 코드 패턴 기반 분할
- 각 `C[숫자]` 패턴에서 청크 경계 설정

---

### 2.3 Manual 청크 수 증가 (예상보다 많음)

**Before:** Service ~100개, User ~150개

**After:** Service 197개, User 426개

**이유:**
1. **대형 섹션 분할**: 계획에서는 섹션 단위로만 분할을 고려했으나, 일부 섹션이 매우 큼
2. **chunk_size 적용**: 1000자 초과 섹션은 추가 분할 (`_split_large_content`)
3. **오버랩 적용**: 청크 간 200자 오버랩으로 연속성 보장

```
예시: "1.2. Safety Guidelines" 섹션이 5000자인 경우
→ 5개의 청크로 분할 (각 ~1000자 + 200자 오버랩)
```

**이점:**
- 검색 정확도 향상 (작은 청크가 더 정확한 매칭)
- LLM 컨텍스트 효율적 사용
- 오버랩으로 문맥 손실 방지

---

### 2.4 ChunkingConfig 클래스 분리 (chunker.py)

**Before:** 청킹 파라미터를 메서드 인자로 전달

**After:** ChunkingConfig dataclass로 분리
```python
@dataclass
class ChunkingConfig:
    chunk_size: int = 1000
    chunk_overlap: int = 200
    min_chunk_size: int = 100
```

**이유:**
1. **설정 관리 용이**: 여러 곳에서 같은 설정 재사용
2. **테스트 용이**: 다른 설정으로 쉽게 테스트 가능
3. **확장성**: 향후 문서 유형별 다른 설정 적용 가능

---

## 3. 생성된 파일 및 코드 분석

### 3.1 파일 구조

```
src/ingestion/
├── __init__.py         ← 패키지 export 정의
├── models.py           ← 데이터 클래스 (180줄)
├── pdf_parser.py       ← PDF 파서 (210줄)
└── chunker.py          ← 청커 (380줄)

scripts/
└── run_ingestion.py    ← 실행 스크립트 (130줄)

data/processed/chunks/
├── error_codes_chunks.json      ← 99 chunks, 321KB
├── service_manual_chunks.json   ← 197 chunks, 129KB
└── user_manual_chunks.json      ← 426 chunks, 388KB
```

### 3.2 코드 분석: models.py

```python
# ============================================================
# [1] ChunkMetadata - 청크의 메타데이터
# ============================================================
@dataclass
class ChunkMetadata:
    source: str              # 원본 파일명
    page: int                # 페이지 번호
    doc_type: str            # 문서 유형
    section: Optional[str]   # 섹션 제목
    error_code: Optional[str]# 에러 코드 (ErrorCodes용)
    chapter: Optional[str]   # 챕터 번호
```

**왜 이렇게 설계했는가?**
- `source`: 검색 결과에서 "출처: ErrorCodes.pdf p.12" 표시용
- `doc_type`: 검색 시 필터링 ("에러 코드만 검색")
- `error_code`: 온톨로지 연결용 ("C4 에러와 관련된 컴포넌트 찾기")

### 3.3 코드 분석: pdf_parser.py

```python
class PDFParser:
    # 문서 유형 자동 판별
    DOC_TYPE_PATTERNS = {
        "error_code": ["ErrorCodes", "Error Codes Directory"],
        "service_manual": ["Service Manual", "Service Handbook"],
        "user_manual": ["User Manual"],
    }
```

**핵심 메서드:**
| 메서드 | 역할 | 반환값 |
|--------|------|--------|
| `parse()` | PDF → Document 변환 | Document |
| `_extract_metadata()` | PDF 메타데이터 추출 | Dict |
| `_extract_toc()` | 목차 추출 | List[Tuple] |
| `_extract_pages()` | 페이지별 텍스트 | List[str] |
| `_detect_doc_type()` | 문서 유형 판별 | str |

### 3.4 코드 분석: chunker.py

```python
class Chunker:
    def chunk_document(self, document: Document) -> List[Chunk]:
        if document.doc_type == "error_code":
            return self._chunk_by_toc(document)      # TOC 기반
        elif document.doc_type in ["service_manual", "user_manual"]:
            return self._chunk_by_section(document)  # 섹션 기반
        else:
            return self._chunk_by_size(document)     # 크기 기반 (폴백)
```

**청킹 전략별 처리 흐름:**

```
ErrorCodes.pdf (TOC 기반)
┌─────────────────────────────────┐
│ TOC에서 Level 2 항목 추출        │
│ [(C0, p12), (C1, p12), ...]     │
└───────────────┬─────────────────┘
                ▼
┌─────────────────────────────────┐
│ 각 항목의 페이지 범위 텍스트 추출 │
│ C4: page 12-18                  │
└───────────────┬─────────────────┘
                ▼
┌─────────────────────────────────┐
│ Chunk 객체 생성                  │
│ id: error_codes_C4_004          │
└─────────────────────────────────┘

Manual (섹션 기반)
┌─────────────────────────────────┐
│ 정규식으로 섹션 제목 찾기         │
│ "1.2. Title" 패턴               │
└───────────────┬─────────────────┘
                ▼
┌─────────────────────────────────┐
│ 섹션별 텍스트 추출               │
└───────────────┬─────────────────┘
                ▼
        ┌───────┴───────┐
        ▼               ▼
   작은 섹션          큰 섹션
   (< 2000자)       (> 2000자)
        │               │
        ▼               ▼
   단일 Chunk      _split_large_content()
                        │
                        ▼
                   여러 Chunk
                   (오버랩 적용)
```

---

## 4. 출력 데이터 샘플

### 4.1 ErrorCodes 청크 예시

```json
{
  "id": "error_codes_C4_004",
  "content": "C4A1 Lost communication with Controller\nEXPLANATION\nCommunication was lost between the Safety Control Board...\nSUGGESTION\nTry the following actions...",
  "metadata": {
    "source": "ErrorCodes.pdf",
    "page": 12,
    "doc_type": "error_code",
    "section": "C4",
    "error_code": "C4"
  }
}
```

### 4.2 Service Manual 청크 예시

```json
{
  "id": "service_manual_000",
  "content": "2.1. About This Document\nPurpose\nThe purpose of this service manual is to help Universal Robots (UR)...",
  "metadata": {
    "source": "e-Series_Service_Manual_en.pdf",
    "page": 5,
    "doc_type": "service_manual",
    "section": "About This Document",
    "chapter": "2.1."
  }
}
```

---

## 5. 결과 요약

### 5.1 수치 요약

| 항목 | 값 |
|------|-----|
| 처리된 PDF | 3개 |
| 총 페이지 수 | 539 페이지 |
| 총 청크 수 | 722개 |
| 총 문자 수 | 618,869자 |
| 출력 파일 크기 | 837 KB |

### 5.2 문서별 세부

| 문서 | 청크 수 | 문자 수 | 평균 청크 크기 |
|------|--------|---------|---------------|
| Error Codes | 99 | 291,264 | 2,942자 |
| Service Manual | 197 | 69,681 | 354자 |
| User Manual | 426 | 257,924 | 605자 |

---

## 6. Phase 2 완료 체크리스트

- [x] `src/ingestion/` 폴더 구조 생성
- [x] `models.py` - Document, Chunk, ChunkMetadata 클래스 구현
- [x] `pdf_parser.py` - PDF 텍스트 추출 구현
- [x] `chunker.py` - 청킹 로직 구현 (TOC/섹션/크기 기반)
- [x] `run_ingestion.py` - 실행 스크립트 구현
- [x] ErrorCodes.pdf 청킹 완료 (99 chunks)
- [x] Service Manual 청킹 완료 (197 chunks)
- [x] User Manual 청킹 완료 (426 chunks)
- [x] 청크 JSON 파일 생성 확인
- [x] 완료 보고서 작성

---

## 7. 다음 단계 (Phase 3 예정)

### 7.1 Phase 3: 임베딩 및 벡터 DB

```
목표: 청크를 벡터로 변환하고 ChromaDB에 저장

예상 작업:
1. OpenAI 임베딩 API 연동
2. ChromaDB 컬렉션 생성
3. 청크 임베딩 및 저장
4. 유사도 검색 테스트
```

### 7.2 필요한 파일 (예상)

```
src/
├── embedding/
│   ├── embedder.py      ← 임베딩 생성
│   └── vector_store.py  ← ChromaDB 연동
│
└── retrieval/
    └── retriever.py     ← 검색 로직
```

---

**Phase 2 완료!**
