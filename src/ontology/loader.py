"""
온톨로지 로더

온톨로지 데이터 로드/저장 기능을 제공합니다.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

import yaml

from .models import OntologySchema, Entity, Relationship
from .schema import EntityType, RelationType

logger = logging.getLogger(__name__)


class OntologyLoader:
    """온톨로지 로더/저장"""

    DEFAULT_PATH = Path("data/processed/ontology/ontology.json")
    LEXICON_PATH = Path("data/processed/ontology/lexicon.yaml")

    _cached_schema: Optional[OntologySchema] = None
    _cached_lexicon: Optional[Dict[str, Any]] = None

    @classmethod
    def load(cls, path: Optional[Path] = None, use_cache: bool = True) -> OntologySchema:
        """온톨로지 로드

        Args:
            path: 온톨로지 파일 경로 (기본: DEFAULT_PATH)
            use_cache: 캐시 사용 여부

        Returns:
            OntologySchema 인스턴스
        """
        if use_cache and cls._cached_schema is not None:
            return cls._cached_schema

        path = path or cls.DEFAULT_PATH
        logger.info(f"온톨로지 로드: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        schema = OntologySchema.from_dict(data)

        if use_cache:
            cls._cached_schema = schema

        logger.info(f"온톨로지 로드 완료: {len(schema.entities)} 엔티티, {len(schema.relationships)} 관계")
        return schema

    @classmethod
    def save(cls, schema: OntologySchema, path: Optional[Path] = None) -> None:
        """온톨로지 저장

        Args:
            schema: 저장할 OntologySchema
            path: 저장 경로 (기본: DEFAULT_PATH)
        """
        path = path or cls.DEFAULT_PATH
        path.parent.mkdir(parents=True, exist_ok=True)

        data = schema.to_dict()

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"온톨로지 저장 완료: {path}")

        # 캐시 업데이트
        cls._cached_schema = schema

    @classmethod
    def load_lexicon(cls, path: Optional[Path] = None, use_cache: bool = True) -> Dict[str, Any]:
        """동의어 사전 로드

        Args:
            path: 동의어 사전 파일 경로
            use_cache: 캐시 사용 여부

        Returns:
            동의어 사전 딕셔너리
        """
        if use_cache and cls._cached_lexicon is not None:
            return cls._cached_lexicon

        path = path or cls.LEXICON_PATH
        logger.info(f"동의어 사전 로드: {path}")

        with open(path, "r", encoding="utf-8") as f:
            lexicon = yaml.safe_load(f)

        if use_cache:
            cls._cached_lexicon = lexicon

        return lexicon

    @classmethod
    def resolve_alias(
        cls,
        term: str,
        lexicon: Optional[Dict] = None
    ) -> Optional[str]:
        """동의어를 표준 ID로 변환

        Args:
            term: 검색할 용어
            lexicon: 동의어 사전 (없으면 자동 로드)

        Returns:
            표준 엔티티 ID 또는 None
        """
        if lexicon is None:
            lexicon = cls.load_lexicon()

        term_lower = term.lower().strip()

        # 각 카테고리에서 검색 (기존 형식 + lexicon.yaml 형식 모두 지원)
        categories = [
            "entities", "relationships", "states", "patterns",  # 새 형식
            "error_codes", "components"  # lexicon.yaml 형식
        ]
        alias_keys = ["aliases", "synonyms"]  # 두 가지 키 모두 지원

        for category in categories:
            category_data = lexicon.get(category, {})
            for entity_id, data in category_data.items():
                # 정확히 일치하는 ID
                if entity_id.lower() == term_lower:
                    return data.get("canonical", entity_id)

                # canonical 이름 검색
                canonical = data.get("canonical", "")
                if canonical.lower() == term_lower:
                    return canonical

                # 별칭/동의어 검색
                for alias_key in alias_keys:
                    aliases = data.get(alias_key, [])
                    if term_lower in [a.lower() for a in aliases]:
                        return data.get("canonical", entity_id)

        return None

    @classmethod
    def get_aliases(cls, entity_id: str, lexicon: Optional[Dict] = None) -> List[str]:
        """엔티티의 별칭 목록 반환

        Args:
            entity_id: 엔티티 ID
            lexicon: 동의어 사전

        Returns:
            별칭 목록
        """
        if lexicon is None:
            lexicon = cls.load_lexicon()

        categories = [
            "entities", "relationships", "states", "patterns",
            "error_codes", "components"
        ]
        alias_keys = ["aliases", "synonyms"]

        for category in categories:
            category_data = lexicon.get(category, {})
            if entity_id in category_data:
                for alias_key in alias_keys:
                    if alias_key in category_data[entity_id]:
                        return category_data[entity_id][alias_key]

        return []

    @classmethod
    def clear_cache(cls) -> None:
        """캐시 초기화"""
        cls._cached_schema = None
        cls._cached_lexicon = None
        logger.info("온톨로지 캐시 초기화")


def load_ontology(path: Optional[Path] = None) -> OntologySchema:
    """온톨로지 로드 (편의 함수)"""
    return OntologyLoader.load(path)


def save_ontology(schema: OntologySchema, path: Optional[Path] = None) -> None:
    """온톨로지 저장 (편의 함수)"""
    OntologyLoader.save(schema, path)


def load_lexicon(path: Optional[Path] = None) -> Dict[str, Any]:
    """동의어 사전 로드 (편의 함수)"""
    return OntologyLoader.load_lexicon(path)


def resolve_alias(term: str) -> Optional[str]:
    """동의어 해석 (편의 함수)"""
    return OntologyLoader.resolve_alias(term)
