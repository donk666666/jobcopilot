"""
JobCopilot FastAPI 入口文件
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import CORS_ORIGINS
from database import init_db
from api import jd, resume, cover_letter, tracker

# 创建FastAPI应用
app = FastAPI(
    title="JobCopilot - AI求职助手",
    description="基于LangChain Agent + RAG + Prompt工程的智能求职助手API",
    version="1.0.0",
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(jd.router)
app.include_router(resume.router)
app.include_router(cover_letter.router)
app.include_router(tracker.router)


@app.on_event("startup")
async def startup():
    """应用启动时初始化数据库"""
    init_db()
    # 确保data目录存在
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/chroma_db", exist_ok=True)


@app.get("/")
async def root():
    return {
        "name": "JobCopilot",
        "version": "1.0.0",
        "description": "AI求职助手API",
        "docs": "/docs",
    }


@app.get("/api/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok", "service": "JobCopilot"}


# ---- Agent 全流程执行 ----

from pydantic import BaseModel
from agent.core import JobCopilotAgent
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


class AgentRunRequest(BaseModel):
    question: str


@app.post("/api/agent/run")
async def run_agent(request: AgentRunRequest):
    """
    ReAct Agent 全流程执行
    可以处理多步骤任务，如：
    - "分析这个JD并帮我优化简历"
    - "为这个职位生成一封求职信"
    """
    agent = JobCopilotAgent(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        model=DEEPSEEK_MODEL,
        verbose=False,
    )
    result = await agent.run(request.question)
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
