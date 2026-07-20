"""
求职信生成 API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent.core import generate_cover_letter_direct
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

router = APIRouter(prefix="/api/cover-letter", tags=["求职信"])


class CoverLetterRequest(BaseModel):
    jd_text: str
    resume_text: str
    candidate_name: str = "求职者"
    style: str = Field(default="formal", description="风格: formal/casual/tech")
    recipient: str = Field(default="招聘负责人", description="收信人称谓")


@router.post("/generate")
async def generate_cover_letter(request: CoverLetterRequest):
    """生成个性化求职信"""
    if request.style not in ("formal", "casual", "tech"):
        raise HTTPException(status_code=400, detail="风格必须是 formal/casual/tech 之一")

    result = await generate_cover_letter_direct(
        jd_text=request.jd_text,
        resume_text=request.resume_text,
        candidate_name=request.candidate_name,
        style=request.style,
        recipient=request.recipient,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )
    return result
