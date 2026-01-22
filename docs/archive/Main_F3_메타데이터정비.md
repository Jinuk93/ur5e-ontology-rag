# Main-F3: 메타데이터 정비 상세 설계서

> **Phase**: Main-F3 (Foundation 개선 Phase 3)
> **목표**: 근거 추적을 위한 메타데이터 파일(sources.yaml, chunk_manifest.jsonl) 작성
> **선행 조건**: Main-F2 (Trace 시스템 완성) 완료
> **참조**: Main__Spec.md Section 5 / Foundation_Spec.md Section 4.4.3

---

## 1. 개요

### 1.1 배경 (Foundation의 문제점)

Foundation에서 근거 추적이 불완전한 상태:

```
data/processed/
├── chunks/
│   ├── error_codes_chunks.json      # 청크 파일 O
│   ├── service_manual_chunks.json
│   └── user_manual_chunks.json
├── metatdata/                       # 디렉토리 존재 (typo)
│   └── (비어 있음)                   # sources.yaml 없음!
└── ontology/
    ├── ontology.json
    └── lexicon.yaml
```

**문제점**:
1. `sources.yaml` 미구현 - 문서 출처/버전 정보 없음
2. `chunk_manifest.jsonl` 미구현 - 청크 → 문서 역추적 정확도 낮음
3. 현재 청크 metadata의 `page`가 추정값 (정확하지 않음)
4. citation 제시 시 "Service Manual p.45" 같은 정확한 참조 어려움
5. 문서 버전 관리/업데이트 추적 불가

### 1.2 현재 청크 구조 분석

```json
// 현재 error_codes_chunks.json 예시
{
  "id": "error_codes_C4_004",
  "content": "C4A15 Communication with joint 3 lost...",
  "metadata": {
    "source": "ErrorCodes.pdf",      // 파일명만
    "page": 12,                       // 추정값
    "doc_type": "error_code",
    "section": "C4",
    "error_code": "C4"
  }
}
```

**부족한 정보**:
- 문서 버전 (e.g., "5.12")
- 문서 발행일
- 정확한 문자 위치 (char_start, char_end)
- 섹션 계층 구조

### 1.3 목표

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Main-F3 목표                                      │
├─────────────────────────────────────────────────────────────────────┤
│ 1. sources.yaml: 문서 출처/버전/메타 정보 정의                       │
│ 2. chunk_manifest.jsonl: 모든 청크의 정확한 출처 매핑                │
│ 3. /evidence API에서 정확한 citation 반환                           │
│ 4. 미래 문서 업데이트 시 버전 추적 가능                              │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.4 핵심 가치

| 가치 | 설명 |
|------|------|
| **정확한 인용** | "Service Manual p.45, Section 5.2" 수준의 citation |
| **역추적 가능** | chunk_id → doc_id/page/section 즉시 조회 |
| **버전 관리** | 문서 업데이트 시 어떤 청크가 영향받는지 파악 |
| **신뢰성** | 사용자에게 정확한 근거 출처 제공 |

---

## 2. 파일 구조

### 2.1 목표 디렉토리 구조

```
data/processed/
├── chunks/
│   ├── error_codes_chunks.json
│   ├── service_manual_chunks.json
│   └── user_manual_chunks.json
│
├── metadata/                        # [Main-F3] 디렉토리명 수정 (typo 수정)
│   ├── sources.yaml                 # [Main-F3] 문서 출처 정보
│   └── chunk_manifest.jsonl         # [Main-F3] 청크 매핑 정보
│
└── ontology/
    ├── ontology.json
    └── lexicon.yaml
```

### 2.2 관련 코드 파일

```
src/
├── ingestion/
│   ├── models.py                    # ChunkMetadata 확장
│   └── chunker.py                   # manifest 생성 로직 추가
│
├── rag/
│   └── retriever.py                 # 메타데이터 조회 추가
│
└── api/
    └── services/
        └── metadata_service.py      # [Main-F3] 신규 생성
```

