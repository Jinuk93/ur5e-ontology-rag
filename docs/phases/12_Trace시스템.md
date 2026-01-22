# Phase 12: Trace 시스템

> **상태**: ✅ 완료
> **도메인**: 운영 레이어 (Operations)
> **목표**: 완전한 audit_trail 및 근거 추적 시스템 구현
> **이전 명칭**: Main-F2

---

## 1. 개요

모든 RAG 요청에 대해 trace_id를 부여하고, 검색/생성/검증 과정을
audit_trail.jsonl에 기록하여 나중에 근거를 추적할 수 있도록 하는 단계.

---

## 2. 태스크

| # | 태스크 | 상태 |
|---|--------|------|
| 1 | AuditLogger 클래스 구현 | ✅ |
| 2 | audit_trail.jsonl 저장 구현 | ✅ |
| 3 | /evidence/{trace_id} 엔드포인트 | ✅ |
| 4 | UI에서 trace_id 표시 | ✅ |
| 5 | 단위 테스트 작성 | ✅ |

---

## 3. Trace 아키텍처

### 3.1 흐름도

```
┌─────────────┐
│  API 요청   │
│ (질문 입력)  │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│                    RAG Pipeline + Audit                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  [1] trace_id 생성                                           │
│      └─▶ UUID: "550e8400-e29b-41d4-a716-446655440000"       │
│                                                              │
│  [2] 검색 단계 기록                                           │
│      └─▶ 검색된 청크, 점수, 소요 시간                          │
│                                                              │
│  [3] 생성 단계 기록                                           │
│      └─▶ 프롬프트, LLM 응답, 토큰 사용량                       │
│                                                              │
│  [4] 검증 단계 기록                                           │
│      └─▶ 검증 상태, 신뢰도, 경고                              │
│                                                              │
│  [5] audit_trail.jsonl 저장                                  │
│      └─▶ 모든 정보 한 줄로 저장                               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│  API 응답   │
│ + trace_id  │
└─────────────┘
```

### 3.2 Audit Trail 스키마

```json
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-01-22T14:30:00.000Z",
  "request": {
    "question": "C154A3 에러의 원인은?",
    "top_k": 5
  },
  "retrieval": {
    "method": "hybrid",
    "chunks": [
      {
        "chunk_id": "error_codes_p015_c002",
        "score": 0.92,
        "doc_id": "error_codes",
        "page": 15
      }
    ],
    "duration_ms": 150
  },
  "generation": {
    "model": "gpt-4o-mini",
    "prompt_tokens": 1200,
    "completion_tokens": 350,
    "duration_ms": 1500
  },
  "verification": {
    "status": "pass",
    "confidence": 0.88,
    "doc_score": 0.92,
    "sensor_score": null,
    "warnings": []
  },
  "response": {
    "answer": "C154A3는 Control Box 팬 오작동...",
    "sources_count": 2
  },
  "total_duration_ms": 1850
}
```

---

## 4. 구현

### 4.1 AuditLogger 클래스

```python
# src/api/services/audit_logger.py

import json
import uuid
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List

@dataclass
class AuditEntry:
    trace_id: str
    timestamp: str
    request: dict
    retrieval: dict
    generation: dict
    verification: dict
    response: dict
    total_duration_ms: int

class AuditLogger:
    def __init__(self, log_path: str = "stores/audit/audit_trail.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def create_trace(self) -> str:
        """새 trace_id 생성"""
        return str(uuid.uuid4())

    def log(self, entry: AuditEntry) -> None:
        """audit_trail.jsonl에 기록"""
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")

    def get_entry(self, trace_id: str) -> Optional[AuditEntry]:
        """trace_id로 항목 조회"""
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line)
                if entry["trace_id"] == trace_id:
                    return AuditEntry(**entry)
        return None

    def get_entries_by_date(
        self, date: str, limit: int = 100
    ) -> List[AuditEntry]:
        """날짜별 항목 조회"""
        entries = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line)
                if entry["timestamp"].startswith(date):
                    entries.append(AuditEntry(**entry))
                    if len(entries) >= limit:
                        break
        return entries
```

### 4.2 Evidence 엔드포인트

