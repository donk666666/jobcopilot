# JobCopilot 迭代设计文档 — 简历解析 / 多 Agent 并行 / Redis

> 日期：2026-08-01 | 状态：已确认

## 概述

本次迭代在 JobCopilot 现有架构基础上增加三个能力：

1. **简历上传解析**：支持 Word(.docx) / PDF 上传，自动提取文本
2. **多 Agent 并行协作**：多维度同时分析 + 汇总讨论
3. **Redis 引入**：LLM 缓存 + Celery 任务队列

原则：渐进增强，不推翻现有架构，所有改动保持向后兼容。

---

## 一、简历上传与解析

### 1.1 后端

**新增 `backend/api/upload.py`**：

| 项目 | 细节 |
|------|------|
| 端点 | `POST /api/resume/upload` |
| 输入 | `multipart/form-data`，字段 `file` |
| 允许格式 | `.docx`、`.pdf` |
| 大小限制 | 最大 5MB |
| Word 解析 | `python-docx` — 遍历 `document.paragraphs`，用换行符拼接 |
| PDF 解析 | `pdfplumber` — 逐页 `page.extract_text()`，用换行符拼接 |
| 响应 | `{ "filename": str, "text": str, "char_count": int, "file_type": "docx"|"pdf" }` |
| 错误处理 | 格式不支持 → 400；文件为空/无法解析 → 400 并说明原因 |
| 存储 | 解析后纯文本不入库，仅返回前端；用户确认后通过现有 `/api/resume/active` 保存 |

**新增依赖**：`python-docx`、`pdfplumber`

### 1.2 前端

改造 `frontend/src/views/ResumeOptimizer.vue` 左侧"简历文本"区域：

- 文本框上方增加上传区：`el-upload` 组件，`drag` 模式，`accept=".docx,.pdf"`，`:auto-upload="false"`，`:limit="1"`
- 选择文件后调 `/api/resume/upload`，成功后将 `text` 填入下方文本框，显示 toast 提示
- 上传区下方显示文件名和字符数

### 1.3 一键全流程按钮

匹配/优化按钮下方增加"一键全流程"按钮（详见第三节异步任务）。

---

## 二、多 Agent 并行协作

### 2.1 架构

改造 `backend/agent/multi_agent.py` 中 `full_pipeline` 路径：

```
Supervisor → JD分析 → [并行分析组] → 汇总Agent → 简历改写 → 求职信 → END
```

### 2.2 并行分析节点

新增 `parallel_analysis_node`：

- 用 `asyncio.gather` 同时启动 4 个 LLM 调用，每个带独立的 System Prompt：

| Agent | 分析维度 | Prompt 要点 |
|-------|---------|-------------|
| A — 技术栈 | 硬技能匹配 | 编程语言、框架、工具链与 JD 要求对比 |
| B — 项目经验 | 实战能力匹配 | 项目复杂度、角色、量化成果与 JD 场景对比 |
| C — 软技能/文化 | 综合素质匹配 | 沟通、领导力、团队协作、价值观契合 |
| D — 成长潜力 | 发展空间匹配 | 学习能力、技术广度、职业发展轨迹 |

- 每个 Agent 输出统一 JSON：`{ "dimension": str, "score": 0-100, "matched": [...], "gaps": [...], "analysis": str }`
- 超时：每个 Agent 30s，超时返回 `{ "dimension": str, "timeout": true }`
- 异常：单个 Agent 异常不阻塞整体，汇总时标注

### 2.3 汇总 Agent 节点

新增 `debate_summary_node`：

- 输入：4 份并行分析结果（含超时/异常标记）
- 任务：综合 4 维度打分、标记矛盾点（如技术栈 Agent 评分高但项目 Agent 评分低并说明原因）、产出最终匹配报告
- 输出：兼容现有 `match_result` 格式，额外增加 `dimension_scores` 字段和 `contradictions` 字段

### 2.4 路由

- `full_pipeline`：JD分析 → 并行分析 → 汇总 → 改写 → 求职信
- `jd_analysis`：仅 JD 分析，不变
- `cover_letter`：仅求职信生成，不变

---

## 三、Redis 引入

### 3.1 架构

```
FastAPI
  ├─ Redis 缓存层
  │   ├─ LLM 分析结果缓存（TTL 1h）
  │   └─ RAG 检索结果缓存（TTL 30min）
  └─ Celery 任务队列（Broker/Backend 均为 Redis）
      └─ 全流程异步任务（run_full_pipeline）
```

### 3.2 缓存策略

**新增 `backend/cache.py`**：