---

## 3. 상세 설계

### 3.1 sources.yaml 스키마

```yaml
# data/processed/metadata/sources.yaml
# 문서 출처 및 메타 정보 정의
# ============================================================

version: "1.0"
last_updated: "2024-01-21"

documents:
  # ---------------------------------------------------------
  # Error Codes Directory
  # ---------------------------------------------------------
  error_codes:
    doc_id: "error_codes"
    title: "Error Codes Directory"
    subtitle: "All Robots"
    version: "5.12"
    date: "2023-06"
    language: "en"
    pages: 45
    publisher: "Universal Robots A/S"
    copyright: "2009-2025"

    # 원본 파일 정보
    source_file: "ErrorCodes.pdf"
    file_hash: "sha256:abc123..."  # 무결성 검증용

    # 처리 정보
    processed_date: "2024-01-15"
    chunk_count: 99

    # 문서 URL (있는 경우)
    url: "https://www.universal-robots.com/download/?option=101202"

    # 섹션 구조
    sections:
      - id: "intro"
        title: "Introduction"
        page_start: 1
        page_end: 11
      - id: "error_codes"
        title: "Error Codes"
        page_start: 12
        page_end: 45

  # ---------------------------------------------------------
  # Service Manual
  # ---------------------------------------------------------
  service_manual:
    doc_id: "service_manual"
    title: "UR e-Series Service Manual"
    subtitle: "UR5e"
    version: "5.12"
    date: "2023-06"
    language: "en"
    pages: 328
    publisher: "Universal Robots A/S"
    copyright: "2009-2025"

    source_file: "ServiceManual.pdf"
    file_hash: "sha256:def456..."

    processed_date: "2024-01-15"
    chunk_count: 245

    url: "https://www.universal-robots.com/download/?option=101201"

    sections:
      - id: "safety"
        title: "Safety"
        page_start: 1
        page_end: 45
      - id: "installation"
        title: "Installation"
        page_start: 46
        page_end: 89
      - id: "maintenance"
        title: "Maintenance"
        page_start: 90
        page_end: 180
      - id: "troubleshooting"
        title: "Troubleshooting"
        page_start: 181
        page_end: 280
      - id: "specifications"
        title: "Specifications"
        page_start: 281
        page_end: 328

  # ---------------------------------------------------------
  # User Manual
  # ---------------------------------------------------------
  user_manual:
    doc_id: "user_manual"
    title: "UR5e User Manual"
    subtitle: "e-Series"
    version: "5.12"
    date: "2023-06"
    language: "en"
    pages: 256
    publisher: "Universal Robots A/S"
    copyright: "2009-2025"

    source_file: "UserManual.pdf"
    file_hash: "sha256:ghi789..."

    processed_date: "2024-01-15"
    chunk_count: 180

    url: "https://www.universal-robots.com/download/?option=101200"

    sections:
      - id: "overview"
        title: "Overview"
        page_start: 1
        page_end: 30
      - id: "operation"
        title: "Operation"
        page_start: 31
        page_end: 120
      - id: "programming"
        title: "Programming"
        page_start: 121
        page_end: 200
      - id: "safety"
        title: "Safety Features"
        page_start: 201
        page_end: 256

# ---------------------------------------------------------
# 메타 정보
# ---------------------------------------------------------
meta:
  total_documents: 3
  total_chunks: 524
  total_pages: 629
  index_version: "1.0"
  embedding_model: "text-embedding-3-small"
```

### 3.2 chunk_manifest.jsonl 스키마

JSONL (JSON Lines) 형식으로, 한 줄에 하나의 청크 매핑 정보:

