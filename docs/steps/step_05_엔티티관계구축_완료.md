# Step 05: 엔티티/관계 구축 - 완료 보고서

## 1. 요약

| 항목 | 내용 |
|------|------|
| Phase | 05 - 엔티티/관계 구축 (Entity/Relationship Population) |
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
| `src/ontology/loader.py` | 184 | 신규 작성 | OntologyLoader 클래스 |
| `data/processed/ontology/ontology.json` | 501 | 업데이트 | 전체 온톨로지 인스턴스 |
| `data/processed/ontology/lexicon.yaml` | 402 | 기존 유지 | 동의어 사전 |
| `scripts/build_ontology.py` | 178 | 신규 작성 | 빌드/검증 스크립트 |
| `src/ontology/__init__.py` | 77 | 업데이트 | loader 모듈 노출 |

### 2.2 온톨로지 통계

| 항목 | 수량 |
|------|------|
| 총 엔티티 | 54개 |
| 총 관계 | 62개 |

### 2.3 도메인별 엔티티 분포

| 도메인 | 엔티티 수 | 주요 엔티티 |
|--------|----------|------------|
| Equipment | 9 | UR5e, Joint_0~5, ControlBox, ToolFlange |
| Measurement | 14 | Axia80, Fx~Fz, Tx~Tz, States, Patterns |
| Knowledge | 26 | C153, C119, C189, Causes, Resolutions, Documents |
| Context | 5 | Shift_Day/Night, Product_A/B, WorkCycle_Assembly |

### 2.4 관계 타입별 분포

| 관계 타입 | 수량 | 예시 |
|----------|------|------|
| HAS_COMPONENT | 8 | UR5e → Joint_0~5, ControlBox, ToolFlange |
| MOUNTED_ON | 1 | Axia80 → ToolFlange |
| MEASURES | 6 | Axia80 → Fx, Fy, Fz, Tx, Ty, Tz |
| HAS_STATE | 6 | 각 축 → State_Normal |
| INDICATES | 5 | PAT_COLLISION → CAUSE_COLLISION |
| TRIGGERS | 4 | PAT_COLLISION → C153, C119 |
| CAUSED_BY | 11 | C153 → CAUSE_COLLISION |
| RESOLVED_BY | 5 | CAUSE_COLLISION → RES_CLEAR_PATH |
| DOCUMENTED_IN | 4 | C153 → DOC_USER_MANUAL |
| PREVENTS | 4 | RES_CLEAR_PATH → C153 |
| AFFECTS | 6 | C50~C55 → Joint_0~5 |
| OCCURS_DURING | 1 | PAT_COLLISION → Shift_Day |
| INVOLVES | 1 | PAT_OVERLOAD → Product_B |

---

## 3. 구현 상세

### 3.1 OntologyLoader 클래스

```python
class OntologyLoader:
    """온톨로지 로더/저장"""

    DEFAULT_PATH = Path("data/processed/ontology/ontology.json")
    LEXICON_PATH = Path("data/processed/ontology/lexicon.yaml")

    @classmethod
    def load(cls, path=None, use_cache=True) -> OntologySchema:
        """온톨로지 로드 (캐시 지원)"""

    @classmethod
    def save(cls, schema, path=None) -> None:
        """온톨로지 저장"""

    @classmethod
    def load_lexicon(cls, path=None, use_cache=True) -> Dict:
        """동의어 사전 로드"""

    @classmethod
    def resolve_alias(cls, term, lexicon=None) -> Optional[str]:
        """동의어를 표준 ID로 변환"""

    @classmethod
    def get_aliases(cls, entity_id, lexicon=None) -> List[str]:
        """엔티티의 별칭 목록 반환"""

    @classmethod
    def clear_cache(cls) -> None:
        """캐시 초기화"""
```

### 3.2 ontology.json 구조

```json
{
  "version": "1.0",
  "description": "UR5e 협동로봇 온톨로지 - 4-Domain Architecture",

  "entities": [
    {
      "id": "UR5e",
      "type": "Robot",
      "domain": "equipment",
      "name": "UR5e 협동로봇",
      "properties": {"payload_kg": 5.0, "reach_mm": 850}
    }
    // ... 54 entities
  ],

  "relationships": [
    {
      "source": "UR5e",
      "relation": "HAS_COMPONENT",
      "target": "Joint_0"
    }
    // ... 62 relationships
  ]
}
```

### 3.3 Lexicon 호환성

기존 lexicon.yaml 형식을 지원하도록 loader를 수정:

```python
# 두 가지 형식 모두 지원
categories = ["entities", "error_codes", "components"]
alias_keys = ["aliases", "synonyms"]
```

### 3.4 빌드 스크립트 검증 결과

```
============================================================
[*] Build Complete
============================================================

  Total Entities: 54
  Total Relationships: 62
  Validation: PASS
```

---

## 4. 사용법

### 4.1 온톨로지 로드

```python
from src.ontology import load_ontology, load_lexicon

# 온톨로지 로드
schema = load_ontology()
print(f"Entities: {len(schema.entities)}")
print(f"Relationships: {len(schema.relationships)}")

# 엔티티 조회
ur5e = schema.get_entity("UR5e")
joints = schema.get_entities_by_type(EntityType.JOINT)
equipment = schema.get_entities_by_domain(Domain.EQUIPMENT)
```

### 4.2 관계 조회

