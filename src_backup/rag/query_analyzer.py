# ============================================================
# src/rag/query_analyzer.py - 질문 분석기
# ============================================================
# 사용자 질문을 분석하여 검색 전략을 결정합니다.
#
# 주요 기능:
#   - 에러 코드 감지 (C4A15, C50 등)
#   - 부품명 감지 (Control Box, Joint 등)
#   - 쿼리 타입 분류 (error_resolution, component_info, general)
#   - 검색 전략 결정 (graph_first, vector_first, hybrid)
#
# [Main-F1 개선] EntityLinker 통합
#   - lexicon.yaml 기반 동의어 매칭
#   - rules.yaml 기반 정규화
# ============================================================

import re
import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Set

# 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# EntityLinker 임포트 (Main-F1)
try:
    from src.rag.entity_linker import EntityLinker, LinkedEntity
    ENTITY_LINKER_AVAILABLE = True
except ImportError:
    ENTITY_LINKER_AVAILABLE = False


# ============================================================
# [1] 분석 결과 데이터 클래스
# ============================================================

@dataclass
class QueryAnalysis:
    """
    질문 분석 결과

    Attributes:
        original_query: 원본 질문
        error_codes: 감지된 에러 코드 리스트
        components: 감지된 부품명 리스트
        keywords: 추출된 키워드
        query_type: 쿼리 타입 (error_resolution, component_info, general)
        search_strategy: 검색 전략 (graph_first, vector_first, hybrid)
    """
    original_query: str
    error_codes: List[str] = field(default_factory=list)
    components: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    query_type: str = "general"
    search_strategy: str = "vector_first"

    def __repr__(self):
        return (
            f"QueryAnalysis(\n"
            f"  query='{self.original_query[:50]}...'\n"
            f"  error_codes={self.error_codes}\n"
            f"  components={self.components}\n"
            f"  query_type={self.query_type}\n"
            f"  strategy={self.search_strategy}\n"
            f")"
        )


# ============================================================
# [2] 부품명 사전
# ============================================================

# UR5e 로봇의 주요 부품명 (영문/한글)
COMPONENT_NAMES = {
    # Main Components
    "control box": ["control box", "컨트롤 박스", "컨트롤박스", "제어 박스"],
    "teach pendant": ["teach pendant", "티치 펜던트", "티치펜던트", "펜던트"],
    "robot arm": ["robot arm", "로봇 팔", "로봇팔", "arm"],

    # Boards
    "safety control board": ["safety control board", "safety board", "세이프티 보드", "안전 제어 보드"],
    "motherboard": ["motherboard", "마더보드", "메인보드"],
    "screen board": ["screen board", "스크린보드", "스크린 보드"],

    # Joints
    "joint": ["joint", "조인트", "관절"],
    "joint 0": ["joint 0", "조인트 0", "base joint", "베이스 조인트"],
    "joint 1": ["joint 1", "조인트 1", "shoulder joint", "숄더 조인트"],
    "joint 2": ["joint 2", "조인트 2", "elbow joint", "엘보우 조인트"],
    "joint 3": ["joint 3", "조인트 3", "wrist 1", "손목 1"],
    "joint 4": ["joint 4", "조인트 4", "wrist 2", "손목 2"],
    "joint 5": ["joint 5", "조인트 5", "wrist 3", "손목 3"],

    # Cables
    "cable": ["cable", "케이블", "선"],
    "communication cable": ["communication cable", "통신 케이블", "통신선"],
    "power cable": ["power cable", "전원 케이블", "전원선"],
    "ethernet cable": ["ethernet cable", "이더넷 케이블", "랜선", "lan cable"],

    # Power
    "power supply": ["power supply", "전원 공급 장치", "전원", "psu"],
    "current distributor": ["current distributor", "전류 분배기"],

    # Safety
    "safety system": ["safety system", "안전 시스템", "세이프티 시스템"],
    "emergency stop": ["emergency stop", "비상 정지", "e-stop", "이머전시 스톱"],
    "safeguard": ["safeguard", "세이프가드", "안전 장치"],

    # Tools
    "tool": ["tool", "툴", "공구", "end effector", "엔드 이펙터"],
    "gripper": ["gripper", "그리퍼", "집게"],

    # Euromap
    "euromap": ["euromap", "유로맵", "euromap67"],
}