```jsonl
{"chunk_id": "error_codes_C4_004", "doc_id": "error_codes", "page": 12, "page_end": 18, "section": "C4 Communication issue", "section_id": "error_codes", "char_start": 2456, "char_end": 8934, "tokens": 1523, "error_code": "C4", "created_at": "2024-01-15T10:30:00Z"}
{"chunk_id": "error_codes_C5_005", "doc_id": "error_codes", "page": 18, "page_end": 19, "section": "C5 Heavy processor load warning", "section_id": "error_codes", "char_start": 8935, "char_end": 10234, "tokens": 312, "error_code": "C5", "created_at": "2024-01-15T10:30:00Z"}
{"chunk_id": "service_manual_001", "doc_id": "service_manual", "page": 45, "page_end": 48, "section": "5.2 Complete Rebooting Sequence", "section_id": "troubleshooting", "char_start": 45000, "char_end": 48500, "tokens": 856, "chapter": "5.2", "created_at": "2024-01-15T10:30:00Z"}
```

### 3.3 필드 설명

#### sources.yaml 필드

| 필드 | 타입 | 필수 | 설명 |
|------|------|:---:|------|
| `doc_id` | string | ✓ | 문서 고유 ID |
| `title` | string | ✓ | 문서 제목 |
| `version` | string | ✓ | 문서 버전 |
| `date` | string | ✓ | 발행일 (YYYY-MM) |
| `pages` | int | ✓ | 총 페이지 수 |
| `source_file` | string | ✓ | 원본 파일명 |
| `file_hash` | string | | 파일 해시 (무결성 검증) |
| `chunk_count` | int | ✓ | 생성된 청크 수 |
| `sections` | array | | 섹션 목록 |
| `url` | string | | 다운로드 URL |

#### chunk_manifest.jsonl 필드

| 필드 | 타입 | 필수 | 설명 |
|------|------|:---:|------|
| `chunk_id` | string | ✓ | 청크 고유 ID |
| `doc_id` | string | ✓ | 소속 문서 ID |
| `page` | int | ✓ | 시작 페이지 |
| `page_end` | int | | 끝 페이지 (여러 페이지 걸칠 경우) |
| `section` | string | ✓ | 섹션 제목 |
| `section_id` | string | | 섹션 ID |
| `char_start` | int | | 문서 내 시작 위치 |
| `char_end` | int | | 문서 내 끝 위치 |
| `tokens` | int | | 토큰 수 |
| `error_code` | string | | 에러코드 (해당 시) |
| `chapter` | string | | 챕터 번호 |
| `created_at` | string | ✓ | 생성 시간 (ISO8601) |

---

## 4. 구현 설계

### 4.1 MetadataService 클래스

