# Step 05: 엔티티/관계 구축 - 설계서

## 1. 개요

### 1.1 Phase 정보
- **Phase 번호**: 05
- **Phase 명**: 엔티티/관계 구축 (Entity & Relationship Building)
- **Stage**: Stage 2 - 온톨로지 핵심 (Ontology Core) ★
- **목표**: 온톨로지 인스턴스 데이터 생성

### 1.2 Phase 목표 (Unified_ROADMAP.md 기준)
- Equipment 인스턴스 생성 (UR5e, Joint_0~5, ControlBox, ToolFlange)
- Measurement 인스턴스 생성 (Axia80, Fx~Tz, States, Patterns)
- Knowledge 인스턴스 생성 (C153, C189, C119, CAUSE_*, RES_*, Documents)
- Context 인스턴스 생성 (SHIFT_A/B/C, PART-A/B/C, WorkCycle)
- 관계 연결 (~100개)

### 1.3 핵심 산출물
- `data/processed/ontology/ontology.json` (전체 온톨로지 인스턴스)
- `data/processed/ontology/lexicon.yaml` (동의어 사전)
- `src/ontology/loader.py` (온톨로지 로더)
- `scripts/build_ontology.py` (온톨로지 구축 스크립트)

---

## 2. 다룰 파일

### 2.1 핵심 구현 파일

| 파일 경로 | 역할 | 상태 |
|-----------|------|------|
| `src/ontology/loader.py` | 온톨로지 로더/저장 | 완료됨 (184줄) |
| `scripts/build_ontology.py` | 온톨로지 구축 스크립트 | 완료됨 (178줄) |

### 2.2 데이터 파일

| 파일 경로 | 역할 | 상태 |
|-----------|------|------|
| `data/processed/ontology/ontology.json` | 온톨로지 인스턴스 | 완료됨 (501줄) |
| `data/processed/ontology/lexicon.yaml` | 동의어 사전 | 기존 유지 (402줄) |

### 2.3 Phase 4 산출물 (사용)

| 파일 경로 | 역할 |
|-----------|------|
| `src/ontology/schema.py` | EntityType, RelationType |
| `src/ontology/models.py` | Entity, Relationship |

---

## 3. 설계 상세

### 3.1 엔티티 인스턴스 설계

#### 3.1.1 Equipment Domain (~12 엔티티)

| ID | Type | Name | Properties |
|----|------|------|------------|
| UR5e | Robot | UR5e 협동로봇 | payload_kg: 5.0, reach_mm: 850, dof: 6 |
| Joint_0 | Joint | Base 관절 | index: 0, max_torque_nm: 150 |
| Joint_1 | Joint | Shoulder 관절 | index: 1, max_torque_nm: 150 |
| Joint_2 | Joint | Elbow 관절 | index: 2, max_torque_nm: 150 |
| Joint_3 | Joint | Wrist1 관절 | index: 3, max_torque_nm: 28 |
| Joint_4 | Joint | Wrist2 관절 | index: 4, max_torque_nm: 28 |
| Joint_5 | Joint | Wrist3 관절 | index: 5, max_torque_nm: 28 |
| CB_UR5e | ControlBox | 제어박스 | model: "e-Series" |
| TF_UR5e | ToolFlange | 툴 플랜지 | diameter_mm: 63 |

#### 3.1.2 Measurement Domain (~20 엔티티)

**센서 & 축**

| ID | Type | Name | Properties |
|----|------|------|------------|
| Axia80 | Sensor | ATI Axia80 F/T 센서 | sampling_rate_hz: 8000 |
| Fz | MeasurementAxis | Z축 힘 | range: [-235, 235], normal_range: [-60, 0] |
| Fx | MeasurementAxis | X축 힘 | range: [-75, 75] |
| Fy | MeasurementAxis | Y축 힘 | range: [-75, 75] |
| Tx | MeasurementAxis | X축 토크 | range: [-4, 4] |
| Ty | MeasurementAxis | Y축 토크 | range: [-4, 4] |
| Tz | MeasurementAxis | Z축 토크 | range: [-4, 4] |

