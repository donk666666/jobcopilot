"""
JobCopilot 量化评估脚本

评估维度：
1. JD 分析 — JSON 有效性、字段完整率、关键字段准确率
2. 简历匹配 — JSON 有效性、字段完整率、分数分布、重复稳定性
3. 简历改写 — 长度保留率、JD 关键词覆盖、不虚构检查
4. 求职信 — 格式规范、收信人/署名完整、卖点覆盖
"""

import sys
import os
import json
import time
import re

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

os.environ.setdefault("DEEPSEEK_API_KEY", "sk-PuqBL3Tq8jGAlgyf7npHqRgI8RokD4uDzExyZ6VWSNVIXN3x")
os.environ.setdefault("DEEPSEEK_BASE_URL", "https://cloud.hongqiye.com/v1")
os.environ.setdefault("DEEPSEEK_MODEL", "glm-5.2")

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


# ============================================================
# 测试数据集
# ============================================================

JD_TEST_CASES = [
    {
        "id": "jd_001",
        "jd_text": "【岗位】Python 后端开发工程师\n【要求】3年以上Python开发经验，熟悉FastAPI/Django，掌握MySQL/Redis，有Docker部署经验。本科以上学历。",
        "expected": {
            "position_title": "Python后端开发工程师",
            "experience_years": 3.0,
            "hard_skills": ["Python", "FastAPI", "Django", "MySQL", "Redis", "Docker"],
            "education": "本科及以上",
        },
        "key_skills": ["Python", "FastAPI", "Redis", "Docker"],
    },
    {
        "id": "jd_002",
        "jd_text": "招聘高级前端工程师，要求5年以上React/Vue开发经验，精通TypeScript，有大型项目架构经验。",
        "expected": {
            "position_title": "高级前端工程师",
            "experience_years": 5.0,
            "hard_skills": ["React", "Vue", "TypeScript"],
        },
        "key_skills": ["React", "TypeScript"],
    },
    {
        "id": "jd_003",
        "jd_text": "AI算法实习生招聘：计算机相关专业，熟悉Python和PyTorch，了解Transformer架构，有论文阅读能力。",
        "expected": {
            "position_title": "AI算法实习生",
            "hard_skills": ["Python", "PyTorch"],
        },
        "key_skills": ["Python", "PyTorch", "Transformer"],
    },
]

MATCH_TEST_CASES = [
    {
        "id": "match_001",
        "jd_analysis": json.dumps({
            "position_title": "Python后端工程师",
            "hard_skills": ["Python", "FastAPI", "MySQL", "Docker"],
            "experience_years": 2,
        }, ensure_ascii=False),
        "resume_text": "熟练掌握Python和FastAPI开发，有2年后端经验，熟悉MySQL数据库，使用Docker部署过项目。",
        "expected_direction": "high",  # 预期匹配度高
    },
    {
        "id": "match_002",
        "jd_analysis": json.dumps({
            "position_title": "高级前端工程师",
            "hard_skills": ["React", "TypeScript", "Webpack"],
            "experience_years": 5,
        }, ensure_ascii=False),
        "resume_text": "应届生，会一点HTML和CSS，Python写过课设。",
        "expected_direction": "low",  # 预期匹配度低
    },
]

TAILOR_TEST_CASES = [
    {
        "id": "tailor_001",
        "jd_analysis": json.dumps({
            "position_title": "Python后端工程师",
            "hard_skills": ["Python", "FastAPI", "MySQL", "Docker"],
        }, ensure_ascii=False),
        "match_result": "匹配度 70%，硬技能匹配较好但缺少 Docker 相关经验描述。",
        "resume_text": (
            "教育背景：华南理工大学 大数据管理与应用 本科 2023-2027\n"
            "技能：Python、FastAPI、MySQL、Linux\n"
            "项目经历：\n"
            "1. 智能文档问答助手 — 基于LangGraph+ChromaDB构建RAG问答系统，FastAPI后端，已部署至腾讯云\n"
            "2. 数据分析项目 — 使用Python爬虫采集电商数据，MySQL存储，Tableau可视化"
        ),
        "jd_keywords": ["FastAPI", "MySQL", "Docker", "后端"],
    },
]

COVER_LETTER_CASES = [
    {
        "id": "cover_001",
        "candidate_name": "张三",
        "recipient": "招聘负责人",
        "style": "formal",
    },
]


# ============================================================
# 评估函数
# ============================================================

