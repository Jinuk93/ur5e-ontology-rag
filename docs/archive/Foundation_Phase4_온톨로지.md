# Phase 4: 온톨로지 및 그래프 DB - 계획 문서

> **목표:** 지식 구조(온톨로지)를 설계하고 Neo4j에 저장하여 "관계 기반 검색"이 가능하게 한다.
>
> **예상 작업일:** 2026-01-20 ~

---

## 0. 핵심 개념 정리

### 0.1 VectorDB vs GraphDB vs Ontology

Phase 4를 시작하기 전에, 핵심 개념들의 차이점을 명확히 이해해야 합니다.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        지식 표현의 3가지 방식                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. VectorDB (ChromaDB) - "의미" 기반                               │
│     ┌───────┐                                                       │
│     │ 청크1 │ → [0.12, -0.34, 0.56, ...] (1536차원 벡터)            │
│     │ 청크2 │ → [0.11, -0.33, 0.55, ...] (비슷한 벡터 = 비슷한 의미)  │
│     └───────┘                                                       │
│     검색: "통신 에러" → 의미적으로 유사한 청크 반환                     │
│                                                                     │
│  2. GraphDB (Neo4j) - "관계" 기반                                   │
│     ┌──────────┐    HAS_ERROR    ┌──────┐                          │
│     │ControlBox│───────────────→│  C4  │                           │
│     └──────────┘                 └──────┘                           │
│           │                          │                              │
│           │ CONTAINS                 │ RESOLVED_BY                  │
│           ↓                          ↓                              │
│     ┌──────────┐               ┌──────────┐                        │
│     │Motherboard│              │케이블 점검│                        │
│     └──────────┘               └──────────┘                        │
│     검색: "Control Box 관련 에러 전부" → 관계를 따라 모든 에러 반환     │
│                                                                     │
│  3. Ontology - "스키마/정의"                                        │
│     - GraphDB에 저장할 데이터의 "구조"를 정의                         │
│     - 어떤 노드(Entity)가 있고, 어떤 관계(Relation)가 가능한지          │
│     - 예: Component → HAS_ERROR → ErrorCode (이 관계가 유효함)       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 0.2 왜 GraphDB가 필요한가?

**VectorDB만으로는 어려운 질문들:**

```
질문: "Control Box에서 발생할 수 있는 모든 에러 코드는?"

VectorDB 방식:
  - "Control Box 에러"로 검색 → 의미적으로 유사한 청크 몇 개 반환
  - 하지만 모든 에러를 찾는 것은 보장되지 않음

GraphDB 방식:
  - Control Box 노드에서 HAS_ERROR 관계를 따라감
  - 연결된 모든 에러 코드 노드를 반환 (완전한 목록)
```

**VectorDB + GraphDB 조합의 장점:**

| 검색 유형 | VectorDB | GraphDB |
|----------|----------|---------|
| "통신 에러 해결법" | ✅ 의미 검색 | |
| "C4 에러 관련 부품" | | ✅ 관계 탐색 |
| "Joint 0 관련 모든 정보" | | ✅ 완전한 탐색 |
| "에러가 자주 나는 부품" | | ✅ 통계/패턴 |

### 0.3 Ontology란?

```
Ontology = "지식의 구조를 정의하는 것"

쉽게 말하면:
  - 데이터베이스의 "스키마"와 비슷
  - 어떤 종류의 것(Entity)이 있고
  - 그것들 사이에 어떤 관계(Relation)가 가능한지 정의

예시:
  Entity Types:
    - Component (부품): Control Box, Joint, Cable...
    - ErrorCode (에러 코드): C4, C10, C17...
    - Procedure (절차): 케이블 점검, 조인트 교체...

  Relation Types:
    - HAS_ERROR: Component → ErrorCode
    - RESOLVED_BY: ErrorCode → Procedure
    - CONTAINS: Component → Component
```

---

