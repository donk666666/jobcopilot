"""
JD分析 API
"""

import json
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from prompts.jd_analyzer import JD_ANALYZER_SYSTEM, JD_ANALYZER_USER_TEMPLATE
from database import get_db, JDAnalysis

router = APIRouter(prefix="/api/jd", tags=["JD分析"])


class JDAnalyzeRequest(BaseModel):
    jd_text: str
    save: bool = True


def _extract_json(text: str):
    """用多种策略尝试从模型输出中提取JSON"""
    if not text or not text.strip():
        raise ValueError("模型返回空内容")

    cleaned = text.strip()
    for prefix in ["好的", "以下是", "这是", "为您", "根据", "分析结果", "结果"]:
        idx = cleaned.find(prefix)
        if idx != -1 and idx < 10:
            cleaned = cleaned[idx + len(prefix):].strip()
            if cleaned.startswith(("：", ":", "，")):
                cleaned = cleaned[1:].strip()

    for marker in ["```json", "```"]:
        m = re.search(rf'{re.escape(marker)}\s*(.*?)\s*```', cleaned, re.DOTALL)
        if m:
            cleaned = m.group(1).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]

    # 尝试直接解析
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 解析失败：尝试补全截断的 JSON（补充缺失的引号、括号、方括号）
    # 统计未闭合的符号
    stack = []
    in_string = False
    escape = False
    for ch in cleaned:
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in '{[':
            stack.append(ch)
        elif ch == '}':
            if stack and stack[-1] == '{':
                stack.pop()
        elif ch == ']':
            if stack and stack[-1] == '[':
                stack.pop()

    # 如果在字符串中，关闭字符串
    if in_string:
        cleaned = cleaned + '"'

    # 补全未闭合的括号
    closers = []
    for s in reversed(stack):
        if s == '{':
            closers.append('}')
        elif s == '[':
            closers.append(']')
    cleaned = cleaned + ''.join(closers)

    return json.loads(cleaned)


@router.post("/analyze")
async def analyze_jd(request: JDAnalyzeRequest, db: Session = Depends(get_db)):
    """分析职位描述JD，返回结构化信息，并存入历史记录"""
    if not request.jd_text.strip():
        raise HTTPException(status_code=400, detail="JD文本不能为空")

    llm = ChatOpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        model=DEEPSEEK_MODEL,
        temperature=0.1,
        max_tokens=2000,
    )

    nonce = uuid.uuid4().hex[:8]
    user_prompt = JD_ANALYZER_USER_TEMPLATE.format(jd_text=request.jd_text) + f"\n[req:{nonce}]"

    messages = [
        SystemMessage(content=JD_ANALYZER_SYSTEM),
        HumanMessage(content=user_prompt)
    ]

    for attempt in range(2):
        response = await llm.ainvoke(messages)
        content = response.content
        if content and content.strip():
            break
    else:
        return {
            "result": None,
            "raw": "",
            "success": False,
            "error": "API两次均返回空内容，请重试"
        }

    try:
        parsed = _extract_json(content)
        if isinstance(parsed.get("experience_years"), dict):
            exp = parsed["experience_years"]
            parsed["experience_years"] = round((exp.get("min", 0) + exp.get("max", 0)) / 2, 1)

        # 存入历史
        if request.save:
            record = JDAnalysis(
                position_title=parsed.get("position_title", "未知职位"),
                company_name=parsed.get("company_name") or "",
                jd_raw=request.jd_text,
                analysis_json=json.dumps(parsed, ensure_ascii=False),
                match_weight=json.dumps(parsed.get("match_weight"), ensure_ascii=False) if parsed.get("match_weight") else None,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return {"result": parsed, "raw": response.content, "success": True, "id": record.id}

        return {"result": parsed, "raw": response.content, "success": True}
    except (json.JSONDecodeError, ValueError) as e:
        return {
            "result": None,
            "raw": response.content,
            "success": False,
            "error": f"JSON解析失败: {str(e)}"
        }


# ---- 历史记录 ----

@router.get("/history")
def list_analyses(db: Session = Depends(get_db)):
    """获取所有JD分析历史，按时间倒序"""
    records = db.query(JDAnalysis).order_by(JDAnalysis.created_at.desc()).limit(30).all()
    return [
        {
            "id": r.id,
            "position_title": r.position_title,
            "company_name": r.company_name,
            "jd_preview": r.jd_raw[:120] + ("..." if len(r.jd_raw) > 120 else ""),
            "analysis": json.loads(r.analysis_json) if r.analysis_json else None,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in records
    ]


@router.delete("/history/{analysis_id}")
def delete_analysis(analysis_id: int, db: Session = Depends(get_db)):
    """删除一条JD分析记录"""
    record = db.query(JDAnalysis).filter(JDAnalysis.id == analysis_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(record)
    db.commit()
    return {"message": "已删除"}