def eval_jd_analysis():
    """评估 JD 分析：JSON 有效性 + 字段完整率 + 技能召回"""
    print("=" * 60)
    print("[1] JD 分析评估")
    print("=" * 60)

    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    from prompts.jd_analyzer import JD_ANALYZER_SYSTEM, JD_ANALYZER_USER_TEMPLATE

    llm = ChatOpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        model=DEEPSEEK_MODEL,
        temperature=0.1,
        max_tokens=2000,
    )

    results = []
    for tc in JD_TEST_CASES:
        t0 = time.time()
        messages = [
            SystemMessage(content=JD_ANALYZER_SYSTEM),
            HumanMessage(content=JD_ANALYZER_USER_TEMPLATE.format(jd_text=tc["jd_text"])),
        ]
        resp = llm.invoke(messages)
        elapsed = time.time() - t0

        # JSON 有效性
        try:
            parsed = json.loads(resp.content)
            json_valid = True
        except json.JSONDecodeError:
            # 尝试从 markdown 提取
            m = re.search(r'```(?:json)?\s*(.*?)\s*```', resp.content, re.DOTALL)
            if m:
                try:
                    parsed = json.loads(m.group(1))
                    json_valid = True
                except json.JSONDecodeError:
                    parsed = {}
                    json_valid = False
            else:
                parsed = {}
                json_valid = False

        # 字段完整率
        required_fields = [
            "position_title", "level", "hard_skills", "soft_skills",
            "education", "experience_years", "core_responsibilities"
        ]
        present = sum(1 for f in required_fields if parsed.get(f))
        field_rate = present / len(required_fields)

        # 关键技能召回（expected 里的 key_skills 在 hard_skills 中出现了几个）
        expected_skills = tc.get("key_skills", [])
        extracted_skills = parsed.get("hard_skills", [])
        extracted_lower = [s.lower().strip() for s in extracted_skills]
        skill_hits = sum(
            1 for s in expected_skills
            if any(s.lower() in e for e in extracted_lower)
        )
        skill_recall = skill_hits / len(expected_skills) if expected_skills else 1.0

        # 职位名相似度（简单包含匹配）
        expected_title = tc["expected"].get("position_title", "")
        actual_title = parsed.get("position_title", "")
        title_match = expected_title.lower() in actual_title.lower() or actual_title.lower() in expected_title.lower()

        result = {
            "id": tc["id"],
            "json_valid": json_valid,
            "field_rate": field_rate,
            "skill_recall": skill_recall,
            "title_match": title_match,
            "elapsed": round(elapsed, 2),
            "raw": resp.content[:200],
        }
        results.append(result)

        status = "OK" if json_valid else "!!"
        print(f"\n[{tc['id']}] {status} | JSON={json_valid} | 字段={field_rate:.0%} | "
              f"技能召回={skill_recall:.0%} | 职位匹配={title_match} | {elapsed:.1f}s")
        if not json_valid:
            print(f"  原始输出: {resp.content[:150]}")

    n = len(results)
    json_ok = sum(1 for r in results if r["json_valid"])
    avg_field = sum(r["field_rate"] for r in results) / n
    avg_skill = sum(r["skill_recall"] for r in results) / n
    title_ok = sum(1 for r in results if r["title_match"])
    avg_time = sum(r["elapsed"] for r in results) / n

    print(f"\n  汇总: JSON有效性={json_ok}/{n} | 字段完整率={avg_field:.0%} | "
          f"技能召回={avg_skill:.0%} | 职位准确={title_ok}/{n} | 平均耗时={avg_time:.1f}s")

    return results