## 1. 현재 상태 (Phase 3 완료 후)

```
[완료된 것]
├── PDF 파싱 → 722개 청크
├── 임베딩 생성 → 1536차원 벡터
└── ChromaDB 저장 → 의미 기반 검색 가능

[Phase 4에서 할 것]
├── 온톨로지 스키마 설계
├── 엔티티 추출 (LLM 사용)
├── 관계 정의
└── Neo4j에 그래프 구축
```

---

## 2. 목표 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                     Hybrid RAG System                        │
│                                                              │
│  ┌─────────────┐         ┌─────────────┐                    │
│  │  VectorDB   │         │   GraphDB   │                    │
│  │  (ChromaDB) │         │   (Neo4j)   │                    │
│  ├─────────────┤         ├─────────────┤                    │
│  │ 722 청크    │         │ Entities    │                    │
│  │ 1536d 벡터  │         │ Relations   │                    │
│  ├─────────────┤         ├─────────────┤                    │
│  │ "의미" 검색 │         │ "관계" 검색  │                    │
│  │ 유사도 기반 │         │ 그래프 탐색  │                    │
│  └─────────────┘         └─────────────┘                    │
│         │                       │                            │
│         └───────────┬───────────┘                            │
│                     │                                        │
│              ┌──────▼──────┐                                 │
│              │   Retriever  │                                │
│              │  (하이브리드) │                                │
│              └─────────────┘                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 온톨로지 스키마 설계

### 3.1 Entity Types (노드 유형)

```
┌────────────────────────────────────────────────────────────┐
│                      Entity Types                           │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Component (부품)                                        │
│     - Control Box, Joint, Cable, Motherboard...            │
│     - 속성: name, type, location                           │
│                                                             │
│  2. ErrorCode (에러 코드)                                   │
│     - C4, C10, C17, C50...                                 │
│     - 속성: code, title, severity, description             │
│                                                             │
│  3. Procedure (절차/해결책)                                  │
│     - 케이블 점검, 조인트 교체, 펌웨어 업데이트...            │
│     - 속성: name, steps, tools_required                    │
│                                                             │
│  4. Document (문서)                                         │
│     - ErrorCodes.pdf, ServiceManual.pdf, UserManual.pdf   │
│     - 속성: name, type, page_count                         │
│                                                             │
│  5. Chunk (청크) - VectorDB 연결용                          │
│     - 청크 ID로 VectorDB와 연결                             │
│     - 속성: chunk_id, page, section                        │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

### 3.2 Relation Types (관계 유형)

```
┌────────────────────────────────────────────────────────────┐
│                     Relation Types                          │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Component 관련:                                            │
│    - CONTAINS: Component → Component                       │
│      예: Control Box -[CONTAINS]→ Motherboard             │
│                                                             │
│    - CONNECTED_TO: Component → Component                   │
│      예: Joint 0 -[CONNECTED_TO]→ Joint 1                 │
│                                                             │
│  ErrorCode 관련:                                            │
│    - HAS_ERROR: Component → ErrorCode                      │
│      예: Control Box -[HAS_ERROR]→ C4                     │
│                                                             │
│    - CAUSED_BY: ErrorCode → Component                      │
│      예: C4 -[CAUSED_BY]→ Ethernet Cable                  │
│                                                             │
│    - RESOLVED_BY: ErrorCode → Procedure                    │
│      예: C4 -[RESOLVED_BY]→ 케이블 점검                    │
│                                                             │
│  Document 관련:                                             │
│    - MENTIONED_IN: Entity → Document                       │
│      예: C4 -[MENTIONED_IN]→ ErrorCodes.pdf               │
│                                                             │
│    - HAS_CHUNK: Document → Chunk                           │
│      예: ErrorCodes.pdf -[HAS_CHUNK]→ error_codes_001     │
│                                                             │
│  Chunk 연결:                                                │
│    - DESCRIBES: Chunk → Entity                             │
│      예: error_codes_035 -[DESCRIBES]→ C4                 │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

