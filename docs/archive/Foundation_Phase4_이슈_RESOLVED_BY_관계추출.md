# Phase 4 이슈: RESOLVED_BY 관계 추출 문제 및 해결

> **이슈 발견일:** 2026-01-20
>
> **해결일:** 2026-01-20
>
> **상태:** ✅ 해결 완료

---

## 1. 문제 발견

### 1.1 현상

Neo4j Browser에서 에러 코드 노드(C4A15)를 확인했을 때, **해결 방법(Procedure)과의 연결이 없었습니다.**

```
Node properties:
  ErrorCode: C4A15
  code: C4A15
  title: Communication with joint 3 lost
  description: More than 1 package lost
  source_chunk: error_codes_C4_004

연결된 RESOLVED_BY 관계: 0개  ❌
```

### 1.2 원인 분석

**원본 데이터(VectorDB)에는 해결 방법이 존재:**

```
C4A15 Communication with joint 3 lost
EXPLANATION
More than 1 package lost
SUGGESTION
Try the following actions to see which resolves the issue:
(A) Verify the communication cables are connected properly,
(B) Conduct a complete rebooting sequence
```

**하지만 GraphDB에는 관계가 생성되지 않음:**

| 추출 방식 | 문제점 |
|----------|--------|
| LLM 기반 | Procedure 이름을 다르게 추출하여 ID 불일치 |
| | 예: "Check cable" vs "Verify communication cables" |
| | source_id와 target_id가 매칭되지 않음 |

---

## 2. 해결 방법

### 2.1 규칙 기반 추출 추가

에러 코드 문서는 **일관된 패턴**을 가지고 있으므로, 정규식 기반의 규칙 추출을 추가했습니다.

**패턴 인식:**
```
(에러코드) (제목)
EXPLANATION
(설명)
SUGGESTION
Try the following actions: (A) 해결방법1, (B) 해결방법2
```

### 2.2 코드 변경

**파일:** `src/ontology/entity_extractor.py`

**추가된 메서드:** `extract_error_codes_rule_based()`

```python
def extract_error_codes_rule_based(self, text: str, chunk_id: Optional[str] = None):
    """
    규칙 기반으로 에러 코드와 해결 방법 추출

    1. 에러 코드 패턴 추출: C4A15, C50A100 등
    2. SUGGESTION 섹션에서 해결 방법 추출
    3. (A), (B), (C) 패턴으로 개별 단계 분리
    4. 표준화된 Procedure 엔티티 생성
    5. RESOLVED_BY 관계 생성
    """
    # 에러 코드 패턴
    error_pattern = r'(C\d+(?:A\d+)?)\s+([^\n]+?)(?=\n|EXPLANATION|SUGGESTION|$)'

    # SUGGESTION 패턴
    suggestion_pattern = r'(C\d+(?:A\d+)?)[^\n]*\n(?:EXPLANATION[^\n]*\n[^\n]*\n)?SUGGESTION\s*\n([^\n]+)'

    # ... 추출 로직
```

### 2.3 파이프라인 변경

**파일:** `scripts/run_ontology.py`

**변경 내용:**
- 에러 코드 청크는 **규칙 기반 추출** 우선 적용
- 나머지 청크는 **LLM 기반 추출** 적용

```python
# Step 4: 엔티티 추출 (규칙 기반 + LLM)

# 4-1. 에러 코드 청크는 규칙 기반 추출 (SUGGESTION 패턴)
error_chunks = [c for c in all_chunks if c.metadata.doc_type == 'error_code']
err_entities, err_relations = extractor.extract_error_codes_from_chunks(error_chunks)

# 4-2. 나머지 청크는 LLM 추출
other_chunks = [c for c in all_chunks if c not in error_chunks]
other_entities, other_relations = extractor.extract_from_chunks(other_chunks)
```

---

## 3. 결과 비교

### 3.1 Before (개선 전)

```
총 관계 수: 48개
├── HAS_CHUNK: 20
├── HAS_ERROR: 18
├── CAUSED_BY: 10
└── RESOLVED_BY: 0  ❌
```

### 3.2 After (개선 후)

```
총 관계 수: 201개
├── RESOLVED_BY: 144  ✅ (+144)
├── HAS_CHUNK: 20
├── HAS_ERROR: 19
├── CAUSED_BY: 16
└── CONTAINS: 2
```

### 3.3 C4A15 에러 확인

**Before:**
```
C4A15 → (해결 방법 없음)
```

**After:**
```
C4A15 → Verify the communication cables are connected properly
C4A15 → Conduct a complete rebooting sequence
```

---

## 4. 검증 쿼리

### 4.1 Neo4j Browser에서 확인

```cypher
-- C4A15 에러 해결 방법 조회
MATCH (e:ErrorCode {name: 'C4A15'})-[:RESOLVED_BY]->(p:Procedure)
RETURN e.name as error, p.name as procedure

-- 결과:
-- C4A15 → Verify the communication cables are connected properly
-- C4A15 → Conduct a complete rebooting sequence
```

### 4.2 전체 RESOLVED_BY 관계 확인

```cypher
-- 에러별 해결 방법 개수
MATCH (e:ErrorCode)-[:RESOLVED_BY]->(p:Procedure)
RETURN e.name as error, count(p) as procedure_count
ORDER BY procedure_count DESC
LIMIT 10
```

---

## 5. 교훈 및 권장 사항

### 5.1 교훈

| 항목 | 내용 |
|------|------|
| **LLM의 한계** | 구조화된 문서에서 일관된 추출이 어려움 |
| **하이브리드 접근** | 규칙 기반 + LLM 조합이 효과적 |
| **ID 일관성** | 엔티티 이름 → ID 변환 시 표준화 필요 |

### 5.2 권장 사항

1. **규칙 기반 우선**
   - 패턴이 명확한 문서는 정규식 사용
   - 예: 에러 코드 문서, API 명세

2. **LLM은 보조**
   - 복잡하거나 비정형 텍스트에 사용
   - 예: 일반 매뉴얼, 설명 텍스트

3. **ID 표준화**
   - 엔티티 이름을 ID로 변환할 때 정규화
   - 공백, 특수문자 처리 일관성

---

## 6. 관련 파일

| 파일 | 변경 내용 |
|------|----------|
| `src/ontology/entity_extractor.py` | `extract_error_codes_rule_based()` 추가 |
| `scripts/run_ontology.py` | 에러코드/일반청크 분리 처리 |

---

## 7. 시각적 확인 (Neo4j Browser)

**쿼리:**
```cypher
MATCH (e:ErrorCode)-[r:RESOLVED_BY]->(p:Procedure)
WHERE e.name STARTS WITH 'C4A1'
RETURN e, r, p
```

**결과:** C4A1x 에러들과 해결 방법들이 연결된 그래프 시각화

---

**작성일:** 2026-01-20
