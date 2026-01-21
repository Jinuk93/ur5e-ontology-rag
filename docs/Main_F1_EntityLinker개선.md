# Main-F1: Entity Linker 개선

> **Phase**: Main-F1 (Foundation 개선 Phase 1)
> **목표**: 단순 정규식 → Lexicon + Rules + Embedding 기반 링킹
> **상태**: 진행 중

---

## 1. 개요

### 1.1 현재 상태 (Foundation)

현재 Entity Linker 기능은 `src/rag/query_analyzer.py`에 포함되어 있습니다.

**문제점:**

```python
# 에러 코드: 단순 정규식만 사용
self.error_code_pattern = re.compile(r'\b(C\d+(?:A\d+)?)\b', re.IGNORECASE)

# 부품명: 코드에 하드코딩된 딕셔너리
COMPONENT_NAMES = {
    "control box": ["control box", "컨트롤 박스", ...],
    ...
}
```

**한계:**
1. 동의어/한영 변환이 코드에 하드코딩됨 (유지보수 어려움)
2. 약어 처리 미흡 ("J3" → "Joint 3")
3. 유사 매칭 불가 (오타, 부분 일치)
4. 정규화 룰이 코드에 산재됨
5. 별도 모듈이 아닌 QueryAnalyzer에 종속됨

### 1.2 개선 목표

| 항목 | Foundation | Main-F1 |
|------|------------|---------|
| 동의어 사전 | 코드 하드코딩 | `lexicon.yaml` 파일 |
| 정규화 룰 | 코드 산재 | `rules.yaml` 파일 |
| 매칭 방식 | 정규식만 | Lexicon → Regex → Embedding |
| 모듈 구조 | QueryAnalyzer 내부 | **별도 EntityLinker 클래스** |
| 확장성 | 코드 수정 필요 | YAML 수정으로 가능 |

### 1.3 핵심 산출물

1. **`data/processed/ontology/lexicon.yaml`** - 동의어/별칭 사전
2. **`configs/rules.yaml`** - 정규화 룰
3. **`src/rag/entity_linker.py`** - 개선된 EntityLinker 클래스
4. **단위 테스트** - 한영/약어 변환 테스트

---

## 2. 설계

### 2.1 EntityLinker 아키텍처

```
┌───────────────────────────────────────────────────────────────┐
│                       EntityLinker                             │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│   입력: "컨트롤 박스에서 C-4A15 에러 발생"                      │
│         │                                                      │
│         ▼                                                      │
│   ┌─────────────────┐                                         │
│   │ 1. Lexicon 매칭  │ ← lexicon.yaml                          │
│   │    (동의어 사전)  │   "컨트롤 박스" → "Control Box"         │
│   └────────┬────────┘                                         │
│            │ 미매칭 시                                         │
│            ▼                                                   │
│   ┌─────────────────┐                                         │
│   │ 2. Regex 룰 매칭 │ ← rules.yaml                            │
│   │    (정규화 패턴)  │   "C-4A15" → "C4A15"                    │
│   └────────┬────────┘                                         │
│            │ 미매칭 시                                         │
│            ▼                                                   │
│   ┌─────────────────┐                                         │
│   │ 3. Embedding    │ ← OpenAI Embedding                      │
│   │    (유사도 검색) │   "컨트롤러" → "Control Box" (0.85)      │
│   └────────┬────────┘                                         │
│            │                                                   │
│            ▼                                                   │
│   출력: [                                                      │
│     {entity: "Control Box", node_id: "COMP_CONTROL_BOX",      │
│      confidence: 1.0, matched_by: "lexicon"},                 │
│     {entity: "C4A15", node_id: "ERR_C4A15",                   │
│      confidence: 0.95, matched_by: "regex"}                   │
│   ]                                                           │
└───────────────────────────────────────────────────────────────┘
```

### 2.2 매칭 우선순위

