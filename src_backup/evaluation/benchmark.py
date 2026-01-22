# ============================================================
# src/evaluation/benchmark.py - Benchmark Dataset Loader
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
    expected_contexts: List[str]
    category: str
    difficulty: str
    expected_verification: str
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "BenchmarkItem":
        """딕셔너리에서 BenchmarkItem 생성"""
        return cls(
            id=data["id"],
            question=data["question"],
            expected_answer=data["expected_answer"],
            expected_contexts=data.get("expected_contexts", []),
            category=data["category"],
            difficulty=data["difficulty"],
            expected_verification=data["expected_verification"],
            tags=data.get("tags", []),
        )

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "question": self.question,
            "expected_answer": self.expected_answer,
            "expected_contexts": self.expected_contexts,
            "category": self.category,
            "difficulty": self.difficulty,
            "expected_verification": self.expected_verification,
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

        # 모든 JSON 파일 로드
        json_files = [
            "error_code_qa.json",
            "component_qa.json",
            "general_qa.json",
            "invalid_qa.json",
        ]

        for filename in json_files:
            filepath = self.data_dir / filename
            if filepath.exists():
                with open(filepath, "r", encoding="utf-8") as f:
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

        by_verification = {}
        for item in self.items:
            by_verification[item.expected_verification] = by_verification.get(item.expected_verification, 0) + 1

        return {
            "total": len(self.items),
            "by_category": by_category,
            "by_difficulty": by_difficulty,
            "by_verification": by_verification,
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
