# ============================================================
# src/ontology/entity_extractor.py - LLM 기반 엔티티 추출
# ============================================================
# 청크 텍스트에서 엔티티(Component, ErrorCode, Procedure)를 추출합니다.
#
# 추출 방식:
#   1. LLM (GPT-4o-mini)에게 청크를 보여주고
#   2. 구조화된 JSON 형식으로 엔티티 추출
#   3. Entity 객체로 변환
#
# 배치 처리로 비용 최적화:
#   - 여러 청크를 한 번에 처리
#   - 중복 엔티티 통합
# ============================================================

import os
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from openai import OpenAI

from .schema import (
    Entity,
    EntityType,
    Relation,
    RelationType,
    create_component,
    create_error_code,
    create_procedure,
)

# 프로젝트 루트의 .env 파일 로드
load_dotenv()

import re


# ============================================================
# [1] 프롬프트 템플릿
# ============================================================

ENTITY_EXTRACTION_PROMPT = """You are an expert at extracting structured information from technical documents about the UR5e robot.

Extract the following types of entities from the given text:

1. **Components**: Physical parts of the robot
   - Examples: Control Box, Joint 0, Motherboard, Ethernet Cable, Safety Control Board
   - Include component type if mentioned (main, cable, board, etc.)

2. **Error Codes**: Error codes and their descriptions
   - Examples: C4, C10, C17A, C50A54
   - Include the error title/description if available

3. **Procedures**: Repair/maintenance procedures or solutions
   - Examples: Check cable connection, Replace joint, Update firmware
   - Include steps if mentioned

Also extract **Relations** between entities:
- HAS_ERROR: Component → ErrorCode (e.g., "Control Box has error C4")
- RESOLVED_BY: ErrorCode → Procedure (e.g., "C4 is resolved by checking cable")
- CAUSED_BY: ErrorCode → Component (e.g., "C4 is caused by faulty cable")
- CONTAINS: Component → Component (e.g., "Control Box contains Motherboard")

TEXT:
{text}

Respond ONLY with valid JSON in this exact format (no markdown, no explanation):
{{
  "components": [
    {{"name": "Component Name", "type": "component_type"}}
  ],
  "error_codes": [
    {{"code": "C4", "title": "Error title", "description": "Description"}}
  ],
  "procedures": [
    {{"name": "Procedure name", "steps": ["step1", "step2"]}}
  ],
  "relations": [
    {{"source": "entity_name", "relation": "HAS_ERROR|RESOLVED_BY|CAUSED_BY|CONTAINS", "target": "entity_name"}}
  ]
}}

If no entities of a type are found, use empty arrays. Extract only what is explicitly mentioned in the text."""


# ============================================================
# [2] EntityExtractor 클래스
# ============================================================