```python
# src/api/services/metadata_service.py

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import yaml


@dataclass
class DocumentInfo:
    """문서 정보"""
    doc_id: str
    title: str
    version: str
    date: str
    pages: int
    source_file: str
    chunk_count: int
    url: Optional[str] = None
    sections: List[Dict] = None


@dataclass
class ChunkMapping:
    """청크 매핑 정보"""
    chunk_id: str
    doc_id: str
    page: int
    page_end: Optional[int]
    section: str
    section_id: Optional[str]
    char_start: Optional[int]
    char_end: Optional[int]
    tokens: Optional[int]
    error_code: Optional[str]
    chapter: Optional[str]


class MetadataService:
    """
    메타데이터 관리 서비스

    sources.yaml과 chunk_manifest.jsonl을 로드/조회합니다.
    """

    def __init__(
        self,
        sources_path: str = "data/processed/metadata/sources.yaml",
        manifest_path: str = "data/processed/metadata/chunk_manifest.jsonl"
    ):
        self.sources_path = Path(sources_path)
        self.manifest_path = Path(manifest_path)

        self._sources: Dict[str, DocumentInfo] = {}
        self._manifest: Dict[str, ChunkMapping] = {}
        self._loaded = False

    def load(self) -> bool:
        """메타데이터 로드"""
        try:
            self._load_sources()
            self._load_manifest()
            self._loaded = True
            print(f"[OK] MetadataService loaded: {len(self._sources)} docs, {len(self._manifest)} chunks")
            return True
        except Exception as e:
            print(f"[ERROR] MetadataService load failed: {e}")
            return False

    def _load_sources(self):
        """sources.yaml 로드"""
        if not self.sources_path.exists():
            print(f"[WARN] sources.yaml not found: {self.sources_path}")
            return

        with open(self.sources_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        for doc_id, doc_data in data.get("documents", {}).items():
            self._sources[doc_id] = DocumentInfo(
                doc_id=doc_id,
                title=doc_data.get("title", ""),
                version=doc_data.get("version", ""),
                date=doc_data.get("date", ""),
                pages=doc_data.get("pages", 0),
                source_file=doc_data.get("source_file", ""),
                chunk_count=doc_data.get("chunk_count", 0),
                url=doc_data.get("url"),
                sections=doc_data.get("sections", [])
            )

    def _load_manifest(self):
        """chunk_manifest.jsonl 로드"""
        if not self.manifest_path.exists():
            print(f"[WARN] chunk_manifest.jsonl not found: {self.manifest_path}")
            return

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    chunk_id = data.get("chunk_id")
                    if chunk_id:
                        self._manifest[chunk_id] = ChunkMapping(
                            chunk_id=chunk_id,
                            doc_id=data.get("doc_id", ""),
                            page=data.get("page", 0),
                            page_end=data.get("page_end"),
                            section=data.get("section", ""),
                            section_id=data.get("section_id"),
                            char_start=data.get("char_start"),
                            char_end=data.get("char_end"),
                            tokens=data.get("tokens"),
                            error_code=data.get("error_code"),
                            chapter=data.get("chapter")
                        )
                except json.JSONDecodeError:
                    continue

    # ---------------------------------------------------------
    # 조회 메서드
    # ---------------------------------------------------------

    def get_document(self, doc_id: str) -> Optional[DocumentInfo]:
        """문서 정보 조회"""
        return self._sources.get(doc_id)

    def get_chunk_mapping(self, chunk_id: str) -> Optional[ChunkMapping]:
        """청크 매핑 조회"""
        return self._manifest.get(chunk_id)

    def get_citation(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        청크 ID로 완전한 citation 정보 반환

        Returns:
            {
                "doc_id": "service_manual",
                "doc_title": "UR e-Series Service Manual",
                "version": "5.12",
                "page": 45,
                "page_end": 48,
                "section": "5.2 Complete Rebooting Sequence",
                "citation": "Service Manual v5.12, p.45-48, Section 5.2"
            }
        """
        mapping = self.get_chunk_mapping(chunk_id)
        if not mapping:
            return None

        doc = self.get_document(mapping.doc_id)
        if not doc:
            return None

        # citation 문자열 생성
        page_str = f"p.{mapping.page}"
        if mapping.page_end and mapping.page_end != mapping.page:
            page_str = f"p.{mapping.page}-{mapping.page_end}"

        citation = f"{doc.title} v{doc.version}, {page_str}"
        if mapping.section:
            citation += f", {mapping.section}"

        return {
            "doc_id": doc.doc_id,
            "doc_title": doc.title,
            "version": doc.version,
            "page": mapping.page,
            "page_end": mapping.page_end,
            "section": mapping.section,
            "chapter": mapping.chapter,
            "error_code": mapping.error_code,
            "citation": citation
        }

    def get_all_documents(self) -> List[DocumentInfo]:
        """모든 문서 정보 반환"""
        return list(self._sources.values())

    def get_chunks_by_doc(self, doc_id: str) -> List[ChunkMapping]:
        """문서에 속한 모든 청크 반환"""
        return [m for m in self._manifest.values() if m.doc_id == doc_id]

    def get_chunks_by_page(self, doc_id: str, page: int) -> List[ChunkMapping]:
        """특정 페이지의 청크 반환"""
        return [
            m for m in self._manifest.values()
            if m.doc_id == doc_id and m.page <= page <= (m.page_end or m.page)
        ]


# 싱글톤
_metadata_service: Optional[MetadataService] = None

def get_metadata_service() -> MetadataService:
    """MetadataService 싱글톤 반환"""
    global _metadata_service
    if _metadata_service is None:
        _metadata_service = MetadataService()
        _metadata_service.load()
    return _metadata_service
```

