"""데이터 수집(ingestion) 파이프라인 실행 스크립트.

Step02(데이터 준비)의 재현성을 위해 다음 두 모드를 제공합니다.

1) validate: 현재 저장된 청크/매니페스트가 기대값(722 chunks 등)을 충족하는지 검증
2) generate: data/raw/pdf의 PDF를 파싱/청킹하여 data/processed/chunks에 저장하고
            data/processed/metadata/manifest.json을 생성

주의: generate는 기존 산출물과 동일한 청크 ID/경계를 1:1로 재현하는 것을 목표로 하지 않습니다.
      (특히 ErrorCodes 문서는 구조적 청킹 로직이 별도 필요할 수 있습니다.)
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict, List

from src.config import get_settings
from src.ingestion import (
    Chunk,
    Manifest,
    chunk_pages,
    load_chunks_from_file,
    load_all_chunks,
    load_manifest,
    parse_pdf,
    save_chunks_to_file,
    save_manifest,
)


logger = logging.getLogger(__name__)


def _iter_pdfs(pdf_dir: Path) -> List[Path]:
    return sorted([p for p in pdf_dir.glob("*.pdf") if p.is_file()])


def run_validate(check_sensor: bool = True) -> int:
    settings = get_settings()

    chunks = load_all_chunks()
    manifest = load_manifest()

    print(f"Chunks loaded: {len(chunks)}")
    if manifest.totals:
        print(f"Manifest totals: {manifest.totals}")
    else:
        print("Manifest totals: <empty>")

    if check_sensor:
        sensor_path = settings.paths.sensor_dir / "raw" / "axia80_week_01.parquet"
        if sensor_path.exists():
            try:
                import pandas as pd  # type: ignore
            except ImportError:
                print("[WARN] pandas not installed; skipping sensor parquet check")
            else:
                df = pd.read_parquet(sensor_path)
                print(f"Sensor records: {len(df)} ({sensor_path})")
        else:
            print(f"Sensor file not found: {sensor_path}")

    # 기대값(문서 기준)
    expected_chunks = 722
    if len(chunks) != expected_chunks:
        print(f"[WARN] Expected {expected_chunks} chunks, got {len(chunks)}")
        return 2

    if manifest.totals.get("chunks") not in (0, expected_chunks):
        print(f"[WARN] Manifest totals mismatch: {manifest.totals}")
        return 2

    print("[OK] Validation passed")
    return 0


def run_generate(force: bool = False) -> int:
    settings = get_settings()

    pdf_dir = settings.paths.data_raw_dir
    chunks_dir = settings.paths.chunks_dir
    manifest_path = settings.paths.data_processed_dir / "metadata" / "manifest.json"

    pdf_files = _iter_pdfs(pdf_dir)
    if not pdf_files:
        print(f"[ERROR] No PDF files found in: {pdf_dir}")
        return 2

    chunks_dir.mkdir(parents=True, exist_ok=True)

    manifest = Manifest()
    manifest.settings = {
        "chunk_size": settings.document.chunk_size,
        "chunk_overlap": settings.document.chunk_overlap,
    }

    total_chunks = 0
    for pdf_path in pdf_files:
        meta, pages = parse_pdf(pdf_path)

        # doc_id는 pipeline 전체에서 사용되는 식별자. 기본은 doc_type.
        doc_id = meta.doc_type
        out_file = chunks_dir / f"{doc_id}_chunks.json"

        if out_file.exists() and not force:
            existing = load_chunks_from_file(out_file)
            print(f"[SKIP] {out_file.name} exists (use --force to overwrite)")
            # manifest에는 파일 기준 정보만 추가
            # chunk_count는 파일 기반으로 세는게 더 정확하지만, 여기선 최소 정보만
            manifest.add_document(
                doc_id,
                {
                    "source": meta.source,
                    "chunks_file": out_file.name,
                    "total_pages": meta.total_pages,
                    "topics": meta.topics,
                    "doc_type": meta.doc_type,
                    "chunk_count": len(existing),
                },
            )
            continue

        chunks: List[Chunk] = chunk_pages(
            pages,
            doc_id=doc_id,
            doc_type=meta.doc_type,
            source=meta.source,
        )
        save_chunks_to_file(chunks, out_file)

        manifest.add_document(
            doc_id,
            {
                "source": meta.source,
                "chunks_file": out_file.name,
                "total_pages": meta.total_pages,
                "topics": meta.topics,
                "doc_type": meta.doc_type,
                "chunk_count": len(chunks),
            },
        )
        total_chunks += len(chunks)

        print(f"[OK] {pdf_path.name} -> {out_file.name} ({len(chunks)} chunks)")

    manifest.update_totals()
    save_manifest(manifest, manifest_path=manifest_path)
    print(f"[OK] Manifest saved: {manifest_path}")
    print(f"[OK] Total chunks (generated this run): {total_chunks}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="UR5e Ontology RAG - Ingestion")
    parser.add_argument(
        "--mode",
        choices=["validate", "generate"],
        default="validate",
        help="실행 모드 (기본: validate)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="(generate) 기존 청크 파일을 덮어씀",
    )
    parser.add_argument(
        "--no-sensor-check",
        action="store_true",
        help="(validate) 센서 parquet 검증을 건너뜀",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.mode == "validate":
        return run_validate(check_sensor=not args.no_sensor_check)
    return run_generate(force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
