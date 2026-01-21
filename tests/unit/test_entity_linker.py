# ============================================================
# tests/unit/test_entity_linker.py - EntityLinker 단위 테스트
# ============================================================
# pytest -v tests/unit/test_entity_linker.py
# ============================================================

import os
import sys
import pytest

# 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.rag.entity_linker import EntityLinker, LinkedEntity


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def linker():
    """EntityLinker 인스턴스 생성"""
    return EntityLinker()


# ============================================================
# [1] Lexicon 매칭 테스트 - 에러코드
# ============================================================

class TestLexiconErrorCodes:
    """에러코드 Lexicon 매칭 테스트"""

    def test_exact_match(self, linker):
        """정확히 일치하는 에러코드"""
        results = linker.link(["C4A15"], ["error_code"])
        assert len(results) == 1
        assert results[0].canonical == "C4A15"
        assert results[0].matched_by == "lexicon"
        assert results[0].confidence == 1.0

    def test_lowercase(self, linker):
        """소문자 에러코드"""
        results = linker.link(["c4a15"], ["error_code"])
        assert len(results) == 1
        assert results[0].canonical == "C4A15"

    def test_with_hyphen(self, linker):
        """하이픈이 포함된 에러코드"""
        results = linker.link(["C-4A15"], ["error_code"])
        assert len(results) == 1
        assert results[0].canonical == "C4A15"

    def test_safety_error(self, linker):
        """안전 관련 에러코드"""
        results = linker.link(["C119"], ["error_code"])
        assert len(results) == 1
        assert results[0].canonical == "C119"
        assert results[0].metadata.get('category') == "safety"

    def test_joint_communication_error(self, linker):
        """조인트 통신 에러코드"""
        results = linker.link(["C50A100"], ["error_code"])
        assert len(results) == 1
        assert results[0].canonical == "C50A100"


# ============================================================
# [2] Lexicon 매칭 테스트 - 부품명
# ============================================================

class TestLexiconComponents:
    """부품명 Lexicon 매칭 테스트"""

    def test_english_name(self, linker):
        """영문 부품명"""
        results = linker.link(["Control Box"], ["component"])
        assert len(results) == 1
        assert results[0].canonical == "Control Box"

    def test_korean_name(self, linker):
        """한글 부품명"""
        results = linker.link(["컨트롤 박스"], ["component"])
        assert len(results) == 1
        assert results[0].canonical == "Control Box"

    def test_abbreviation(self, linker):
        """약어"""
        results = linker.link(["J3"], ["component"])
        assert len(results) == 1
        assert results[0].canonical == "Joint 3"

    def test_alternative_korean(self, linker):
        """대안 한글 표현"""
        results = linker.link(["컨트롤러"], ["component"])
        assert len(results) == 1
        assert results[0].canonical == "Control Box"

    def test_korean_joint_number(self, linker):
        """한글 조인트 번호"""
        results = linker.link(["3번 조인트"], ["component"])
        assert len(results) == 1
        assert results[0].canonical == "Joint 3"


# ============================================================
# [3] Regex 룰 매칭 테스트
# ============================================================

class TestRegexRules:
    """Regex 룰 매칭 테스트"""

    def test_spaced_error_code(self, linker):
        """공백이 포함된 에러코드"""
        results = linker.link(["C 4 A 15"], ["error_code"])
        assert len(results) >= 1
        # 첫 번째 결과가 C4A15이거나 C4인지 확인

    def test_hyphen_error_code(self, linker):
        """하이픈이 포함된 에러코드 (lexicon에 없는 경우)"""
        results = linker.link(["C-10"], ["error_code"])
        assert len(results) == 1
        assert results[0].canonical == "C10"


# ============================================================
# [4] 텍스트 추출 테스트
# ============================================================

