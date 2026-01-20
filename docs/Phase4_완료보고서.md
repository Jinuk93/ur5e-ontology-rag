# Phase 4: 온톨로지 및 그래프 DB - 완료 보고서

> **목표:** 지식 구조(온톨로지)를 설계하고 Neo4j에 저장하여 "관계 기반 검색"이 가능하게 한다.
>
> **완료일:** 2026-01-20

---

## 1. Before vs After 비교

### 1.1 파일 구조

| 항목 | Before (계획) | After (실제) | 차이점 |
|------|--------------|--------------|--------|
| `schema.py` | 스키마 정의 | 스키마 + 헬퍼 함수 | **헬퍼 함수 추가** |
| `graph_store.py` | Neo4j CRUD | CRUD + 통계 + 쿼리 | **기능 확장** |
| `entity_extractor.py` | LLM 추출 | LLM + **규칙 기반 추출** | **하이브리드 방식** |
| `run_ontology.py` | 실행 스크립트 | 실행 + 테스트 쿼리 | **테스트 통합** |
| `docker-compose.yml` | 계획대로 | 계획대로 | 동일 |

### 1.2 추출 방식

| 항목 | Before (계획) | After (실제) | 이유 |
|------|--------------|--------------|------|
| 엔티티 추출 | LLM만 사용 | **규칙 기반 + LLM** | RESOLVED_BY 관계 정확도 향상 |
| 에러코드 문서 | LLM 추출 | **정규식 패턴 매칭** | 일관된 패턴 활용 |
| 관계 추출 | LLM 추출 | **규칙 기반 우선** | ID 매칭 문제 해결 |

### 1.3 결과 비교

| 항목 | Before (1차 시도) | After (개선 후) | 증가율 |
|------|------------------|-----------------|--------|
| 총 노드 | 263개 | **325개** | +24% |
| 총 관계 | 48개 | **201개** | **+319%** |
| RESOLVED_BY | 0개 | **144개** | **신규** |
| ErrorCode | 171개 | **202개** | +18% |
| Procedure | 33개 | **63개** | +91% |

---

## 2. 생성된 파일 및 코드 분석

### 2.1 파일 구조

```
src/ontology/
├── __init__.py           ← 패키지 export
├── schema.py             ← 온톨로지 스키마 정의 (250줄)
├── graph_store.py        ← Neo4j 연동 (350줄)
└── entity_extractor.py   ← 엔티티 추출 (480줄)

scripts/
├── run_ontology.py       ← 파이프라인 실행 (250줄)
└── test_graph.py         ← 그래프 테스트 (200줄)

stores/neo4j/             ← Neo4j 데이터 저장
├── data/
├── logs/
└── import/

docker-compose.yml        ← Neo4j Docker 설정
```

### 2.2 코드 분석: schema.py

```python
# Entity Types (노드 유형)
class EntityType(Enum):
    COMPONENT = "Component"      # 부품
    ERROR_CODE = "ErrorCode"     # 에러 코드
    PROCEDURE = "Procedure"      # 절차/해결책
    DOCUMENT = "Document"        # 문서
    CHUNK = "Chunk"              # 청크

# Relation Types (관계 유형)
class RelationType(Enum):
    HAS_ERROR = "HAS_ERROR"          # Component → ErrorCode
    RESOLVED_BY = "RESOLVED_BY"      # ErrorCode → Procedure
    CAUSED_BY = "CAUSED_BY"          # ErrorCode → Component
    CONTAINS = "CONTAINS"            # Component → Component
    HAS_CHUNK = "HAS_CHUNK"          # Document → Chunk
```

### 2.3 코드 분석: entity_extractor.py

```python
class EntityExtractor:
    """하이브리드 엔티티 추출기"""

    # 1. 규칙 기반 추출 (에러코드 문서용)
    def extract_error_codes_rule_based(self, text, chunk_id):
        """
        SUGGESTION 패턴 파싱:
        C4A15 Communication with joint 3 lost
        EXPLANATION
        More than 1 package lost
        SUGGESTION
        (A) Verify cables, (B) Reboot
        """

    # 2. LLM 기반 추출 (일반 문서용)
    def extract_from_text(self, text, chunk_id):
        """GPT-4o-mini로 구조화된 JSON 추출"""
```

