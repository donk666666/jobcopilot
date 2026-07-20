"""
简历优化 API
"""

import json
import re
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agent.core import match_resume_direct, tailor_resume_direct
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from rag.vector_store import get_vector_store
from database import get_db, ResumeOptimization, Resume
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from prompts.resume_tailor import RESUME_MATCH_SYSTEM, RESUME_MATCH_USER_TEMPLATE, RESUME_TAILOR_SYSTEM, RESUME_TAILOR_USER_TEMPLATE

router = APIRouter(prefix="/api/resume", tags=["简历优化"])


class ResumeMatchRequest(BaseModel):
    resume_text: str
    jd_analysis: str
    jd_analysis_id: int = None


class ResumeTailorRequest(BaseModel):
    resume_text: str
    jd_analysis: str
    match_result: str
    opt_id: int = None
    show_annotations: bool = True


@router.post("/match")
async def match_resume(request: ResumeMatchRequest, db: Session = Depends(get_db)):
    """评估简历与职位的匹配度，结果自动入库"""
    if not request.resume_text.strip():
        raise HTTPException(status_code=400, detail="简历文本不能为空")

    result = await match_resume_direct(
        jd_analysis=request.jd_analysis,
        resume_text=request.resume_text,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    if result.get("success") and result.get("result"):
        parsed = result["result"]
        record = ResumeOptimization(
            jd_analysis_id=request.jd_analysis_id,
            resume_text=request.resume_text,
            jd_analysis_json=request.jd_analysis,
            match_score=parsed.get("match_score"),
            match_detail=json.dumps(parsed, ensure_ascii=False),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return {"result": parsed, "success": True, "opt_id": record.id}

    return result


@router.post("/tailor")
async def tailor_resume(request: ResumeTailorRequest, db: Session = Depends(get_db)):
    """根据JD定向优化简历，结果自动入库"""
    if not request.resume_text.strip():
        raise HTTPException(status_code=400, detail="简历文本不能为空")

    # 使用自定义模板以支持注释开关
    annotations_on = request.show_annotations

    tailor_system = RESUME_TAILOR_SYSTEM
    if not annotations_on:
        tailor_system = RESUME_TAILOR_SYSTEM.replace(
            "并在每处修改之后用【改动说明：xxx】标注", "。不要添加任何改动说明或注释"
        )

    llm = ChatOpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        model=DEEPSEEK_MODEL,
        temperature=0.6,
    )

    messages = [
        SystemMessage(content=tailor_system),
        HumanMessage(content=RESUME_TAILOR_USER_TEMPLATE.format(
            jd_analysis=request.jd_analysis,
            match_result=request.match_result,
            resume_text=request.resume_text
        ))
    ]

    response = await llm.ainvoke(messages)

    # 存入库
    if request.opt_id:
        record = db.query(ResumeOptimization).filter(ResumeOptimization.id == request.opt_id).first()
        if record:
            record.tailored_resume = response.content
            record.annotations_enabled = 1 if annotations_on else 0
            db.commit()
            return {"result": response.content, "success": True, "opt_id": record.id}

    # 无 opt_id，新建
    record = ResumeOptimization(
        jd_analysis_json=request.jd_analysis,
        resume_text=request.resume_text,
        tailored_resume=response.content,
        annotations_enabled=1 if annotations_on else 0,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"result": response.content, "success": True, "opt_id": record.id}


@router.get("/history")
def list_optimizations(db: Session = Depends(get_db)):
    """获取简历优化历史"""
    records = db.query(ResumeOptimization).order_by(ResumeOptimization.updated_at.desc()).limit(20).all()
    return [
        {
            "id": r.id,
            "jd_analysis_id": r.jd_analysis_id,
            "match_score": r.match_score,
            "match_detail": json.loads(r.match_detail) if r.match_detail else None,
            "tailored_resume": r.tailored_resume,
            "annotations_enabled": bool(r.annotations_enabled),
            "resume_preview": r.resume_text[:80] + ("..." if len(r.resume_text) > 80 else ""),
            "created_at": r.created_at.isoformat() if r.created_at else "",
            "updated_at": r.updated_at.isoformat() if r.updated_at else "",
        }
        for r in records
    ]


@router.get("/history/{opt_id}")
def get_optimization(opt_id: int, db: Session = Depends(get_db)):
    """获取单条优化记录"""
    r = db.query(ResumeOptimization).filter(ResumeOptimization.id == opt_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {
        "id": r.id,
        "jd_analysis_id": r.jd_analysis_id,
        "resume_text": r.resume_text,
        "jd_analysis_json": r.jd_analysis_json,
        "match_score": r.match_score,
        "match_detail": json.loads(r.match_detail) if r.match_detail else None,
        "tailored_resume": r.tailored_resume,
        "annotations_enabled": bool(r.annotations_enabled),
        "created_at": r.created_at.isoformat() if r.created_at else "",
    }


@router.delete("/history/{opt_id}")
def delete_optimization(opt_id: int, db: Session = Depends(get_db)):
    """删除一条优化记录"""
    r = db.query(ResumeOptimization).filter(ResumeOptimization.id == opt_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(r)
    db.commit()
    return {"message": "已删除"}


class ResumeSaveRequest(BaseModel):
    resume_text: str
    name: str = "默认简历"


@router.get("/active")
def get_active_resume(db: Session = Depends(get_db)):
    """获取当前激活的简历"""
    r = db.query(Resume).filter(Resume.is_active == 1).order_by(Resume.updated_at.desc()).first()
    if not r:
        return {"content": "", "name": ""}
    return {"id": r.id, "content": r.content, "name": r.name}


@router.post("/active")
def save_active_resume(request: ResumeSaveRequest, db: Session = Depends(get_db)):
    """保存简历（设为激活，其他取消激活）"""
    # 取消所有激活
    db.query(Resume).filter(Resume.is_active == 1).update({Resume.is_active: 0})
    # 新建一条激活记录
    record = Resume(name=request.name, content=request.resume_text, is_active=1)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "message": "已保存"}


@router.get("/rag-stats")
async def get_rag_stats():
    """获取RAG向量库状态"""
    store = get_vector_store()
    return store.get_store_stats()