### 4.2 ManifestGenerator 클래스

```python
# src/ingestion/manifest_generator.py

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any
import yaml

from .models import Chunk


class ManifestGenerator:
    """
    청킹 결과로부터 metadata 파일 생성

    사용 예시:
        generator = ManifestGenerator()
        generator.generate_from_chunks(chunks, doc_info)
        generator.save()
    """

    def __init__(
        self,
        output_dir: str = "data/processed/metadata"
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._sources: Dict[str, Any] = {
            "version": "1.0",
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "documents": {},
            "meta": {}
        }
        self._manifest: List[Dict[str, Any]] = []

    def add_document(
        self,
        doc_id: str,
        title: str,
        version: str,
        date: str,
        pages: int,
        source_file: str,
        chunks: List[Chunk],
        url: str = None,
        sections: List[Dict] = None
    ):
        """문서 정보 추가"""
        # 파일 해시 계산
        file_hash = self._compute_file_hash(f"data/raw/pdf/{source_file}")

        self._sources["documents"][doc_id] = {
            "doc_id": doc_id,
            "title": title,
            "version": version,
            "date": date,
            "language": "en",
            "pages": pages,
            "publisher": "Universal Robots A/S",
            "source_file": source_file,
            "file_hash": file_hash,
            "processed_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "chunk_count": len(chunks),
            "url": url,
            "sections": sections or []
        }

        # manifest 엔트리 추가
        for chunk in chunks:
            self._manifest.append({
                "chunk_id": chunk.id,
                "doc_id": doc_id,
                "page": chunk.metadata.page,
                "page_end": getattr(chunk.metadata, 'page_end', None),
                "section": chunk.metadata.section,
                "section_id": getattr(chunk.metadata, 'section_id', None),
                "char_start": getattr(chunk.metadata, 'char_start', None),
                "char_end": getattr(chunk.metadata, 'char_end', None),
                "tokens": self._estimate_tokens(chunk.content),
                "error_code": chunk.metadata.error_code,
                "chapter": chunk.metadata.chapter,
                "created_at": datetime.now(timezone.utc).isoformat()
            })

    def _compute_file_hash(self, filepath: str) -> str:
        """파일 SHA256 해시 계산"""
        try:
            with open(filepath, "rb") as f:
                return f"sha256:{hashlib.sha256(f.read()).hexdigest()[:16]}"
        except FileNotFoundError:
            return "sha256:unknown"

    def _estimate_tokens(self, text: str) -> int:
        """토큰 수 추정 (대략 4자당 1토큰)"""
        return len(text) // 4

    def update_meta(self):
        """메타 정보 업데이트"""
        docs = self._sources["documents"]
        self._sources["meta"] = {
            "total_documents": len(docs),
            "total_chunks": len(self._manifest),
            "total_pages": sum(d.get("pages", 0) for d in docs.values()),
            "index_version": "1.0",
            "embedding_model": "text-embedding-3-small"
        }

    def save(self):
        """파일 저장"""
        self.update_meta()

        # sources.yaml 저장
        sources_path = self.output_dir / "sources.yaml"
        with open(sources_path, "w", encoding="utf-8") as f:
            yaml.dump(self._sources, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f"[OK] Saved sources.yaml: {len(self._sources['documents'])} documents")

        # chunk_manifest.jsonl 저장
        manifest_path = self.output_dir / "chunk_manifest.jsonl"
        with open(manifest_path, "w", encoding="utf-8") as f:
            for entry in self._manifest:
                # None 값 제거
                clean_entry = {k: v for k, v in entry.items() if v is not None}
                f.write(json.dumps(clean_entry, ensure_ascii=False) + "\n")
        print(f"[OK] Saved chunk_manifest.jsonl: {len(self._manifest)} chunks")
```