1. **Lexicon 매칭** (신뢰도 1.0)
   - 동의어 사전에서 직접 매칭
   - 가장 빠르고 정확함

2. **Regex 룰 매칭** (신뢰도 0.9~0.95)
   - 정규화 패턴으로 변환 후 매칭
   - 에러코드 포맷 정규화

3. **Embedding 매칭** (신뢰도 0.7~0.9)
   - 임베딩 유사도 검색
   - 오타, 부분 일치 처리
   - Fallback으로만 사용

### 2.3 데이터 흐름

```
QueryAnalyzer
    │
    ├── _detect_error_codes() ──┐
    │                            │
    ├── _detect_components() ───┼──▶ EntityLinker.link()
    │                            │
    └── 결과 통합 ◀──────────────┘
```

---

## 3. 파일 명세

### 3.1 lexicon.yaml

**위치**: `data/processed/ontology/lexicon.yaml`

```yaml
# ============================================================
# lexicon.yaml - 동의어/별칭 사전
# ============================================================
# 에러코드와 부품명의 동의어를 정의합니다.
# EntityLinker가 이 파일을 로드하여 매칭에 사용합니다.
# ============================================================

# ------------------------------------------------------------
# 에러 코드 동의어
# ------------------------------------------------------------
error_codes:
  # Communication Errors (C4)
  C4:
    canonical: "C4"
    synonyms: ["C-4", "c4", "C 4"]
    node_id: "ERR_C4"
    category: "communication"

  C4A1:
    canonical: "C4A1"
    synonyms: ["C-4A1", "c4a1", "C4-A1", "C 4 A 1"]
    node_id: "ERR_C4A1"
    category: "communication"

  C4A15:
    canonical: "C4A15"
    synonyms: ["C-4A15", "c4a15", "C4-A15", "C 4 A 15", "C-4-A-15"]
    node_id: "ERR_C4A15"
    category: "communication"

  # Safety Errors (C119, C153)
  C119:
    canonical: "C119"
    synonyms: ["C-119", "c119"]
    node_id: "ERR_C119"
    category: "safety"

  C153:
    canonical: "C153"
    synonyms: ["C-153", "c153"]
    node_id: "ERR_C153"
    category: "safety"

  # Overload Errors (C189)
  C189:
    canonical: "C189"
    synonyms: ["C-189", "c189"]
    node_id: "ERR_C189"
    category: "overload"

  # Joint Communication Errors (C50-C55)
  C50:
    canonical: "C50"
    synonyms: ["C-50", "c50"]
    node_id: "ERR_C50"
    category: "joint_communication"

  C50A100:
    canonical: "C50A100"
    synonyms: ["C-50A100", "c50a100", "C50-A100"]
    node_id: "ERR_C50A100"
    category: "joint_communication"

# ------------------------------------------------------------
# 부품명 동의어
# ------------------------------------------------------------
components:
  # 메인 컴포넌트
  control_box:
    canonical: "Control Box"
    synonyms:
      - "control box"
      - "컨트롤 박스"
      - "컨트롤박스"
      - "controller"
      - "컨트롤러"
      - "제어기"
      - "제어 박스"
      - "CB"
    node_id: "COMP_CONTROL_BOX"

  teach_pendant:
    canonical: "Teach Pendant"
    synonyms:
      - "teach pendant"
      - "티치 펜던트"
      - "티치펜던트"
      - "펜던트"
      - "pendant"
      - "TP"
    node_id: "COMP_TEACH_PENDANT"

  robot_arm:
    canonical: "Robot Arm"
    synonyms:
      - "robot arm"
      - "로봇 팔"
      - "로봇팔"
      - "arm"
      - "매니퓰레이터"
      - "manipulator"
    node_id: "COMP_ROBOT_ARM"

  # 보드류
  safety_control_board:
    canonical: "Safety Control Board"
    synonyms:
      - "safety control board"
      - "safety board"
      - "세이프티 보드"
      - "안전 제어 보드"
      - "SCB"
    node_id: "COMP_SAFETY_BOARD"

  motherboard:
    canonical: "Motherboard"
    synonyms:
      - "motherboard"
      - "마더보드"
      - "메인보드"
      - "mainboard"
    node_id: "COMP_MOTHERBOARD"

  # 조인트
  joint_0:
    canonical: "Joint 0"
    synonyms:
      - "joint 0"
      - "joint0"
      - "조인트 0"
      - "조인트0"
      - "base joint"
      - "베이스 조인트"
      - "J0"
    node_id: "COMP_JOINT_0"

  joint_1:
    canonical: "Joint 1"
    synonyms:
      - "joint 1"
      - "joint1"
      - "조인트 1"
      - "조인트1"
      - "shoulder joint"
      - "숄더 조인트"
      - "J1"
    node_id: "COMP_JOINT_1"

  joint_2:
    canonical: "Joint 2"
    synonyms:
      - "joint 2"
      - "joint2"
      - "조인트 2"
      - "조인트2"
      - "elbow joint"
      - "엘보우 조인트"
      - "J2"
    node_id: "COMP_JOINT_2"

  joint_3:
    canonical: "Joint 3"
    synonyms:
      - "joint 3"
      - "joint3"
      - "조인트 3"
      - "조인트3"
      - "wrist 1"
      - "손목 1"
      - "J3"
    node_id: "COMP_JOINT_3"

  joint_4:
    canonical: "Joint 4"
    synonyms:
      - "joint 4"
      - "joint4"
      - "조인트 4"
      - "조인트4"
      - "wrist 2"
      - "손목 2"
      - "J4"
    node_id: "COMP_JOINT_4"

  joint_5:
    canonical: "Joint 5"
    synonyms:
      - "joint 5"
      - "joint5"
      - "조인트 5"
      - "조인트5"
      - "wrist 3"
      - "손목 3"
      - "J5"
    node_id: "COMP_JOINT_5"

  # 케이블
  communication_cable:
    canonical: "Communication Cable"
    synonyms:
      - "communication cable"
      - "통신 케이블"
      - "통신선"
      - "comm cable"
    node_id: "COMP_COMM_CABLE"

  power_cable:
    canonical: "Power Cable"
    synonyms:
      - "power cable"
      - "전원 케이블"
      - "전원선"
    node_id: "COMP_POWER_CABLE"

  # 안전 장치
  emergency_stop:
    canonical: "Emergency Stop"
    synonyms:
      - "emergency stop"
      - "비상 정지"
      - "비상정지"
      - "e-stop"
      - "estop"
      - "이머전시 스톱"
    node_id: "COMP_ESTOP"

  # 툴
  gripper:
    canonical: "Gripper"
    synonyms:
      - "gripper"
      - "그리퍼"
      - "집게"
      - "end effector"
      - "엔드 이펙터"
    node_id: "COMP_GRIPPER"

  # 센서 (Main 추가)
  force_torque_sensor:
    canonical: "Force/Torque Sensor"
    synonyms:
      - "force torque sensor"
      - "ft sensor"
      - "힘토크 센서"
      - "힘/토크 센서"
      - "axia80"
      - "ATI Axia80"
    node_id: "COMP_FT_SENSOR"
```

