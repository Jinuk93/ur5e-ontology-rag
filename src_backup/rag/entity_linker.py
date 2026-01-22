# ============================================================
# src/rag/entity_linker.py - 엔티티 링커
# ============================================================
# 자연어 텍스트에서 추출된 엔티티를 온톨로지 노드에 링킹합니다.
#
# 매칭 순서:
# 1. Lexicon 매칭 (동의어 사전) - 신뢰도 1.0
# 2. Regex 룰 매칭 (정규화 패턴) - 신뢰도 0.95
# 3. Embedding 유사도 (fallback) - 신뢰도 0.7~0.9
# ============================================================

import os
import sys
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

import yaml

# 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


# ============================================================
# [1] 데이터 클래스
# ============================================================

@dataclass
class LinkedEntity:
    """링킹된 엔티티"""
    entity: str           # 원본 텍스트
    canonical: str        # 정규화된 이름
    node_id: str          # 온톨로지 노드 ID
    entity_type: str      # "error_code" | "component"
    confidence: float     # 신뢰도 (0.0 ~ 1.0)
    matched_by: str       # "lexicon" | "regex" | "embedding"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self):
        return (
            f"LinkedEntity("
            f"'{self.entity}' → '{self.canonical}' "
            f"[{self.matched_by}, {self.confidence:.2f}])"
        )


# ============================================================
# [2] EntityLinker 클래스
# ============================================================