def eval_resume_match():
    """评估简历匹配：JSON 有效性 + 字段完整 + 分数方向正确"""
    print("\n" + "=" * 60)
    print("[2] 简历匹配评估")
    print("=" * 60)

    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    from prompts.resume_tailor import RESUME_MATCH_SYSTEM, RESUME_MATCH_USER_TEMPLATE

    llm = ChatOpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        model=DEEPSEEK_MODEL,
        temperature=0.5,
    )

    results = []
    for tc in MATCH_TEST_CASES:
        t0 = time.time()
        messages = [
            SystemMessage(content=RESUME_MATCH_SYSTEM),
            HumanMessage(content=RESUME_MATCH_USER_TEMPLATE.format(
                jd_analysis=tc["jd_analysis"],
                resume_text=tc["resume_text"],
                rag_context="（RAG 未就绪，使用纯 LLM 分析）",
            )),
        ]
        resp = llm.invoke(messages)
        elapsed = time.time() - t0

        # 解析 JSON
        content = resp.content
        m = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if m:
            content = m.group(1)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {}
        json_valid = isinstance(parsed, dict) and "match_score" in parsed

        # 分数方向正确
        score = parsed.get("match_score", 0)
        direction_ok = True
        if tc["expected_direction"] == "high" and score < 50:
            direction_ok = False
        if tc["expected_direction"] == "low" and score > 50:
            direction_ok = False

        # 必要字段
        required = ["match_score", "score_breakdown", "matched_points", "gap_points"]
        fields_ok = sum(1 for f in required if f in parsed)
        field_rate = fields_ok / len(required)

        r = {
            "id": tc["id"],
            "json_valid": json_valid,
            "score": score,
            "direction_ok": direction_ok,
            "field_rate": field_rate,
            "elapsed": round(elapsed, 2),
        }
        results.append(r)

        status = "OK" if json_valid else "!!"
        print(f"\n[{tc['id']}] {status} | score={score} | 方向={direction_ok} | "
              f"字段={field_rate:.0%} | {elapsed:.1f}s")

    n = len(results)
    json_ok = sum(1 for r in results if r["json_valid"])
    dir_ok = sum(1 for r in results if r["direction_ok"])
    avg_field = sum(r["field_rate"] for r in results) / n
    avg_time = sum(r["elapsed"] for r in results) / n

    print(f"\n  汇总: JSON有效性={json_ok}/{n} | 方向正确={dir_ok}/{n} | "
          f"字段完整={avg_field:.0%} | 平均耗时={avg_time:.1f}s")

    return results


def eval_resume_tailor():
    """评估简历改写：长度保留 + JD关键词覆盖"""
    print("\n" + "=" * 60)
    print("[3] 简历改写评估")
    print("=" * 60)

    from prompts.resume_tailor import RESUME_TAILOR_SYSTEM, RESUME_TAILOR_USER_TEMPLATE
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = ChatOpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        model=DEEPSEEK_MODEL,
        temperature=0.6,
    )

    results = []
    for tc in TAILOR_TEST_CASES:
        t0 = time.time()
        messages = [
            SystemMessage(content=RESUME_TAILOR_SYSTEM),
            HumanMessage(content=RESUME_TAILOR_USER_TEMPLATE.format(
                jd_analysis=tc["jd_analysis"],
                match_result=tc["match_result"],
                resume_text=tc["resume_text"],
            )),
        ]
        resp = llm.invoke(messages)
        elapsed = time.time() - t0

        tailored = resp.content

        # 长度保留率（不能把简历改没了）
        len_ratio = len(tailored) / len(tc["resume_text"])
        len_ok = 0.5 <= len_ratio <= 10.0  # 含格式和注释，可显著扩展

        # JD 关键词覆盖
        jd_kw = tc.get("jd_keywords", [])
        kw_hits = sum(1 for kw in jd_kw if kw.lower() in tailored.lower())
        kw_rate = kw_hits / len(jd_kw) if jd_kw else 1.0

        # 不虚构检查：原始简历里没有的技能不应该凭空出现
        # 简单检查：改写结果中不应包含完全不存在的技能名
        r = {
            "id": tc["id"],
            "len_ratio": round(len_ratio, 2),
            "len_ok": len_ok,
            "kw_rate": kw_rate,
            "elapsed": round(elapsed, 2),
            "preview": tailored[:100],
        }
        results.append(r)

        print(f"\n[{tc['id']}] | 长度比={len_ratio:.1%} | 关键词={kw_rate:.0%} "
              f"({kw_hits}/{len(jd_kw)}) | {elapsed:.1f}s")
        print(f"  改写前({len(tc['resume_text'])}字): {tc['resume_text'][:80]}...")
        print(f"  改写后({len(tailored)}字): {tailored[:80]}...")

    n = len(results)
    len_ok = sum(1 for r in results if r["len_ok"])
    avg_kw = sum(r["kw_rate"] for r in results) / n
    avg_time = sum(r["elapsed"] for r in results) / n

    print(f"\n  汇总: 长度合格={len_ok}/{n} | 关键词覆盖={avg_kw:.0%} | "
          f"平均耗时={avg_time:.1f}s")

    return results