### 3.2 rules.yaml

**위치**: `configs/rules.yaml`

```yaml
# ============================================================
# rules.yaml - 엔티티 정규화/링킹 룰
# ============================================================
# 정규식 패턴과 매칭 규칙을 정의합니다.
# ============================================================

# ------------------------------------------------------------
# 에러 코드 정규화 룰
# ------------------------------------------------------------
error_code:
  # 정규식 패턴 (우선순위 순)
  patterns:
    # C4A15, C50A100 형태
    - name: "full_format"
      regex: 'C-?(\d+)A-?(\d+)'
      normalize: 'C{1}A{2}'
      examples: ["C-4A15 → C4A15", "C50-A100 → C50A100"]

    # C4, C50 형태 (기본)
    - name: "base_format"
      regex: 'C-?(\d+)'
      normalize: 'C{1}'
      examples: ["C-4 → C4", "C 50 → C50"]

  # 유효성 검증
  validation:
    base_range: [0, 55]  # C0 ~ C55만 유효

  # 대소문자 정책
  case_policy: "upper"  # 항상 대문자로 정규화

# ------------------------------------------------------------
# 부품명 매칭 룰
# ------------------------------------------------------------
component:
  # 매칭 순서 (우선순위)
  matching:
    order:
      - "lexicon"     # 1. 동의어 사전 매칭 (가장 정확)
      - "regex"       # 2. 정규식 패턴 매칭
      - "embedding"   # 3. 임베딩 유사도 (fallback)

    # 최소 신뢰도 (이하면 미매칭 처리)
    min_confidence: 0.7

    # Embedding 매칭 설정
    embedding:
      enabled: true
      threshold: 0.75   # 유사도 임계값
      top_k: 3          # 후보 개수

  # 정규식 패턴
  patterns:
    # Joint + 숫자 패턴
    - name: "joint_number"
      regex: '(?:joint|조인트|J)\s*(\d)'
      normalize: 'Joint {1}'
      examples: ["J3 → Joint 3", "조인트 1 → Joint 1"]

# ------------------------------------------------------------
# 전처리 룰
# ------------------------------------------------------------
preprocessing:
  # 공백 정규화
  normalize_whitespace: true

  # 특수문자 처리
  remove_special_chars: false  # 에러코드에 하이픈 있을 수 있음

  # 대소문자
  case_sensitive: false

# ------------------------------------------------------------
# 후처리 룰
# ------------------------------------------------------------
postprocessing:
  # 중복 제거
  deduplicate: true

  # 신뢰도 순 정렬
  sort_by_confidence: true
```

