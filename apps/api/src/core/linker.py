"""
엔티티 링킹 모듈: 자연어 엔티티를 온톨로지 노드 ID로 매핑
"""
from typing import List, Dict, Optional, Tuple
import yaml
import re
from difflib import SequenceMatcher


class EntityLinker:
    """
    엔티티 링킹: 추출된 자연어 엔티티를 온톨로지의 정규화된 노드 ID로 연결
    """
    
    def __init__(self, 
                 lexicon_path: str = "data/processed/ontology/lexicon.yaml",
                 rules_path: str = "configs/ontology_rules.yaml"):
        self.lexicon = self._load_lexicon(lexicon_path)
        self.rules = self._load_rules(rules_path)
        
    def _load_lexicon(self, path: str) -> dict:
        """동의어 사전 로드"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Warning: Lexicon file not found at {path}")
            return {"synonyms": {}, "variants": {}}
    
    def _load_rules(self, path: str) -> dict:
        """정규화 및 링킹 룰 로드"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Warning: Rules file not found at {path}")
            return {"normalization_rules": {}, "linking_rules": {}}
    
    def normalize(self, entity: str) -> str:
        """엔티티 텍스트 정규화"""
        normalized = entity
        
        # 공백 정규화
        if self.rules.get("normalization_rules", {}).get("normalize_whitespace"):
            normalized = " ".join(normalized.split())
        
        # 대소문자 정규화
        if self.rules.get("normalization_rules", {}).get("case_insensitive"):
            normalized = normalized.lower()
        
        # 정규식 패턴 매칭
        patterns = self.rules.get("normalization_rules", {}).get("patterns", [])
        for pattern_rule in patterns:
            pattern = pattern_rule.get("pattern", "")
            canonical = pattern_rule.get("canonical", "")
            if re.search(pattern, normalized, re.IGNORECASE):
                return canonical
        
        return normalized
    
    def fuzzy_match(self, text1: str, text2: str) -> float:
        """퍼지 매칭 점수 계산"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def link_to_ontology(self, entity: str, neo4j_client=None) -> Optional[Dict]:
        """
        엔티티를 온톨로지 노드에 링크
        
        Args:
            entity: 추출된 자연어 엔티티
            neo4j_client: Neo4j 클라이언트 (선택)
        
        Returns:
            링크된 노드 정보 또는 None
        """
        # 1. 정규화
        normalized = self.normalize(entity)
        
        # 2. 동의어 사전 검색
        for canonical, synonyms in self.lexicon.get("synonyms", {}).items():
            if normalized in [s.lower() for s in synonyms]:
                return {
                    "node_id": canonical,
                    "canonical_name": canonical,
                    "confidence": 1.0,
                    "method": "exact_match"
                }
        
        # 3. Fuzzy matching (활성화된 경우)
        if self.rules.get("linking_rules", {}).get("fuzzy_matching"):
            threshold = self.rules.get("linking_rules", {}).get("fuzzy_threshold", 0.85)
            best_match = None
            best_score = 0.0
            
            for canonical, synonyms in self.lexicon.get("synonyms", {}).items():
                for synonym in synonyms:
                    score = self.fuzzy_match(normalized, synonym)
                    if score > best_score and score >= threshold:
                        best_score = score
                        best_match = canonical
            
            if best_match:
                return {
                    "node_id": best_match,
                    "canonical_name": best_match,
                    "confidence": best_score,
                    "method": "fuzzy_match"
                }
        
        # 4. Neo4j 전체 텍스트 검색 (클라이언트가 제공된 경우)
        if neo4j_client:
            result = neo4j_client.fulltext_search(normalized)
            if result:
                return result
        
        # 매칭 실패
        return None
    
    def link_entities(self, entities: List[str], neo4j_client=None) -> List[Dict]:
        """
        여러 엔티티를 일괄 링크
        
        Args:
            entities: 엔티티 목록
            neo4j_client: Neo4j 클라이언트 (선택)
        
        Returns:
            링크 결과 목록
        """
        results = []
        for entity in entities:
            linked = self.link_to_ontology(entity, neo4j_client)
            if linked:
                results.append({
                    "original": entity,
                    **linked
                })
        return results


if __name__ == "__main__":
    # 테스트
    linker = EntityLinker()
    
    test_entities = ["UR-5e", "teach pendant", "e-stop", "Emergency Stop"]
    results = linker.link_entities(test_entities)
    
    for result in results:
        print(f"{result['original']} -> {result['canonical_name']} "
              f"(confidence: {result['confidence']:.2f}, method: {result['method']})")
