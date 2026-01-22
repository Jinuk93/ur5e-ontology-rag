# Phase 2: PDF 파싱 & 청킹

> **상태**: ✅ 완료
> **도메인**: 데이터 레이어 (Data)
> **목표**: PDF 문서를 검색 가능한 텍스트 청크로 변환

---

## 1. 개요

PyMuPDF를 사용하여 PDF 문서에서 텍스트를 추출하고,
적절한 크기의 청크로 분할하여 벡터 검색에 최적화된 형태로 저장하는 단계.

---

## 2. 태스크

| # | 태스크 | 상태 |
|---|--------|------|
| 1 | PyMuPDF로 텍스트 추출 | ✅ |
| 2 | 페이지별/섹션별 분리 | ✅ |
| 3 | 청킹 전략 정의 및 구현 | ✅ |
| 4 | 메타데이터 기록 (doc_id, page 등) | ✅ |
| 5 | JSON 형식으로 저장 | ✅ |

---

## 3. 청킹 전략

### 3.1 파라미터

| 파라미터 | 값 | 설명 |
|----------|-----|------|
| chunk_size | 500 | 청크당 최대 문자 수 |
| overlap | 50 | 청크 간 중첩 문자 수 |
| separator | 문장 경계 | 문장 단위로 분할 시도 |

### 3.2 전략 설명

```
┌─────────────────────────────────────────────────────┐
│ 원본 텍스트 (전체)                                    │
├─────────────────────────────────────────────────────┤
│ [Chunk 1: 500자]                                     │
│     └──[50자 overlap]──┐                            │
│                        ├──[Chunk 2: 500자]          │
│                        │      └──[50자 overlap]──┐  │
│                        │                         │  │
│                        │         [Chunk 3: 500자]│  │
└─────────────────────────────────────────────────────┘
```

### 3.3 설계 이유

- **500자**: 문맥 충분 + LLM 토큰 효율적
- **50자 overlap**: 문장 중간 잘림 방지
- **문장 경계**: 의미 단위 보존

---

## 4. 구현

### 4.1 핵심 코드

**PDF 파서** (`src/ingestion/pdf_parser.py`):
```python
import fitz  # PyMuPDF

class PDFParser:
    def parse(self, pdf_path: str) -> List[PageContent]:
        """PDF에서 페이지별 텍스트 추출"""
        doc = fitz.open(pdf_path)
        pages = []
        for page_num, page in enumerate(doc):
            text = page.get_text("text")
            pages.append(PageContent(
                page_num=page_num + 1,
                text=text,
                doc_id=self._generate_doc_id(pdf_path)
            ))
        return pages
```

**청킹 모듈** (`src/ingestion/chunker.py`):
```python
class Chunker:
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str, metadata: dict) -> List[Chunk]:
        """텍스트를 청크로 분할"""
        chunks = []
        sentences = self._split_sentences(text)

        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= self.chunk_size:
                current_chunk += sentence
            else:
                chunks.append(self._create_chunk(current_chunk, metadata))
                # overlap 적용
                current_chunk = current_chunk[-self.overlap:] + sentence

        return chunks
```

### 4.2 청크 스키마

```json
{
  "chunk_id": "service_manual_p042_c003",
  "doc_id": "service_manual",
  "page": 42,
  "chunk_index": 3,
  "text": "청크 텍스트 내용...",
  "metadata": {
    "source": "UR5e Service Manual",
    "section": "Troubleshooting"
  }
}
```

---

## 5. 산출물

### 5.1 파일 목록

| 파일 | 내용 | 크기/개수 |
|------|------|----------|
| `data/processed/chunks/service_manual_chunks.json` | Service Manual 청크 | 400+ 청크 |
| `data/processed/chunks/error_codes_chunks.json` | Error Codes 청크 | 150+ 청크 |
| `data/processed/chunks/user_manual_chunks.json` | User Manual 청크 | 170+ 청크 |
| `src/ingestion/pdf_parser.py` | PDF 파서 | ~100 lines |
| `src/ingestion/chunker.py` | 청킹 모듈 | ~150 lines |

### 5.2 통계

| 문서 | 페이지 | 청크 수 | 평균 청크 길이 |
|------|--------|---------|---------------|
| Service Manual | ~300 | 405 | 487자 |
| Error Codes | ~50 | 152 | 456자 |
| User Manual | ~200 | 165 | 478자 |
| **총계** | - | **722** | 475자 |

---

## 6. 검증 체크리스트

- [x] PDF 3개 모두 파싱 성공
- [x] 총 청크 수 700개 이상
- [x] 청크당 평균 길이 400~500자
- [x] 메타데이터 (doc_id, page, chunk_index) 포함
- [x] JSON 형식 유효성 검증

---

## 7. 다음 단계

→ [Phase 03: 벡터 인덱싱](03_벡터인덱싱.md)

---

**Phase**: 2 / 19
**작성일**: 2026-01-22