### 3.3 entity_linker.py 인터페이스

**위치**: `src/rag/entity_linker.py`

```python
"""
Entity Linker - 엔티티 정규화 및 링킹

자연어 텍스트에서 추출된 엔티티를 온톨로지 노드에 링킹합니다.

매칭 순서:
1. Lexicon 매칭 (동의어 사전)
2. Regex 룰 매칭 (정규화 패턴)
3. Embedding 유사도 (fallback)
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path
import yaml
import re


@dataclass
class LinkedEntity:
    """링킹된 엔티티"""
    entity: str           # 원본 텍스트
    canonical: str        # 정규화된 이름
    node_id: str          # 온톨로지 노드 ID
    entity_type: str      # "error_code" | "component"
    confidence: float     # 신뢰도 (0.0 ~ 1.0)
    matched_by: str       # "lexicon" | "regex" | "embedding"
    metadata: Dict[str, Any] = None  # 추가 메타데이터


class EntityLinker:
    """
    엔티티 링커

    사용 예시:
        linker = EntityLinker(
            lexicon_path="data/processed/ontology/lexicon.yaml",
            rules_path="configs/rules.yaml"
        )

        entities = ["컨트롤 박스", "C-4A15"]
        linked = linker.link(entities)

        for e in linked:
            print(f"{e.entity} → {e.canonical} ({e.confidence})")
    """

    def __init__(
        self,
        lexicon_path: str,
        rules_path: str,
        embedding_model: str = "text-embedding-3-small"
    ):
        """
        초기화

        Args:
            lexicon_path: lexicon.yaml 경로
            rules_path: rules.yaml 경로
            embedding_model: 임베딩 모델 (fallback용)
        """
        self.lexicon = self._load_yaml(lexicon_path)
        self.rules = self._load_yaml(rules_path)
        self.embedding_model = embedding_model

        # 동의어 → 정규 이름 역매핑 구축
        self._build_reverse_mapping()

    def link(
        self,
        entities: List[str],
        entity_types: List[str] = None
    ) -> List[LinkedEntity]:
        """
        엔티티 링킹 수행

        Args:
            entities: 링킹할 엔티티 리스트
            entity_types: 엔티티 타입 힌트 (없으면 자동 감지)

        Returns:
            링킹된 엔티티 리스트
        """
        results = []

        for i, entity in enumerate(entities):
            entity_type = entity_types[i] if entity_types else None

            # 1. Lexicon 매칭
            linked = self._match_lexicon(entity, entity_type)
            if linked:
                results.append(linked)
                continue

            # 2. Regex 룰 매칭
            linked = self._match_rules(entity, entity_type)
            if linked:
                results.append(linked)
                continue

            # 3. Embedding fallback
            linked = self._match_embedding(entity, entity_type)
            if linked:
                results.append(linked)

        return results

    def link_from_text(self, text: str) -> List[LinkedEntity]:
        """
        텍스트에서 엔티티 추출 및 링킹

        Args:
            text: 분석할 텍스트

        Returns:
            링킹된 엔티티 리스트
        """
        # 에러코드 추출
        error_codes = self._extract_error_codes(text)

        # 부품명 추출
        components = self._extract_components(text)

        # 링킹
        all_entities = error_codes + components
        entity_types = (
            ["error_code"] * len(error_codes) +
            ["component"] * len(components)
        )

        return self.link(all_entities, entity_types)

    def _match_lexicon(
        self,
        entity: str,
        entity_type: Optional[str]
    ) -> Optional[LinkedEntity]:
        """Lexicon(동의어 사전) 매칭"""
        # 구현 예정
        pass

    def _match_rules(
        self,
        entity: str,
        entity_type: Optional[str]
    ) -> Optional[LinkedEntity]:
        """Regex 룰 매칭"""
        # 구현 예정
        pass

    def _match_embedding(
        self,
        entity: str,
        entity_type: Optional[str]
    ) -> Optional[LinkedEntity]:
        """Embedding 유사도 매칭 (fallback)"""
        # 구현 예정
        pass

    def _build_reverse_mapping(self):
        """동의어 → 정규이름 역매핑 구축"""
        # 구현 예정
        pass

    def _extract_error_codes(self, text: str) -> List[str]:
        """텍스트에서 에러코드 추출"""
        # 구현 예정
        pass

    def _extract_components(self, text: str) -> List[str]:
        """텍스트에서 부품명 추출"""
        # 구현 예정
        pass

    @staticmethod
    def _load_yaml(path: str) -> dict:
        """YAML 파일 로드"""
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
```

