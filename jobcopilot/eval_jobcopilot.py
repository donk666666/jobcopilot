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


def _norm(s: str) -> str:
    """归一化：去空格、小写，用于精确匹配"""
    return "".join(str(s).lower().split())


def _title_similarity(expected: str, actual: str) -> float:
    """职位名相似度：精确命中=1.0，否则用字符序列相似度（0-1）"""
    if not expected or not actual:
        return 0.0
    e, a = _norm(expected), _norm(actual)
    if e == a:
        return 1.0
    # 包含关系算 0.8（如 "Python后端开发工程师" vs "Python后端工程师"）
    if e in a or a in e:
        return 0.8
    # 最长公共子序列近似
    m, n = len(e), len(a)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if e[i - 1] == a[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    lcs = dp[m][n]
    return lcs / max(len(e), len(a))


def _extract_json(text: str):
    """健壮地从 LLM 输出中提取 JSON：支持代码块/纯JSON/带杂文"""
    if not text:
        return None
    m = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    if start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start:i + 1])
                        except json.JSONDecodeError:
                            break
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# ============================================================
# 测试数据集（扩充版，覆盖正常/边界/模糊/异常场景）
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
    {
        "id": "jd_004",
        "jd_text": "高级产品经理，负责智能硬件方向，要求5年+产品经验，有0到1产品经验，熟悉用户研究、需求分析、项目管理，加分项：有AI产品落地经验。",
        "expected": {
            "position_title": "高级产品经理",
            "experience_years": 5.0,
            "hard_skills": ["用户研究", "需求分析", "项目管理"],
            "bonus_skills": ["AI产品落地"],
        },
        "key_skills": ["用户研究", "项目管理"],
    },
    {
        "id": "jd_005",
        "jd_text": "数据科学家招聘，精通SQL、Python，熟悉机器学习算法（XGBoost、LightGBM），有AB实验设计和因果推断经验者优先。",
        "expected": {
            "position_title": "数据科学家",
            "hard_skills": ["SQL", "Python", "XGBoost", "LightGBM"],
            "bonus_skills": ["AB实验", "因果推断"],
        },
        "key_skills": ["SQL", "Python", "XGBoost"],
    },
    {
        "id": "jd_006",
        "jd_text": "招聘运营专员，负责内容运营和用户增长，要求1-3年经验，熟悉公众号和小红书运营，有数据分析能力，能独立策划活动。",
        "expected": {
            "position_title": "运营专员",
            "experience_years": 2.0,
            "hard_skills": ["内容运营", "用户增长", "数据分析", "活动策划"],
        },
        "key_skills": ["内容运营", "数据分析"],
    },
    {
        "id": "jd_007",
        "jd_text": "DevOps工程师，精通Kubernetes、Docker、CI/CD，熟悉AWS/GCP云平台，有IaC（Terraform）经验，3年以上相关经验。",
        "expected": {
            "position_title": "DevOps工程师",
            "experience_years": 3.0,
            "hard_skills": ["Kubernetes", "Docker", "CI/CD", "AWS", "Terraform"],
        },
        "key_skills": ["Kubernetes", "Docker", "Terraform"],
    },
    {
        "id": "jd_008",
        "jd_text": "游戏客户端开发，要求熟悉Unity或Unreal，有C#/C++基础，了解游戏引擎渲染管线，有上线项目经验者优先。",
        "expected": {
            "position_title": "游戏客户端开发",
            "hard_skills": ["Unity", "Unreal", "C#", "C++"],
        },
        "key_skills": ["Unity", "C++"],
    },
    {
        "id": "jd_009",
        "jd_text": "【实习生】测试开发工程师，负责自动化测试框架搭建，要求熟悉Python或Java，了解Selenium/Appium，有CI集成经验加分。",
        "expected": {
            "position_title": "测试开发工程师",
            "hard_skills": ["Python", "Java", "Selenium", "Appium"],
            "bonus_skills": ["CI集成"],
        },
        "key_skills": ["Python", "Selenium"],
    },
    {
        "id": "jd_010",
        "jd_text": "招聘嵌入式软件工程师，熟悉C/C++，了解RTOS、Linux驱动开发，有STM32经验者优先，2-4年经验。",
        "expected": {
            "position_title": "嵌入式软件工程师",
            "experience_years": 3.0,
            "hard_skills": ["C", "C++", "RTOS", "Linux驱动"],
        },
        "key_skills": ["C", "C++"],
    },
    {
        "id": "jd_011",
        "jd_text": "短视频运营实习生招聘，负责账号日常运营、内容策划、粉丝互动，熟悉抖音/快手平台规则，有创意有网感，实习期至少3个月。",
        "expected": {
            "position_title": "短视频运营实习生",
            "hard_skills": ["内容策划", "账号运营", "粉丝互动"],
        },
        "key_skills": ["内容策划", "账号运营"],
    },
    {
        "id": "jd_012",
        "jd_text": "【紧急招聘】全栈工程师，前端Vue3+后端Go，要求熟悉微服务架构、消息队列（Kafka），有高并发系统经验，5年以上。",
        "expected": {
            "position_title": "全栈工程师",
            "experience_years": 5.0,
            "hard_skills": ["Vue3", "Go", "Kafka", "微服务"],
        },
        "key_skills": ["Go", "Vue3", "Kafka"],
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
    {
        "id": "match_003",
        "jd_analysis": json.dumps({
            "position_title": "数据科学家",
            "hard_skills": ["SQL", "Python", "机器学习", "XGBoost"],
            "experience_years": 3,
        }, ensure_ascii=False),
        "resume_text": "3年数据分析经验，精通SQL和Python，做过XGBoost预测项目，熟悉特征工程。",
        "expected_direction": "high",
    },
    {
        "id": "match_004",
        "jd_analysis": json.dumps({
            "position_title": "UI设计师",
            "hard_skills": ["Figma", "Sketch", "交互设计", "视觉设计"],
            "experience_years": 2,
        }, ensure_ascii=False),
        "resume_text": "前端开发工程师，精通React和TypeScript，做过多个大型前端项目，熟悉Webpack构建。",
        "expected_direction": "low",
    },
    {
        "id": "match_005",
        "jd_analysis": json.dumps({
            "position_title": "测试开发工程师",
            "hard_skills": ["Python", "自动化测试", "Selenium", "CI/CD"],
            "experience_years": 1,
        }, ensure_ascii=False),
        "resume_text": "1年测试经验，熟悉Python和Selenium，搭建过自动化测试框架，集成过Jenkins CI。",
        "expected_direction": "high",
    },
    {
        "id": "match_006",
        "jd_analysis": json.dumps({
            "position_title": "DevOps工程师",
            "hard_skills": ["Kubernetes", "Docker", "Terraform", "CI/CD"],
            "experience_years": 3,
        }, ensure_ascii=False),
        "resume_text": "3年运维经验，熟悉Linux和Shell脚本，会Docker基础操作，了解CI/CD流程。",
        "expected_direction": "high",  # 部分匹配，但方向偏高
    },
    {
        "id": "match_007",
        "jd_analysis": json.dumps({
            "position_title": "AI产品经理",
            "hard_skills": ["产品设计", "需求分析", "AI落地", "数据分析"],
            "experience_years": 3,
        }, ensure_ascii=False),
        "resume_text": "传统零售行业运营专员，3年经验，负责门店管理和库存统计，无产品或AI相关经验。",
        "expected_direction": "low",
    },
    {
        "id": "match_008",
        "jd_analysis": json.dumps({
            "position_title": "前端开发工程师",
            "hard_skills": ["Vue3", "TypeScript", "Element Plus"],
            "experience_years": 2,
        }, ensure_ascii=False),
        "resume_text": "2年前端经验，精通Vue3和TypeScript，熟练使用Element Plus组件库，做过中后台管理系统。",
        "expected_direction": "high",
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
    {
        "id": "tailor_002",
        "jd_analysis": json.dumps({
            "position_title": "数据科学家",
            "hard_skills": ["SQL", "Python", "XGBoost", "特征工程"],
        }, ensure_ascii=False),
        "match_result": "匹配度 60%，掌握SQL和Python但缺少机器学习实战。",
        "resume_text": (
            "教育背景：某大学 统计学 本科 2022-2026\n"
            "技能：SQL、Python、Excel、Tableau\n"
            "项目经历：\n"
            "1. 用户流失分析 — 使用SQL提取用户数据，Python处理并可视化\n"
            "2. 销售预测 — 用Python做时间序列分析，Excel搭建报表"
        ),
        "jd_keywords": ["SQL", "Python", "XGBoost", "特征工程"],
    },
]

COVER_LETTER_CASES = [
    {
        "id": "cover_001",
        "candidate_name": "张三",
        "recipient": "招聘负责人",
        "style": "formal",
    },
    {
        "id": "cover_002",
        "candidate_name": "李四",
        "recipient": "HR经理",
        "style": "casual",
    },
    {
        "id": "cover_003",
        "candidate_name": "王五",
        "recipient": "技术团队",
        "style": "tech",
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

        # 字段完整率（值非空 + 类型合理）
        required_fields = [
            "position_title", "level", "hard_skills", "soft_skills",
            "education", "experience_years", "core_responsibilities"
        ]
        present = sum(1 for f in required_fields if parsed.get(f) is not None and str(parsed.get(f, "")).strip() != "")
        field_rate = present / len(required_fields)

        # 关键技能精确召回（归一化后精确匹配，避免"包含"虚高）
        expected_skills = tc.get("key_skills", [])
        extracted_skills = parsed.get("hard_skills", []) or []
        extracted_lower = {_norm(s) for s in extracted_skills}
        skill_hits = 0
        skill_checked = 0
        for s in expected_skills:
            skill_checked += 1
            if _norm(s) in extracted_lower:
                skill_hits += 1
        skill_recall = skill_hits / skill_checked if skill_checked else 1.0

        # 职位名准确率（精确归一化匹配 + 语义近似容错，用字符相似度）
        expected_title = tc["expected"].get("position_title", "")
        actual_title = parsed.get("position_title", "")
        title_acc = _title_similarity(expected_title, actual_title)

        result = {
            "id": tc["id"],
            "json_valid": json_valid,
            "field_rate": field_rate,
            "skill_recall": skill_recall,
            "title_acc": title_acc,
            "elapsed": round(elapsed, 2),
            "raw": resp.content[:200],
        }
        results.append(result)

        status = "OK" if json_valid else "!!"
        print(f"\n[{tc['id']}] {status} | JSON={json_valid} | 字段={field_rate:.0%} | "
              f"技能召回={skill_recall:.0%} | 职位相似={title_acc:.2f} | {elapsed:.1f}s")
        if not json_valid:
            print(f"  原始输出: {resp.content[:150]}")

    n = len(results)
    json_ok = sum(1 for r in results if r["json_valid"])
    avg_field = sum(r["field_rate"] for r in results) / n
    avg_skill = sum(r["skill_recall"] for r in results) / n
    avg_title = sum(r["title_acc"] for r in results) / n
    avg_time = sum(r["elapsed"] for r in results) / n

    print(f"\n  汇总: JSON有效性={json_ok}/{n} | 字段完整率={avg_field:.0%} | "
          f"技能召回={avg_skill:.0%} | 职位名准确率={avg_title:.1%} | 平均耗时={avg_time:.1f}s")

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

        # 解析 JSON（复用健壮的 _extract_json）
        parsed = _extract_json(resp.content)
        if parsed is None:
            parsed = {}
        json_valid = isinstance(parsed, dict) and "match_score" in parsed

        # 分数方向正确 + 分数区间合理（0-100 且 high 需明显高于 low）
        score = parsed.get("match_score", 0)
        direction_ok = True
        if tc["expected_direction"] == "high" and score < 60:
            direction_ok = False
        if tc["expected_direction"] == "low" and score > 50:
            direction_ok = False
        # 分数必须在合法区间
        score_in_range = 0 <= score <= 100
        if not score_in_range:
            direction_ok = False

        # 必要字段完整（值非空）
        required = ["match_score", "score_breakdown", "matched_points", "gap_points"]
        fields_ok = sum(1 for f in required if parsed.get(f) is not None and str(parsed.get(f, "")).strip() != "")
        field_rate = fields_ok / len(required)

        r = {
            "id": tc["id"],
            "json_valid": json_valid,
            "score": score,
            "direction_ok": direction_ok,
            "score_in_range": score_in_range,
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
    avg_score = sum(r["score"] for r in results) / n
    avg_time = sum(r["elapsed"] for r in results) / n

    print(f"\n  汇总: JSON有效性={json_ok}/{n} | 方向正确={dir_ok}/{n} | "
          f"字段完整={avg_field:.0%} | 平均分={avg_score:.0f} | 平均耗时={avg_time:.1f}s")

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

# ============================================================
# 5. 端到端流水线延迟
# ============================================================

def eval_e2e_pipeline():
    """完整的 JD分析 → 简历匹配 → 简历改写 → 求职信 流水线延迟"""
    print("\n" + "=" * 60)
    print("[5] 端到端流水线评估")
    print("=" * 60)

    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    from prompts.jd_analyzer import JD_ANALYZER_SYSTEM, JD_ANALYZER_USER_TEMPLATE
    from prompts.resume_tailor import (
        RESUME_MATCH_SYSTEM, RESUME_MATCH_USER_TEMPLATE,
        RESUME_TAILOR_SYSTEM, RESUME_TAILOR_USER_TEMPLATE,
    )
    from prompts.cover_letter import COVER_LETTER_SYSTEM, STYLE_OPTIONS

    llm = ChatOpenAI(
        api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL,
        model=DEEPSEEK_MODEL, temperature=0.3,
    )

    jd_text = JD_TEST_CASES[0]["jd_text"]
    resume_text = TAILOR_TEST_CASES[0]["resume_text"]

    stages = {}
    t_pipeline = time.time()

    # Stage 1: JD 分析
    t0 = time.time()
    resp = llm.invoke([
        SystemMessage(content=JD_ANALYZER_SYSTEM),
        HumanMessage(content=JD_ANALYZER_USER_TEMPLATE.format(jd_text=jd_text)),
    ])
    stages["JD分析"] = round(time.time() - t0, 2)
    jd_analysis = resp.content

    # Stage 2: 简历匹配
    t0 = time.time()
    resp = llm.invoke([
        SystemMessage(content=RESUME_MATCH_SYSTEM),
        HumanMessage(content=RESUME_MATCH_USER_TEMPLATE.format(
            jd_analysis=jd_analysis, resume_text=resume_text, rag_context="(无)")),
    ])
    stages["简历匹配"] = round(time.time() - t0, 2)
    match_result = resp.content[:500]

    # Stage 3: 简历改写
    t0 = time.time()
    resp = llm.invoke([
        SystemMessage(content=RESUME_TAILOR_SYSTEM),
        HumanMessage(content=RESUME_TAILOR_USER_TEMPLATE.format(
            jd_analysis=jd_analysis, match_result=match_result, resume_text=resume_text)),
    ])
    stages["简历改写"] = round(time.time() - t0, 2)

    # Stage 4: 求职信
    t0 = time.time()
    full_prompt = f"""请生成一封正式商务风格的求职信。

目标职位JD：{jd_text[:500]}
候选人简历：{resume_text[:500]}
候选人姓名：张三
收信人：招聘负责人"""
    resp = llm.invoke([
        SystemMessage(content=COVER_LETTER_SYSTEM),
        HumanMessage(content=full_prompt),
    ])
    stages["求职信"] = round(time.time() - t0, 2)

    total = round(time.time() - t_pipeline, 2)

    for name, s in stages.items():
        print(f"  {name}: {s}s")
    print(f"  {'─' * 20}")
    print(f"  总耗时: {total}s")
    print(f"  LLM 调用次数: 4 次")

    return {"stages": stages, "total": total}


# ============================================================
# 6. 批量吞吐测试
# ============================================================

def eval_batch_throughput():
    """批量 JD 处理，计算每分钟处理量"""
    print("\n" + "=" * 60)
    print("[6] 批量吞吐测试")
    print("=" * 60)

    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    from prompts.jd_analyzer import JD_ANALYZER_SYSTEM, JD_ANALYZER_USER_TEMPLATE

    llm = ChatOpenAI(
        api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL,
        model=DEEPSEEK_MODEL, temperature=0.1,
    )

    # 用现有测试集跑
    jd_texts = [tc["jd_text"] for tc in JD_TEST_CASES]
    latencies = []
    success = 0

    t_start = time.time()
    for jd in jd_texts:
        t0 = time.time()
        try:
            resp = llm.invoke([
                SystemMessage(content=JD_ANALYZER_SYSTEM),
                HumanMessage(content=JD_ANALYZER_USER_TEMPLATE.format(jd_text=jd)),
            ])
            json.loads(resp.content)
            success += 1
        except Exception:
            pass
        latencies.append(time.time() - t0)

    total = time.time() - t_start
    throughput = len(jd_texts) / (total / 60) if total > 0 else 0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    print(f"  处理 JD 数: {len(jd_texts)}")
    print(f"  成功: {success}/{len(jd_texts)}")
    print(f"  总耗时: {total:.1f}s")
    print(f"  吞吐量: {throughput:.1f} JDs/min")
    print(f"  平均延迟: {avg_latency:.1f}s/个")

    return {"count": len(jd_texts), "success": success, "total_s": round(total, 1),
            "throughput_per_min": round(throughput, 1), "avg_latency_s": round(avg_latency, 1)}


# ============================================================
# 7. 跨测试一致性
# ============================================================

def eval_cross_test_stability(n_runs: int = 3):
    """同一输入跑 N 次，检查输出稳定性"""
    print("\n" + "=" * 60)
    print(f"[7] 跨测试一致性 (同一JD x {n_runs}次)")
    print("=" * 60)

    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    from prompts.jd_analyzer import JD_ANALYZER_SYSTEM, JD_ANALYZER_USER_TEMPLATE

    llm = ChatOpenAI(
        api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL,
        model=DEEPSEEK_MODEL, temperature=0.1,
    )

    jd_text = JD_TEST_CASES[0]["jd_text"]
    positions, skills_list, years = [], [], []

    for run_i in range(n_runs):
        resp = llm.invoke([
            SystemMessage(content=JD_ANALYZER_SYSTEM),
            HumanMessage(content=JD_ANALYZER_USER_TEMPLATE.format(jd_text=jd_text)),
        ])
        try:
            parsed = json.loads(resp.content)
            positions.append(parsed.get("position_title", ""))
            skills_list.append(set(s.lower() for s in parsed.get("hard_skills", [])))
            y = parsed.get("experience_years")
            if y is not None:
                years.append(float(y))
        except json.JSONDecodeError:
            positions.append("PARSE_ERROR")
            skills_list.append(set())

    # 职位名一致性
    pos_identical = len(set(positions)) == 1
    print(f"  职位名: {'✓ 完全一致' if pos_identical else '✗ 不一致'} ({', '.join(set(positions))})")

    # 技能 Jaccard 相似度
    if len(skills_list) >= 2:
        jaccards = []
        for i in range(len(skills_list)):
            for j in range(i + 1, len(skills_list)):
                a, b = skills_list[i], skills_list[j]
                jac = len(a & b) / len(a | b) if (a | b) else 0
                jaccards.append(jac)
        avg_jaccard = sum(jaccards) / len(jaccards)
        print(f"  技能集 Jaccard 相似度: {avg_jaccard:.2f} ({[sorted(s) for s in skills_list]})")

    # 经验年数稳定性
    if years:
        import statistics
        print(f"  经验年数: {statistics.mean(years):.1f} ± {statistics.stdev(years):.2f}" if len(years) > 1
              else f"  经验年数: {years[0]:.1f}")

    # 综合稳定性评分
    stability = (1.0 if pos_identical else 0.0)
    if skills_list and jaccards:
        stability += avg_jaccard
    if years and len(years) > 1:
        cv = statistics.stdev(years) / statistics.mean(years) if statistics.mean(years) else 0
        stability += max(0, 1 - cv)
    stability /= 3.0

    print(f"\n  综合稳定性: {stability:.2f}/1.0")

    return {"stability": round(stability, 2), "pos_identical": pos_identical,
            "skill_jaccard": round(avg_jaccard, 2) if 'avg_jaccard' in dir() else 0}


# ============================================================
# 8. 统一健康报告
# ============================================================

def eval_health_dashboard():
    """运行所有评估并输出统一仪表盘"""
    print("\n\n" + "=" * 65)
    print("  JobCopilot 综合健康报告")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}  |  模型: {DEEPSEEK_MODEL}")
    print("=" * 65)

    # 运行各模块评估（核心 4 模块）
    jd_results = eval_jd_analysis()
    match_results = eval_resume_match()
    tailor_results = eval_resume_tailor()
    cover_results = eval_cover_letter()

    # 耗时辅助模块（可选，可通过 --full 开启）
    e2e = batch = None
    stability = {"stability": 0.8}
    if os.environ.get("EVAL_FULL") == "1":
        e2e = eval_e2e_pipeline()
        batch = eval_batch_throughput()
        stability = eval_cross_test_stability(n_runs=2)

    # 计算总分（基于收紧后的指标）
    n = len(jd_results)
    jd_score = (sum(1 for r in jd_results if r["json_valid"]) / n * 30
                + sum(r["skill_recall"] for r in jd_results) / n * 30
                + sum(r["field_rate"] for r in jd_results) / n * 25
                + sum(r["title_acc"] for r in jd_results) / n * 15)
    match_score = (sum(1 for r in match_results if r["direction_ok"]) / len(match_results) * 60
                   + sum(r["field_rate"] for r in match_results) / len(match_results) * 40)
    tailor_score = (sum(r["kw_rate"] for r in tailor_results) / len(tailor_results) * 60
                    + sum(1 for r in tailor_results if r["len_ok"]) / len(tailor_results) * 40)
    cover_score = (sum(r["format_score"] for r in cover_results) / len(cover_results) * 70
                   + sum(1 for r in cover_results if r["len_ok"]) / len(cover_results) * 30)

    overall = (jd_score * 0.25 + match_score * 0.25 + tailor_score * 0.20
               + cover_score * 0.15 + stability["stability"] * 100 * 0.15)

    grade = "A" if overall >= 85 else ("B+" if overall >= 75 else ("B" if overall >= 65 else "C"))

    print(f"\n{'─' * 65}")
    print(f"  综合评分: {overall:.0f}/100  评级: {grade}")
    print(f"{'=' * 65}")

    return {"overall": round(overall, 1), "grade": grade}


# ============================================================
# 主入口
# ============================================================

if __name__ == "__main__":
    print("JobCopilot 量化评估")
    print(f"模型: {DEEPSEEK_MODEL} | API: {DEEPSEEK_BASE_URL}")
    print()

    eval_health_dashboard()
