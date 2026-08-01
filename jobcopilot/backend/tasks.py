"""
Celery 异步任务 — 全流程流水线
"""

from celery import Celery
from config import REDIS_URL

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


@app.task(bind=True, name="run_full_pipeline")
def run_full_pipeline(
    self,
    resume_text: str,
    jd_text: str,
    jd_analysis_id: int = None,
    style: str = "professional",
    candidate_name: str = "",
):
    """异步全流程：JD分析 → 简历匹配 → 简历定制 → 求职信"""
    import asyncio

    async def _run():
        from agent.multi_agent import run_multi_agent

        self.update_state(state="ANALYZING_JD", meta={"progress": 10, "step": "正在分析JD..."})

        result = await run_multi_agent(
            question="请帮我完整分析这个职位，匹配简历，定制优化简历，并生成求职信",
            jd_text=jd_text,
            resume_text=resume_text,
            candidate_name=candidate_name or "求职者",
            style=style,
        )

        self.update_state(state="MATCHING", meta={"progress": 40, "step": "正在匹配简历..."})
        self.update_state(state="TAILORING", meta={"progress": 60, "step": "正在定制简历..."})
        self.update_state(state="WRITING_LETTER", meta={"progress": 80, "step": "正在生成求职信..."})

        return {
            "success": result.get("success", False),
            "intent": result.get("intent", ""),
            "output": result.get("output", ""),
            "dimension_scores": result.get("dimension_scores"),
            "contradictions": result.get("contradictions"),
            "stage_timings": result.get("stage_timings", {}),
            "total_time_s": result.get("total_time_s", 0),
            "errors": result.get("errors", []),
            "jd_analysis_id": jd_analysis_id,
        }

    return asyncio.run(_run())