---

## 4. 구현 태스크

### 4.1 Task 목록

```
Main-F1-1: lexicon.yaml 작성
├── data/processed/ontology/lexicon.yaml 생성
├── 에러코드 동의어 정의 (최소 20개)
├── 부품명 동의어 정의 (최소 15개)
├── 한영 변환, 약어 포함
└── 검증: YAML 문법 검사

Main-F1-2: rules.yaml 작성
├── configs/rules.yaml 생성
├── 에러코드 정규식 패턴 정의
├── 부품명 매칭 룰 정의
├── 전처리/후처리 룰 정의
└── 검증: 샘플 케이스 테스트

Main-F1-3: EntityLinker 클래스 구현
├── src/rag/entity_linker.py 작성
├── Lexicon 매칭 구현
├── Regex 룰 매칭 구현
├── Embedding fallback 구현
├── 역매핑 구축 구현
└── 검증: 단위 테스트

Main-F1-4: QueryAnalyzer 통합
├── src/rag/query_analyzer.py 수정
├── EntityLinker 호출로 교체
├── 기존 하드코딩 제거
└── 검증: 기존 테스트 통과

Main-F1-5: 단위 테스트 작성
├── tests/unit/test_entity_linker.py 작성
├── Lexicon 매칭 테스트 (10개+)
├── Regex 룰 테스트 (10개+)
├── 한영/약어 변환 테스트 (5개+)
└── 검증: 테스트 커버리지 80%+
```

