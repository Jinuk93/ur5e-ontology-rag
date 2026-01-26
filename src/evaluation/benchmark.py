# ============================================================
# src/evaluation/benchmark.py - Benchmark Dataset Loader
# ============================================================
# 온톨로지 RAG 시스템 벤치마크 데이터셋 로더
# ============================================================

import json
import os
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


@dataclass
class BenchmarkItem:
    """벤치마크 항목"""
    id: str
    question: str
    expected_answer: str
    expected_entities: List[str]  # 추출되어야 할 엔티티 ID
    category: str  # ontology, sensor_analysis, error_resolution, pattern_history, specification, invalid
    difficulty: str  # easy, medium, hard
    expected_abstain: bool  # ABSTAIN 예상 여부
    query_type: str  # ONTOLOGY, HYBRID, RAG
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "BenchmarkItem":
        """딕셔너리에서 BenchmarkItem 생성"""
        return cls(
            id=data["id"],
            question=data["question"],
            expected_answer=data["expected_answer"],
            expected_entities=data.get("expected_entities", []),
            category=data["category"],
            difficulty=data["difficulty"],
            expected_abstain=data.get("expected_abstain", False),
            query_type=data.get("query_type", "ONTOLOGY"),
            tags=data.get("tags", []),
        )

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "question": self.question,
            "expected_answer": self.expected_answer,
            "expected_entities": self.expected_entities,
            "category": self.category,
            "difficulty": self.difficulty,
            "expected_abstain": self.expected_abstain,
            "query_type": self.query_type,
            "tags": self.tags,
        }


class BenchmarkDataset:
    """벤치마크 데이터셋 관리"""

    def __init__(self, data_dir: str = "data/benchmark"):
        self.data_dir = Path(data_dir)
        self.items: List[BenchmarkItem] = []
        self._loaded = False

    def load(self) -> List[BenchmarkItem]:
        """JSON 파일들에서 벤치마크 로드"""
        if self._loaded:
            return self.items

        self.items = []

        # 온톨로지 RAG 시스템용 벤치마크 파일들
        json_files = [
            "ontology_qa.json",
            "sensor_analysis_qa.json",
            "error_resolution_qa.json",
            "pattern_history_qa.json",
            "specification_qa.json",
            "invalid_qa.json",
        ]

        for filename in json_files:
            filepath = self.data_dir / filename
            if filepath.exists():
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item_data in data:
                        self.items.append(BenchmarkItem.from_dict(item_data))

        # 통합 파일도 지원
        combined_path = self.data_dir / "benchmark.json"
        if combined_path.exists() and not self.items:
            with open(combined_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item_data in data:
                    self.items.append(BenchmarkItem.from_dict(item_data))

        self._loaded = True
        return self.items

    def get_all(self) -> List[BenchmarkItem]:
        """모든 벤치마크 항목 반환"""
        if not self._loaded:
            self.load()
        return self.items

    def get_by_category(self, category: str) -> List[BenchmarkItem]:
        """카테고리별 필터링"""
        if not self._loaded:
            self.load()
        return [item for item in self.items if item.category == category]

    def get_by_difficulty(self, difficulty: str) -> List[BenchmarkItem]:
        """난이도별 필터링"""
        if not self._loaded:
            self.load()
        return [item for item in self.items if item.difficulty == difficulty]

    def get_by_query_type(self, query_type: str) -> List[BenchmarkItem]:
        """쿼리 타입별 필터링"""
        if not self._loaded:
            self.load()
        return [item for item in self.items if item.query_type == query_type]

    def get_by_id(self, item_id: str) -> Optional[BenchmarkItem]:
        """ID로 항목 검색"""
        if not self._loaded:
            self.load()
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def get_categories(self) -> List[str]:
        """모든 카테고리 목록"""
        if not self._loaded:
            self.load()
        return list(set(item.category for item in self.items))

    def get_difficulties(self) -> List[str]:
        """모든 난이도 목록"""
        if not self._loaded:
            self.load()
        return list(set(item.difficulty for item in self.items))

    def get_statistics(self) -> dict:
        """데이터셋 통계"""
        if not self._loaded:
            self.load()

        by_category = {}
        for item in self.items:
            by_category[item.category] = by_category.get(item.category, 0) + 1

        by_difficulty = {}
        for item in self.items:
            by_difficulty[item.difficulty] = by_difficulty.get(item.difficulty, 0) + 1

        by_query_type = {}
        for item in self.items:
            by_query_type[item.query_type] = by_query_type.get(item.query_type, 0) + 1

        by_abstain = {"abstain": 0, "answer": 0}
        for item in self.items:
            if item.expected_abstain:
                by_abstain["abstain"] += 1
            else:
                by_abstain["answer"] += 1

        return {
            "total": len(self.items),
            "by_category": by_category,
            "by_difficulty": by_difficulty,
            "by_query_type": by_query_type,
            "by_abstain": by_abstain,
        }

    def __len__(self) -> int:
        if not self._loaded:
            self.load()
        return len(self.items)

    def __iter__(self):
        if not self._loaded:
            self.load()
        return iter(self.items)


# 모듈 테스트
if __name__ == "__main__":
    dataset = BenchmarkDataset()
    dataset.load()

    print(f"Total items: {len(dataset)}")
    print(f"Statistics: {dataset.get_statistics()}")

    print("\nCategories:")
    for cat in dataset.get_categories():
        items = dataset.get_by_category(cat)
        print(f"  {cat}: {len(items)} items")

    print("\nSample item:")
    if dataset.items:
        print(f"  {dataset.items[0].to_dict()}")
