# Phase 11: Entity Linker 개선

> **상태**: ✅ 완료
> **도메인**: 지식 레이어 (Knowledge)
> **목표**: Lexicon + Rules 기반 엔티티 링킹 정확도 향상
> **이전 명칭**: Main-F1

---

## 1. 개요

기존 LLM 기반 엔티티 추출의 한계를 보완하기 위해
도메인 특화 Lexicon(동의어 사전)과 Rules(정규화 룰)를 구축하여
엔티티 링킹 정확도를 향상시키는 단계.

---

## 2. 태스크

| # | 태스크 | 상태 |
|---|--------|------|
| 1 | lexicon.yaml 작성 (에러코드) | ✅ |
| 2 | lexicon.yaml 작성 (컴포넌트) | ✅ |
| 3 | rules.yaml 작성 | ✅ |
| 4 | EntityLinker 클래스 개선 | ✅ |
| 5 | 단위 테스트 작성 | ✅ |

---

## 3. 3단계 매칭 전략

### 3.1 매칭 우선순위

```
┌─────────────────────────────────────────────────────────────┐
│                    Entity Linker 매칭 전략                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [1단계] Lexicon 매칭 (우선)                                 │
│      └─▶ 동의어 사전에서 정확히 매칭                         │
│      └─▶ "제어박스" → "Control Box" (canonical)             │
│                                                             │
│  [2단계] Rules 매칭                                          │
│      └─▶ 정규 표현식 패턴 매칭                               │
│      └─▶ "C154A3", "c154a3" → "C154A3" (정규화)             │
│                                                             │
│  [3단계] Embedding Fallback (비활성)                         │
│      └─▶ 의미 유사도 기반 매칭                               │
│      └─▶ 현재 미사용 (향후 활성화 가능)                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 매칭 흐름

```
입력: "제어박스 팬 에러 c154a3"
         │
         ▼
┌─────────────────┐
│ 1. Lexicon 매칭 │ "제어박스" → "Control Box"
└────────┬────────┘
         ▼
┌─────────────────┐
│ 2. Rules 매칭   │ "c154a3" → "C154A3"
└────────┬────────┘
         ▼
결과: ["Control Box", "C154A3"]
```

---

## 4. Lexicon 구조

### 4.1 lexicon.yaml 형식

```yaml
# data/processed/ontology/lexicon.yaml

error_codes:
  C154A3:
    canonical: "C154A3"
    synonyms:
      - "c154a3"
      - "C154-A3"
      - "팬 오작동 에러"
      - "control box fan error"
    category: "control_box"
    severity: "warning"

  C15402:
    canonical: "C15402"
    synonyms:
      - "c15402"
      - "전압 에러"
      - "voltage error"
    category: "control_box"
    severity: "error"

components:
  Control Box:
    canonical: "Control Box"
    synonyms:
      - "제어박스"
      - "제어 박스"
      - "컨트롤 박스"
      - "controller"
      - "control unit"
    node_type: "Component"

  Joint 0:
    canonical: "Joint 0"
    synonyms:
      - "조인트 0"
      - "joint0"
      - "J0"
      - "base joint"
      - "베이스 조인트"
    node_type: "Component"
```

### 4.2 Lexicon 통계

| 카테고리 | 항목 수 | 총 동의어 |
|----------|---------|----------|
| 에러코드 | 20 | 80+ |
| 컴포넌트 | 21 | 100+ |
| **총계** | **41** | **180+** |

---

## 5. Rules 구조

### 5.1 rules.yaml 형식

```yaml
# configs/rules.yaml

normalization_rules:
  # 에러코드 정규화
  - name: "error_code_uppercase"
    pattern: "([csjCSJ][0-9]{1,2}[a-fA-F0-9]{3,4})"
    action: "uppercase"
    description: "에러코드를 대문자로 정규화"

  - name: "error_code_remove_dash"
    pattern: "([CSJ][0-9]{1,2})-([A-F0-9]{3,4})"
    replacement: "\\1\\2"
    description: "에러코드에서 대시 제거"

  # 컴포넌트 정규화
  - name: "joint_normalize"
    pattern: "joint\\s*([0-5])"
    replacement: "Joint \\1"
    flags: "IGNORECASE"
    description: "Joint N 형식으로 정규화"

  - name: "control_box_normalize"
    patterns:
      - "control\\s*box"
      - "컨트롤\\s*박스"
      - "제어\\s*박스"
    canonical: "Control Box"
    flags: "IGNORECASE"
