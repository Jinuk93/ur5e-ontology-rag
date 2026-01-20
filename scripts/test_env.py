# ============================================================
# test_env.py - 환경 설정 검증 스크립트
# ============================================================
# 실행 방법: python scripts/test_env.py
# 이 스크립트는 Phase 0에서 설정한 환경이 제대로 동작하는지 확인합니다.
# ============================================================

import sys


def check_python_version():
    """
    Python 버전 확인
    최소 3.10 이상이어야 함
    """
    print("=" * 50)
    print("[1] Python Version Check")
    print("=" * 50)

    version = sys.version_info                        # 현재 Python 버전 정보
    print(f"Current: Python {version.major}.{version.minor}.{version.micro}")

    if version.major >= 3 and version.minor >= 10:   # 3.10 이상인지 확인
        print("[OK] Python version OK")
        return True
    else:
        print("[FAIL] Python 3.10+ required")
        return False


def check_packages():
    """
    필수 패키지 설치 확인
    """
    print("\n" + "=" * 50)
    print("[2] Package Check")
    print("=" * 50)

    # 확인할 패키지 목록
    packages = [
        ("dotenv", "python-dotenv"),      # (import 이름, 패키지 이름)
        ("yaml", "pyyaml"),
        ("fitz", "pymupdf"),              # pymupdf는 fitz로 import
        ("openai", "openai"),
        ("chromadb", "chromadb"),
        ("neo4j", "neo4j"),
        ("fastapi", "fastapi"),
        ("streamlit", "streamlit"),
    ]

    all_ok = True
    for import_name, package_name in packages:
        try:
            __import__(import_name)                   # 동적으로 import 시도
            print(f"[OK] {package_name}")
        except ImportError:
            print(f"[FAIL] {package_name} - pip install {package_name}")
            all_ok = False

    return all_ok


def check_env_variables():
    """
    환경변수 확인 (.env 파일)
    """
    print("\n" + "=" * 50)
    print("[3] Environment Variables Check")
    print("=" * 50)

    import os
    from dotenv import load_dotenv

    load_dotenv()                                     # .env 파일 로드

    # 확인할 환경변수 목록
    env_vars = [
        "OPENAI_API_KEY",
        "NEO4J_URI",
        "NEO4J_USER",
        "NEO4J_PASSWORD",
        "CHROMA_PERSIST_DIR",
    ]

    all_ok = True
    for var in env_vars:
        value = os.getenv(var)                        # 환경변수 값 가져오기
        if value:
            # API 키는 앞 10자만 표시 (보안)
            if "KEY" in var or "PASSWORD" in var:
                display = value[:10] + "..." if len(value) > 10 else value
            else:
                display = value
            print(f"[OK] {var} = {display}")
        else:
            print(f"[FAIL] {var} - not set")
            all_ok = False

    return all_ok


def check_neo4j_connection():
    """
    Neo4j 연결 확인
    """
    print("\n" + "=" * 50)
    print("[4] Neo4j Connection Check")
    print("=" * 50)

    import os
    from dotenv import load_dotenv

    load_dotenv()

    try:
        from neo4j import GraphDatabase

        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER")
        password = os.getenv("NEO4J_PASSWORD")

        # Neo4j 드라이버 생성 및 연결 테스트
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()                  # 연결 확인
        driver.close()

        print(f"[OK] Neo4j connected ({uri})")
        return True

    except Exception as e:
        print(f"[FAIL] Neo4j connection failed: {e}")
        print("   -> Check if Docker is running: docker ps")
        return False


def check_openai_api():
    """
    OpenAI API 연결 확인
    """
    print("\n" + "=" * 50)
    print("[5] OpenAI API Check")
    print("=" * 50)

    import os
    from dotenv import load_dotenv

    load_dotenv()

    try:
        from openai import OpenAI

        client = OpenAI()                             # 환경변수에서 자동으로 키 로드

        # 간단한 테스트 (모델 목록 조회)
        models = client.models.list()
        print("[OK] OpenAI API connected")
        return True

    except Exception as e:
        print(f"[FAIL] OpenAI API failed: {e}")
        print("   -> Check your API key")
        return False


def main():
    """
    메인 함수 - 모든 검증 실행
    """
    print("\n[*] Starting environment verification...\n")

    results = []

    results.append(("Python Version", check_python_version()))
    results.append(("Packages", check_packages()))
    results.append(("Env Variables", check_env_variables()))
    results.append(("Neo4j Connection", check_neo4j_connection()))
    results.append(("OpenAI API", check_openai_api()))

    # 최종 결과 출력
    print("\n" + "=" * 50)
    print("[SUMMARY] Final Results")
    print("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {name}")
        if not passed:
            all_passed = False

    print("=" * 50)
    if all_passed:
        print("\n*** All checks passed! ***")
        print("Ready to proceed to Phase 1!")
    else:
        print("\n*** Some checks failed ***")
        print("Please fix the [FAIL] items above.")

    return all_passed


if __name__ == "__main__":
    main()
