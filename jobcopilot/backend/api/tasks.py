"""
异步任务查询 API
"""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/task", tags=["任务查询"])


@router.get("/{task_id}")
def get_task_status(task_id: str):
    """查询 Celery 异步任务状态"""
    try:
        from celery.result import AsyncResult
        from tasks import app
    except ImportError:
        raise HTTPException(status_code=503, detail="异步任务服务未启动")

    result = AsyncResult(task_id, app=app)

    response = {
        "task_id": task_id,
        "status": result.state,
    }

    if result.state == "PENDING":
        response["progress"] = 0
    elif result.state == "STARTED" or result.state == "PROGRESS":
        info = result.info or {}
        response["progress"] = info.get("progress", 10)
        response["step"] = info.get("step", "")
    elif result.state == "SUCCESS":
        response["progress"] = 100
        response["result"] = result.result
    elif result.state == "FAILURE":
        response["progress"] = 0
        response["error"] = str(result.info)

    return response