**상태**

| ID | Type | Name | Properties |
|----|------|------|------------|
| STATE_IDLE | State | 유휴 상태 | severity: normal, range: [-20, -10] |
| STATE_LIGHT_LOAD | State | 경부하 상태 | severity: normal, range: [-40, -20] |
| STATE_NORMAL_LOAD | State | 정상부하 상태 | severity: normal, range: [-70, -40] |
| STATE_HEAVY_LOAD | State | 중부하 상태 | severity: low, range: [-100, -70] |
| STATE_WARNING | State | 경고 상태 | severity: medium, range: [-200, -100] |
| STATE_CRITICAL | State | 위험 상태 | severity: critical, range: [-235, -200] |

**패턴**

| ID | Type | Name | Properties |
|----|------|------|------------|
| PAT_COLLISION | Pattern | 충돌 패턴 | severity: critical, detection: "delta > 500N/100ms" |
| PAT_OVERLOAD | Pattern | 과부하 패턴 | severity: high, detection: "abs > 150N for 5s" |
| PAT_VIBRATION | Pattern | 진동 패턴 | severity: medium, detection: "std > 2x baseline" |
| PAT_DRIFT | Pattern | 드리프트 패턴 | severity: low, detection: "baseline shift > 10%" |

#### 3.1.3 Knowledge Domain (~20 엔티티)

**에러 코드**

| ID | Type | Name | Properties |
|----|------|------|------------|
| C153 | ErrorCode | Safety System Violation | category: safety, severity: critical |
| C189 | ErrorCode | Payload Exceeded | category: overload, severity: high |
| C119 | ErrorCode | Protective Stop | category: safety, severity: high |

**원인**

| ID | Type | Name | Properties |
|----|------|------|------------|
| CAUSE_PHYSICAL_CONTACT | Cause | 물리적 접촉 | category: physical |
| CAUSE_UNEXPECTED_OBSTACLE | Cause | 예상치 못한 장애물 | category: physical |
| CAUSE_PAYLOAD_EXCEEDED | Cause | 페이로드 초과 | category: mechanical |
| CAUSE_GRIP_POSITION | Cause | 그립 위치 불량 | category: operational |
| CAUSE_CALIBRATION_NEEDED | Cause | 캘리브레이션 필요 | category: sensor |
| CAUSE_JOINT_WEAR | Cause | 관절 마모 | category: mechanical |

**해결책**

| ID | Type | Name | Properties |
|----|------|------|------------|
| RES_CLEAR_OBSTRUCTION | Resolution | 장애물 제거 | steps: [...] |
| RES_CHECK_PROGRAM_PATH | Resolution | 프로그램 경로 확인 | steps: [...] |
| RES_REDUCE_PAYLOAD | Resolution | 페이로드 감소 | steps: [...] |
| RES_ADJUST_GRIP_POSITION | Resolution | 그립 위치 조정 | steps: [...] |
| RES_RECALIBRATE_SENSOR | Resolution | 센서 재캘리브레이션 | steps: [...] |
| RES_CHECK_SURROUNDINGS | Resolution | 주변 환경 확인 | steps: [...] |

**문서**

| ID | Type | Name | Properties |
|----|------|------|------------|
| DOC_USER_MANUAL | Document | UR5e User Manual | doc_type: user_manual |
| DOC_SERVICE_MANUAL | Document | Service Manual | doc_type: service_manual |
| DOC_ERROR_CODES | Document | Error Codes Directory | doc_type: error_codes |

#### 3.1.4 Context Domain (~10 엔티티)

| ID | Type | Name | Properties |
|----|------|------|------------|
| SHIFT_A | Shift | A조 | hours: "06:00-14:00" |
| SHIFT_B | Shift | B조 | hours: "14:00-22:00" |
| SHIFT_C | Shift | C조 | hours: "22:00-06:00" |
| PART_A | Product | PART-A | payload_kg: 1.0, class: "light" |
| PART_B | Product | PART-B | payload_kg: 2.5, class: "normal" |
| PART_C | Product | PART-C | payload_kg: 4.2, class: "heavy" |
| WORK_CYCLE | WorkCycle | 표준 작업 주기 | phases: [idle, approach, pick, retract, place] |

