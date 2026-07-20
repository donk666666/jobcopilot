import logging
import os
import secrets
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import settings
from app.agent.graph import run_agent
from app.rag.loader import index_document, index_directory
from app.rag.vectorstore import get_or_create_collection
from app.crawler.feed import fetch_feeds, start_scheduler
from app.feishu.bot import handle_event
from app.session_store import SessionStore
from app.memory import build_context

# 日志配置
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

# 静态文件
static_dir = Path(__file__).parent / "web" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 会话持久化存储
store = SessionStore()


# --- 模型 ---
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


# --- 路由 ---
@app.get("/")
async def root():
    return FileResponse(str(static_dir / "index.html"))


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    # 读取完整历史
    history = store.get_history(req.session_id)

    # 第一条消息自动设为会话标题
    if not history:
        title = req.message[:20].replace("\n", " ")
        store.create_session(req.session_id, title)

    # 构建上下文（滑动窗口 + 摘要）
    context_msgs, summary = build_context(req.session_id, store, history)

    # 跑 Agent
    result = run_agent(req.message, context=context_msgs)

    # 持久化当前轮消息
    store.add_message(req.session_id, "user", req.message)
    store.add_message(req.session_id, "assistant", result["answer"])

    return {
        "reply": result["answer"],
        "sources": result["sources"],
        "session_id": req.session_id,
    }


# --- 会话管理 API ---

@app.get("/api/sessions")
async def list_sessions():
    sessions = store.list_sessions()
    return {"sessions": sessions}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    messages = store.get_history(session_id)
    return {"session": session, "messages": messages}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    store.delete_session(session_id)
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