# 에러 관련 키워드
ERROR_KEYWORDS = [
    "에러", "error", "오류", "문제", "발생", "해결", "원인", "조치",
    "해결법", "해결방법", "troubleshoot", "fix", "solve", "issue"
]

# 부품 관련 키워드
COMPONENT_KEYWORDS = [
    "부품", "component", "관련", "목록", "리스트", "list", "종류"
]


# ============================================================
# [3] QueryAnalyzer 클래스
# ============================================================

class QueryAnalyzer:
    """
    질문 분석기

    사용자 질문을 분석하여 에러 코드, 부품명을 감지하고
    최적의 검색 전략을 결정합니다.

    [Main-F1] EntityLinker 통합:
    - lexicon.yaml 기반 동의어 매칭
    - rules.yaml 기반 정규화

    사용 예시:
        analyzer = QueryAnalyzer()
        analysis = analyzer.analyze("C4A15 에러가 발생했어요")
        print(analysis.error_codes)  # ['C4A15']
        print(analysis.search_strategy)  # 'graph_first'
    """

    def __init__(self, use_entity_linker: bool = True):
        """
        QueryAnalyzer 초기화

        Args:
            use_entity_linker: EntityLinker 사용 여부 (기본: True)
        """
        # [Main-F1] EntityLinker 초기화
        self.entity_linker = None
        self.use_entity_linker = use_entity_linker and ENTITY_LINKER_AVAILABLE

        if self.use_entity_linker:
            try:
                self.entity_linker = EntityLinker()
                print("[OK] QueryAnalyzer initialized with EntityLinker")
            except Exception as e:
                print(f"[WARN] EntityLinker 초기화 실패, 기본 모드 사용: {e}")
                self.use_entity_linker = False

        if not self.use_entity_linker:
            # 기존 방식 (Fallback)
            # 에러 코드 패턴: C4, C4A1, C4A15, C50A100 등
            self.error_code_pattern = re.compile(r'\b(C\d+(?:A\d+)?)\b', re.IGNORECASE)

            # 유효한 에러 코드 기본 번호 (C0 ~ C55)
            self.valid_error_bases = set(range(0, 56))  # 0~55

            # 부품명 매핑 구축 (검색용)
            self.component_mapping = {}
            for canonical, variants in COMPONENT_NAMES.items():
                for variant in variants:
                    self.component_mapping[variant.lower()] = canonical

            print("[OK] QueryAnalyzer initialized (legacy mode)")

    # --------------------------------------------------------
    # [3.1] 메인 분석 메서드
    # --------------------------------------------------------

    def analyze(self, query: str) -> QueryAnalysis:
        """
        질문 분석 수행

        Args:
            query: 사용자 질문

        Returns:
            QueryAnalysis: 분석 결과
        """
        # [Main-F1] EntityLinker 사용
        if self.use_entity_linker and self.entity_linker:
            return self._analyze_with_entity_linker(query)

        # 기존 방식 (Fallback)
        # 1. 에러 코드 감지
        error_codes = self._detect_error_codes(query)

        # 2. 부품명 감지
        components = self._detect_components(query)

        # 3. 키워드 추출
        keywords = self._extract_keywords(query)

        # 4. 쿼리 타입 결정
        query_type = self._determine_query_type(query, error_codes, components)

        # 5. 검색 전략 결정
        search_strategy = self._determine_search_strategy(query_type, error_codes, components)

        return QueryAnalysis(
            original_query=query,
            error_codes=error_codes,
            components=components,
            keywords=keywords,
            query_type=query_type,
            search_strategy=search_strategy,
        )

    def _analyze_with_entity_linker(self, query: str) -> QueryAnalysis:
        """
        [Main-F1] EntityLinker를 사용한 질문 분석

        Args:
            query: 사용자 질문

        Returns:
            QueryAnalysis: 분석 결과
        """
        # EntityLinker로 엔티티 추출 및 링킹
        linked_entities = self.entity_linker.link_from_text(query)

        # 에러코드/부품명 분리
        error_codes = []
        components = []

        for entity in linked_entities:
            if entity.entity_type == "error_code":
                # 정규화된 에러코드 사용
                if entity.canonical not in error_codes:
                    error_codes.append(entity.canonical)
            elif entity.entity_type == "component":
                # 정규화된 부품명 사용
                if entity.canonical not in components:
                    components.append(entity.canonical)

        # 키워드 추출
        keywords = self._extract_keywords(query)

        # 쿼리 타입 결정
        query_type = self._determine_query_type(query, error_codes, components)

        # 검색 전략 결정
        search_strategy = self._determine_search_strategy(query_type, error_codes, components)

        return QueryAnalysis(
            original_query=query,
            error_codes=error_codes,
            components=components,
            keywords=keywords,
            query_type=query_type,
            search_strategy=search_strategy,
        )

    # --------------------------------------------------------
    # [3.2] 에러 코드 감지
    # --------------------------------------------------------

    def _detect_error_codes(self, query: str) -> List[str]:
        """
        에러 코드 패턴 감지

        패턴:
            - C4, C10, C17, C50, C55 (기본)
            - C4A1, C4A15, C50A100 (세부)

        유효 범위:
            - C0 ~ C55 (UR5e 에러 코드 범위)

        Args:
            query: 질문 텍스트

        Returns:
            List[str]: 감지된 에러 코드 리스트
        """
        matches = self.error_code_pattern.findall(query)

        # 대문자로 정규화 및 유효성 검증
        valid_codes = []
        for code in matches:
            code_upper = code.upper()

            # 기본 번호 추출 (C4A15 → 4, C50 → 50)
            base_match = re.match(r'C(\d+)', code_upper)
            if base_match:
                base_num = int(base_match.group(1))
                # 유효 범위 확인 (C0 ~ C55)
                if base_num in self.valid_error_bases:
                    valid_codes.append(code_upper)

        # 중복 제거하면서 순서 유지
        seen = set()
        unique_codes = []
        for code in valid_codes:
            if code not in seen:
                seen.add(code)
                unique_codes.append(code)

        return unique_codes

    # --------------------------------------------------------
    # [3.3] 부품명 감지
    # --------------------------------------------------------

    def _detect_components(self, query: str) -> List[str]:
        """
        부품명 감지

        Args:
            query: 질문 텍스트

        Returns:
            List[str]: 감지된 부품명 리스트 (정규화된 이름, 중복 제거)
        """
        query_lower = query.lower()
        detected = []
        matched_spans = []  # 이미 매칭된 위치 추적

        # 긴 부품명부터 매칭 (예: "safety control board"가 "control box"보다 먼저)
        sorted_variants = sorted(
            self.component_mapping.keys(),
            key=len,
            reverse=True
        )

        for variant in sorted_variants:
            # 모든 매칭 위치 찾기
            start = 0
            while True:
                pos = query_lower.find(variant, start)
                if pos == -1:
                    break

                end = pos + len(variant)

                # 이미 다른 부품명에 포함된 위치인지 확인
                is_overlapping = any(
                    s <= pos < e or s < end <= e
                    for s, e in matched_spans
                )

                if not is_overlapping:
                    canonical = self.component_mapping[variant]
                    if canonical not in detected:
                        detected.append(canonical)
                    matched_spans.append((pos, end))

                start = pos + 1

        return detected

    # --------------------------------------------------------
    # [3.4] 키워드 추출
    # --------------------------------------------------------

    def _extract_keywords(self, query: str) -> List[str]:
        """
        핵심 키워드 추출

        Args:
            query: 질문 텍스트

        Returns:
            List[str]: 키워드 리스트
        """
        keywords = []

        # 에러 관련 키워드 확인
        for keyword in ERROR_KEYWORDS:
            if keyword in query.lower():
                keywords.append(keyword)

        # 부품 관련 키워드 확인
        for keyword in COMPONENT_KEYWORDS:
            if keyword in query.lower():
                keywords.append(keyword)

        return keywords

    # --------------------------------------------------------
    # [3.5] 쿼리 타입 결정
    # --------------------------------------------------------

    def _determine_query_type(
        self,
        query: str,
        error_codes: List[str],
        components: List[str]
    ) -> str:
        """
        쿼리 타입 결정

        타입:
            - error_resolution: 에러 해결 질문
            - component_info: 부품 정보 질문
            - general: 일반 질문

        Args:
            query: 질문 텍스트
            error_codes: 감지된 에러 코드
            components: 감지된 부품명

        Returns:
            str: 쿼리 타입
        """
        query_lower = query.lower()

        # 에러 코드가 있고 해결/조치 관련 키워드가 있으면
        if error_codes:
            resolution_keywords = ["해결", "조치", "어떻게", "방법", "fix", "solve", "how"]
            if any(kw in query_lower for kw in resolution_keywords):
                return "error_resolution"
            # 에러 코드만 있어도 일단 error_resolution
            return "error_resolution"

        # 부품명이 있고 에러/문제 관련 키워드가 있으면
        if components:
            error_keywords = ["에러", "error", "오류", "문제", "목록", "list"]
            if any(kw in query_lower for kw in error_keywords):
                return "component_info"
            # 부품명만 있어도 일단 component_info
            return "component_info"

        return "general"

    # --------------------------------------------------------
    # [3.6] 검색 전략 결정
    # --------------------------------------------------------

    def _determine_search_strategy(
        self,
        query_type: str,
        error_codes: List[str],
        components: List[str]
    ) -> str:
        """
        검색 전략 결정

        전략:
            - graph_first: GraphDB 우선 검색 (에러코드/부품 있을 때)
            - vector_first: VectorDB 우선 검색 (일반 질문)
            - hybrid: 둘 다 동시 검색

        Args:
            query_type: 쿼리 타입
            error_codes: 감지된 에러 코드
            components: 감지된 부품명

        Returns:
            str: 검색 전략
        """
        if query_type == "error_resolution" and error_codes:
            return "graph_first"
        elif query_type == "component_info" and components:
            return "graph_first"
        else:
            return "vector_first"


