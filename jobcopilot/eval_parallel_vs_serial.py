"""
并行 vs 串行 多 Agent 分析性能对比

验证 multi_agent.py 中 asyncio.gather 并发 vs 顺序串行执行 4 个维度 Agent 的耗时差异。

用法：python eval_parallel_vs_serial.py
"""

import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

os.environ.setdefault("DEEPSEEK_API_KEY", "sk-PuqBL3Tq8jGAlgyf7npHqRgI8RokD4uDzExyZ6VWSNVIXN3x")
os.environ.setdefault("DEEPSEEK_BASE_URL", "https://cloud.hongqiye.com/v1")
os.environ.setdefault("DEEPSEEK_MODEL", "glm-5.2")

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from prompts.parallel_agents import AGENT_PROMPTS

JD_TEXT = "【岗位】Python 后端开发工程师\n【要求】3年以上Python开发经验，熟悉FastAPI/Django，掌握MySQL/Redis，有Docker部署经验。本科以上学历。"
RESUME_TEXT = (
    "教育背景：华南理工大学 大数据管理与应用 本科 2023-2027\n"
    "技能：Python、FastAPI、MySQL、Linux、Docker\n"
    "项目经历：\n"
    "1. 智能文档问答助手 — 基于LangGraph+ChromaDB构建RAG问答系统，FastAPI后端，已部署至腾讯云\n"
    "2. JobCopilot — 基于LangChain ReAct + LangGraph Supervisor 的多Agent求职平台，Vue3+FastAPI全栈"
)


def _make_prompt(dim_key: str, sys_prompt: str) -> list:
    user_prompt = f"""## 职位描述（JD）
{JD_TEXT}

## 求职者简历
{RESUME_TEXT}

请根据你的分析维度，对以上简历与JD进行评估，严格按JSON格式输出结果。"""
    return [SystemMessage(content=sys_prompt), HumanMessage(content=user_prompt)]


async def _run_one(dim_key: str, sys_prompt: str) -> None:
    """跑单个维度的 LLM 分析"""
    llm = ChatOpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url=os.environ["DEEPSEEK_BASE_URL"],
        model=os.environ["DEEPSEEK_MODEL"],
        temperature=0.3,
    )
    await asyncio.wait_for(llm.ainvoke(_make_prompt(dim_key, sys_prompt)), timeout=60)


async def run_parallel() -> float:
    """并行：asyncio.gather 同时跑 4 个维度"""
    t0 = time.time()
    tasks = [_run_one(d, sp) for d, sp in AGENT_PROMPTS.items()]
    await asyncio.gather(*tasks)
    return time.time() - t0


async def run_serial() -> float:
    """串行：逐个顺序跑 4 个维度"""
    t0 = time.time()
    for d, sp in AGENT_PROMPTS.items():
        await _run_one(d, sp)
    return time.time() - t0


async def main():
    dims = len(AGENT_PROMPTS)
    print("=" * 60)
    print(f"并行 vs 串行 性能对比 | {dims} 个维度 Agent | 模型: {os.environ['DEEPSEEK_MODEL']}")
    print("=" * 60)
    print(f"分析维度: {', '.join(AGENT_PROMPTS.keys())}")
    print()

    # 跑三轮取平均，减少波动
    print("预热一轮...")
    t = await run_parallel()
    print(f"  预热(并行)耗时: {t:.1f}s")

    parallel_times, serial_times = [], []
    for i in range(3):
        tp = await run_parallel()
        ts = await run_serial()
        parallel_times.append(tp)
        serial_times.append(ts)
        print(f"第{i+1}轮: 并行={tp:.1f}s | 串行={ts:.1f}s | 提速={ts/tp:.2f}x")

    avg_p = sum(parallel_times) / len(parallel_times)
    avg_s = sum(serial_times) / len(serial_times)
    speedup = avg_s / avg_p if avg_p > 0 else 0

    # 理论最大提速 = 维度数（理想情况下并行时间 = 串行/维度数）
    ideal = dims

    print()
    print("─" * 60)
    print(f"  平均并行耗时: {avg_p:.1f}s")
    print(f"  平均串行耗时: {avg_s:.1f}s")
    print(f"  实际提速: {speedup:.2f}x")
    print(f"  理论最大提速: {ideal}x（理想并行，不考虑IO开销）")
    print(f"  并行效率: {speedup/ideal:.0%}（实际提速/理论最大）")
    print("─" * 60)

    return {
        "dims": dims,
        "avg_parallel_s": round(avg_p, 1),
        "avg_serial_s": round(avg_s, 1),
        "speedup_x": round(speedup, 2),
        "parallel_efficiency": round(speedup / ideal, 2),
    }


if __name__ == "__main__":
    result = asyncio.run(main())
    print()
    print("对比结果:", json.dumps(result, ensure_ascii=False))