### 4.2 예상 일정

| Task | 설명 | 소요 |
|------|------|------|
| Main-F1-1 | lexicon.yaml 작성 | - |
| Main-F1-2 | rules.yaml 작성 | - |
| Main-F1-3 | EntityLinker 구현 | - |
| Main-F1-4 | QueryAnalyzer 통합 | - |
| Main-F1-5 | 단위 테스트 | - |

---

## 5. 테스트 케이스

### 5.1 Lexicon 매칭 테스트

| 입력 | 예상 출력 | 매칭 방식 |
|------|----------|----------|
| "컨트롤 박스" | "Control Box" | lexicon |
| "컨트롤러" | "Control Box" | lexicon |
| "CB" | "Control Box" | lexicon |
| "J3" | "Joint 3" | lexicon |
| "조인트 3" | "Joint 3" | lexicon |

### 5.2 Regex 룰 테스트

| 입력 | 예상 출력 | 매칭 방식 |
|------|----------|----------|
| "C-4A15" | "C4A15" | regex |
| "c4a15" | "C4A15" | regex |
| "C 4 A 15" | "C4A15" | regex |
| "C-50" | "C50" | regex |
| "c50a100" | "C50A100" | regex |

### 5.3 통합 테스트

| 쿼리 | 예상 결과 |
|------|----------|
| "컨트롤 박스에서 C-4A15 에러" | ["Control Box", "C4A15"] |
| "J3 통신 오류" | ["Joint 3"] |
| "c119 안전 정지" | ["C119"] |

---

## 6. 코드 리뷰 체크포인트

### 6.1 정합성
- [ ] lexicon.yaml의 node_id가 Neo4j 노드와 일치하는가?
- [ ] rules.yaml의 정규식이 올바른가?
- [ ] Main__Spec.md의 인터페이스와 일치하는가?

### 6.2 커버리지
- [ ] 주요 에러코드 20개 이상 정의되었는가?
- [ ] 주요 부품명 15개 이상 정의되었는가?
- [ ] 한영/약어 변환이 충분히 정의되었는가?

### 6.3 테스트
- [ ] 단위 테스트가 25개 이상인가?
- [ ] 한영/약어 변환 테스트가 포함되었는가?
- [ ] 엣지 케이스가 테스트되었는가?

### 6.4 성능
- [ ] Lexicon 로드 시간이 적절한가? (< 100ms)
- [ ] 링킹 성능이 적절한가? (< 50ms per entity)
- [ ] Embedding fallback 시 지연이 허용 범위인가? (< 500ms)

### 6.5 호환성
- [ ] 기존 벤치마크 테스트가 통과하는가?
- [ ] QueryAnalyzer 동작이 유지되는가?

---

## 7. 완료 기준

### 7.1 필수 항목
- [ ] lexicon.yaml에 최소 20개 에러코드, 15개 부품 동의어 정의
- [ ] rules.yaml 작성 완료
- [ ] EntityLinker 클래스 구현 완료
- [ ] QueryAnalyzer 통합 완료
- [ ] 단위 테스트 25개 이상, 통과율 100%

### 7.2 품질 항목
- [ ] 기존 벤치마크 성능 저하 없음
- [ ] 한영/약어 변환 정확도 95%+
- [ ] 코드 리뷰 체크리스트 통과

---

## 8. 다음 단계

Main-F1 완료 후:
- **Main-F2**: Trace 시스템 완성 (audit_trail.jsonl)
- **Main-F3**: 메타데이터 정비 (sources.yaml, chunk_manifest)

---

**작성일**: 2024-01-21
**참조**: Main__Spec.md (Section 10), Main__ROADMAP.md (Main-F1)
