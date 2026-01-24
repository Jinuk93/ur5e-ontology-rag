# 온톨로지 그래프 탐색 API

팔란티어 스타일의 동적 지식 그래프 탐색 기능을 제공합니다.

## 개요

이 API는 UR5e 로봇과 Axia80 센서의 온톨로지 데이터를 그래프 형태로 탐색할 수 있게 해줍니다.
사용자는 임의의 엔티티에서 시작하여 연결된 관계를 따라 탐색하고, 원인-결과 체인을 시각적으로 확인할 수 있습니다.

## API 엔드포인트

### 1. 전체 엔티티 목록 조회

**GET** `/api/ontology/entities`

그래프 탐색의 시작점을 선택하기 위한 전체 엔티티 목록을 반환합니다.

**응답 예시:**
```json
{
  "entities": [
    {"id": "PAT_COLLISION", "type": "Pattern", "label": "충돌 패턴", "domain": "measurement"},
    {"id": "C153", "type": "ErrorCode", "label": "C153 안전 정지", "domain": "knowledge"},
    ...
  ],
  "total": 54,
  "by_type": {"Robot": 1, "Pattern": 4, "ErrorCode": 12, ...},
  "by_domain": {"equipment": 9, "measurement": 13, "knowledge": 26, ...}
}
```

### 2. 엔티티 상세 정보 조회

**GET** `/api/ontology/entity/{entity_id}`

특정 엔티티의 상세 정보를 반환합니다.

**파라미터:**
- `entity_id`: 엔티티 ID (예: `PAT_COLLISION`, `C153`)

**응답 예시:**
```json
{
  "id": "PAT_COLLISION",
  "type": "Pattern",
  "name": "충돌 패턴",
  "domain": "measurement",
  "properties": {"detection_method": "force_spike", "severity": "high"},
  "description": "UR5e 에러 코드: 충돌 패턴"
}
```

### 3. 이웃 노드 조회 (1-hop 탐색)

**GET** `/api/ontology/neighbors/{entity_id}`

클릭한 노드의 직접 연결된 이웃들을 반환합니다.

**파라미터:**
- `entity_id`: 중심 엔티티 ID
- `direction`: 탐색 방향 (`outgoing`, `incoming`, `both`) - 기본값: `both`

**응답 예시:**
```json
{
  "center": {"id": "PAT_COLLISION", "type": "Pattern", "label": "충돌 패턴"},
  "nodes": [
    {"id": "CAUSE_COLLISION", "type": "Cause", "label": "물리적 충돌"},
    {"id": "C153", "type": "ErrorCode", "label": "C153 안전 정지"},
    {"id": "C119", "type": "ErrorCode", "label": "C119 충돌 감지"}
  ],
  "edges": [
    {"source": "PAT_COLLISION", "target": "CAUSE_COLLISION", "relation": "INDICATES"},
    {"source": "PAT_COLLISION", "target": "C153", "relation": "TRIGGERS"},
    {"source": "PAT_COLLISION", "target": "C119", "relation": "TRIGGERS"}
  ],
  "total_neighbors": 3
}
```

### 4. 서브그래프 조회 (N-hop 탐색)

**GET** `/api/ontology/graph`

중심 노드에서 depth만큼 확장된 서브그래프를 반환합니다.

**파라미터:**
- `center`: 중심 노드 ID (필수)
- `depth`: 탐색 깊이 1-4 (기본값: 2)
- `direction`: 탐색 방향 (`outgoing`, `incoming`, `both`) - 기본값: `both`

