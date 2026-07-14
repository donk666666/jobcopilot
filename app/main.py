import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import settings
from app.agent.graph import run_agent
from app.rag.loader import index_document, index_directory
from app.rag.vectorstore import get_or_create_collection
from app.crawler.feed import fetch_feeds, start_scheduler
from app.feishu.bot import handle_event

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
    start_scheduler()
    logger.info(f"爬虫定时器已启动，间隔 {settings.crawl_schedule_hours} 小时")
    yield
    logger.info("应用关闭")


app = FastAPI(title="智能文档问答助手", version="1.0.0", lifespan=lifespan)

# 静态文件
static_dir = Path(__file__).parent / "web" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# --- 模型 ---
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


__session_store: dict[str, list[dict]] = {}


# --- 路由 ---
@app.get("/")
async def root():
    return FileResponse(str(static_dir / "index.html"))


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    history = __session_store.get(req.session_id, [])
    result = run_agent(req.message, history=history)
    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": result["answer"]})
    __session_store[req.session_id] = history[-20:]
    return {"reply": result["answer"], "sources": result["sources"], "session_id": req.session_id}


@app.post("/api/knowledge/upload")
async def upload_knowledge(file: UploadFile = File(...)):
    os.makedirs("./data/docs", exist_ok=True)
    file_path = Path("./data/docs") / file.filename
    content = await file.read()
    file_path.write_bytes(content)
    chunks = index_document(str(file_path))
    return {"status": "ok", "chunks": chunks, "filename": file.filename}


@app.post("/api/knowledge/crawl")
async def trigger_crawl():
    new_docs = fetch_feeds()
    return {"status": "ok", "new_docs": new_docs}


@app.get("/api/knowledge/stats")
async def knowledge_stats():
    try:
        col = get_or_create_collection()
        count = col.count()
    except Exception:
        count = 0
    return {"doc_count": "未知", "chunk_count": count}


@app.post("/feishu/callback")
async def feishu_callback(request: Request):
    body = await request.body()
    result = handle_event(body, dict(request.headers))
    return JSONResponse(content=result)