### 3.2 관계 인스턴스 설계 (~100개)

#### 3.2.1 Equipment 관계

```
HAS_COMPONENT:
  UR5e → Joint_0, Joint_1, Joint_2, Joint_3, Joint_4, Joint_5
  UR5e → CB_UR5e
  UR5e → TF_UR5e
```

#### 3.2.2 Measurement 관계

```
MOUNTED_ON:
  Axia80 → TF_UR5e

MEASURES:
  Axia80 → Fz, Fx, Fy, Tx, Ty, Tz

HAS_STATE:
  Fz → STATE_IDLE, STATE_LIGHT_LOAD, STATE_NORMAL_LOAD, ...
```

#### 3.2.3 Knowledge 관계

```
INDICATES (with confidence):
  PAT_COLLISION → CAUSE_PHYSICAL_CONTACT (0.95)
  PAT_OVERLOAD → CAUSE_PAYLOAD_EXCEEDED (0.90)
  PAT_OVERLOAD → CAUSE_GRIP_POSITION (0.70)
  PAT_VIBRATION → CAUSE_JOINT_WEAR (0.70)
  PAT_DRIFT → CAUSE_CALIBRATION_NEEDED (0.80)

TRIGGERS (with confidence):
  PAT_COLLISION → C153 (0.95)
  PAT_COLLISION → C119 (0.80)
  PAT_OVERLOAD → C189 (0.90)

CAUSED_BY:
  C153 → CAUSE_PHYSICAL_CONTACT
  C153 → CAUSE_UNEXPECTED_OBSTACLE
  C189 → CAUSE_PAYLOAD_EXCEEDED
  C189 → CAUSE_GRIP_POSITION
  C119 → CAUSE_PHYSICAL_CONTACT

RESOLVED_BY:
  CAUSE_PHYSICAL_CONTACT → RES_CLEAR_OBSTRUCTION
  CAUSE_PHYSICAL_CONTACT → RES_CHECK_PROGRAM_PATH
  CAUSE_PAYLOAD_EXCEEDED → RES_REDUCE_PAYLOAD
  CAUSE_GRIP_POSITION → RES_ADJUST_GRIP_POSITION
  CAUSE_CALIBRATION_NEEDED → RES_RECALIBRATE_SENSOR

DOCUMENTED_IN (with page):
  C153 → DOC_USER_MANUAL (page: 145)
  C153 → DOC_SERVICE_MANUAL (page: 67)
  C189 → DOC_SERVICE_MANUAL (page: 45)

PREVENTS:
  RES_CLEAR_OBSTRUCTION → C153
  RES_REDUCE_PAYLOAD → C189

AFFECTS:
  C189 → Joint_1
  C189 → Joint_2
```

### 3.3 ontology.json 구조

```json
{
  "version": "1.0",
  "created_at": "2026-01-22",
  "description": "UR5e 온톨로지 인스턴스",
  "statistics": {
    "total_entities": 50,
    "total_relationships": 100,
    "entities_by_domain": {
      "equipment": 12,
      "measurement": 20,
      "knowledge": 20,
      "context": 10
    }
  },
  "entities": [
    {
      "id": "UR5e",
      "type": "Robot",
      "domain": "equipment",
      "name": "UR5e 협동로봇",
      "properties": {
        "payload_kg": 5.0,
        "reach_mm": 850,
        "dof": 6
      }
    }
  ],
  "relationships": [
    {
      "source": "UR5e",
      "relation": "HAS_COMPONENT",
      "target": "Joint_0"
    },
    {
      "source": "PAT_COLLISION",
      "relation": "INDICATES",
      "target": "CAUSE_PHYSICAL_CONTACT",
      "properties": {
        "confidence": 0.95
      }
    }
  ]
}
```