### 4.3 Retriever 확장

```python
# src/rag/retriever.py (수정 부분)

from src.api.services.metadata_service import get_metadata_service

class Retriever:
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """검색 수행 및 citation 정보 추가"""
        # 기존 검색 로직...
        results = self._vector_search(query, top_k)

        # citation 정보 추가
        metadata_service = get_metadata_service()
        for result in results:
            chunk_id = result.get("chunk_id")
            if chunk_id:
                citation = metadata_service.get_citation(chunk_id)
                if citation:
                    result["citation"] = citation

        return results
```

---

## 5. 구현 태스크

### 5.1 태스크 목록

```
Main-F3-1: 디렉토리 구조 정리
├── data/processed/metatdata/ → metadata/ 수정 (typo)
├── metadata 디렉토리 생성
└── 검증: 디렉토리 구조 확인

Main-F3-2: sources.yaml 작성
├── 3개 문서 정보 수집 (Error Codes, Service Manual, User Manual)
├── 버전, 페이지 수, 섹션 구조 조사
├── sources.yaml 작성
└── 검증: YAML 유효성 검사

Main-F3-3: ManifestGenerator 구현
├── src/ingestion/manifest_generator.py 작성
├── 기존 청크 파일에서 manifest 생성 스크립트
└── 검증: chunk_manifest.jsonl 생성 확인

Main-F3-4: MetadataService 구현
├── src/api/services/metadata_service.py 작성
├── sources.yaml, chunk_manifest.jsonl 로드
├── get_citation() 메서드 구현
└── 검증: 단위 테스트

Main-F3-5: Retriever 통합
├── src/rag/retriever.py 수정
├── 검색 결과에 citation 정보 추가
└── 검증: 통합 테스트

Main-F3-6: /evidence API 개선
├── EvidenceResponse에 citation 필드 추가
├── 정확한 문서/페이지 정보 반환
└── 검증: API 테스트
```

### 5.2 메타데이터 생성 스크립트

```python
# scripts/generate_metadata.py

"""
기존 청크 파일에서 metadata 파일 생성

사용법:
    python scripts/generate_metadata.py
"""

import os
import sys
import json
from pathlib import Path

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.ingestion.models import Chunk, load_chunks_from_json
from src.ingestion.manifest_generator import ManifestGenerator


# 문서 정보 (수동 조사 필요)
DOCUMENT_INFO = {
    "error_codes": {
        "title": "Error Codes Directory",
        "version": "5.12",
        "date": "2023-06",
        "pages": 45,
        "source_file": "ErrorCodes.pdf",
        "url": "https://www.universal-robots.com/download/?option=101202"
    },
    "service_manual": {
        "title": "UR e-Series Service Manual",
        "version": "5.12",
        "date": "2023-06",
        "pages": 328,
        "source_file": "ServiceManual.pdf",
        "url": "https://www.universal-robots.com/download/?option=101201"
    },
    "user_manual": {
        "title": "UR5e User Manual",
        "version": "5.12",
        "date": "2023-06",
        "pages": 256,
        "source_file": "UserManual.pdf",
        "url": "https://www.universal-robots.com/download/?option=101200"
    }
}


def main():
    print("=" * 60)
    print("Metadata Generation Script")
    print("=" * 60)

    generator = ManifestGenerator()
    chunks_dir = Path("data/processed/chunks")

    for doc_id, info in DOCUMENT_INFO.items():
        chunk_file = chunks_dir / f"{doc_id}_chunks.json"

        if not chunk_file.exists():
            print(f"[WARN] Chunk file not found: {chunk_file}")
            continue

        # 청크 로드
        chunks = load_chunks_from_json(str(chunk_file))
        print(f"[OK] Loaded {len(chunks)} chunks from {chunk_file.name}")

        # 문서 추가
        generator.add_document(
            doc_id=doc_id,
            title=info["title"],
            version=info["version"],
            date=info["date"],
            pages=info["pages"],
            source_file=info["source_file"],
            chunks=chunks,
            url=info.get("url")
        )

    # 저장
    generator.save()

    print("\n" + "=" * 60)
    print("[OK] Metadata generation completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
```