### 2.4 코드 분석: graph_store.py

```python
class GraphStore:
    """Neo4j 그래프 저장소"""

    def add_entity(self, entity)      # 노드 추가
    def add_relation(self, relation)  # 관계 추가
    def query(self, cypher)           # Cypher 쿼리 실행
    def get_related_entities(self, entity_id)  # 관련 엔티티 조회
    def get_statistics(self)          # 통계 정보
```

---

## 3. 테스트 결과

### 3.1 기본 통계

```
총 노드: 325개
├── ErrorCode: 202개
├── Procedure: 63개
├── Chunk: 30개
├── Component: 27개
└── Document: 3개

총 관계: 201개
├── RESOLVED_BY: 144개  ← 핵심!
├── HAS_CHUNK: 20개
├── HAS_ERROR: 19개
├── CAUSED_BY: 16개
└── CONTAINS: 2개
```

### 3.2 쿼리 테스트 결과

#### 테스트 1: C4A15 에러 해결 방법

**인풋:** "C4A15 에러가 발생했는데, 어떻게 해결하나요?"

**Cypher 쿼리:**
```cypher
MATCH (e:ErrorCode {name: "C4A15"})-[:RESOLVED_BY]->(p:Procedure)
RETURN e.name, p.name
```

**출력:**
```
C4A15 → Verify the communication cables are connected properly
C4A15 → Conduct a complete rebooting sequence
```

**한글 해석:**
- 통신 케이블이 제대로 연결되어 있는지 확인
- 완전한 재부팅 수행

#### 테스트 2: Safety Control Board 관련 에러

**인풋:** "Safety Control Board에서 어떤 에러가 발생할 수 있나요?"

**Cypher 쿼리:**
```cypher
MATCH (c:Component)-[:HAS_ERROR]->(e:ErrorCode)
WHERE c.name CONTAINS "Safety Control Board"
RETURN e.name, e.title
```

**출력:**
```
Safety Control Board → C55A53: 5V too high
Safety Control Board → C55A52: 5V too low
Safety Control Board → C55A51: Voltage will not disappear
Safety Control Board → C55A50: Voltage present at unpowered robot
Safety Control Board → C55: Safety system error
Safety Control Board → C53: IO overcurrent detected
```

#### 테스트 3: 가장 많이 사용되는 해결 방법

**Cypher 쿼리:**
```cypher
MATCH (e:ErrorCode)-[:RESOLVED_BY]->(p:Procedure)
RETURN p.name, count(e) as usage
ORDER BY usage DESC LIMIT 5
```

**출력:**
```
1위. Conduct a complete rebooting sequence (57개 에러)
2위. Verify the communication cables (28개 에러)
3위. Exchange component (6개 에러)
4위. Replace if happens more than twice (5개 에러)
5위. Exchange Teach Pendant (4개 에러)
```

---

## 4. 이슈 및 해결

### 4.1 RESOLVED_BY 관계 누락 문제

**문제:**
- 1차 시도에서 RESOLVED_BY 관계가 0개
- 원인: LLM이 Procedure 이름을 다르게 추출하여 ID 불일치

**해결:**
- 규칙 기반 추출 추가 (`extract_error_codes_rule_based()`)
- SUGGESTION 패턴을 정규식으로 파싱
- 표준화된 Procedure 엔티티 생성

**결과:**
- RESOLVED_BY 관계 0개 → **144개**

**상세 문서:** [Phase4_이슈_RESOLVED_BY_관계추출.md](Phase4_이슈_RESOLVED_BY_관계추출.md)

---

## 5. 비용 분석

### 5.1 LLM 비용

```
처리된 청크: 30개 (샘플링)
├── error_code: 10개 (규칙 기반 + LLM)
├── service_manual: 10개 (LLM)
└── user_manual: 10개 (LLM)

LLM 호출: ~20회 (error_code 외 청크)
예상 비용: ~$0.03 (약 40원)
```

### 5.2 Neo4j 비용

```
로컬 Docker 실행: 무료
데이터 저장: stores/neo4j/ (~10MB)
```

---

## 6. 핵심 개념 정리

### 6.1 VectorDB vs GraphDB