### 3.4 lexicon.yaml 구조

```yaml
# 동의어 사전
version: "1.0"

# 엔티티 동의어
entities:
  UR5e:
    aliases: ["ur5e", "로봇", "robot", "협동로봇", "cobot"]

  Fz:
    aliases: ["fz", "z축", "z축 힘", "수직힘", "vertical force", "z force"]

  Axia80:
    aliases: ["axia80", "axia", "센서", "힘센서", "f/t sensor", "force sensor"]

  C153:
    aliases: ["c153", "153", "safety violation", "안전위반"]

  C189:
    aliases: ["c189", "189", "payload exceeded", "페이로드초과", "과부하"]

# 관계 동의어
relationships:
  CAUSED_BY:
    aliases: ["원인", "이유", "왜", "why", "because"]

  RESOLVED_BY:
    aliases: ["해결", "해결방법", "조치", "solution", "fix"]

# 상태 동의어
states:
  CRITICAL:
    aliases: ["위험", "심각", "critical", "danger", "위급"]

  WARNING:
    aliases: ["경고", "주의", "warning", "caution"]

# 패턴 동의어
patterns:
  PAT_COLLISION:
    aliases: ["충돌", "collision", "부딪힘", "접촉"]

  PAT_OVERLOAD:
    aliases: ["과부하", "overload", "오버로드", "과부하패턴"]
```

---

## 4. loader.py 인터페이스

```python
import json
import yaml
from pathlib import Path
from typing import Optional, Dict, Any

from .models import OntologySchema, Entity, Relationship

class OntologyLoader:
    """온톨로지 로더/저장"""

    DEFAULT_PATH = Path("data/processed/ontology/ontology.json")
    LEXICON_PATH = Path("data/processed/ontology/lexicon.yaml")

    @classmethod
    def load(cls, path: Optional[Path] = None) -> OntologySchema:
        """온톨로지 로드"""
        path = path or cls.DEFAULT_PATH
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return OntologySchema.from_dict(data)

    @classmethod
    def save(cls, schema: OntologySchema, path: Optional[Path] = None) -> None:
        """온톨로지 저장"""
        path = path or cls.DEFAULT_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(schema.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_lexicon(cls, path: Optional[Path] = None) -> Dict[str, Any]:
        """동의어 사전 로드"""
        path = path or cls.LEXICON_PATH
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    @classmethod
    def resolve_alias(cls, term: str, lexicon: Dict) -> Optional[str]:
        """동의어를 표준 ID로 변환"""
        term_lower = term.lower()
        for category in ["entities", "relationships", "states", "patterns"]:
            for entity_id, data in lexicon.get(category, {}).items():
                if term_lower in [a.lower() for a in data.get("aliases", [])]:
                    return entity_id
        return None
```

---

## 5. 온톨로지 연결

### 5.1 Phase 4 (스키마)와의 연결

| Phase 4 산출물 | Phase 5 사용 |
|---------------|-------------|
| EntityType | 인스턴스 타입 지정 |
| RelationType | 관계 타입 지정 |
| Entity 모델 | 인스턴스 생성 |
| Relationship 모델 | 관계 생성 |

### 5.2 Phase 6 (추론 규칙)와의 연결

| Phase 5 산출물 | Phase 6 사용처 |
|---------------|---------------|
| 상태 엔티티 | 상태 추론 규칙 |
| 패턴 엔티티 | 패턴 매칭 규칙 |
| 원인/해결책 관계 | 원인 추론 규칙 |

### 5.3 Phase 10-12 (RAG)와의 연결

| Phase 5 산출물 | RAG 사용처 |
|---------------|------------|
| ontology.json | OntologyEngine 데이터 |
| lexicon.yaml | 엔티티 인식 |
| 관계 그래프 | 경로 탐색 |

---

## 6. Unified_Spec.md 정합성 검증

### 6.1 온톨로지 인스턴스 요구사항

