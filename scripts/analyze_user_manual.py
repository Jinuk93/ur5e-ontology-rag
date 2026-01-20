# ============================================================
# analyze_user_manual.py - User Manual 상세 분석
# ============================================================
# User Manual의 구조와 내용 패턴을 파악합니다.
# ============================================================

import fitz
import sys
import re

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def analyze_user_manual():
    """
    User Manual PDF 상세 분석
    """
    pdf_path = "data/raw/pdf/710-965-00_UR5e_User_Manual_en_Global.pdf"
    doc = fitz.open(pdf_path)

    print("="*60)
    print("[*] User Manual - Detailed Analysis")
    print("="*60)
    print(f"Total pages: {len(doc)}")

    # 1. 첫 10페이지 내용 분석 (목차 등)
    print(f"\n[1] First 10 Pages Overview")
    print("-"*60)

    for page_num in range(min(10, len(doc))):
        page = doc[page_num]
        text = page.get_text()
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        print(f"\n  Page {page_num + 1} ({len(text)} chars, {len(lines)} lines):")
        for line in lines[:3]:
            clean = str(line).encode('ascii', 'ignore').decode('ascii')
            if len(clean) > 55:
                clean = clean[:55] + "..."
            print(f"    | {clean}")

    # 2. 목차 구조 추정 (텍스트 기반)
    print(f"\n[2] Chapter Structure Estimation")
    print("-"*60)

    # 큰 제목 패턴 찾기
    chapter_pattern = re.compile(r'^(\d+)\.\s*([A-Z][a-z]+.*)')
    chapters = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        lines = text.split('\n')

        for line in lines:
            match = chapter_pattern.match(line.strip())
            if match and len(match.group(2)) > 3:
                chapters.append((match.group(1), match.group(2).strip(), page_num + 1))

    # 중복 제거하고 첫 15개만
    seen = set()
    unique_chapters = []
    for num, title, page in chapters:
        if title not in seen and len(title) > 5:
            seen.add(title)
            unique_chapters.append((num, title, page))

    print(f"Estimated chapters (first 15):")
    for num, title, page in unique_chapters[:15]:
        clean = title.encode('ascii', 'ignore').decode('ascii')
        if len(clean) > 40:
            clean = clean[:40] + "..."
        print(f"  {num}. {clean} (p.{page})")

    # 3. 사용자 가이드 관련 용어 분석
    print(f"\n[3] User Guide Terms Analysis")
    print("-"*60)

    guide_terms = [
        "Installation", "Setup", "Operation", "Configuration",
        "Troubleshooting", "Safety", "Program", "Screen",
        "Button", "Interface", "Settings", "Feature"
    ]

    term_pages = {}
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        for term in guide_terms:
            if term.lower() in text.lower():
                term_pages[term] = term_pages.get(term, 0) + 1

    print(f"User guide term mentions (page count):")
    for term, count in sorted(term_pages.items(), key=lambda x: -x[1])[:10]:
        print(f"  - {term}: {count} pages")

    # 4. UI/Screen 관련 내용 분석
    print(f"\n[4] UI/Screen Content Analysis")
    print("-"*60)

    ui_keywords = ["screen", "button", "menu", "tab", "panel", "window", "dialog"]
    ui_pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text().lower()

        ui_count = sum(1 for kw in ui_keywords if kw in text)
        if ui_count >= 3:
            ui_pages.append(page_num + 1)

    print(f"Pages with multiple UI references: {len(ui_pages)}")
    if ui_pages:
        print(f"  Sample pages: {ui_pages[:10]}")

    # 5. PolyScope 관련 분석 (로봇 소프트웨어)
    print(f"\n[5] PolyScope Software Analysis")
    print("-"*60)

    polyscope_pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()

        if "PolyScope" in text or "polyscope" in text.lower():
            polyscope_pages.append(page_num + 1)

    print(f"Pages mentioning PolyScope: {len(polyscope_pages)}")

    # PolyScope 관련 기능 키워드
    polyscope_features = ["Move", "Waypoint", "Program", "Installation", "Safety"]
    feature_mentions = {}

    for page_num in polyscope_pages[:50]:  # 처음 50개 페이지만 분석
        page = doc[page_num - 1]
        text = page.get_text()
        for feature in polyscope_features:
            if feature.lower() in text.lower():
                feature_mentions[feature] = feature_mentions.get(feature, 0) + 1

    print(f"PolyScope feature mentions:")
    for feature, count in sorted(feature_mentions.items(), key=lambda x: -x[1]):
        print(f"  - {feature}: {count} pages")

    # 6. 샘플 내용 페이지
    print(f"\n[6] Sample Content Pages")
    print("-"*60)

    sample_pages = [50, 100, 150, 200]
    for page_num in sample_pages:
        if page_num < len(doc):
            page = doc[page_num]
            text = page.get_text()
            lines = [l.strip() for l in text.split('\n') if l.strip()]

            print(f"\n  Page {page_num + 1}:")
            for line in lines[:5]:
                clean = str(line).encode('ascii', 'ignore').decode('ascii')
                if len(clean) > 55:
                    clean = clean[:55] + "..."
                print(f"    | {clean}")

    doc.close()

    print(f"\n{'='*60}")
    print("[*] User Manual Analysis Complete!")
    print("="*60)


if __name__ == "__main__":
    analyze_user_manual()
