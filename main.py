"""
作用：
- 项目统一启动入口，支持 Web 全栈服务与终端命令行两种运行方式。

用法：
    python3 main.py            # 默认启动 Web 服务（推荐），浏览器访问 http://127.0.0.1:8000
    python3 main.py web        # 同上，显式启动 Web 服务
    python3 main.py cli        # 启动终端交互式命令行

环境变量（仅 Web 模式）：
    WEB_HOST（默认 127.0.0.1）、WEB_PORT（默认 8000，端口占用时可改，如 WEB_PORT=8010）
"""

from __future__ import annotations

import os
import sys

from config.logging import setup_logging


def run_web() -> None:
    """启动 FastAPI 全栈 Web 服务。"""
    import uvicorn

    host = os.getenv("WEB_HOST", "127.0.0.1")
    port = int(os.getenv("WEB_PORT", "8000"))
    print("=" * 60)
    print("运筹优化智能体 · 全栈 Web 服务启动")
    print(f"请在浏览器打开: http://{host}:{port}")
    print("（端口被占用时可用 WEB_PORT 指定，例如 WEB_PORT=8010 python3 main.py）")
    print("=" * 60)
    uvicorn.run("app.api:app", host=host, port=port, log_level="info")


def run_terminal() -> None:
    """启动终端交互式命令行。"""
    from app.cli import run_cli

    run_cli()


def main() -> None:
    setup_logging()
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "web"
    if mode in {"web", "server", "serve"}:
        run_web()
    elif mode in {"cli", "terminal", "term"}:
        run_terminal()
    else:
        print(f"未知模式: {mode}\n用法: python3 main.py [web|cli]")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