**응답 예시:**
```json
{
  "nodes": [
    {"id": "PAT_COLLISION", "type": "Pattern", "label": "충돌 패턴"},
    {"id": "CAUSE_COLLISION", "type": "Cause", "label": "물리적 충돌"},
    {"id": "C153", "type": "ErrorCode", "label": "C153 안전 정지"},
    {"id": "RES_CHECK_OBSTACLE", "type": "Resolution", "label": "장애물 확인"}
  ],
  "edges": [
    {"source": "PAT_COLLISION", "target": "CAUSE_COLLISION", "relation": "INDICATES"},
    {"source": "PAT_COLLISION", "target": "C153", "relation": "TRIGGERS"},
    {"source": "CAUSE_COLLISION", "target": "RES_CHECK_OBSTACLE", "relation": "RESOLVED_BY"}
  ],
  "center_id": "PAT_COLLISION",
  "depth": 2,
  "total_nodes": 4,
  "total_edges": 3
}
```

## 관계 타입 (RelationType)

온톨로지에서 사용되는 주요 관계 타입:

| 관계 | 설명 | 예시 |
|------|------|------|
| `TRIGGERS` | 패턴이 에러를 유발 | PAT_COLLISION → C153 |
| `CAUSED_BY` | 에러의 원인 | C153 → CAUSE_COLLISION |
| `RESOLVED_BY` | 해결 방법 | CAUSE_COLLISION → RES_CHECK_OBSTACLE |
| `INDICATES` | 상태가 패턴을 나타냄 | State_Critical → PAT_OVERLOAD |
| `HAS_STATE` | 측정축의 상태 | Fz → State_Warning |
| `PART_OF` | 부품 관계 | Joint_0 → UR5e |

## 프론트엔드 연동

### React Query 훅 사용

```typescript
import {
  useOntologyEntities,
  useOntologyGraph,
  useOntologyEntity,
  useOntologyNeighbors
} from '@/hooks/useApi';

// 전체 엔티티 목록
const { data: entities } = useOntologyEntities();

// 서브그래프 조회
const { data: graph } = useOntologyGraph('PAT_COLLISION', 2, 'both');

// 엔티티 상세 정보
const { data: entity } = useOntologyEntity('C153');

// 이웃 노드 조회
const { data: neighbors } = useOntologyNeighbors('PAT_COLLISION', 'both');
```

### GraphView 컴포넌트

`frontend/src/components/graph/GraphView.tsx`에서 동적 그래프 탐색 UI를 제공합니다.

**주요 기능:**
- 시작점 선택: 타입별/검색으로 엔티티 필터링
- 깊이 조절: 1-4 hop까지 탐색 범위 조절
- 노드 클릭: 상세 정보 표시
- 더블클릭: 해당 노드를 중심으로 그래프 재구성
- 초기화: 기본 상태로 복원

## 사용 시나리오

### 1. 에러 원인 분석

1. `C153` 에러 코드에서 시작
2. `CAUSED_BY` 관계를 따라 원인 탐색
3. `RESOLVED_BY` 관계로 해결 방법 확인

### 2. 센서 패턴 예측

1. 현재 센서 상태에서 시작 (예: `State_Warning`)
2. `INDICATES` 관계로 가능한 패턴 확인
3. `TRIGGERS` 관계로 예상 에러 코드 파악

### 3. 장비 구조 이해

1. `UR5e` 로봇에서 시작
2. `PART_OF` 관계로 하위 조인트 탐색
3. 각 조인트의 상태와 관련 에러 확인

## 백엔드 구현

### 파일 위치

- API 라우터: `src/api/routes/ontology.py`
- 온톨로지 엔진: `src/ontology/ontology_engine.py`
- 그래프 탐색기: `src/ontology/graph_traverser.py`

### 주요 클래스

```python
# GraphTraverser - BFS 기반 그래프 탐색
traverser = GraphTraverser(ontology)
result = traverser.bfs(start_id, max_depth=2, direction='both')

# OntologyEngine - 추론 및 컨텍스트 제공
engine = OntologyEngine()
context = engine.get_context(entity_id)
```

## 향후 개선 사항

1. **경로 검색**: 두 노드 간 최단 경로 찾기
2. **필터링**: 관계 타입별 필터링 옵션
3. **히스토리**: 탐색 경로 히스토리 관리
4. **북마크**: 중요 노드 저장 기능
5. **내보내기**: 그래프 이미지/JSON 내보내기
