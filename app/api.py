"""
作用：
- 全栈后端（FastAPI），单用户简化架构，把多轮对话/问题分解纠正/求解能力暴露为 HTTP 接口，并托管前端页面。
- 复用 `core.conversation.ConversationManager` 作为业务核心，不引入额外持久化。

接口：
- GET  /                 -> 返回单文件前端页面。
- POST /api/analyze      -> {session_id, message} 首轮分析，返回数学模型草案。
- POST /api/refine       -> {session_id, message} 纠正并重新分析。
- POST /api/solve        -> {session_id} 确认并求解，返回目标值/路径/路线图/甘特图/完整代码。
- POST /api/reset        -> {session_id} 重置会话。
- GET  /api/history      -> {session_id} 拉取对话历史。

调用关系：
- 被 `main.py`（web 模式）或 `uvicorn app.api:app` 启动。
- 调用 `core.conversation.get_conversation_manager`。
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from core.conversation import get_conversation_manager

FRONTEND_PATH = Path(__file__).resolve().parent / "static" / "index.html"


class AnalyzeRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class RefineRequest(BaseModel):
    session_id: str
    message: str


class SessionRequest(BaseModel):
    session_id: str


def create_api_app() -> FastAPI:
    """创建并配置 FastAPI 应用。"""
    app = FastAPI(title="运筹优化智能体", version="1.0.0")
    manager = get_conversation_manager()

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        if FRONTEND_PATH.exists():
            return HTMLResponse(FRONTEND_PATH.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>前端页面缺失</h1><p>请确认 app/static/index.html 存在。</p>", status_code=500)

    @app.post("/api/analyze")
    def analyze(req: AnalyzeRequest) -> JSONResponse:
        session_id = req.session_id or uuid.uuid4().hex[:12]
        try:
            payload = manager.analyze(session_id, req.message)
        except Exception as exc:  # pragma: no cover - 运行期保护
            return JSONResponse({"type": "error", "message": f"分析失败: {exc}"}, status_code=500)
        payload["session_id"] = session_id
        return JSONResponse(payload)

    @app.post("/api/refine")
    def refine(req: RefineRequest) -> JSONResponse:
        try:
            payload = manager.refine(req.session_id, req.message)
        except Exception as exc:  # pragma: no cover
            return JSONResponse({"type": "error", "message": f"纠正失败: {exc}"}, status_code=500)
        payload["session_id"] = req.session_id
        return JSONResponse(payload)

    @app.post("/api/solve")
    def solve(req: SessionRequest) -> JSONResponse:
        try:
            payload = manager.solve(req.session_id)
        except Exception as exc:  # pragma: no cover
            return JSONResponse({"type": "error", "message": f"求解失败: {exc}"}, status_code=500)
        payload["session_id"] = req.session_id
        return JSONResponse(payload)

    @app.post("/api/reset")
    def reset(req: SessionRequest) -> Dict[str, Any]:
        manager.reset(req.session_id)
        return {"type": "reset", "session_id": req.session_id, "message": "会话已重置。"}

    @app.get("/api/history")
    def history(session_id: str) -> Dict[str, Any]:
        return {"session_id": session_id, "messages": manager.history(session_id)}

    return app


app = create_api_app()


if __name__ == "__main__":
    import uvicorn

    print("=== 启动运筹优化智能体全栈服务 http://127.0.0.1:8000 ===")
    uvicorn.run(app, host="127.0.0.1", port=8000)