```python
# UR5e의 모든 관계
rels = schema.get_relationships_for_entity("UR5e")

# 나가는 관계만
outgoing = schema.get_relationships_for_entity("UR5e", direction="outgoing")

# 관계 타입별
has_component = schema.get_relationships_by_type(RelationType.HAS_COMPONENT)
```

### 4.3 동의어 해석

```python
from src.ontology import resolve_alias

# 다양한 표현을 표준 ID로 변환
resolve_alias("c153")        # "C153"
resolve_alias("컨트롤 박스")   # "Control Box"
resolve_alias("joint 0")     # "Joint 0"
```

### 4.4 빌드 스크립트 실행

```bash
python scripts/build_ontology.py
```

---

## 5. 아키텍처 정합성

### 5.1 Unified_ROADMAP.md 충족 사항

| ROADMAP 요구사항 | 구현 내용 | 상태 |
|-----------------|----------|------|
| Equipment 엔티티 생성 | 9개 엔티티 (UR5e, Joints, etc.) | O |
| Measurement 엔티티 생성 | 14개 엔티티 (Sensor, Axes, etc.) | O |
| Knowledge 엔티티 생성 | 26개 엔티티 (ErrorCodes, Causes, etc.) | O |
| Context 엔티티 생성 | 5개 엔티티 (Shifts, Products, etc.) | O |
| 관계 인스턴스 생성 | 62개 관계 | O |

### 5.2 Phase 5와 Phase 6 연결점

```
Phase 5 (엔티티/관계)              Phase 6 (동의어 사전)
─────────────────                   ─────────────────
OntologySchema.entities  →          EntityLinker 입력
lexicon.yaml            →          resolve_alias() 함수
```

---

## 6. 폴더 구조

```
ur5e-ontology-rag/
├── data/
│   └── processed/
│       └── ontology/
│           ├── ontology.json [업데이트]   # 전체 온톨로지
│           ├── lexicon.yaml [기존]        # 동의어 사전
│           └── schema.yaml                # 스키마 정의
│
├── scripts/
│   └── build_ontology.py [신규]           # 빌드/검증 스크립트
│
└── src/
    └── ontology/
        ├── __init__.py [업데이트]         # loader 노출
        ├── schema.py                      # Enum 정의
        ├── models.py                      # 데이터 모델
        └── loader.py [신규]               # OntologyLoader
```

---

## 7. 다음 단계 준비

### Phase 6 (동의어 사전)와의 연결

| Phase 5 산출물 | Phase 6 사용처 |
|---------------|---------------|
| ontology.json | EntityLinker 엔티티 참조 |
| lexicon.yaml | 동의어 확장 기반 |
| resolve_alias() | EntityLinker 핵심 함수 |
| OntologyLoader | 통합 로딩 인터페이스 |

### 준비 사항

```python
# Phase 6에서 사용할 코드
from src.ontology import (
    load_ontology,
    load_lexicon,
    resolve_alias,
)

# 온톨로지 로드
schema = load_ontology()

# 동의어 해석
canonical_id = resolve_alias("컨트롤박스")  # "Control Box"

# 엔티티 조회
if canonical_id:
    entity = schema.get_entity(canonical_id)
```

---

## 8. 이슈 및 참고사항

### 8.1 해결된 이슈

1. **Lexicon 형식 호환성**: 기존 lexicon.yaml의 `synonyms` 키와 새 형식의 `aliases` 키 모두 지원하도록 수정
2. **Sensor→Document 관계 검증**: DOCUMENTED_IN 제약 조건에 Sensor를 추가하여 검증 통과

### 8.2 알려진 제한사항

없음 - 모든 검증 통과

### 8.3 검증 명령어

```bash
# 온톨로지 빌드 및 검증
python scripts/build_ontology.py

# Python에서 직접 테스트
python -c "
from src.ontology import load_ontology
schema = load_ontology()
print(f'Entities: {len(schema.entities)}')
print(f'Relationships: {len(schema.relationships)}')
"
```

---

## 9. 리팩토링 수행 내역

### 9.1 설계서 업데이트 (v1.0 → v2.0)

| 추가/변경 섹션 | 내용 |
|---------------|------|
| 구현 상태 업데이트 | "신규 작성" → "완료됨 (X줄)" 상태 반영 |
| 체크리스트 완료 | [ ] → [x] 모든 항목 완료 표시 |
| 실제 구현 결과 | Section 10 추가 - 최종 통계 및 검증 결과 |

### 9.2 코드 리팩토링

| 파일 | 변경 내용 |
|------|----------|
| `src/ontology/schema.py` | DOCUMENTED_IN 제약 조건에 Sensor 추가 |

### 9.3 검증 결과

```bash
python scripts/build_ontology.py

============================================================
[*] Build Complete
============================================================

  Total Entities: 54
  Total Relationships: 62
  Validation: PASS
```

모든 검증 테스트 통과 확인.

---

## 10. 문서 정보

| 항목 | 값 |
|------|---|
| 문서 버전 | v2.0 (리팩토링 완료) |
| 작성일 | 2026-01-22 |
| 리팩토링일 | 2026-01-22 |
| 설계서 참조 | [step_05_엔티티관계구축_설계.md](step_05_엔티티관계구축_설계.md) |
| ROADMAP 섹션 | A.2 Phase 5 |
| Spec 섹션 | Section 6 |

---

*Phase 05 완료. Phase 06 (동의어 사전)으로 진행합니다.*