### 3.3 스키마 다이어그램

```
                    ┌──────────┐
                    │ Document │
                    └────┬─────┘
                         │ HAS_CHUNK
                         ▼
                    ┌──────────┐
                    │  Chunk   │◄─────────────────┐
                    └────┬─────┘                  │
                         │ DESCRIBES              │
                         ▼                        │
┌───────────┐      ┌──────────┐      ┌───────────┐
│ Component │◄─────│ ErrorCode│─────►│ Procedure │
└─────┬─────┘      └──────────┘      └───────────┘
      │              HAS_ERROR         RESOLVED_BY
      │ CONTAINS
      ▼
┌───────────┐
│ Component │
└───────────┘
```

---

## 4. 구현 계획

### 4.1 파일 구조

```
src/ontology/
├── __init__.py           ← 패키지 export
├── schema.py             ← 온톨로지 스키마 정의
├── entity_extractor.py   ← LLM으로 엔티티 추출
├── relation_extractor.py ← LLM으로 관계 추출
└── graph_store.py        ← Neo4j 연동

scripts/
└── run_ontology.py       ← 파이프라인 실행
```

### 4.2 단계별 작업

```
Step 1: Neo4j 설정
  - Docker로 Neo4j 실행
  - Python 드라이버 연결 테스트

Step 2: 스키마 정의 (schema.py)
  - Entity 클래스 정의
  - Relation 클래스 정의
  - 검증 로직

Step 3: 엔티티 추출 (entity_extractor.py)
  - 청크에서 Component, ErrorCode, Procedure 추출
  - LLM (GPT-4) 사용
  - 구조화된 출력 (JSON)

Step 4: 관계 추출 (relation_extractor.py)
  - 엔티티 간 관계 추출
  - HAS_ERROR, RESOLVED_BY 등
  - LLM 사용

Step 5: 그래프 구축 (graph_store.py)
  - Neo4j에 노드 생성
  - 관계 생성
  - 인덱스 설정

Step 6: 검증 및 쿼리 테스트
  - Cypher 쿼리로 데이터 확인
  - 관계 탐색 테스트
```

### 4.3 Neo4j 설정 (docker-compose.yml)

```yaml
version: '3.8'
services:
  neo4j:
    image: neo4j:5.15-community
    container_name: ur5e-neo4j
    ports:
      - "7474:7474"  # HTTP (Browser)
      - "7687:7687"  # Bolt (Driver)
    environment:
      - NEO4J_AUTH=neo4j/password123
      - NEO4J_PLUGINS=["apoc"]
    volumes:
      - ./stores/neo4j/data:/data
      - ./stores/neo4j/logs:/logs
```

### 4.4 Python 패키지

```
# requirements.txt에 추가
neo4j>=5.15.0        # Neo4j 드라이버
```

---

## 5. 엔티티 추출 전략

### 5.1 LLM 프롬프트 설계

```python
ENTITY_EXTRACTION_PROMPT = """
아래 텍스트에서 다음 유형의 엔티티를 추출하세요:

1. Component (부품): 로봇의 물리적 부품
   - 예: Control Box, Joint 0, Motherboard, Ethernet Cable

2. ErrorCode (에러 코드): 에러 코드와 설명
   - 예: C4, C10, C17A

3. Procedure (절차): 수리/점검 절차
   - 예: 케이블 점검, 조인트 교체, 펌웨어 업데이트

텍스트:
{chunk_content}

JSON 형식으로 출력:
{
  "components": [{"name": "...", "type": "..."}],
  "error_codes": [{"code": "...", "title": "..."}],
  "procedures": [{"name": "...", "steps": [...]}]
}
"""
```

### 5.2 배치 처리

```
722개 청크 → 배치 처리 (10개씩)
  - API 비용 최적화
  - Rate limit 관리
  - 중복 엔티티 통합
```