---

## 6. 테스트 계획

### 6.1 단위 테스트

```python
# tests/unit/test_metadata_service.py

import os
import sys
import pytest
import tempfile
from pathlib import Path

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


# ============================================================
# [1] sources.yaml 테스트
# ============================================================

class TestSourcesYaml:
    """sources.yaml 관련 테스트"""

    def test_load_sources(self, metadata_service):
        """sources.yaml 로드"""
        docs = metadata_service.get_all_documents()
        assert len(docs) >= 1

    def test_get_document(self, metadata_service):
        """문서 정보 조회"""
        doc = metadata_service.get_document("error_codes")
        assert doc is not None
        assert doc.title == "Error Codes Directory"
        assert doc.pages > 0

    def test_document_not_found(self, metadata_service):
        """존재하지 않는 문서"""
        doc = metadata_service.get_document("nonexistent")
        assert doc is None


# ============================================================
# [2] chunk_manifest.jsonl 테스트
# ============================================================

class TestChunkManifest:
    """chunk_manifest.jsonl 관련 테스트"""

    def test_load_manifest(self, metadata_service):
        """manifest 로드"""
        mapping = metadata_service.get_chunk_mapping("error_codes_C4_004")
        assert mapping is not None

    def test_chunk_mapping_fields(self, metadata_service):
        """매핑 필드 확인"""
        mapping = metadata_service.get_chunk_mapping("error_codes_C4_004")
        assert mapping.doc_id == "error_codes"
        assert mapping.page > 0
        assert mapping.section is not None

    def test_chunks_by_doc(self, metadata_service):
        """문서별 청크 조회"""
        chunks = metadata_service.get_chunks_by_doc("error_codes")
        assert len(chunks) > 0


# ============================================================
# [3] Citation 테스트
# ============================================================

class TestCitation:
    """Citation 생성 테스트"""

    def test_get_citation(self, metadata_service):
        """citation 조회"""
        citation = metadata_service.get_citation("error_codes_C4_004")
        assert citation is not None
        assert "doc_title" in citation
        assert "page" in citation
        assert "citation" in citation

    def test_citation_format(self, metadata_service):
        """citation 문자열 형식"""
        citation = metadata_service.get_citation("error_codes_C4_004")
        # 예: "Error Codes Directory v5.12, p.12, C4 Communication issue"
        assert "v5.12" in citation["citation"] or "v" in citation["citation"]
        assert "p." in citation["citation"]

    def test_citation_not_found(self, metadata_service):
        """존재하지 않는 청크"""
        citation = metadata_service.get_citation("nonexistent_chunk")
        assert citation is None


# ============================================================
# [4] Fixtures
# ============================================================

@pytest.fixture
def metadata_service():
    """테스트용 MetadataService"""
    from src.api.services.metadata_service import MetadataService
    service = MetadataService()
    service.load()
    return service


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### 6.2 통합 테스트

```python
# tests/integration/test_retriever_citation.py

def test_search_with_citation(rag_service):
    """검색 결과에 citation 포함 확인"""
    results = rag_service.search("C4A15 에러", top_k=3)

    for result in results:
        assert "citation" in result
        assert "doc_title" in result["citation"]
        assert "page" in result["citation"]


