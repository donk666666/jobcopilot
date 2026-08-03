import logging
import os
import json
import hashlib
import secrets
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.config import settings
from app.agent.graph import run_agent, run_agent_stream
from app.rag.loader import index_document, index_directory
from app.rag.vectorstore import get_or_create_collection
from app.crawler.feed import fetch_feeds, start_scheduler
from app.feishu.bot import handle_event
from app.session_store import SessionStore
from app.memory import build_context

os.makedirs(settings.log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(Path(settings.log_dir) / "app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("应用启动")
    from app.rag.vectorstore import get_embedding_model, get_or_create_collection
    logger.info("预热 embedding 模型...")
    get_embedding_model()
    get_or_create_collection()
    logger.info("预热完成")
    start_scheduler()
    logger.info(f"爬虫定时器已启动，间隔 {settings.crawl_schedule_hours} 小时")
    yield
    logger.info("应用关闭")


app = FastAPI(title="智能文档问答助手", version="1.0.0", lifespan=lifespan)

static_dir = Path(__file__).parent / "web" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

store = SessionStore()

# --- 认证 ---

_auth_tokens: set[str] = set()
_bearer = HTTPBearer(auto_error=False)


def _hash_password(password: str) -> str:
    secret_salt = settings.llm_api_key[:16] if settings.llm_api_key else "smart-doc-qa-salt"
    return hashlib.sha256((password + secret_salt).encode()).hexdigest()


def _generate_token() -> str:
    return secrets.token_urlsafe(32)


def _require_auth(credentials: HTTPAuthorizationCredentials = Depends(_bearer)):
    """认证依赖：无密码时放行，有密码时校验 Bearer token"""
    if not settings.access_password:
        return
    if not credentials or credentials.credentials not in _auth_tokens:
        raise HTTPException(status_code=401, detail="未认证，请先输入访问密码")


class AuthRequest(BaseModel):
    password: str


# --- 模型 ---

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    user_id: str = ""


class DeleteRequest(BaseModel):
    user_id: str = ""


# --- 路由 ---

@app.get("/")
async def root():
    return FileResponse(str(static_dir / "index.html"))


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}


@app.post("/api/auth")
async def auth(req: AuthRequest):
    if not settings.access_password:
        return {"token": "", "need_auth": False}
    if _hash_password(req.password) == _hash_password(settings.access_password):
        token = _generate_token()
        _auth_tokens.add(token)
        return {"token": token, "need_auth": True}
    raise HTTPException(status_code=401, detail="密码错误")


@app.post("/api/chat")
async def chat(req: ChatRequest, _=Depends(_require_auth)):
    user_id = req.user_id or "default"
    history = store.get_history(req.session_id, user_id)

    if not history:
        title = req.message[:20].replace("\n", " ")
        store.create_session(req.session_id, user_id, title)

    context_msgs, _ = build_context(req.session_id, user_id, store, history)
    result = run_agent(req.message, context=context_msgs)

    store.add_message(req.session_id, user_id, "user", req.message)
    store.add_message(req.session_id, user_id, "assistant", result["answer"],
                      json.dumps(result.get("sources", []), ensure_ascii=False))

    return {
        "reply": result["answer"],
        "sources": result["sources"],
        "session_id": req.session_id,
    }


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest, _=Depends(_require_auth)):
    """SSE 流式对话端点：实时播报步骤进度"""
    user_id = req.user_id or "default"
    history = store.get_history(req.session_id, user_id)

    if not history:
        title = req.message[:20].replace("\n", " ")
        store.create_session(req.session_id, user_id, title)

    context_msgs, _ = build_context(req.session_id, user_id, store, history)

    store.add_message(req.session_id, user_id, "user", req.message)

    async def event_stream():
        full_answer = ""
        full_sources = []

        async for node_name, data in run_agent_stream(req.message, context=context_msgs):
            if node_name == "__done__":
                full_answer = data["answer"]
                full_sources = data["sources"]
                yield f"event: answer\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            elif node_name == "__init__":
                yield f"event: init\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            else:
                yield f"event: step\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

        store.add_message(req.session_id, user_id, "assistant", full_answer,
                          json.dumps(full_sources, ensure_ascii=False))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/sessions")
async def list_sessions(user_id: str = "", _=Depends(_require_auth)):
    uid = user_id or "default"
    sessions = store.list_sessions(uid)
    return {"sessions": sessions}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str, user_id: str = "", _=Depends(_require_auth)):
    uid = user_id or "default"
    session = store.get_session(session_id, uid)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    messages = store.get_history(session_id, uid)
    return {"session": session, "messages": messages}


class RenameRequest(BaseModel):
    title: str

@app.put("/api/sessions/{session_id}")
async def rename_session(session_id: str, req: RenameRequest, user_id: str = "", _=Depends(_require_auth)):
    uid = user_id or "default"
    store.update_title(session_id, uid, req.title)
    return {"status": "ok", "title": req.title}

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str, user_id: str = "", _=Depends(_require_auth)):
    uid = user_id or "default"
    store.delete_session(session_id, uid)
    return {"status": "ok"}


# --- 知识库 ---

@app.post("/api/knowledge/upload")
async def upload_knowledge(file: UploadFile = File(...)):
    safe_name = Path(file.filename).name
    if safe_name != file.filename or ".." in file.filename:
        raise HTTPException(status_code=400, detail="非法文件名")
    ext = Path(safe_name).suffix.lower()
    if ext not in (".md", ".txt", ".pdf", ".markdown"):
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")

    os.makedirs("./data/docs", exist_ok=True)
    file_path = Path("./data/docs") / safe_name
    content = await file.read()
    file_path.write_bytes(content)
    chunks = index_document(str(file_path))
    return {"status": "ok", "chunks": chunks, "filename": safe_name}


@app.post("/api/knowledge/crawl")
async def trigger_crawl():
    new_docs = fetch_feeds()
    return {"status": "ok", "new_docs": new_docs}


@app.get("/api/knowledge/stats")
async def knowledge_stats():
    try:
        col = get_or_create_collection()
        count = col.count()
        all_data = col.get()
        sources = set()
        if all_data.get("metadatas"):
            for meta in all_data["metadatas"]:
                sources.add(meta.get("source", "unknown"))
        doc_count = len(sources)
    except Exception:
        count = 0
        doc_count = 0
    return {"doc_count": doc_count, "chunk_count": count}


@app.post("/feishu/callback")
async def feishu_callback(request: Request):
    body = await request.body()
    result = handle_event(body, dict(request.headers))
    return JSONResponse(content=result)