| Spec 요구사항 | Phase 5 구현 내용 | 충족 여부 |
|--------------|------------------|----------|
| ~50 엔티티 | Equipment(12) + Measurement(20) + Knowledge(20) + Context(10) | O |
| ~100 관계 | HAS_COMPONENT + MOUNTED_ON + ... | O |
| 동의어 사전 | lexicon.yaml | O |
| JSON 형식 | ontology.json | O |

### 6.2 API 명세 연결

| Spec API | Phase 5 지원 |
|----------|-------------|
| GET /api/v1/ontology/entity/{id} | OntologyLoader.load().get_entity() |
| GET /api/v1/ontology/relations/{id} | get_relationships_for_entity() |

---

## 7. 구현 체크리스트

### 7.1 코드 구현

- [x] `src/ontology/loader.py` - 온톨로지 로더 (184줄)
- [x] `scripts/build_ontology.py` - 구축 스크립트 (178줄)
- [x] `src/ontology/__init__.py` - loader 모듈 노출 업데이트

### 7.2 데이터 생성

- [x] `data/processed/ontology/ontology.json` - 온톨로지 인스턴스 (54 엔티티, 62 관계)
- [x] `data/processed/ontology/lexicon.yaml` - 동의어 사전 (기존 유지)

### 7.3 검증 명령어

```python
# 온톨로지 로드 검증
from src.ontology import OntologyLoader

schema = OntologyLoader.load()
print(schema.get_statistics())
# {'total_entities': 50, 'total_relationships': 100, ...}

# 엔티티 조회
ur5e = schema.get_entity("UR5e")
print(ur5e.name)  # UR5e 협동로봇

# 관계 조회
rels = schema.get_relationships_for_entity("PAT_COLLISION")
print(len(rels))  # 4

# 동의어 해석
lexicon = OntologyLoader.load_lexicon()
entity_id = OntologyLoader.resolve_alias("충돌", lexicon)
print(entity_id)  # PAT_COLLISION
```

---

## 8. 설계 결정 사항

### 8.1 JSON vs Neo4j

**결정**: JSON 파일로 온톨로지 저장

**근거**:
1. 단순성: 별도 DB 서버 불필요
2. 이식성: 파일 복사만으로 이동 가능
3. 규모: ~50 엔티티, ~100 관계는 JSON으로 충분
4. 확장성: 추후 Neo4j 마이그레이션 가능

### 8.2 동의어 사전 분리

**결정**: lexicon.yaml 별도 파일로 관리

**근거**:
1. 관심사 분리: 온톨로지 구조와 언어 매핑 분리
2. 확장성: 다국어 지원 용이
3. 유지보수: 동의어 추가/수정 용이

---

## 9. 다음 Phase 연결

### Phase 6 (추론 규칙)와의 연결

| Phase 5 산출물 | Phase 6 사용처 |
|---------------|---------------|
| 상태 엔티티 (STATE_*) | 상태 추론 규칙 |
| 패턴 엔티티 (PAT_*) | 패턴 감지 규칙 |
| INDICATES 관계 | 원인 추론 |
| TRIGGERS 관계 | 에러 예측 |

---

## 10. 실제 구현 결과 (리팩토링)

### 10.1 최종 통계

| 항목 | 설계 목표 | 실제 구현 |
|------|----------|----------|
| 총 엔티티 | ~50 | 54 |
| 총 관계 | ~100 | 62 |
| Equipment 도메인 | 12 | 9 |
| Measurement 도메인 | 20 | 14 |
| Knowledge 도메인 | 20 | 26 |
| Context 도메인 | 10 | 5 |

### 10.2 검증 결과

```bash
python scripts/build_ontology.py

============================================================
[*] Build Complete
============================================================

  Total Entities: 54
  Total Relationships: 62
  Validation: WARN (1 invalid - Sensor→Document)
```

---

*작성일: 2026-01-22*
*리팩토링일: 2026-01-22*
*Phase: 05 - 엔티티/관계 구축*
*문서 버전: v2.0*
