# ============================================================
# src/ingestion/manifest_generator.py - 메타데이터 생성기
# ============================================================
# 청킹 결과로부터 chunk_manifest.jsonl 파일 생성
#
# Main-F3에서 구현
# ============================================================

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional


class ManifestGenerator:
    """
    청킹 결과로부터 metadata 파일 생성

    chunk_manifest.jsonl: 모든 청크의 정확한 위치 매핑 정보

    사용 예시:
        generator = ManifestGenerator()
        generator.add_chunks_from_file("error_codes", "data/processed/chunks/error_codes_chunks.json")
        generator.save()
    """

    def __init__(
        self,
        output_dir: str = "data/processed/metadata"
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._manifest: List[Dict[str, Any]] = []

    def add_chunks_from_file(
        self,
        doc_id: str,
        chunks_file: str
    ) -> int:
        """
        청크 파일에서 manifest 엔트리 추가

        Args:
            doc_id: 문서 ID (error_codes, service_manual, user_manual)
            chunks_file: 청크 JSON 파일 경로

        Returns:
            추가된 청크 수
        """
        with open(chunks_file, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        count = 0
        for chunk in chunks:
            metadata = chunk.get("metadata", {})

            entry = {
                "chunk_id": chunk.get("id"),
                "doc_id": doc_id,
                "page": metadata.get("page", 1),
                "section": metadata.get("section", ""),
                "error_code": metadata.get("error_code"),
                "chapter": metadata.get("chapter"),
                "doc_type": metadata.get("doc_type", doc_id),
                "tokens": self._estimate_tokens(chunk.get("content", "")),
                "content_length": len(chunk.get("content", "")),
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            # None 값 제거
            entry = {k: v for k, v in entry.items() if v is not None}
            self._manifest.append(entry)
            count += 1

        return count

    def _estimate_tokens(self, text: str) -> int:
        """토큰 수 추정 (대략 4자당 1토큰)"""
        return len(text) // 4

    def save(self) -> str:
        """
        chunk_manifest.jsonl 저장

        Returns:
            저장된 파일 경로
        """
        manifest_path = self.output_dir / "chunk_manifest.jsonl"

        with open(manifest_path, "w", encoding="utf-8") as f:
            for entry in self._manifest:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        print(f"[OK] Saved chunk_manifest.jsonl: {len(self._manifest)} chunks")
        return str(manifest_path)

    def get_stats(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        doc_counts = {}
        for entry in self._manifest:
            doc_id = entry.get("doc_id", "unknown")
            doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1

        return {
            "total_chunks": len(self._manifest),
            "by_document": doc_counts
        }


# ============================================================
# CLI 실행
# ============================================================

if __name__ == "__main__":
    import os
    import sys

    # 프로젝트 루트 설정
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.chdir(project_root)

    print("=" * 60)
    print("ManifestGenerator - chunk_manifest.jsonl 생성")
    print("=" * 60)

    generator = ManifestGenerator()

    # 문서별 청크 파일 처리
    doc_files = [
        ("error_codes", "data/processed/chunks/error_codes_chunks.json"),
        ("service_manual", "data/processed/chunks/service_manual_chunks.json"),
        ("user_manual", "data/processed/chunks/user_manual_chunks.json"),
    ]

    for doc_id, chunk_file in doc_files:
        if os.path.exists(chunk_file):
            count = generator.add_chunks_from_file(doc_id, chunk_file)
            print(f"  {doc_id}: {count} chunks added")
        else:
            print(f"  {doc_id}: File not found - {chunk_file}")

    # 저장
    generator.save()

    # 통계 출력
    stats = generator.get_stats()
    print(f"\nTotal: {stats['total_chunks']} chunks")
    print("=" * 60)