# ============================================================
# 테스트 코드 (직접 실행 시)
# ============================================================

if __name__ == "__main__":
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 60)
    print("[*] QueryAnalyzer Test")
    print("=" * 60)

    analyzer = QueryAnalyzer()

    # 테스트 케이스
    test_queries = [
        # 에러 코드 질문
        "C4A15 에러가 발생했어요. 어떻게 해결하나요?",
        "C50 또는 C51 에러 원인이 뭐예요?",
        "c4a1 에러 조치방법 알려줘",

        # 부품 질문
        "Control Box 관련 에러 목록 알려줘",
        "Safety Control Board에서 문제가 생겼어요",
        "조인트 3에서 통신 오류가 발생해요",

        # 일반 질문
        "로봇이 갑자기 멈췄어요",
        "캘리브레이션은 어떻게 하나요?",
        "안전 설정 방법을 알려주세요",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'─' * 60}")
        print(f"[Test {i}] {query}")
        print(f"{'─' * 60}")

        analysis = analyzer.analyze(query)

        print(f"  Error codes: {analysis.error_codes}")
        print(f"  Components:  {analysis.components}")
        print(f"  Query type:  {analysis.query_type}")
        print(f"  Strategy:    {analysis.search_strategy}")

    print("\n" + "=" * 60)
    print("[OK] QueryAnalyzer test completed!")
    print("=" * 60)