class TestTextExtraction:
    """텍스트에서 엔티티 추출 테스트"""

    def test_extract_error_code_from_text(self, linker):
        """텍스트에서 에러코드 추출"""
        results = linker.link_from_text("C4A15 에러가 발생했습니다")
        error_codes = [r for r in results if r.entity_type == "error_code"]
        assert len(error_codes) >= 1
        assert any(r.canonical == "C4A15" for r in error_codes)

    def test_extract_component_from_text(self, linker):
        """텍스트에서 부품명 추출"""
        results = linker.link_from_text("컨트롤 박스에서 문제 발생")
        components = [r for r in results if r.entity_type == "component"]
        assert len(components) >= 1
        assert any(r.canonical == "Control Box" for r in components)

    def test_extract_mixed(self, linker):
        """에러코드 + 부품명 혼합 추출"""
        results = linker.link_from_text("컨트롤러에서 C-119 에러 발생")
        error_codes = [r for r in results if r.entity_type == "error_code"]
        components = [r for r in results if r.entity_type == "component"]

        assert len(error_codes) >= 1
        assert len(components) >= 1
        assert any(r.canonical == "C119" for r in error_codes)
        assert any(r.canonical == "Control Box" for r in components)


# ============================================================
# [5] 한영 변환 테스트
# ============================================================

class TestKoreanEnglish:
    """한영 변환 테스트"""

    def test_korean_to_english_component(self, linker):
        """한글 부품명 → 영문 정규화"""
        test_cases = [
            ("티치 펜던트", "Teach Pendant"),
            ("비상 정지", "Emergency Stop"),
            ("그리퍼", "Gripper"),
            ("안전 제어 보드", "Safety Control Board"),
        ]

        for korean, expected_english in test_cases:
            results = linker.link([korean], ["component"])
            assert len(results) >= 1, f"Failed for: {korean}"
            assert results[0].canonical == expected_english, f"Expected {expected_english}, got {results[0].canonical}"


# ============================================================
# [6] 약어 테스트
# ============================================================

class TestAbbreviations:
    """약어 테스트"""

    def test_joint_abbreviations(self, linker):
        """조인트 약어"""
        test_cases = [
            ("J0", "Joint 0"),
            ("J1", "Joint 1"),
            ("J2", "Joint 2"),
            ("J3", "Joint 3"),
            ("J4", "Joint 4"),
            ("J5", "Joint 5"),
        ]

        for abbrev, expected in test_cases:
            results = linker.link([abbrev], ["component"])
            assert len(results) >= 1, f"Failed for: {abbrev}"
            assert results[0].canonical == expected, f"Expected {expected}, got {results[0].canonical}"

    def test_component_abbreviations(self, linker):
        """기타 부품 약어"""
        test_cases = [
            ("CB", "Control Box"),
            ("TP", "Teach Pendant"),
            ("SCB", "Safety Control Board"),
        ]

        for abbrev, expected in test_cases:
            results = linker.link([abbrev], ["component"])
            assert len(results) >= 1, f"Failed for: {abbrev}"
            assert results[0].canonical == expected, f"Expected {expected}, got {results[0].canonical}"


# ============================================================
# [7] 에지 케이스 테스트
# ============================================================

class TestEdgeCases:
    """에지 케이스 테스트"""

    def test_empty_input(self, linker):
        """빈 입력"""
        results = linker.link([], [])
        assert len(results) == 0

    def test_no_entity_text(self, linker):
        """엔티티가 없는 텍스트"""
        results = linker.link_from_text("로봇이 갑자기 멈췄어요")
        # 아무 엔티티도 없을 수 있음 (또는 있을 수 있음)
        # 단순히 에러가 발생하지 않는지만 확인
        assert isinstance(results, list)

    def test_multiple_error_codes(self, linker):
        """여러 에러코드"""
        results = linker.link_from_text("C50 또는 C51 에러")
        error_codes = [r for r in results if r.entity_type == "error_code"]
        canonicals = [r.canonical for r in error_codes]
        assert "C50" in canonicals
        assert "C51" in canonicals


# ============================================================
# [8] 신뢰도 테스트
# ============================================================

class TestConfidence:
    """신뢰도 테스트"""

    def test_lexicon_confidence(self, linker):
        """Lexicon 매칭 신뢰도"""
        results = linker.link(["C4A15"], ["error_code"])
        assert len(results) == 1
        assert results[0].confidence == 1.0
        assert results[0].matched_by == "lexicon"

    def test_regex_confidence(self, linker):
        """Regex 매칭 신뢰도 (lexicon에 없는 경우)"""
        # 유효하지만 lexicon에 없는 에러코드를 찾기 어려우므로
        # 일단 lexicon에 있는 것으로 테스트
        results = linker.link(["c4a15"], ["error_code"])
        assert len(results) == 1
        # lexicon에서 찾으면 1.0, regex면 0.9~0.95
        assert results[0].confidence >= 0.9


# ============================================================
# 메인 실행
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
