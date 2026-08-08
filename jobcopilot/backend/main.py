"""
JobCopilot FastAPI 入口文件
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import CORS_ORIGINS
from database import init_db
from api import jd, resume, cover_letter, tracker, upload, tasks as task_api, greet

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
app.include_router(upload.router)
app.include_router(task_api.router)
app.include_router(greet.router)


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
    from cache import get_redis_status
    redis_info = get_redis_status()
    return {
        "status": "ok",
        "service": "JobCopilot",
        "redis": redis_info,
    }


# ---- Agent 全流程执行 ----

from pydantic import BaseModel
from agent.core import JobCopilotAgent
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


class AgentRunRequest(BaseModel):
    question: str


@app.post("/api/agent/run")
async def run_agent(request: AgentRunRequest):
    """ReAct Agent 全流程执行"""
    agent = JobCopilotAgent(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        model=DEEPSEEK_MODEL,
        verbose=False,
    )
    result = await agent.run(request.question)
    return result


# ---- 多智能体端点 ----

class MultiAgentRequest(BaseModel):
    question: str
    jd_text: str = ""
    resume_text: str = ""
    candidate_name: str = "求职者"
    style: str = "formal"
    recipient: str = "招聘负责人"


@app.post("/api/agent/multi-run")
async def run_multi_agent(request: MultiAgentRequest):
    """
    多智能体协作流水线端点

    根据用户意图自动路由：
    - jd_analysis: 仅 JD 分析
    - full_pipeline: JD分析 → 简历匹配 → 简历改写 → 求职信
    - cover_letter: 仅生成求职信

    示例请求：
    {
        "question": "帮我分析这个JD，并生成求职信",
        "jd_text": "...",
        "resume_text": "...",
        "candidate_name": "张三",
        "style": "formal"
    }
    """
    from agent.multi_agent import run_multi_agent

    if not request.question.strip():
        return {"success": False, "error": "问题不能为空"}

    result = await run_multi_agent(
        question=request.question,
        jd_text=request.jd_text,
        resume_text=request.resume_text,
        candidate_name=request.candidate_name,
        style=request.style,
        recipient=request.recipient,
    )
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
