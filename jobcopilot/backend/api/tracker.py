"""
投递进度管理 API
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from database import get_db, Application

router = APIRouter(prefix="/api/tracker", tags=["投递管理"])


# ---- Pydantic Models ----

class ApplicationCreate(BaseModel):
    company_name: str
    position_title: str
    jd_text: Optional[str] = None
    jd_analysis: Optional[str] = None
    match_score: Optional[float] = None
    match_detail: Optional[str] = None
    tailored_resume: Optional[str] = None
    cover_letter: Optional[str] = None
    status: str = "待投递"
    notes: Optional[str] = None


class ApplicationUpdate(BaseModel):
    company_name: Optional[str] = None
    position_title: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    match_score: Optional[float] = None
    tailored_resume: Optional[str] = None
    cover_letter: Optional[str] = None


class ApplicationResponse(BaseModel):
    id: int
    company_name: str
    position_title: str
    status: str
    match_score: Optional[float]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# ---- Endpoints ----

@router.get("/", response_model=list[ApplicationResponse])
def list_applications(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取所有投递记录，可按状态筛选"""
    query = db.query(Application)
    if status:
        query = query.filter(Application.status == status)
    records = query.order_by(Application.updated_at.desc()).all()

    return [
        ApplicationResponse(
            id=r.id,
            company_name=r.company_name,
            position_title=r.position_title,
            status=r.status,
            match_score=r.match_score,
            created_at=r.created_at.isoformat() if r.created_at else "",
            updated_at=r.updated_at.isoformat() if r.updated_at else "",
        )
        for r in records
    ]


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """获取投递统计"""
    total = db.query(Application).count()
    statuses = [
        "待投递", "已投递", "初筛中", "面试中", "已发Offer", "已拒绝"
    ]
    breakdown = {}
    for s in statuses:
        breakdown[s] = db.query(Application).filter(Application.status == s).count()

    avg_score = db.query(Application).filter(
        Application.match_score.isnot(None)
    ).all()
    avg = sum(a.match_score for a in avg_score) / len(avg_score) if avg_score else 0

    return {
        "total": total,
        "by_status": breakdown,
        "avg_match_score": round(avg, 1)
    }


@router.get("/{application_id}")
def get_application(application_id: int, db: Session = Depends(get_db)):
    """获取单条投递记录详情"""
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {
        "id": app.id,
        "company_name": app.company_name,
        "position_title": app.position_title,
        "jd_text": app.jd_text,
        "jd_analysis": app.jd_analysis,
        "match_score": app.match_score,
        "match_detail": app.match_detail,
        "tailored_resume": app.tailored_resume,
        "cover_letter": app.cover_letter,
        "status": app.status,
        "notes": app.notes,
        "created_at": app.created_at.isoformat() if app.created_at else "",
        "updated_at": app.updated_at.isoformat() if app.updated_at else "",
    }


@router.post("/")
def create_application(data: ApplicationCreate, db: Session = Depends(get_db)):
    """创建投递记录"""
    app = Application(
        company_name=data.company_name,
        position_title=data.position_title,
        jd_text=data.jd_text,
        jd_analysis=data.jd_analysis,
        match_score=data.match_score,
        match_detail=data.match_detail,
        tailored_resume=data.tailored_resume,
        cover_letter=data.cover_letter,
        status=data.status,
        notes=data.notes,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return {"id": app.id, "message": "创建成功"}


@router.put("/{application_id}")
def update_application(
    application_id: int,
    data: ApplicationUpdate,
    db: Session = Depends(get_db)
):
    """更新投递记录"""
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="记录不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(app, key, value)

    app.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": application_id, "message": "更新成功"}


@router.delete("/{application_id}")
def delete_application(application_id: int, db: Session = Depends(get_db)):
    """删除投递记录"""
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(app)
    db.commit()
    return {"id": application_id, "message": "已删除"}