| 函数 | 用途 | Key 规则 | TTL |
|------|------|---------|-----|
| `cache_llm_result(jd, resume, result)` | 缓存 LLM 分析 | `md5(jd_text + resume_text + operation)` | 1h |
| `get_cached_llm(jd, resume, operation)` | 查询缓存 | 同上 | — |
| `cache_rag_result(query, result)` | 缓存 RAG 检索 | `md5(query)` | 30min |
| `get_cached_rag(query)` | 查询 RAG 缓存 | 同上 | — |
| `invalidate(pattern)` | 按前缀清除缓存 | `keys(pattern)` | — |

**改造 `api/resume.py`**：
- `match`、`tailor` 端点在调 LLM 前先查缓存，命中直接返回（响应中加 `cached: true`）
- LLM 返回后写入缓存

### 3.3 Celery 异步任务

**新增 `backend/tasks.py`**：

- Celery app：Broker 和 Result Backend 均为 Redis（同一 URL，不同 db：db 0 缓存，db 1 队列，db 2 结果）
- 任务 `run_full_pipeline(jd_text, resume_text, candidate_name, style)`：
  1. 更新状态为 `analyzing_jd`
  2. JD 分析 → `matching` → 并行匹配（多 Agent）→ `tailoring` → 改写 → `writing_letter` → 求职信
  3. 完成后返回全流程结果，状态 `done`
  4. 异常时状态 `failed`，返回错误信息

**新增 `backend/api/tasks.py`**：

- `GET /api/task/{task_id}` → `{ status: "pending"|"running"|"done"|"failed", progress: {...}, result: {...}, error: str }`

**改造 `api/resume.py`**：

- `POST /api/resume/full-pipeline`：提交异步任务，立即返回 `{ task_id, status: "pending" }`

### 3.4 前端适配

"一键全流程"按钮：

1. 点击 → `POST /api/resume/full-pipeline`，拿到 `task_id`
2. 每 2s 轮询 `GET /api/task/{task_id}`
3. 进度展示：进度条 + 当前阶段文字（"正在分析JD…" → "正在多维度匹配…" → "正在优化简历…" → "正在生成求职信…"）
4. 完成后一次性渲染全流程结果

### 3.5 降级策略

- Redis 连接失败：`cache.py` 所有函数静默降级为空操作（缓存穿透直调 LLM）→ 不影响业务
- Celery Worker 未启动：`/api/resume/full-pipeline` 返回 503，提示"异步服务暂不可用，请使用分步操作"
- 降级行为在应用启动时自动检测并记录日志，前端无需感知（除了 503 提示）

### 3.6 新增依赖

`backend/requirements.txt` 新增：
```
redis>=5.0.0
celery>=5.3.0
python-docx>=1.0.0
pdfplumber>=0.10.0
```

### 3.7 启动方式

```bash
# Redis（如使用 Docker）
docker run -d --name jobcopilot-redis -p 6379:6379 redis:7-alpine

# Celery Worker（独立终端）
cd backend && celery -A tasks worker --loglevel=info --pool=solo

# FastAPI（不变）
cd backend && uvicorn main:app --reload
```

---

## 四、改动清单

| 类型 | 文件 | 改动性质 |
|------|------|---------|
| 后端 | `backend/api/upload.py` | **新增**：上传解析端点 |
| 后端 | `backend/cache.py` | **新增**：Redis 缓存封装 |
| 后端 | `backend/tasks.py` | **新增**：Celery 异步任务 |
| 后端 | `backend/api/tasks.py` | **新增**：任务状态查询端点 |
| 后端 | `backend/agent/multi_agent.py` | **改造**：新增并行分析节点 + 汇总节点 |
| 后端 | `backend/api/resume.py` | **改造**：加缓存查询 + 全流程异步端点 |
| 后端 | `backend/config.py` | **改造**：加 REDIS_URL |
| 后端 | `backend/main.py` | **改造**：注册新路由 |
| 后端 | `requirements.txt` | **改造**：加 redis、celery、python-docx、pdfplumber |
| 前端 | `src/views/ResumeOptimizer.vue` | **改造**：上传区 + 一键全流程 + 轮询进度 |
| 前端 | `src/api/index.ts` | **改造**：加 upload、fullPipeline、taskStatus 接口 |

---

## 五、不变的部分

- SQLite 数据库模型不变，继续存结构化数据
- ChromaDB 向量存储不变
- DeepSeek API 调用不变
- JD 分析、求职信生成、投递追踪模块不变
- 前端其余页面不变
- API 现有端点请求/响应格式不变，仅新增字段（向后兼容）