```

### 5.2 Rules 통계

| 룰 유형 | 개수 |
|---------|------|
| 에러코드 정규화 | 5 |
| 컴포넌트 정규화 | 8 |
| 공백/특수문자 처리 | 4 |
| **총계** | **17** |

---

## 6. 구현

### 6.1 EntityLinker 클래스

```python
# src/rag/entity_linker.py

from typing import List, Dict, Optional
import re
import yaml

class EntityLinker:
    def __init__(
        self,
        lexicon_path: str = "data/processed/ontology/lexicon.yaml",
        rules_path: str = "configs/rules.yaml"
    ):
        self.lexicon = self._load_lexicon(lexicon_path)
        self.rules = self._load_rules(rules_path)
        self.synonym_map = self._build_synonym_map()

    def link(self, text: str) -> List[LinkedEntity]:
        """텍스트에서 엔티티 추출 및 링킹"""
        entities = []

        # 1단계: Lexicon 매칭
        lexicon_matches = self._match_lexicon(text)
        entities.extend(lexicon_matches)

        # 2단계: Rules 매칭
        rule_matches = self._match_rules(text)
        entities.extend(rule_matches)

        # 중복 제거 및 정렬
        return self._deduplicate(entities)

    def _match_lexicon(self, text: str) -> List[LinkedEntity]:
        """Lexicon 기반 매칭"""
        matches = []
        text_lower = text.lower()

        for synonym, canonical in self.synonym_map.items():
            if synonym.lower() in text_lower:
                matches.append(LinkedEntity(
                    mention=synonym,
                    canonical=canonical.canonical,
                    node_type=canonical.node_type,
                    confidence=1.0,
                    method="lexicon"
                ))

        return matches

    def _match_rules(self, text: str) -> List[LinkedEntity]:
        """Rules 기반 매칭"""
        matches = []

        for rule in self.rules:
            pattern = re.compile(rule.pattern, re.IGNORECASE)
            for match in pattern.finditer(text):
                normalized = self._apply_normalization(match.group(), rule)
                matches.append(LinkedEntity(
                    mention=match.group(),
                    canonical=normalized,
                    node_type=rule.get("node_type", "Unknown"),
                    confidence=0.9,
                    method="rules"
                ))

        return matches

    def normalize(self, text: str) -> str:
        """텍스트 정규화"""
        for rule in self.rules:
            if rule.get("action") == "uppercase":
                text = re.sub(rule["pattern"], lambda m: m.group().upper(), text)
            elif rule.get("replacement"):
                text = re.sub(rule["pattern"], rule["replacement"], text, flags=re.IGNORECASE)
        return text
```

### 6.2 LinkedEntity 스키마

```python
@dataclass
class LinkedEntity:
    mention: str        # 원본 텍스트에서 발견된 표현
    canonical: str      # 정규화된 표준 이름
    node_type: str      # 노드 타입 (ErrorCode, Component 등)
    confidence: float   # 매칭 신뢰도 (0.0 ~ 1.0)
    method: str         # 매칭 방법 (lexicon, rules, embedding)
```

---

## 7. 산출물

### 7.1 파일 목록

| 파일 | 내용 | 크기 |
|------|------|------|
| `data/processed/ontology/lexicon.yaml` | 동의어 사전 | 8.8KB |
| `configs/rules.yaml` | 정규화 룰 | 3.9KB |
| `src/rag/entity_linker.py` | EntityLinker 클래스 | ~400 lines |
| `tests/test_entity_linker.py` | 단위 테스트 | 23개 테스트 |

### 7.2 테스트 결과

```
========================= test session starts ==========================
tests/test_entity_linker.py::test_lexicon_match_error_code PASSED
tests/test_entity_linker.py::test_lexicon_match_korean PASSED
tests/test_entity_linker.py::test_rules_normalize_uppercase PASSED
tests/test_entity_linker.py::test_rules_normalize_joint PASSED
tests/test_entity_linker.py::test_combined_matching PASSED
...
========================= 23 passed in 0.45s ===========================
```

---

## 8. 검증 체크리스트

- [x] lexicon.yaml: 20개 에러코드, 21개 컴포넌트
- [x] rules.yaml: 17개 정규화 룰
- [x] Lexicon 매칭 동작 확인
- [x] Rules 매칭 동작 확인
- [x] 한글 동의어 처리 확인
- [x] 23개 단위 테스트 100% 통과

---

## 9. 다음 단계

→ [Phase 12: Trace 시스템](12_Trace시스템.md)

---

**Phase**: 11 / 19
**마일스톤**: Foundation 개선 (Phase 11-13) 시작
**작성일**: 2026-01-22
