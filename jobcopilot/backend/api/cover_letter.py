"""
求职信生成 API（含历史记录）
"""

from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agent.core import generate_cover_letter_direct
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
from database import get_db, CoverLetterHistory

router = APIRouter(prefix="/api/cover-letter", tags=["求职信"])


class CoverLetterRequest(BaseModel):
    jd_text: str
    resume_text: str
    candidate_name: str = "求职者"
    style: str = Field(default="formal", description="风格: formal/casual/tech")
    recipient: str = Field(default="招聘负责人", description="收信人称谓")
    user_id: Optional[str] = None
    company_name: Optional[str] = None
    position_title: Optional[str] = None


class CoverLetterHistoryItem(BaseModel):
    id: int
    candidate_name: Optional[str]
    recipient: Optional[str]
    style: Optional[str]
    company_name: Optional[str]
    position_title: Optional[str]
    content: str
    created_at: str

    class Config:
        from_attributes = True


@router.post("/generate")
async def generate_cover_letter(request: CoverLetterRequest, db: Session = Depends(get_db)):
    """生成个性化求职信（自动保存到历史）"""
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

    # 保存到历史记录
    record = CoverLetterHistory(
        user_id=request.user_id or "anonymous",
        candidate_name=request.candidate_name,
        recipient=request.recipient,
        style=request.style,
        company_name=request.company_name,
        position_title=request.position_title,
        jd_text=request.jd_text,
        resume_text=request.resume_text,
        content=result.get("result", ""),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        **result,
        "id": record.id,
        "saved_at": record.created_at.isoformat() if record.created_at else None,
    }


@router.get("/history", response_model=List[CoverLetterHistoryItem])
def list_history(
    user_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """获取求职信历史记录（按 user_id 过滤）"""
    q = db.query(CoverLetterHistory)
    if user_id:
        q = q.filter(CoverLetterHistory.user_id == user_id)
    records = q.order_by(CoverLetterHistory.created_at.desc()).limit(limit).all()
    return records


@router.get("/history/{history_id}")
def get_history(history_id: int, db: Session = Depends(get_db)):
    """获取单条求职信历史"""
    r = db.query(CoverLetterHistory).filter(CoverLetterHistory.id == history_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    return {
        "id": r.id,
        "candidate_name": r.candidate_name,
        "recipient": r.recipient,
        "style": r.style,
        "company_name": r.company_name,
        "position_title": r.position_title,
        "content": r.content,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@router.delete("/history/{history_id}")
def delete_history(history_id: int, db: Session = Depends(get_db)):
    """删除求职信历史"""
    r = db.query(CoverLetterHistory).filter(CoverLetterHistory.id == history_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    db.delete(r)
    db.commit()
    return {"message": "已删除"}

