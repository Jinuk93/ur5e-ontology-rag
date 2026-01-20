# ============================================================
# scripts/run_ingestion.py - 데이터 수집 파이프라인 실행
# ============================================================
# 실행 방법: python scripts/run_ingestion.py
#
# 전체 파이프라인:
#   1. data/raw/pdf/ 의 PDF 파일 파싱
#   2. 문서 유형별 청킹
#   3. data/processed/chunks/ 에 JSON 저장
#
# 출력 파일:
#   - error_codes_chunks.json
#   - service_manual_chunks.json
#   - user_manual_chunks.json
# ============================================================

import sys
import os
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
# 이렇게 하면 src.ingestion 모듈을 import 할 수 있음
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from src.ingestion import PDFParser, Chunker, ChunkingConfig
from src.ingestion.models import save_chunks_to_json


# ============================================================
# [1] 설정
# ============================================================

# 경로 설정
PDF_DIR = os.path.join(project_root, "data", "raw", "pdf")
OUTPUT_DIR = os.path.join(project_root, "data", "processed", "chunks")

# 출력 파일명 매핑
OUTPUT_FILES = {
    "error_code": "error_codes_chunks.json",
    "service_manual": "service_manual_chunks.json",
    "user_manual": "user_manual_chunks.json",
    "unknown": "unknown_chunks.json",
}


# ============================================================
# [2] 메인 함수
# ============================================================

def run_ingestion():
    """
    데이터 수집 파이프라인 실행

    처리 흐름:
        1. 출력 폴더 생성
        2. PDF 파일 파싱
        3. 각 문서 청킹
        4. JSON 파일로 저장
        5. 결과 요약 출력
    """
    print("=" * 60)
    print("[*] UR5e Ontology RAG - Data Ingestion Pipeline")
    print(f"    Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # --------------------------------------------------------
    # Step 1: 출력 폴더 생성
    # --------------------------------------------------------
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"\n[Step 1] Output directory: {OUTPUT_DIR}")

    # --------------------------------------------------------
    # Step 2: PDF 파싱
    # --------------------------------------------------------
    print(f"\n[Step 2] Parsing PDF files from: {PDF_DIR}")
    print("-" * 40)

    parser = PDFParser()
    documents = []

    # PDF 파일 목록
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')]

    if not pdf_files:
        print("[ERROR] No PDF files found!")
        return

    # 각 PDF 파싱
    for pdf_file in pdf_files:
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        try:
            doc = parser.parse(pdf_path)
            documents.append(doc)
        except Exception as e:
            print(f"[ERROR] Failed to parse {pdf_file}: {e}")

    # --------------------------------------------------------
    # Step 3: 청킹
    # --------------------------------------------------------
    print(f"\n[Step 3] Chunking documents")
    print("-" * 40)

    # 청킹 설정
    config = ChunkingConfig(
        chunk_size=1000,      # 기본 청크 크기
        chunk_overlap=200,    # 오버랩
        min_chunk_size=100,   # 최소 크기
    )

    chunker = Chunker(config=config)

    # 문서 유형별 청크 저장
    chunks_by_type = {}

    for doc in documents:
        chunks = chunker.chunk_document(doc)
        doc_type = doc.doc_type

        if doc_type not in chunks_by_type:
            chunks_by_type[doc_type] = []

        chunks_by_type[doc_type].extend(chunks)

    # --------------------------------------------------------
    # Step 4: JSON 저장
    # --------------------------------------------------------
    print(f"\n[Step 4] Saving chunks to JSON")
    print("-" * 40)

    saved_files = []

    for doc_type, chunks in chunks_by_type.items():
        # 출력 파일명
        filename = OUTPUT_FILES.get(doc_type, f"{doc_type}_chunks.json")
        filepath = os.path.join(OUTPUT_DIR, filename)

        # 저장
        save_chunks_to_json(chunks, filepath)
        saved_files.append((filename, len(chunks)))

    # --------------------------------------------------------
    # Step 5: 결과 요약
    # --------------------------------------------------------
    print(f"\n[Step 5] Summary")
    print("=" * 60)

    total_chunks = 0
    total_chars = 0

    print("\n{:<35} {:>10} {:>15}".format("File", "Chunks", "Characters"))
    print("-" * 60)

    for doc_type, chunks in chunks_by_type.items():
        filename = OUTPUT_FILES.get(doc_type, f"{doc_type}_chunks.json")
        chunk_count = len(chunks)
        char_count = sum(len(c) for c in chunks)
        total_chunks += chunk_count
        total_chars += char_count

        print("{:<35} {:>10,} {:>15,}".format(filename, chunk_count, char_count))

    print("-" * 60)
    print("{:<35} {:>10,} {:>15,}".format("TOTAL", total_chunks, total_chars))

    print("\n" + "=" * 60)
    print(f"[OK] Ingestion complete!")
    print(f"     Output: {OUTPUT_DIR}")
    print(f"     Total chunks: {total_chunks:,}")
    print(f"     Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    return chunks_by_type


# ============================================================
# [3] 실행
# ============================================================

if __name__ == "__main__":
    run_ingestion()