```
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  VectorDB (ChromaDB)           GraphDB (Neo4j)              │
│  ─────────────────             ─────────────────            │
│  "의미" 기반 검색              "관계" 기반 검색              │
│                                                              │
│  질문: "통신 에러"             질문: "Control Box의 모든 에러"│
│  → 의미적으로 유사한 청크      → 연결된 모든 ErrorCode       │
│                                                              │
│  [청크] ─── 유사도 ───> [청크]  [Component] ─HAS_ERROR─> [Error]│
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 온톨로지 스키마

```
                    ┌──────────┐
                    │ Document │
                    └────┬─────┘
                         │ HAS_CHUNK
                         ▼
                    ┌──────────┐
                    │  Chunk   │
                    └──────────┘

┌───────────┐  HAS_ERROR   ┌───────────┐  RESOLVED_BY  ┌───────────┐
│ Component │─────────────>│ ErrorCode │──────────────>│ Procedure │
└───────────┘              └───────────┘               └───────────┘
      │                          │
      │ CONTAINS                 │ CAUSED_BY
      ▼                          ▼
┌───────────┐              ┌───────────┐
│ Component │              │ Component │
└───────────┘              └───────────┘
```

---

## 7. 완료 체크리스트

- [x] Neo4j Docker 설정 (docker-compose.yml)
- [x] 온톨로지 스키마 정의 (schema.py)
- [x] Neo4j 연동 구현 (graph_store.py)
- [x] 엔티티 추출기 구현 (entity_extractor.py)
- [x] 규칙 기반 추출 추가 (SUGGESTION 패턴)
- [x] 파이프라인 실행 스크립트 (run_ontology.py)
- [x] 그래프 테스트 스크립트 (test_graph.py)
- [x] RESOLVED_BY 관계 정상 추출 (144개)
- [x] 테스트 쿼리 검증 완료

---

## 8. 현재까지 완료된 것

```
[Phase 0] 환경 설정 ✅
    └── Python, Docker, 패키지 설치

[Phase 1] PDF 분석 ✅
    └── 3개 PDF 구조 파악

[Phase 2] PDF 파싱 ✅
    └── 722개 청크 생성

[Phase 3] 임베딩 ✅
    └── ChromaDB 저장 (의미 기반 검색)

[Phase 4] 온톨로지 ✅ (현재)
    └── Neo4j 저장 (관계 기반 검색)
    └── 325 노드, 201 관계
    └── RESOLVED_BY 144개
```

---

## 9. 다음 단계 (Phase 5 예정)

### 9.1 Phase 5: RAG 파이프라인

```
목표: VectorDB + GraphDB 하이브리드 검색으로 RAG 완성

예상 작업:
1. 하이브리드 Retriever 구현
   - VectorDB: 의미적 유사 청크 검색
   - GraphDB: 관련 엔티티 탐색

2. LLM 답변 생성
   - 검색된 컨텍스트로 답변 생성
   - 출처 표시

3. API 서버 (FastAPI)
   - /query 엔드포인트
   - /search 엔드포인트

4. UI (Streamlit)
   - 질문 입력
   - 답변 + 출처 표시
```

### 9.2 최종 RAG 흐름

```
┌─────────────────────────────────────────────────────────────┐
│                        RAG Pipeline                          │
│                                                              │
│  [질문] "C4A15 에러 해결법"                                  │
│     │                                                        │
│     ├──> VectorDB ──> 유사 청크 3개                         │
│     │                                                        │
│     └──> GraphDB ──> 관련 Procedure 2개                     │
│                                                              │
│  [컨텍스트] 청크 + Procedure 정보                           │
│     │                                                        │
│     └──> LLM ──> 최종 답변 생성                             │
│                                                              │
│  [답변] "C4A15 에러는 조인트 3 통신 문제입니다.              │
│         해결방법: 1) 케이블 확인 2) 재부팅"                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 10. Neo4j Browser 접속 정보

```
URL: http://localhost:7474
User: neo4j
Password: password123

유용한 쿼리:
- 전체 그래프: MATCH (n)-[r]->(m) RETURN n,r,m LIMIT 100
- 에러 해결법: MATCH (e:ErrorCode)-[:RESOLVED_BY]->(p) RETURN e,p
- 부품별 에러: MATCH (c:Component)-[:HAS_ERROR]->(e) RETURN c,e
```