---

## 6. 관계 추출 전략

### 6.1 규칙 기반 추출

```python
# 에러 코드 문서에서 관계 추출
# 패턴: "C4 - Communication error"
# → ErrorCode(C4) -[HAS_ERROR]→ Communication

# 서비스 매뉴얼에서 관계 추출
# 패턴: "Replace the Joint 0"
# → Procedure(Replace Joint) -[AFFECTS]→ Component(Joint 0)
```

### 6.2 LLM 기반 추출

```python
RELATION_EXTRACTION_PROMPT = """
다음 엔티티들 사이의 관계를 추출하세요:

엔티티:
{entities}

텍스트:
{chunk_content}

가능한 관계 유형:
- HAS_ERROR: 부품 → 에러코드
- RESOLVED_BY: 에러코드 → 절차
- CONTAINS: 부품 → 부품
- CONNECTED_TO: 부품 → 부품

JSON 형식으로 출력:
{
  "relations": [
    {"source": "...", "relation": "...", "target": "..."}
  ]
}
"""
```

---

## 7. 예상 결과

### 7.1 노드 통계 (예상)

| Entity Type | 예상 개수 |
|-------------|----------|
| Component | ~50개 |
| ErrorCode | ~100개 |
| Procedure | ~30개 |
| Document | 3개 |
| Chunk | 722개 |
| **합계** | ~900개 |

### 7.2 관계 통계 (예상)

| Relation Type | 예상 개수 |
|---------------|----------|
| HAS_ERROR | ~150개 |
| RESOLVED_BY | ~100개 |
| CONTAINS | ~30개 |
| DESCRIBES | ~722개 |
| HAS_CHUNK | 722개 |
| **합계** | ~1,700개 |

---

## 8. 테스트 쿼리 (Cypher)

### 8.1 기본 쿼리

```cypher
// Control Box 관련 모든 에러 코드
MATCH (c:Component {name: 'Control Box'})-[:HAS_ERROR]->(e:ErrorCode)
RETURN e.code, e.title

// C4 에러의 해결 절차
MATCH (e:ErrorCode {code: 'C4'})-[:RESOLVED_BY]->(p:Procedure)
RETURN p.name, p.steps

// Joint 0 관련 모든 정보
MATCH (c:Component {name: 'Joint 0'})-[r]->(target)
RETURN type(r), target
```

### 8.2 복잡한 쿼리

```cypher
// 가장 많은 에러가 발생하는 부품
MATCH (c:Component)-[:HAS_ERROR]->(e:ErrorCode)
RETURN c.name, count(e) as error_count
ORDER BY error_count DESC
LIMIT 5

// 특정 에러와 연관된 모든 청크
MATCH (e:ErrorCode {code: 'C4'})<-[:DESCRIBES]-(chunk:Chunk)
RETURN chunk.chunk_id
```

---

## 9. 비용 예상

### 9.1 LLM 비용 (엔티티 + 관계 추출)

```
722 청크 × ~500 토큰 = 361,000 토큰
GPT-4o-mini 기준: $0.15 / 1M 토큰
예상 비용: ~$0.05 (약 70원)
```

### 9.2 Neo4j 비용

```
로컬 Docker 실행: 무료
```

---

## 10. 체크리스트

- [ ] Neo4j Docker 설정
- [ ] Python 드라이버 연결
- [ ] 온톨로지 스키마 정의
- [ ] 엔티티 추출기 구현
- [ ] 관계 추출기 구현
- [ ] Neo4j 저장 구현
- [ ] 테스트 쿼리 실행
- [ ] VectorDB-GraphDB 연결 테스트

---

## 11. 다음 단계 (Phase 5 예고)

```
Phase 5: RAG 파이프라인
  - VectorDB + GraphDB 하이브리드 검색
  - LLM을 사용한 답변 생성
  - 최종 RAG 시스템 완성
```