```python
# src/api/routes/evidence.py

from fastapi import APIRouter, HTTPException
from src.api.services.audit_logger import AuditLogger
from src.api.schemas.evidence import EvidenceResponse

router = APIRouter()
audit_logger = AuditLogger()

@router.get("/evidence/{trace_id}", response_model=EvidenceResponse)
async def get_evidence(trace_id: str):
    """trace_id로 근거 조회"""
    entry = audit_logger.get_entry(trace_id)

    if not entry:
        raise HTTPException(status_code=404, detail="Trace not found")

    return EvidenceResponse(
        trace_id=entry.trace_id,
        timestamp=entry.timestamp,
        question=entry.request["question"],
        answer=entry.response["answer"],
        sources=[
            {
                "chunk_id": c["chunk_id"],
                "doc_id": c["doc_id"],
                "page": c["page"],
                "score": c["score"]
            }
            for c in entry.retrieval["chunks"]
        ],
        verification={
            "status": entry.verification["status"],
            "confidence": entry.verification["confidence"]
        }
    )
```

### 4.3 RAGService 통합

```python
# src/api/services/rag_service.py (수정)

class RAGService:
    def __init__(self, ..., audit_logger: AuditLogger):
        self.audit_logger = audit_logger

    async def query(self, question: str, top_k: int = 5) -> RAGResult:
        trace_id = self.audit_logger.create_trace()
        start_time = time.time()

        # 1. 검색
        retrieval_start = time.time()
        retrieval_result = await self.retriever.retrieve(question, top_k)
        retrieval_duration = int((time.time() - retrieval_start) * 1000)

        # 2. 생성
        generation_start = time.time()
        generation_result = await self.generator.generate(...)
        generation_duration = int((time.time() - generation_start) * 1000)

        # 3. 검증
        verification_result = await self.verifier.verify(...)

        # 4. Audit 기록
        total_duration = int((time.time() - start_time) * 1000)
        self.audit_logger.log(AuditEntry(
            trace_id=trace_id,
            timestamp=datetime.utcnow().isoformat(),
            request={"question": question, "top_k": top_k},
            retrieval={
                "method": "hybrid",
                "chunks": [...],
                "duration_ms": retrieval_duration
            },
            generation={
                "model": self.generator.model,
                "duration_ms": generation_duration
            },
            verification={
                "status": verification_result.status.value,
                "confidence": verification_result.confidence
            },
            response={"answer": generation_result.answer},
            total_duration_ms=total_duration
        ))

        return RAGResult(..., trace_id=trace_id)
```

---

## 5. 산출물

### 5.1 파일 목록

| 파일 | 내용 | Lines |
|------|------|-------|
| `src/api/services/audit_logger.py` | AuditLogger 클래스 | ~330 |
| `src/api/routes/evidence.py` | Evidence 엔드포인트 | ~50 |
| `src/api/schemas/evidence.py` | Evidence 스키마 | ~40 |
| `stores/audit/audit_trail.jsonl` | 로그 저장소 | - |
| `tests/test_audit_logger.py` | 단위 테스트 | 23개 |

### 5.2 테스트 결과

```
========================= test session starts ==========================
tests/test_audit_logger.py::test_create_trace PASSED
tests/test_audit_logger.py::test_log_entry PASSED
tests/test_audit_logger.py::test_get_entry PASSED
tests/test_audit_logger.py::test_get_entries_by_date PASSED
...
========================= 23 passed in 0.38s ===========================
```

---

## 6. API 사용 예시

### 6.1 Query 응답에서 trace_id 확인

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "C154A3 에러의 원인은?"}'

# 응답
{
  "answer": "...",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  ...
}
```

### 6.2 Evidence 조회

```bash
curl http://localhost:8000/api/v1/evidence/550e8400-e29b-41d4-a716-446655440000

# 응답
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-01-22T14:30:00.000Z",
  "question": "C154A3 에러의 원인은?",
  "answer": "C154A3는 Control Box 팬 오작동...",
  "sources": [...],
  "verification": {
    "status": "pass",
    "confidence": 0.88
  }
}
```

---

## 7. 검증 체크리스트

- [x] AuditLogger 클래스 구현
- [x] audit_trail.jsonl 저장 동작
- [x] /evidence/{trace_id} 엔드포인트 동작
- [x] trace_id가 모든 응답에 포함
- [x] 23개 단위 테스트 100% 통과

---

## 8. 다음 단계

→ [Phase 13: 메타데이터 정비](13_메타데이터정비.md)

---

**Phase**: 12 / 19
**작성일**: 2026-01-22
