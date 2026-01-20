# Phase 2: PDF 파싱 및 텍스트 추출

> **목표:** PDF 문서에서 텍스트를 추출하고, 의미 단위로 청킹하여 저장한다.
>
> **왜 필요한가?** RAG 시스템은 텍스트 청크를 기반으로 검색하므로, PDF를 적절한 크기로 분할해야 한다.

---

## 1. 이번 Phase에서 배울 것

| 개념 | 설명 | 왜 필요한가? |
|------|------|-------------|
| **PDF 파싱** | PDF에서 텍스트 추출 | 원본 문서를 처리 가능한 형태로 변환 |
| **청킹(Chunking)** | 텍스트를 작은 단위로 분할 | LLM 컨텍스트 제한, 검색 정확도 향상 |
| **메타데이터** | 청크에 부가 정보 추가 | 검색 시 필터링, 출처 추적 |
| **데이터 클래스** | Python dataclass 사용 | 구조화된 데이터 관리 |

---

## 2. 다룰 파일들과 역할

```
ur5e-ontology-rag/
│
├── src/
│   └── ingestion/              ← [신규] 데이터 수집/처리 모듈
│       ├── __init__.py         ← 패키지 초기화
│       ├── pdf_parser.py       ← [1] PDF 파싱 클래스
│       ├── chunker.py          ← [2] 청킹 로직
│       └── models.py           ← [3] 데이터 모델 (dataclass)
│
├── data/
│   ├── raw/pdf/                ← 원본 PDF (입력)
│   └── processed/              ← [신규] 처리된 데이터 (출력)
│       └── chunks/             ← 청크 JSON 파일들
│
└── scripts/
    └── run_ingestion.py        ← [4] 실행 스크립트
```

### 각 파일의 역할

| 번호 | 파일 | 역할 | 왜 필요? |
|------|------|------|----------|
| **1** | `pdf_parser.py` | PDF → 텍스트 추출 | PyMuPDF로 페이지별 텍스트 추출 |
| **2** | `chunker.py` | 텍스트 → 청크 분할 | 의미 단위로 분할, 오버랩 처리 |
| **3** | `models.py` | 데이터 구조 정의 | Chunk, Document 등 타입 정의 |
| **4** | `run_ingestion.py` | 전체 파이프라인 실행 | PDF → 청크 → 저장 한 번에 실행 |

---

## 3. Phase 2 진행 순서

```
Step 1: 데이터 모델 정의 (models.py)
   └─▶ Document, Chunk 클래스 정의
   └─▶ 메타데이터 구조 설계

Step 2: PDF 파서 구현 (pdf_parser.py)
   └─▶ PyMuPDF로 텍스트 추출
   └─▶ 페이지별 메타데이터 추출

Step 3: 청커 구현 (chunker.py)
   └─▶ 문서별 청킹 전략 적용
   └─▶ 오버랩 처리

Step 4: 실행 스크립트 (run_ingestion.py)
   └─▶ 전체 파이프라인 연결
   └─▶ JSON 파일로 저장

Step 5: 테스트 및 검증
   └─▶ 3개 PDF 모두 처리
   └─▶ 청크 품질 확인
```

---

## 4. 청킹 전략 (Phase 1 분석 기반)

### 4.1 문서별 전략

| 문서 | 청킹 단위 | 방법 |
|------|----------|------|
| **ErrorCodes.pdf** | 에러 코드별 | TOC 기반 분할 (C0, C1, C2...) |
| **Service Manual** | 절차/섹션별 | 제목 패턴 기반 분할 |
| **User Manual** | 기능/섹션별 | 제목 패턴 기반 분할 |

### 4.2 청킹 파라미터 (예상)

```yaml
chunking:
  default:
    chunk_size: 1000        # 기본 청크 크기 (문자)
    chunk_overlap: 200      # 오버랩 크기

  error_codes:
    strategy: "toc_based"   # TOC 기반 분할

  manuals:
    strategy: "section_based"  # 섹션 기반 분할
    section_pattern: "^\\d+\\.\\d*\\s+"  # "1.2. 제목" 패턴
```

