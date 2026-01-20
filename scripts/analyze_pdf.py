# ============================================================
# analyze_pdf.py - PDF 구조 분석 스크립트
# ============================================================
# 실행 방법: python scripts/analyze_pdf.py
# Phase 1에서 PDF 문서의 구조를 파악하기 위한 스크립트입니다.
# ============================================================

import fitz  # PyMuPDF
import os
import sys

# Windows 콘솔 인코딩 문제 해결
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def analyze_pdf(pdf_path):
    """
    PDF 파일의 구조를 분석합니다.

    Args:
        pdf_path: PDF 파일 경로

    Returns:
        dict: PDF 분석 결과
    """
    print(f"\n{'='*60}")
    print(f"[*] Analyzing: {os.path.basename(pdf_path)}")
    print(f"{'='*60}")

    # PDF 열기
    doc = fitz.open(pdf_path)

    # 기본 정보
    print(f"\n[1] Basic Info")
    print(f"    - Total Pages: {len(doc)}")
    print(f"    - File Size: {os.path.getsize(pdf_path) / 1024 / 1024:.2f} MB")

    # 메타데이터
    metadata = doc.metadata
    print(f"\n[2] Metadata")
    for key, value in metadata.items():
        if value:
            # 특수문자 제거 (인코딩 문제 방지)
            clean_value = str(value).encode('ascii', 'ignore').decode('ascii')
            print(f"    - {key}: {clean_value}")

    # 목차 (Table of Contents)
    toc = doc.get_toc()
    print(f"\n[3] Table of Contents (TOC)")
    print(f"    - TOC Entries: {len(toc)}")
    if toc:
        print(f"    - First 10 entries:")
        for i, entry in enumerate(toc[:10]):
            level, title, page = entry
            indent = "      " + "  " * (level - 1)
            # 특수문자 제거
            clean_title = str(title).encode('ascii', 'ignore').decode('ascii')
            print(f"{indent}[L{level}] p.{page}: {clean_title}")
        if len(toc) > 10:
            print(f"      ... and {len(toc) - 10} more entries")
    else:
        print("    - No TOC found in PDF")

    # 페이지별 샘플 분석
    print(f"\n[4] Page Sample Analysis (first 3 pages)")
    for page_num in range(min(3, len(doc))):
        page = doc[page_num]
        text = page.get_text()

        # 텍스트 길이 및 줄 수
        lines = text.split('\n')
        non_empty_lines = [l for l in lines if l.strip()]

        print(f"\n    Page {page_num + 1}:")
        print(f"      - Text length: {len(text)} chars")
        print(f"      - Total lines: {len(lines)}")
        print(f"      - Non-empty lines: {len(non_empty_lines)}")

        # 첫 5줄 미리보기
        print(f"      - Preview (first 5 non-empty lines):")
        for line in non_empty_lines[:5]:
            # 특수문자 제거 및 길이 제한
            clean_line = str(line).encode('ascii', 'ignore').decode('ascii')
            if len(clean_line) > 60:
                clean_line = clean_line[:60] + "..."
            print(f"        | {clean_line}")

    # 이미지 분석
    print(f"\n[5] Image Analysis")
    total_images = 0
    for page_num in range(len(doc)):
        page = doc[page_num]
        images = page.get_images()
        total_images += len(images)
    print(f"    - Total images in PDF: {total_images}")

    # 테이블 패턴 분석 (텍스트 기반 추정)
    print(f"\n[6] Table Pattern Detection")
    table_indicators = 0
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        # 테이블 패턴: 숫자나 코드가 반복되는 패턴
        if '|' in text or '\t' in text:
            table_indicators += 1
    print(f"    - Pages with table-like patterns: {table_indicators}")

    doc.close()

    print(f"\n{'='*60}")
    print(f"[*] Analysis Complete: {os.path.basename(pdf_path)}")
    print(f"{'='*60}")


def main():
    """
    data/raw/pdf/ 폴더의 모든 PDF 분석
    """
    pdf_dir = "data/raw/pdf"

    print("\n" + "="*60)
    print("[*] PDF Structure Analysis - Phase 1")
    print("="*60)

    # PDF 파일 목록
    pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
    print(f"\nFound {len(pdf_files)} PDF files:")
    for f in pdf_files:
        size_mb = os.path.getsize(os.path.join(pdf_dir, f)) / 1024 / 1024
        print(f"  - {f} ({size_mb:.2f} MB)")

    # 각 PDF 분석
    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_dir, pdf_file)
        try:
            analyze_pdf(pdf_path)
        except Exception as e:
            print(f"\n[ERROR] Failed to analyze {pdf_file}: {e}")

    print("\n" + "="*60)
    print("[*] All PDF Analysis Complete!")
    print("="*60)


if __name__ == "__main__":
    main()