class EntityExtractor:
    """
    LLM 기반 엔티티 추출기

    사용 예시:
        extractor = EntityExtractor()
        entities, relations = extractor.extract_from_chunk(chunk)
        all_entities = extractor.extract_from_chunks(chunks)
    """

    DEFAULT_MODEL = "gpt-4o-mini"
    BATCH_SIZE = 5           # 한 번에 처리할 청크 수
    RETRY_DELAY = 1.0        # 재시도 대기 시간
    MAX_RETRIES = 3          # 최대 재시도 횟수

    def __init__(self, model: Optional[str] = None):
        """
        EntityExtractor 초기화

        Args:
            model: 사용할 LLM 모델 (기본값: gpt-4o-mini)
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in .env")

        self.client = OpenAI()
        self.model = model or self.DEFAULT_MODEL

        # 추출된 엔티티 캐시 (중복 방지)
        self._entity_cache: Dict[str, Entity] = {}
        self._relation_cache: List[Relation] = []

        print(f"[OK] EntityExtractor initialized with model: {self.model}")

    # --------------------------------------------------------
    # [2.1] 단일 텍스트에서 추출
    # --------------------------------------------------------

    def extract_from_text(
        self,
        text: str,
        chunk_id: Optional[str] = None
    ) -> Tuple[List[Entity], List[Relation]]:
        """
        텍스트에서 엔티티와 관계 추출

        Args:
            text: 추출할 텍스트
            chunk_id: 청크 ID (출처 추적용)

        Returns:
            Tuple[List[Entity], List[Relation]]: 추출된 엔티티와 관계
        """
        prompt = ENTITY_EXTRACTION_PROMPT.format(text=text)

        # LLM 호출
        response = self._call_llm_with_retry(prompt)
        if not response:
            return [], []

        # JSON 파싱
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            print(f"[WARN] JSON parse error: {e}")
            return [], []

        # 엔티티 변환
        entities = []
        relations = []

        # Components
        for comp in data.get("components", []):
            entity = create_component(
                name=comp.get("name", "Unknown"),
                component_type=comp.get("type", "general"),
            )
            if chunk_id:
                entity.properties["source_chunk"] = chunk_id
            entities.append(entity)

        # Error Codes
        for err in data.get("error_codes", []):
            entity = create_error_code(
                code=err.get("code", "Unknown"),
                title=err.get("title", ""),
                description=err.get("description", ""),
            )
            if chunk_id:
                entity.properties["source_chunk"] = chunk_id
            entities.append(entity)

        # Procedures
        for proc in data.get("procedures", []):
            entity = create_procedure(
                name=proc.get("name", "Unknown"),
                steps=proc.get("steps", []),
            )
            if chunk_id:
                entity.properties["source_chunk"] = chunk_id
            entities.append(entity)

        # Relations
        for rel in data.get("relations", []):
            relation_type = self._parse_relation_type(rel.get("relation", ""))
            if relation_type:
                source_name = rel.get("source", "")
                target_name = rel.get("target", "")

                # 이름으로 ID 생성 (나중에 매칭)
                source_id = self._name_to_id(source_name)
                target_id = self._name_to_id(target_name)

                relation = Relation(
                    source_id=source_id,
                    target_id=target_id,
                    type=relation_type,
                )
                relations.append(relation)

        return entities, relations

    def _parse_relation_type(self, relation_str: str) -> Optional[RelationType]:
        """관계 문자열을 RelationType으로 변환"""
        relation_map = {
            "HAS_ERROR": RelationType.HAS_ERROR,
            "RESOLVED_BY": RelationType.RESOLVED_BY,
            "CAUSED_BY": RelationType.CAUSED_BY,
            "CONTAINS": RelationType.CONTAINS,
            "CONNECTED_TO": RelationType.CONNECTED_TO,
        }
        return relation_map.get(relation_str.upper())

    def _name_to_id(self, name: str) -> str:
        """이름을 ID로 변환"""
        # 에러 코드 패턴 체크
        if name.upper().startswith("C") and any(c.isdigit() for c in name):
            return f"error_{name.lower()}"
        # 일반적인 이름은 component로
        return f"component_{name.lower().replace(' ', '_')}"

    # --------------------------------------------------------
    # [2.2] LLM 호출
    # --------------------------------------------------------

    def _call_llm_with_retry(self, prompt: str) -> Optional[str]:
        """LLM 호출 (재시도 로직 포함)"""
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a technical document analyzer. Always respond with valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0,  # 일관된 출력
                    max_tokens=2000,
                )
                return response.choices[0].message.content.strip()

            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = self.RETRY_DELAY * (attempt + 1)
                    print(f"[WARN] LLM error, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    print(f"[ERROR] LLM failed after {self.MAX_RETRIES} retries: {e}")
                    return None

    # --------------------------------------------------------
    # [2.3] 청크에서 추출
    # --------------------------------------------------------

    def extract_from_chunk(self, chunk) -> Tuple[List[Entity], List[Relation]]:
        """
        Chunk 객체에서 엔티티 추출

        Args:
            chunk: Chunk 객체 (content, id 속성 필요)

        Returns:
            Tuple[List[Entity], List[Relation]]: 추출된 엔티티와 관계
        """
        return self.extract_from_text(
            text=chunk.content,
            chunk_id=chunk.id,
        )

    def extract_from_chunks(
        self,
        chunks: List,
        show_progress: bool = True
    ) -> Tuple[List[Entity], List[Relation]]:
        """
        여러 청크에서 엔티티 배치 추출

        Args:
            chunks: Chunk 객체 리스트
            show_progress: 진행 상황 출력

        Returns:
            Tuple[List[Entity], List[Relation]]: 모든 추출된 엔티티와 관계 (중복 제거됨)
        """
        all_entities: Dict[str, Entity] = {}
        all_relations: List[Relation] = []

        total = len(chunks)

        for i, chunk in enumerate(chunks):
            if show_progress and (i + 1) % 10 == 0:
                print(f"    Processing chunk {i + 1}/{total}...")

            entities, relations = self.extract_from_chunk(chunk)

            # 중복 제거하며 추가
            for entity in entities:
                if entity.id not in all_entities:
                    all_entities[entity.id] = entity

            all_relations.extend(relations)

        # 캐시 업데이트
        self._entity_cache.update(all_entities)
        self._relation_cache.extend(all_relations)

        print(f"[OK] Extracted {len(all_entities)} unique entities, {len(all_relations)} relations")

        return list(all_entities.values()), all_relations

    # --------------------------------------------------------
    # [2.4] 규칙 기반 에러 코드 추출 (SUGGESTION 패턴)
    # --------------------------------------------------------

    def extract_error_codes_rule_based(
        self,
        text: str,
        chunk_id: Optional[str] = None
    ) -> Tuple[List[Entity], List[Relation]]:
        """
        규칙 기반으로 에러 코드와 해결 방법 추출

        에러 코드 문서 패턴:
            C4A15 Communication with joint 3 lost
            EXPLANATION
            More than 1 package lost
            SUGGESTION
            Try the following actions: (A) Verify cables, (B) Reboot

        Returns:
            Tuple[List[Entity], List[Relation]]: 엔티티와 관계
        """
        entities = []
        relations = []

        # 에러 코드 패턴: C숫자 또는 C숫자A숫자 형식
        # 예: C4, C4A1, C4A15, C50A100
        error_pattern = r'(C\d+(?:A\d+)?)\s+([^\n]+?)(?=\n|EXPLANATION|SUGGESTION|$)'

        # SUGGESTION 패턴
        suggestion_pattern = r'(C\d+(?:A\d+)?)[^\n]*\n(?:EXPLANATION[^\n]*\n[^\n]*\n)?SUGGESTION\s*\n([^\n]+(?:\n(?!C\d)[^\n]+)*)'

        # 에러 코드 추출
        for match in re.finditer(error_pattern, text):
            code = match.group(1)
            title = match.group(2).strip()

            entity = create_error_code(
                code=code,
                title=title,
            )
            if chunk_id:
                entity.properties["source_chunk"] = chunk_id
            entities.append(entity)

        # SUGGESTION에서 해결 방법 추출
        for match in re.finditer(suggestion_pattern, text, re.IGNORECASE):
            error_code = match.group(1)
            suggestion_text = match.group(2).strip()

            # 해결 방법 파싱 (A), (B), (C) 패턴
            steps = []
            step_pattern = r'\(([A-Z])\)\s*([^(]+?)(?=\([A-Z]\)|$)'
            for step_match in re.finditer(step_pattern, suggestion_text):
                step_text = step_match.group(2).strip().rstrip(',')
                if step_text:
                    steps.append(step_text)

            if not steps and suggestion_text:
                # (A), (B) 패턴이 없으면 전체를 하나의 단계로
                steps = [suggestion_text[:100]]

            # 표준화된 Procedure 생성
            for step in steps:
                # Procedure 이름 정규화
                proc_name = self._normalize_procedure_name(step)
                proc_entity = create_procedure(
                    name=proc_name,
                    steps=[step],
                )
                if chunk_id:
                    proc_entity.properties["source_chunk"] = chunk_id
                entities.append(proc_entity)

                # RESOLVED_BY 관계 생성
                relation = Relation(
                    source_id=f"error_{error_code.lower()}",
                    target_id=proc_entity.id,
                    type=RelationType.RESOLVED_BY,
                )
                relations.append(relation)

        return entities, relations

    def _normalize_procedure_name(self, text: str) -> str:
        """Procedure 이름을 정규화"""
        # 긴 텍스트는 앞부분만
        text = text[:50] if len(text) > 50 else text
        # 특수문자 제거
        text = re.sub(r'[^\w\s]', '', text)
        # 앞뒤 공백 제거
        return text.strip()

    def extract_error_codes_from_chunks(
        self,
        chunks: List,
        show_progress: bool = True
    ) -> Tuple[List[Entity], List[Relation]]:
        """
        에러 코드 문서에서 구조화된 추출 (규칙 기반 + LLM)

        에러 코드 문서는 패턴이 명확하므로 규칙 기반 추출을 우선 적용
        """
        all_entities: Dict[str, Entity] = {}
        all_relations: List[Relation] = []

        for i, chunk in enumerate(chunks):
            if show_progress and (i + 1) % 20 == 0:
                print(f"    Processing error code chunk {i + 1}/{len(chunks)}...")

            # 1. 규칙 기반 추출 (SUGGESTION 패턴)
            rule_entities, rule_relations = self.extract_error_codes_rule_based(
                text=chunk.content,
                chunk_id=chunk.id
            )

            for entity in rule_entities:
                if entity.id not in all_entities:
                    all_entities[entity.id] = entity
            all_relations.extend(rule_relations)

            # 2. 메타데이터에서 에러 코드 확인
            metadata = chunk.metadata
            if hasattr(metadata, 'error_code') and metadata.error_code:
                error_code = metadata.error_code
                entity = create_error_code(
                    code=error_code,
                    title=metadata.title if hasattr(metadata, 'title') else "",
                )
                entity.properties["source_chunk"] = chunk.id
                if entity.id not in all_entities:
                    all_entities[entity.id] = entity

            # 3. LLM으로 추가 추출 (Component 등)
            entities, relations = self.extract_from_chunk(chunk)
            for entity in entities:
                if entity.id not in all_entities:
                    all_entities[entity.id] = entity
            all_relations.extend(relations)

        return list(all_entities.values()), all_relations

    # --------------------------------------------------------
    # [2.5] 캐시 관리
    # --------------------------------------------------------

    def get_cached_entities(self) -> List[Entity]:
        """캐시된 엔티티 반환"""
        return list(self._entity_cache.values())

    def get_cached_relations(self) -> List[Relation]:
        """캐시된 관계 반환"""
        return self._relation_cache

    def clear_cache(self):
        """캐시 초기화"""
        self._entity_cache.clear()
        self._relation_cache.clear()


# ============================================================
# 테스트 코드 (직접 실행 시)
# ============================================================

if __name__ == "__main__":
    import sys

    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 50)
    print("[*] EntityExtractor Test")
    print("=" * 50)

    # 추출기 생성
    extractor = EntityExtractor()

    # 테스트 텍스트
    test_text = """
    C4 - Communication error
    Lost connection between Safety Control Board and Controller.

    Solution:
    1. Check the Ethernet cable between Safety Control Board and Motherboard.
    2. Replace the cable if damaged.
    3. If the problem persists, contact UR support.

    The Control Box contains the Motherboard and Safety Control Board.
    """

    print("\n[Test 1] Extract from text")
    print(f"  Input text length: {len(test_text)} chars")

    entities, relations = extractor.extract_from_text(test_text, chunk_id="test_001")

    print(f"\n  Extracted {len(entities)} entities:")
    for e in entities:
        print(f"    - [{e.type.value}] {e.name}")

    print(f"\n  Extracted {len(relations)} relations:")
    for r in relations:
        print(f"    - {r.source_id} -[{r.type.value}]-> {r.target_id}")

    print("\n" + "=" * 50)
    print("[OK] EntityExtractor test passed!")
    print("=" * 50)