### 4.3 청크 구조 (예상)

```python
@dataclass
class Chunk:
    id: str                    # 고유 ID (예: "error_codes_C1_001")
    content: str               # 청크 텍스트
    metadata: dict             # 메타데이터
    # metadata 예시:
    # {
    #     "source": "ErrorCodes.pdf",
    #     "page": 12,
    #     "section": "C1 Outbuffer overflow",
    #     "doc_type": "error_code"
    # }
```

---

## 5. 예상 출력 형태

### 5.1 처리된 청크 (JSON)

```json
{
  "id": "error_codes_C1_001",
  "content": "C1 Outbuffer overflow\nC1A1 Buffer of stored warnings overflowed...",
  "metadata": {
    "source": "ErrorCodes.pdf",
    "page": 12,
    "section": "C1",
    "error_code": "C1",
    "doc_type": "error_code"
  }
}
```

### 5.2 파일 구조

```
data/processed/chunks/
├── error_codes_chunks.json     ← ErrorCodes.pdf 청크들
├── service_manual_chunks.json  ← Service Manual 청크들
└── user_manual_chunks.json     ← User Manual 청크들
```

---

## 6. 핵심 코드 구조 (계획)

### 6.1 models.py

```python
from dataclasses import dataclass
from typing import Optional, Dict, List

@dataclass
class Document:
    """PDF 문서를 표현하는 클래스"""
    filename: str
    pages: List[str]       # 페이지별 텍스트
    metadata: Dict

@dataclass
class Chunk:
    """청크를 표현하는 클래스"""
    id: str
    content: str
    metadata: Dict
```

### 6.2 pdf_parser.py

```python
class PDFParser:
    """PDF 파싱 클래스"""

    def parse(self, pdf_path: str) -> Document:
        """PDF를 Document 객체로 변환"""
        pass

    def extract_text(self, pdf_path: str) -> List[str]:
        """페이지별 텍스트 추출"""
        pass
```

### 6.3 chunker.py

```python
class Chunker:
    """청킹 클래스"""

    def chunk_document(self, document: Document) -> List[Chunk]:
        """문서를 청크로 분할"""
        pass

    def chunk_by_toc(self, document: Document) -> List[Chunk]:
        """TOC 기반 청킹 (ErrorCodes용)"""
        pass

    def chunk_by_section(self, document: Document) -> List[Chunk]:
        """섹션 기반 청킹 (Manual용)"""
        pass
```

---

## 7. 완료 조건 (체크리스트)

- [ ] `src/ingestion/` 폴더 구조 생성
- [ ] `models.py` - Document, Chunk 클래스 구현
- [ ] `pdf_parser.py` - PDF 텍스트 추출 구현
- [ ] `chunker.py` - 청킹 로직 구현
- [ ] `run_ingestion.py` - 실행 스크립트 구현
- [ ] ErrorCodes.pdf 청킹 테스트
- [ ] Service Manual 청킹 테스트
- [ ] User Manual 청킹 테스트
- [ ] 청크 JSON 파일 생성 확인
- [ ] 청크 품질 검증 (내용, 크기, 메타데이터)

---

## 8. 예상 어려움 및 해결 방안

| 예상 어려움 | 해결 방안 |
|------------|----------|
| PDF 텍스트 추출 품질 | PyMuPDF 옵션 조정, 후처리 |
| 청크 경계 결정 | 섹션 패턴 정규식, TOC 활용 |
| 메타데이터 추출 | 정규식으로 에러코드, 섹션명 파싱 |
| 이미지 내 텍스트 | 이번 Phase에서는 제외 (OCR 필요) |

---

## 9. 참고: Phase 1에서 발견한 패턴

### ErrorCodes.pdf
```
1.1. C0 No error
1.2. C1 Outbuffer overflow
C1A1 Buffer of stored warnings overflowed
```

### Service Manual
```
5.2.12. Dual Robot Calibration
Description
...
NOTICE
...
```

### User Manual
```
11.2. Move Robot into Position
Description
...
```