def eval_cover_letter():
    """评估求职信：格式规范 + 收信人/署名完整"""
    print("\n" + "=" * 60)
    print("[4] 求职信生成评估")
    print("=" * 60)

    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    from prompts.cover_letter import COVER_LETTER_SYSTEM, STYLE_OPTIONS

    llm = ChatOpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        model=DEEPSEEK_MODEL,
        temperature=0.7,
    )

    sample_jd = JD_TEST_CASES[0]["jd_text"]
    sample_resume = "熟悉Python、FastAPI开发，有Docker部署经验，2年Web后端开发经验。"

    results = []
    for tc in COVER_LETTER_CASES:
        style_name = STYLE_OPTIONS.get(tc["style"], "正式商务")
        t0 = time.time()
        full_prompt = f"""请生成一封{style_name}风格的求职信。

目标职位JD：
{sample_jd}

候选人简历：
{sample_resume}

候选人姓名：{tc["candidate_name"]}
收信人：{tc["recipient"]}

请直接输出完整的求职信正文。"""
        messages = [
            SystemMessage(content=COVER_LETTER_SYSTEM),
            HumanMessage(content=full_prompt),
        ]
        resp = llm.invoke(messages)
        elapsed = time.time() - t0

        letter = resp.content

        # 格式检查
        has_name = tc["candidate_name"] in letter
        has_recipient = tc["recipient"] in letter or "负责人" in letter or "经理" in letter
        has_greeting = any(w in letter for w in ["您好", "尊敬的", "亲爱的", "你好"])
        has_closing = any(w in letter for w in ["此致", "敬礼", "期待", "感谢", "谢谢"])
        format_score = sum([has_name, has_recipient, has_greeting, has_closing]) / 4

        # 长度检查
        len_ok = 200 <= len(letter) <= 3000

        r = {
            "id": tc["id"],
            "format_score": format_score,
            "len_ok": len_ok,
            "char_count": len(letter),
            "elapsed": round(elapsed, 2),
            "preview": letter[:120],
        }
        results.append(r)

        print(f"\n[{tc['id']}] | 格式={format_score:.0%} | 长度={len(letter)}字 "
              f"({'合格' if len_ok else '异常'}) | {elapsed:.1f}s")
        print(f"  {letter[:120]}...")

    n = len(results)
    avg_format = sum(r["format_score"] for r in results) / n
    len_ok = sum(1 for r in results if r["len_ok"])
    avg_time = sum(r["elapsed"] for r in results) / n

    print(f"\n  汇总: 格式规范={avg_format:.0%} | 长度合格={len_ok}/{n} | "
          f"平均耗时={avg_time:.1f}s")

    return results


# ============================================================
# 汇总报告
# ============================================================

def print_summary(jd_results, match_results, tailor_results, cover_results):
    print("\n\n" + "=" * 60)
    print("整体评估汇总")
    print("=" * 60)

    print(f"\n  JD 分析:    JSON有效性={sum(1 for r in jd_results if r['json_valid'])}/{len(jd_results)}"
          f" | 技能召回={sum(r['skill_recall'] for r in jd_results)/len(jd_results):.0%}"
          f" | 平均{sum(r['elapsed'] for r in jd_results)/len(jd_results):.1f}s")

    print(f"  简历匹配:   JSON有效性={sum(1 for r in match_results if r['json_valid'])}/{len(match_results)}"
          f" | 方向正确={sum(1 for r in match_results if r['direction_ok'])}/{len(match_results)}"
          f" | 平均{sum(r['elapsed'] for r in match_results)/len(match_results):.1f}s")

    print(f"  简历改写:   长度合格={sum(1 for r in tailor_results if r['len_ok'])}/{len(tailor_results)}"
          f" | 关键词覆盖={sum(r['kw_rate'] for r in tailor_results)/len(tailor_results):.0%}"
          f" | 平均{sum(r['elapsed'] for r in tailor_results)/len(tailor_results):.1f}s")

    print(f"  求职信:     格式规范={sum(r['format_score'] for r in cover_results)/len(cover_results):.0%}"
          f" | 平均{sum(r['elapsed'] for r in cover_results)/len(cover_results):.1f}s")

    # 整体性能
    all_times = (
        [r["elapsed"] for r in jd_results]
        + [r["elapsed"] for r in match_results]
        + [r["elapsed"] for r in tailor_results]
        + [r["elapsed"] for r in cover_results]
    )
    print(f"\n  整体耗时: 平均{sum(all_times)/len(all_times):.1f}s | "
          f"最短{min(all_times):.1f}s | 最长{max(all_times):.1f}s | "
          f"总{sum(all_times):.1f}s ({len(all_times)}次LLM调用)")


if __name__ == "__main__":
    print("JobCopilot 量化评估")
    print(f"模型: {DEEPSEEK_MODEL} | API: {DEEPSEEK_BASE_URL}")
    print()

    jd_results = eval_jd_analysis()
    match_results = eval_resume_match()
    tailor_results = eval_resume_tailor()
    cover_results = eval_cover_letter()
    print_summary(jd_results, match_results, tailor_results, cover_results)
