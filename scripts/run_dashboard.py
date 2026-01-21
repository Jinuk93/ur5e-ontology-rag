# ============================================================
# scripts/run_dashboard.py - Dashboard Run Script
# ============================================================
# UR5e RAG Dashboard 실행 스크립트
#
# 사용법:
#   python scripts/run_dashboard.py [OPTIONS]
#
# 옵션:
#   --port PORT    포트 번호 (기본: 8501)
#   --api-url URL  API 서버 URL (기본: http://localhost:8000)
# ============================================================

import os
import sys
import argparse
import subprocess

# 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def main():
    """Dashboard 실행"""
    parser = argparse.ArgumentParser(
        description="UR5e RAG Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 기본 실행
  python scripts/run_dashboard.py

  # 커스텀 포트
  python scripts/run_dashboard.py --port 8502

  # API URL 지정
  python scripts/run_dashboard.py --api-url http://192.168.1.100:8000
        """
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="대시보드 포트 번호 (기본: 8501)"
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:8000",
        help="API 서버 URL (기본: http://localhost:8000)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="디버그 모드 활성화"
    )

    args = parser.parse_args()

    # 환경변수 설정
    os.environ["API_BASE_URL"] = args.api_url

    # 배너 출력
    print("=" * 60)
    print("  UR5e RAG Dashboard")
    print("=" * 60)
    print(f"  Dashboard: http://localhost:{args.port}")
    print(f"  API URL:   {args.api_url}")
    print(f"  Debug:     {args.debug}")
    print("=" * 60)
    print()
    print("  📊 Overview       - System status and KPIs")
    print("  💬 RAG Query      - Chat interface with evidence")
    print("  🔍 Search Explorer- Compare search strategies")
    print("  🕸️ Knowledge Graph- Neo4j style visualization")
    print("  📈 Performance    - Benchmarks and comparisons")
    print("  🔧 LLMOps Monitor - Cost and latency tracking")
    print()
    print("=" * 60)
    print()

    # Streamlit 앱 경로
    app_path = os.path.join(project_root, "src", "dashboard", "app.py")

    # Streamlit 실행
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        app_path,
        "--server.port", str(args.port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ]

    if args.debug:
        cmd.extend(["--logger.level", "debug"])

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n[*] Dashboard stopped")
    except Exception as e:
        print(f"[ERROR] Failed to start dashboard: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
