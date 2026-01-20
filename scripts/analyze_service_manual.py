# ============================================================
# analyze_service_manual.py - Service Manual 상세 분석
# ============================================================
# Service Manual의 구조와 내용 패턴을 파악합니다.
# ============================================================

import fitz
import sys
import re

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def analyze_service_manual():
    """
    Service Manual PDF 상세 분석
    """
    pdf_path = "data/raw/pdf/e-Series_Service_Manual_en.pdf"
    doc = fitz.open(pdf_path)

    print("="*60)
    print("[*] Service Manual - Detailed Analysis")
    print("="*60)

    # 1. 목차 페이지 분석 (페이지 2-3)
    print(f"\n[1] Table of Contents (from pages 2-3)")
    print("-"*60)

    toc_text = ""
    for page_num in [1, 2]:  # 0-indexed: 페이지 2, 3
        page = doc[page_num]
        toc_text += page.get_text()

    # 챕터 추출
    chapters = re.findall(r'(\d+)\.\s*([A-Za-z\s&]+)\s*\n', toc_text)
    print(f"Main chapters found:")
    for num, title in chapters[:10]:
        clean = title.strip().encode('ascii', 'ignore').decode('ascii')
        if clean and len(clean) > 2:
            print(f"  {num}. {clean}")

    # 2. 각 챕터 시작 페이지 내용 분석
    print(f"\n[2] Chapter Content Analysis")
    print("-"*60)

    # 주요 챕터 시작으로 추정되는 페이지들 분석
    chapter_pages = [4, 10, 20, 40, 60, 80, 100]

    for page_num in chapter_pages:
        if page_num < len(doc):
            page = doc[page_num]
            text = page.get_text()
            lines = [l.strip() for l in text.split('\n') if l.strip()]

            print(f"\n  Page {page_num + 1}:")
            # 첫 3줄만 출력
            for line in lines[:3]:
                clean = str(line).encode('ascii', 'ignore').decode('ascii')
                if len(clean) > 50:
                    clean = clean[:50] + "..."
                print(f"    | {clean}")

    # 3. 컴포넌트 관련 용어 분석
    print(f"\n[3] Component Terms Analysis")
    print("-"*60)

    # 전체 문서에서 컴포넌트 용어 추출
    component_terms = [
        "Control Box", "Robot Arm", "Teach Pendant", "Joint",
        "Motor", "Encoder", "Safety", "Power Supply",
        "Cable", "Connector", "PCB", "Board"
    ]

    term_counts = {}
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        for term in component_terms:
            if term.lower() in text.lower():
                term_counts[term] = term_counts.get(term, 0) + 1

    print(f"Component mentions (page count):")
    for term, count in sorted(term_counts.items(), key=lambda x: -x[1]):
        print(f"  - {term}: {count} pages")

    # 4. 절차/단계 패턴 분석
    print(f"\n[4] Procedure/Step Patterns")
    print("-"*60)

    step_patterns = {
        "numbered_steps": 0,  # 1. 2. 3. 형태
        "bullet_points": 0,   # - 또는 * 형태
        "warning_notes": 0,   # WARNING, CAUTION
        "figures": 0,         # Figure 언급
    }

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()

        if re.search(r'^\s*\d+\.\s+[A-Z]', text, re.MULTILINE):
            step_patterns["numbered_steps"] += 1
        if "WARNING" in text or "CAUTION" in text:
            step_patterns["warning_notes"] += 1
        if "Figure" in text or "Fig." in text:
            step_patterns["figures"] += 1

    print(f"Pattern occurrences:")
    for pattern, count in step_patterns.items():
        print(f"  - {pattern}: {count} pages")

    # 5. 샘플 절차 페이지 분석
    print(f"\n[5] Sample Procedure Page Content")
    print("-"*60)

    # 절차가 있을 것 같은 페이지 (중간 부분)
    page_num = 55  # Dismantling 관련 페이지 근처
    if page_num < len(doc):
        page = doc[page_num]
        text = page.get_text()
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        print(f"\n  Page {page_num + 1} content:")
        for line in lines[:20]:
            clean = str(line).encode('ascii', 'ignore').decode('ascii')
            if len(clean) > 60:
                clean = clean[:60] + "..."
            print(f"    | {clean}")

    doc.close()

    print(f"\n{'='*60}")
    print("[*] Service Manual Analysis Complete!")
    print("="*60)


if __name__ == "__main__":
    analyze_service_manual()