class EntityLinker:
    """
    엔티티 링커

    사용자 질문에서 추출된 엔티티(에러코드, 부품명)를
    온톨로지 노드에 링킹합니다.

    매칭 우선순위:
    1. Lexicon (동의어 사전) - 가장 정확
    2. Regex (정규화 룰) - 포맷 정규화
    3. Embedding (유사도) - fallback

    사용 예시:
        linker = EntityLinker()
        results = linker.link_from_text("컨트롤 박스에서 C-4A15 에러 발생")

        for r in results:
            print(f"{r.entity} → {r.canonical} ({r.confidence})")
    """

    def __init__(
        self,
        lexicon_path: str = None,
        rules_path: str = None
    ):
        """
        초기화

        Args:
            lexicon_path: lexicon.yaml 경로 (None이면 기본 경로)
            rules_path: rules.yaml 경로 (None이면 기본 경로)
        """
        # 기본 경로 설정
        if lexicon_path is None:
            lexicon_path = os.path.join(
                project_root,
                "data/processed/ontology/lexicon.yaml"
            )
        if rules_path is None:
            rules_path = os.path.join(
                project_root,
                "configs/rules.yaml"
            )

        # YAML 로드
        self.lexicon = self._load_yaml(lexicon_path)
        self.rules = self._load_yaml(rules_path)

        # 역매핑 구축 (동의어 → 정규 이름)
        self._build_reverse_mapping()

        # 에러코드 정규식 패턴 컴파일
        self._compile_patterns()

        print("[OK] EntityLinker initialized")

    # --------------------------------------------------------
    # [2.1] 초기화 헬퍼
    # --------------------------------------------------------

    def _load_yaml(self, path: str) -> dict:
        """YAML 파일 로드"""
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _build_reverse_mapping(self):
        """동의어 → 정규 이름 역매핑 구축"""
        # 에러코드 역매핑
        self.error_code_mapping = {}
        for code, info in self.lexicon.get('error_codes', {}).items():
            canonical = info['canonical']
            node_id = info['node_id']
            category = info.get('category', '')

            # 정규 이름 자체 추가
            self.error_code_mapping[canonical.lower()] = {
                'canonical': canonical,
                'node_id': node_id,
                'category': category
            }

            # 동의어 추가
            for syn in info.get('synonyms', []):
                self.error_code_mapping[syn.lower()] = {
                    'canonical': canonical,
                    'node_id': node_id,
                    'category': category
                }

        # 부품명 역매핑
        self.component_mapping = {}
        for comp_key, info in self.lexicon.get('components', {}).items():
            canonical = info['canonical']
            node_id = info['node_id']

            # 정규 이름 자체 추가
            self.component_mapping[canonical.lower()] = {
                'canonical': canonical,
                'node_id': node_id
            }

            # 동의어 추가
            for syn in info.get('synonyms', []):
                self.component_mapping[syn.lower()] = {
                    'canonical': canonical,
                    'node_id': node_id
                }

    def _compile_patterns(self):
        """정규식 패턴 컴파일"""
        # 에러코드 패턴
        self.error_patterns = []
        for pattern in self.rules.get('error_code', {}).get('patterns', []):
            self.error_patterns.append({
                'name': pattern['name'],
                'regex': re.compile(pattern['regex'], re.IGNORECASE),
                'normalize': pattern['normalize']
            })

        # 부품명 패턴
        self.component_patterns = []
        for pattern in self.rules.get('component', {}).get('patterns', []):
            self.component_patterns.append({
                'name': pattern['name'],
                'regex': re.compile(pattern['regex'], re.IGNORECASE),
                'normalize': pattern['normalize']
            })

        # 에러코드 유효 범위
        error_config = self.rules.get('error_code', {}).get('validation', {})
        base_range = error_config.get('base_range', [0, 55])
        self.valid_error_bases = set(range(base_range[0], base_range[1] + 1))

    # --------------------------------------------------------
    # [2.2] 메인 링킹 메서드
    # --------------------------------------------------------

    def link(
        self,
        entities: List[str],
        entity_types: List[str] = None
    ) -> List[LinkedEntity]:
        """
        엔티티 링킹 수행

        Args:
            entities: 링킹할 엔티티 리스트
            entity_types: 엔티티 타입 힌트 ["error_code" | "component"]

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

            # 3. (선택) Embedding fallback - 나중에 구현

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

    # --------------------------------------------------------
    # [2.3] Lexicon 매칭
    # --------------------------------------------------------

    def _match_lexicon(
        self,
        entity: str,
        entity_type: Optional[str]
    ) -> Optional[LinkedEntity]:
        """
        Lexicon(동의어 사전) 매칭

        Args:
            entity: 매칭할 엔티티
            entity_type: 엔티티 타입 힌트

        Returns:
            LinkedEntity 또는 None
        """
        entity_lower = entity.lower().strip()

        # 에러코드 매칭 시도
        if entity_type in [None, "error_code"]:
            if entity_lower in self.error_code_mapping:
                info = self.error_code_mapping[entity_lower]
                return LinkedEntity(
                    entity=entity,
                    canonical=info['canonical'],
                    node_id=info['node_id'],
                    entity_type="error_code",
                    confidence=1.0,
                    matched_by="lexicon",
                    metadata={'category': info.get('category', '')}
                )

        # 부품명 매칭 시도
        if entity_type in [None, "component"]:
            if entity_lower in self.component_mapping:
                info = self.component_mapping[entity_lower]
                return LinkedEntity(
                    entity=entity,
                    canonical=info['canonical'],
                    node_id=info['node_id'],
                    entity_type="component",
                    confidence=1.0,
                    matched_by="lexicon"
                )

        return None

    # --------------------------------------------------------
    # [2.4] Regex 룰 매칭
    # --------------------------------------------------------

    def _match_rules(
        self,
        entity: str,
        entity_type: Optional[str]
    ) -> Optional[LinkedEntity]:
        """
        Regex 룰 매칭

        Args:
            entity: 매칭할 엔티티
            entity_type: 엔티티 타입 힌트

        Returns:
            LinkedEntity 또는 None
        """
        # 에러코드 패턴 매칭
        if entity_type in [None, "error_code"]:
            for pattern in self.error_patterns:
                match = pattern['regex'].search(entity)
                if match:
                    # 정규화
                    normalized = self._normalize_error_code(
                        match, pattern['normalize']
                    )
                    if normalized:
                        # 정규화된 값으로 lexicon 재검색
                        if normalized.lower() in self.error_code_mapping:
                            info = self.error_code_mapping[normalized.lower()]
                            return LinkedEntity(
                                entity=entity,
                                canonical=info['canonical'],
                                node_id=info['node_id'],
                                entity_type="error_code",
                                confidence=0.95,
                                matched_by="regex",
                                metadata={'pattern': pattern['name']}
                            )
                        else:
                            # lexicon에 없어도 유효한 에러코드면 반환
                            return LinkedEntity(
                                entity=entity,
                                canonical=normalized,
                                node_id=f"ERR_{normalized}",
                                entity_type="error_code",
                                confidence=0.9,
                                matched_by="regex",
                                metadata={'pattern': pattern['name']}
                            )

        # 부품명 패턴 매칭
        if entity_type in [None, "component"]:
            for pattern in self.component_patterns:
                match = pattern['regex'].search(entity)
                if match:
                    normalized = self._normalize_component(
                        match, pattern['normalize']
                    )
                    if normalized:
                        # 정규화된 값으로 lexicon 재검색
                        if normalized.lower() in self.component_mapping:
                            info = self.component_mapping[normalized.lower()]
                            return LinkedEntity(
                                entity=entity,
                                canonical=info['canonical'],
                                node_id=info['node_id'],
                                entity_type="component",
                                confidence=0.95,
                                matched_by="regex",
                                metadata={'pattern': pattern['name']}
                            )

        return None

    def _normalize_error_code(
        self,
        match: re.Match,
        template: str
    ) -> Optional[str]:
        """
        에러코드 정규화

        Args:
            match: 정규식 매치 객체
            template: 정규화 템플릿 (예: 'C{1}A{2}')

        Returns:
            정규화된 에러코드 또는 None
        """
        groups = match.groups()

        # 기본 번호 추출
        if len(groups) >= 1:
            base_num = int(groups[0])

            # 유효 범위 검증
            if base_num not in self.valid_error_bases:
                return None

            # 템플릿 적용
            result = template
            for i, g in enumerate(groups, 1):
                result = result.replace(f'{{{i}}}', g if g else '')

            # 빈 부분 제거 (예: C4A → C4)
            result = result.rstrip('A')

            return result.upper()

        return None

    def _normalize_component(
        self,
        match: re.Match,
        template: str
    ) -> Optional[str]:
        """
        부품명 정규화

        Args:
            match: 정규식 매치 객체
            template: 정규화 템플릿

        Returns:
            정규화된 부품명 또는 None
        """
        groups = match.groups()

        result = template
        for i, g in enumerate(groups, 1):
            result = result.replace(f'{{{i}}}', g if g else '')

        return result

    # --------------------------------------------------------
    # [2.5] 엔티티 추출
    # --------------------------------------------------------

    def _extract_error_codes(self, text: str) -> List[str]:
        """
        텍스트에서 에러코드 추출

        Args:
            text: 분석할 텍스트

        Returns:
            추출된 에러코드 리스트
        """
        results = []
        seen = set()

        # 모든 에러코드 패턴으로 검색
        for pattern in self.error_patterns:
            for match in pattern['regex'].finditer(text):
                matched_text = match.group(0)
                if matched_text.lower() not in seen:
                    seen.add(matched_text.lower())
                    results.append(matched_text)

        return results

    def _extract_components(self, text: str) -> List[str]:
        """
        텍스트에서 부품명 추출

        Args:
            text: 분석할 텍스트

        Returns:
            추출된 부품명 리스트
        """
        results = []
        text_lower = text.lower()
        matched_spans = []  # 이미 매칭된 위치 추적

        # 긴 동의어부터 매칭 (예: "safety control board"가 "control box"보다 먼저)
        sorted_synonyms = sorted(
            self.component_mapping.keys(),
            key=len,
            reverse=True
        )

        for synonym in sorted_synonyms:
            start = 0
            while True:
                pos = text_lower.find(synonym, start)
                if pos == -1:
                    break

                end = pos + len(synonym)

                # 이미 다른 부품명에 포함된 위치인지 확인
                is_overlapping = any(
                    s <= pos < e or s < end <= e
                    for s, e in matched_spans
                )

                if not is_overlapping:
                    # 원본 텍스트에서 해당 부분 추출
                    original = text[pos:end]
                    canonical = self.component_mapping[synonym]['canonical']

                    # 중복 체크 (canonical 기준)
                    if canonical not in [r for r in results]:
                        results.append(original)
                    matched_spans.append((pos, end))

                start = pos + 1

        # 정규식 패턴으로도 검색
        for pattern in self.component_patterns:
            for match in pattern['regex'].finditer(text):
                matched_text = match.group(0)
                normalized = self._normalize_component(match, pattern['normalize'])

                if normalized:
                    # 중복 체크
                    is_dup = False
                    for r in results:
                        if r.lower() == matched_text.lower():
                            is_dup = True
                            break
                        # 이미 같은 canonical이 있는지 확인
                        linked = self._match_lexicon(r, "component")
                        if linked and linked.canonical.lower() == normalized.lower():
                            is_dup = True
                            break

                    if not is_dup:
                        results.append(matched_text)

        return results


# ============================================================
# 테스트 코드 (직접 실행 시)
# ============================================================

if __name__ == "__main__":
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 60)
    print("[*] EntityLinker Test")
    print("=" * 60)

    linker = EntityLinker()

    # 테스트 케이스
    test_texts = [
        # 에러코드 테스트
        "C-4A15 에러가 발생했습니다",
        "c50a100 또는 C51 에러 확인",
        "C 4 A 15 오류 해결법",

        # 부품명 테스트
        "컨트롤 박스에서 문제 발생",
        "J3 조인트 통신 오류",
        "Safety Control Board 점검 필요",

        # 혼합 테스트
        "컨트롤러에서 C-119 에러 발생",
        "3번 조인트 C4A15 통신 오류",
        "티치 펜던트 C153 안전 정지",
    ]

    for i, text in enumerate(test_texts, 1):
        print(f"\n{'─' * 60}")
        print(f"[Test {i}] {text}")
        print(f"{'─' * 60}")

        results = linker.link_from_text(text)

        if results:
            for r in results:
                print(f"  → {r.entity} → {r.canonical}")
                print(f"    type={r.entity_type}, confidence={r.confidence:.2f}, by={r.matched_by}")
        else:
            print("  (no entities found)")

    print("\n" + "=" * 60)
    print("[OK] EntityLinker test completed!")
    print("=" * 60)
