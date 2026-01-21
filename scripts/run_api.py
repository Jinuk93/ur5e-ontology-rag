# ============================================================
# scripts/run_api.py - API 서버 실행 스크립트
# ============================================================
# UR5e RAG API 서버를 실행합니다.
#
# 사용법:
#   python scripts/run_api.py [OPTIONS]
#
# 옵션:
#   --host HOST    바인딩 호스트 (기본: 0.0.0.0)
#   --port PORT    포트 번호 (기본: 8000)
#   --reload       개발 모드 (자동 리로드)
#   --workers N    워커 수 (프로덕션 모드)
# ============================================================

import os
import sys
import argparse

# 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def main():
    """API 서버 실행"""
    parser = argparse.ArgumentParser(
        description="UR5e RAG API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 개발 모드 (자동 리로드)
  python scripts/run_api.py --reload

  # 프로덕션 모드 (4 워커)
  python scripts/run_api.py --workers 4

  # 커스텀 포트
  python scripts/run_api.py --port 8080
        """
    )

    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="바인딩 호스트 (기본: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="포트 번호 (기본: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="개발 모드 (자동 리로드)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="워커 수 (기본: 1)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="로그 레벨 (기본: info)"
    )

    args = parser.parse_args()

    # uvicorn 임포트
    try:
        import uvicorn
    except ImportError:
        print("[ERROR] uvicorn이 설치되지 않았습니다.")
        print("설치: pip install uvicorn[standard]")
        sys.exit(1)

    # 배너 출력
    print("=" * 60)
    print("  UR5e RAG API Server")
    print("=" * 60)
    print(f"  Host:      {args.host}")
    print(f"  Port:      {args.port}")
    print(f"  Reload:    {args.reload}")
    print(f"  Workers:   {args.workers}")
    print(f"  Log Level: {args.log_level}")
    print("=" * 60)
    print()

    # 서버 실행
    if args.reload:
        # 개발 모드
        uvicorn.run(
            "src.api.main:app",
            host=args.host,
            port=args.port,
            reload=True,
            log_level=args.log_level,
        )
    else:
        # 프로덕션 모드
        uvicorn.run(
            "src.api.main:app",
            host=args.host,
            port=args.port,
            workers=args.workers,
            log_level=args.log_level,
        )


if __name__ == "__main__":
    main()
