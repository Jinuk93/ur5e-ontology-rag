# ============================================================
# analyze_error_codes.py - ErrorCodes.pdf 상세 분석
# ============================================================
# 에러 코드의 구조와 패턴을 파악합니다.
# ============================================================

import fitz
import sys
import re

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def analyze_error_codes():
    """
    ErrorCodes.pdf의 에러 코드 구조 상세 분석
    """
    pdf_path = "data/raw/pdf/ErrorCodes.pdf"
    doc = fitz.open(pdf_path)

    print("="*60)
    print("[*] ErrorCodes.pdf - Detailed Analysis")
    print("="*60)

    # 1. TOC 전체 분석
    toc = doc.get_toc()
    print(f"\n[1] Full TOC Analysis ({len(toc)} entries)")
    print("-"*60)

    # 에러 코드 카테고리 분석
    categories = {}
    for level, title, page in toc:
        if level == 1:
            categories[title] = {"page": page, "codes": []}
        elif level == 2:
            # 가장 최근 카테고리에 추가
            if categories:
                last_cat = list(categories.keys())[-1]
                categories[last_cat]["codes"].append(title)

    print(f"\nCategories found: {len(categories)}")
    for cat, info in list(categories.items())[:5]:
        clean_cat = str(cat).encode('ascii', 'ignore').decode('ascii')
        print(f"  - {clean_cat} (p.{info['page']}): {len(info['codes'])} codes")

    # 2. 에러 코드 패턴 분석
    print(f"\n[2] Error Code Pattern Analysis")
    print("-"*60)

    # 모든 레벨 2 항목 (에러 코드들) 추출
    error_codes = [title for level, title, page in toc if level == 2]
    print(f"Total error codes in TOC: {len(error_codes)}")

    # 패턴 분류
    patterns = {
        "C codes (Cx)": [],
        "CC codes (CCxxx)": [],
        "Other": []
    }

    for code in error_codes:
        if re.match(r'^C\d+$', code):
            patterns["C codes (Cx)"].append(code)
        elif re.match(r'^CC\d+', code):
            patterns["CC codes (CCxxx)"].append(code)
        else:
            patterns["Other"].append(code)

    for pattern_name, codes in patterns.items():
        print(f"\n  {pattern_name}: {len(codes)} codes")
        if codes:
            sample = codes[:5]
            print(f"    Sample: {', '.join(sample)}")

    # 3. 실제 페이지 내용 분석 (에러 코드 페이지)
    print(f"\n[3] Sample Error Code Page Content")
    print("-"*60)

    # TOC에서 첫 번째 에러 코드 페이지 찾기
    for level, title, page in toc:
        if level == 2 and title == "C0":
            print(f"\nAnalyzing error code C0 (page {page}):")
            page_obj = doc[page - 1]  # 0-indexed
            text = page_obj.get_text()

            # 깔끔하게 출력
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            print(f"  Content preview:")
            for line in lines[:15]:
                clean = str(line).encode('ascii', 'ignore').decode('ascii')
                if len(clean) > 70:
                    clean = clean[:70] + "..."
                print(f"    | {clean}")
            break

    # 4. 에러 코드 구조 추정
    print(f"\n[4] Error Code Structure Estimation")
    print("-"*60)

    # 중간 페이지에서 에러 코드 패턴 분석
    sample_pages = [12, 20, 50, 100]  # 다양한 페이지 샘플링

    for page_num in sample_pages:
        if page_num < len(doc):
            page = doc[page_num]
            text = page.get_text()

            print(f"\n  Page {page_num + 1} patterns:")

            # 에러 코드 관련 키워드 찾기
            keywords = ["Error", "Warning", "Cause", "Solution", "Action", "Description"]
            for kw in keywords:
                count = text.lower().count(kw.lower())
                if count > 0:
                    print(f"    - '{kw}' appears: {count} times")

    doc.close()

    print(f"\n{'='*60}")
    print("[*] ErrorCodes.pdf Analysis Complete!")
    print("="*60)


if __name__ == "__main__":
    analyze_error_codes()
