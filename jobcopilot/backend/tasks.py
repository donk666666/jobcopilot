"""
Celery 异步任务 — 全流程流水线 v2.0（走真 ReAct Agent）

Agent 自主决定调用顺序：
- analyze_jd → match_resume → tailor_resume → generate_cover_letter
- 强制至少完成 4 个步骤，最多 12 步
- 每步通过 callback 给 Celery 回报 progress
"""

import asyncio
from celery import Celery
from config import REDIS_URL

# 强制 RESP2：Redis 5.x 不支持 HELLO 3 握手
# redis-py 8.x 默认 RESP3，需要 monkey-patch
import redis.client as _rc
_orig_init = _rc.Redis.__init__
def _patched_init(self, *args, **kwargs):
    kwargs["protocol"] = 2
    _orig_init(self, *args, **kwargs)
_rc.Redis.__init__ = _patched_init

app = Celery(
    "jobcopilot",
    broker=f"{REDIS_URL}/1",
    backend=f"{REDIS_URL}/2",
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
)


_STEP_MAP = {
    "analyze_jd": ("ANALYZING_JD", 10, "正在分析 JD..."),
    "match_resume": ("MATCHING", 35, "正在匹配简历..."),
    "tailor_resume": ("TAILORING", 60, "正在改写简历..."),
    "generate_cover_letter": ("WRITING_LETTER", 85, "正在生成求职信..."),
}


class _CeleryReporter:
    """把 Agent 步骤回调映射成 Celery 状态更新"""

    def __init__(self, task):
        self.task = task

    def __call__(self, tool_name: str):
        if tool_name in _STEP_MAP:
            state, progress, step_text = _STEP_MAP[tool_name]
            self.task.update_state(state=state, meta={"progress": progress, "step": step_text})


@app.task(bind=True, name="run_full_pipeline")
def run_full_pipeline(
    self,
    resume_text: str,
    jd_text: str,
    jd_analysis_id: int = None,
    style: str = "professional",
    candidate_name: str = "",
):
    """异步全流程：ReAct Agent 自主编排 JD 分析 → 匹配 → 改写 → 求职信"""
    from agent.react_runner import run_react_full_pipeline

    reporter = _CeleryReporter(self)
    self.update_state(state="PENDING", meta={"progress": 5, "step": "Agent 准备中..."})

    async def _run():
        result = await run_react_full_pipeline(
            jd_text=jd_text,
            resume_text=resume_text,
            candidate_name=candidate_name or "求职者",
            style=style,
            on_step=reporter,
        )
        self.update_state(state="SUCCESS", meta={"progress": 100, "step": "完成"})
        return {
            "success": result.get("success", False),
            "intent": "full_pipeline",
            "jd_analysis": result.get("jd_analysis"),
            "match_result": result.get("match_result"),
            "tailored_resume": result.get("tailored_resume"),
            "cover_letter": result.get("cover_letter"),
            "agent_trace": result.get("agent_trace", []),
            "total_steps": result.get("total_steps", 0),
            "llm_calls": result.get("llm_calls", 0),
            "total_time_s": result.get("total_time_s", 0),
            "errors": result.get("errors", []),
            "jd_analysis_id": jd_analysis_id,
        }

    return asyncio.run(_run())