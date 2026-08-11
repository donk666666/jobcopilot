"""
个性化打招呼 API — 生成求职私信打招呼文案
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent.core import generate_greeting_direct
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

router = APIRouter(prefix="/api/greet", tags=["个性化打招呼"])


class GreetingRequest(BaseModel):
    resume_text: str
    jd_text: str = ""
    company_name: str = ""
    position_title: str = ""
    candidate_name: str = "求职者"
    style: str = Field(default="casual", description="风格: casual/professional/tech")
    variant_count: int = Field(default=3, ge=1, le=5, description="生成几个变体")


@router.post("/generate")
async def generate_greeting(request: GreetingRequest):
    """根据JD和简历生成个性化打招呼文案（多变体）"""
    if request.style not in ("casual", "professional", "tech"):
        raise HTTPException(status_code=400, detail="风格必须是 casual/professional/tech 之一")

    result = await generate_greeting_direct(
        resume_text=request.resume_text,
        jd_text=request.jd_text,
        company_name=request.company_name,
        position_title=request.position_title,
        candidate_name=request.candidate_name,
        style=request.style,
        variant_count=request.variant_count,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )
    return result