def test_evidence_api_citation(client):
    """evidence API에서 정확한 citation 반환"""
    # 쿼리 실행
    response = client.post("/api/v1/query", json={
        "user_query": "C4A15 에러 해결법"
    })
    trace_id = response.json()["trace_id"]

    # evidence 조회
    response = client.get(f"/api/v1/evidence/{trace_id}")
    data = response.json()

    for evidence in data.get("evidence", []):
        assert "doc_title" in evidence
        assert "page" in evidence
        assert "citation" in evidence
```

---

## 7. 코드 리뷰 체크포인트

### 7.1 데이터 정합성

| 항목 | 확인 내용 |
|------|----------|
| ☐ | chunk_id가 기존 ChromaDB와 일치하는가? |
| ☐ | 모든 청크가 manifest에 있는가? |
| ☐ | doc_id가 sources.yaml과 일치하는가? |
| ☐ | 페이지 번호가 실제 문서와 일치하는가? |

### 7.2 성능

| 항목 | 확인 내용 |
|------|----------|
| ☐ | manifest 조회가 빠른가? (<10ms) |
| ☐ | 메모리 사용량이 적절한가? |
| ☐ | 서버 시작 시 로딩 시간이 적절한가? |

### 7.3 확장성

| 항목 | 확인 내용 |
|------|----------|
| ☐ | 새 문서 추가가 쉬운가? |
| ☐ | 문서 버전 업데이트 시 영향 범위 파악 가능한가? |

---

## 8. 완료 기준

### 8.1 필수 항목

- [ ] sources.yaml 작성 완료 (3개 문서)
- [ ] chunk_manifest.jsonl 생성 완료 (모든 청크)
- [ ] MetadataService 구현 완료
- [ ] Retriever에 citation 정보 추가
- [ ] 단위 테스트 10개 이상, 통과율 100%

### 8.2 품질 항목

- [ ] 모든 청크에 대해 원본 추적 가능
- [ ] citation 형식 통일 ("Title vX.X, p.N, Section")
- [ ] manifest 조회 성능 < 10ms
- [ ] 코드 리뷰 체크리스트 통과

---

## 9. 다음 단계

### 9.1 Foundation 개선 완료

Main-F3 완료로 Foundation 개선 Phase (Main-F) 완료:
- Main-F1: Entity Linker 개선 ✓
- Main-F2: Trace 시스템 완성 ✓
- Main-F3: 메타데이터 정비 ✓

### 9.2 센서 통합 Phase 시작 (Main-S)

Main-F 완료 후 진행:
- Main-S1: 센서 데이터 생성 (Axia80 시뮬레이션)
- Main-S2: 패턴 감지
- Main-S3: Context Enricher
- ...

### 9.3 미래 확장

- **문서 업데이트**: 새 버전 문서 추가 시 sources.yaml 업데이트
- **다국어 지원**: 한국어 매뉴얼 추가 시 metadata 확장
- **버전 비교**: 버전별 변경 사항 추적

---

## 10. 참조

### 10.1 관련 문서
- [Main__Spec.md](Main__Spec.md) - Section 5.2 (폴더 구조)
- [Main__ROADMAP.md](Main__ROADMAP.md) - Main-F3
- [Foundation_Spec.md](Foundation_Spec.md) - Section 4.4.3 (Evidence Metadata Files)

### 10.2 생성/수정 파일 경로
```
data/processed/metadata/                  (디렉토리 생성)
data/processed/metadata/sources.yaml      (생성)
data/processed/metadata/chunk_manifest.jsonl (생성)

src/api/services/metadata_service.py      (생성)
src/ingestion/manifest_generator.py       (생성)
src/rag/retriever.py                      (수정)

scripts/generate_metadata.py              (생성)
tests/unit/test_metadata_service.py       (생성)
```

---

**작성일**: 2024-01-21
**참조**: Main__Spec.md, Main__ROADMAP.md, Foundation_Spec.md
