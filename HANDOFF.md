# JobCopilot 交接文档

> **状态**：开发中的全栈项目，跑通主流程、未发布。
> **写这份文档时**：所有「应该工作的核心功能」都能跑，Redis 一键全流程可用，简历优化速度优化完成。

---

## 1. 项目是什么

**JobCopilot** = AI 求职助手，全栈 Web 应用。

| 模块 | 路径 | 作用 |
|---|---|---|
| **JD 智能分析** | `frontend/src/views/JDAnalyzer.vue` + `backend/api/jd.py` | 粘贴 JD → 提取 25+ 字段（薪资/行业/面试重点/风险信号/卖点等） |
| **简历匹配** | `frontend/src/views/ResumeOptimizer.vue` + `backend/api/resume.py` | 简历 vs JD → 5 维评分（雷达图）+ 匹配点/差距点 |
| **简历优化** | 同上 | 基于匹配诊断自动改写简历，支持改动注释开关 |
| **求职信** | `frontend/src/views/CoverLetter.vue` + `backend/api/cover_letter.py` | 3 种风格（专业/亲和/技术极客），自动存历史 |
| **个性化打招呼** | `frontend/src/views/Greeting.vue` + `backend/api/greet.py` | 多变体打招呼语 |
| **投递管理** | `frontend/src/views/Tracker.vue` + `backend/api/tracker.py` | 状态机：待投递→已投递→初筛中→面试中→Offer |
| **一键全流程** | Dashboard 卡片 + `backend/api/resume.py::full-pipeline` | JD分析+匹配+改写+求职信，Celery 异步 |
| **Dashboard** | `frontend/src/views/Dashboard.vue` | 顶部欢迎 + 三大功能卡片 + 数据看板 |

---

## 2. 技术栈

### 前端
- **Vue 3** + Composition API + `<script setup>`
- **TypeScript**（松散模式，部分文件仍是 `.vue`）
- **Vite** 5（端口 5173，HMR 热更新）
- **Element Plus** 2.x（UI 库）
- **Pinia** 未用（项目小，状态都用 ref）
- **Vue Router** 4（hash-free history 模式）
- **axios** 1.x（基础 baseURL = `/api`，自动转发到后端 8000）
- **CSS 变量**：所有主题色统一在 `:root` 定义（`--accent`, `--bg-deepest`, `--text-muted` 等），App.vue 注入

### 后端
- **Python 3.11**
- **FastAPI** + **uvicorn**（端口 8000，`python main.py` 启动）
- **SQLAlchemy 2.x** ORM + **MySQL 8.0**（默认 SQLite，本地开发用）
- **ChromaDB** + **BGE-small-zh-v1.5** embedding（本地离线模型，`models/` 目录）
- **LangChain** + **LangGraph**（多智能体 StateGraph）
- **Celery** + **Redis 7**（异步任务 + LLM 缓存）
- **DeepSeek API**（兼容 OpenAI ChatOpenAI 接口，默认模型 `glm-5.2`，但走的是 DeepSeek 端点）
- **python-docx** + **pdfplumber**（简历文件解析）

### 中间件
- **MySQL 8.0**：3307→3306（compose）
- **Redis 7**：6379（一键全流程 + LLM 缓存必需）
- **Docker**：本地开发可用 `docker-compose.yml` 启动 mysql

---

## 3. 项目结构

```
新项目/
├── jobcopilot/                    ← 主项目
│   ├── backend/
│   │   ├── main.py                 # FastAPI 入口（注册所有 router）
│   │   ├── config.py               # 环境变量配置（DEEPSEEK / DB / REDIS / CHROMA）
│   │   ├── database.py             # SQLAlchemy 表定义（JDAnalysis / Application / Resume / ResumeOptimization / CoverLetterHistory）
│   │   ├── cache.py                # Redis 缓存封装（cache_llm_result / get_cached_llm）
│   │   ├── tasks.py                # Celery 任务定义（run_full_pipeline）
│   │   ├── agent/
│   │   │   ├── core.py             # LLM 调用封装（match_resume_direct / tailor_resume_direct）
│   │   │   ├── multi_agent.py      # LangGraph StateGraph（Supervisor + 4 子 Agent 并行分析）
│   │   │   └── tools.py            # LangChain Tool 定义
│   │   ├── api/                    # FastAPI 路由
│   │   │   ├── jd.py               # POST /analyze + GET/DELETE /history
│   │   │   ├── resume.py           # POST /match + POST /tailor + POST /full-pipeline + GET/DELETE /history + GET /active + POST /active + GET /versions
│   │   │   ├── cover_letter.py     # POST /generate + GET/DELETE /history
│   │   │   ├── greet.py            # POST /generate
│   │   │   ├── tracker.py          # CRUD / + GET /stats
│   │   │   ├── upload.py           # POST /upload（解析 docx/pdf）
│   │   │   └── tasks.py            # GET /{task_id}（查 Celery 任务）
│   │   ├── prompts/                # LLM Prompt 模板
│   │   │   ├── jd_analyzer.py      # JD 分析 Few-shot Prompt（25+ 字段）
│   │   │   ├── resume_tailor.py    # 简历匹配/改写 Prompt（已精简）
│   │   │   ├── parallel_agents.py  # 4 个并行子 Agent Prompt（tech_stack/project_exp/soft_skills/growth）
│   │   │   └── cover_letter.py     # 求职信链式 Prompt
│   │   ├── rag/
│   │   │   └── vector_store.py     # ChromaDB 双集合（resume_store / jd_store）
│   │   └── data/                   # SQLite + ChromaDB 持久化目录
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── views/              # 6 个页面（Dashboard / JDAnalyzer / ResumeOptimizer / CoverLetter / Greeting / Tracker）
│   │   │   ├── components/         # RadarChart / LoadingSkeleton / ProgressBar / EmptyState / StatusIndicator
│   │   │   ├── api/index.ts        # axios 实例 + 所有 API 函数
│   │   │   ├── router/index.ts     # 5 个路由
│   │   │   ├── App.vue             # 侧栏导航 + main-inner 布局
│   │   │   └── main.ts             # Vue 入口
│   │   └── vite.config.ts          # 端口 5173，API 转发到 8000
│   ├── docker-compose.yml          # MySQL 容器（开发时起）
│   ├── mysql/init/                 # MySQL 初始化脚本
│   ├── models/                     # BGE embedding 模型（本地离线）
│   ├── data/docs/                  # 评估用的 JD/简历样本
│   ├── eval_jobcopilot.py          # 简历优化评估脚本
│   ├── eval_parallel_vs_serial.py  # 多智能体并行性能评估
│   └── README.md                   # 项目根 README
├── smartdocqa/                     # 另一个项目（智能文档助手），未在本会话主线
├── docs/superpowers/               # 设计文档
└── *.pdf, *.docx, *.png            # 简历样本和截图
```

---

## 4. 环境与启动

### 4.1 必需的环境变量（`backend/.env` 或系统环境）

```env
# DeepSeek API
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=glm-5.2

# 数据库（默认 SQLite；部署用 MySQL）
DATABASE_URL=mysql+pymysql://root:root123456@localhost:3307/jobcopilot

# Redis（一键全流程 + LLM 缓存）
REDIS_URL=redis://localhost:6379

# ChromaDB 持久化目录（默认 backend/data/chroma_db）
CHROMA_DIR=

# CORS（前端地址，逗号分隔）
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 4.2 启动顺序

```bash
# 1) Redis（一键全流程需要）
docker start jobcopilot-redis  # 或者 docker run -d --name jobcopilot-redis -p 6379:6379 redis:7-alpine

# 2) MySQL（开发用 docker-compose）
cd jobcopilot
docker compose up -d

# 3) 后端
cd backend
python main.py  # → http://localhost:8000

# 4) 前端（新窗口）
cd frontend
npm run dev      # → http://localhost:5173
```

### 4.3 关键命令

```bash
# 后端日志（uvicorn reload 模式，修改 .py 会自动 reload，但有时候 reload 卡住）
netstat -ano | grep ":8000"   # 看哪个 PID 占着端口
powershell -Command "Get-NetTCPConnection -LocalPort 8000 -State Listen | ForEach-Object { Stop-Process -Id \$_.OwningProcess -Force -ErrorAction SilentlyContinue }"

# 杀僵尸进程（用 Win32 API，PowerShell 杀不掉时）
python -c "import ctypes; h=ctypes.windll.kernel32.OpenProcess(1, False, PID); ctypes.windll.kernel32.TerminateProcess(h, 0); ctypes.windll.kernel32.CloseHandle(h)"

# 评估
python eval_jobcopilot.py
python eval_parallel_vs_serial.py
```

---

## 5. 数据库表（`backend/database.py`）

| 表 | 关键字段 | 用途 |
|---|---|---|
| `jd_analyses` | position_title, company_name, jd_raw, analysis_json (TEXT), match_weight | JD 分析历史 |
| `applications` | company_name, position_title, jd_text, jd_analysis, match_score, match_detail, tailored_resume, cover_letter, status, notes | 投递管理 |
| `resumes` | name, content, is_active | 简历历史版本（每次保存都是新行） |
| `resume_optimizations` | jd_analysis_id, resume_text, jd_analysis_json, match_score, match_detail, tailored_resume, annotations_enabled | 简历优化记录（含历史匹配和改写） |
| `cover_letter_history` | user_id, candidate_name, recipient, style, company_name, position_title, jd_text, resume_text, content | 求职信历史 |

**注意**：`analysis_json` / `match_detail` 字段是 `TEXT` 类型存 JSON 字符串，不是 JSON 列。

---

## 6. 后端 API 一览

```
GET  /                                       # 根（返回 service info）
GET  /api/health                             # 健康检查（含 redis 状态）

POST /api/jd/analyze                         # JD 分析（自动入库）
GET  /api/jd/history                         # 列出历史（最近 30 条）
DELETE /api/jd/history/{id}                  # 删除

POST /api/resume/match                       # 简历匹配度评分
POST /api/resume/tailor                      # 简历改写（带改动注释）
POST /api/resume/full-pipeline               # 一键全流程（Celery 异步）
GET  /api/resume/redis-status                # Redis 状态
GET  /api/resume/history                     # 简历优化历史
GET  /api/resume/history/{opt_id}            # 单条详情
DELETE /api/resume/history/{opt_id}          # 删除
GET  /api/resume/active                      # 当前激活简历
POST /api/resume/active                      # 保存并激活
GET  /api/resume/versions                    # 所有简历版本
PUT  /api/resume/{resume_id}                 # 更新简历版本
DELETE /api/resume/{resume_id}               # 删除
GET  /api/resume/rag-stats                   # ChromaDB 统计
POST /api/resume/upload                      # 上传 docx/pdf

POST /api/cover-letter/generate              # 生成求职信
GET  /api/cover-letter/history               # 历史列表（按 user_id 过滤）
GET  /api/cover-letter/history/{id}          # 详情
DELETE /api/cover-letter/history/{id}        # 删除

POST /api/greet/generate                     # 生成打招呼

GET  /api/tracker/                            # 列出投递
GET  /api/tracker/stats                       # 状态统计
GET  /api/tracker/{id}                        # 详情
POST /api/tracker/                            # 新建
PUT  /api/tracker/{id}                        # 更新
DELETE /api/tracker/{id}                      # 删除

GET  /api/task/{task_id}                     # Celery 任务状态
```

Swagger 文档：`http://localhost:8000/docs`

---

## 7. 前端路由 + 主要功能

| 路由 | 页面 | 关键功能 |
|---|---|---|
| `/` | Dashboard | 顶部欢迎条 + 智能建议 + 三大功能卡片（智能匹配分析/一键全流程/优化简历）+ 数据看板 |
| `/jd` | JDAnalyzer | JD 输入 → 25+ 字段分析结果 + 历史侧栏 |
| `/resume` | ResumeOptimizer | 上传简历 + 选 JD → 匹配评分 + 雷达图 + 改写对比 |
| `/cover-letter` | CoverLetter | JD + 简历 → 求职信（3 风格）+ 历史侧栏 |
| `/greet` | Greeting | 简历 → 多变体打招呼 |
| （注：Tracker 没注册到路由表，侧栏没有入口；要访问直接访问路由：可在 router/index.ts 加 `/tracker`）|

**Tracker.vue 已存���但 router 没注册**——这是已知 TODO。

---

## 8. 本次会话改了什么（

**Bug 修复**：
1. ✅ **4 个导航打不开**：Dashboard.vue 重复 `import` + 引用未定义的 `onKeydown` 函数导致 setup 报错，整个 `<RouterView>` 拿到 null。删了重复 import + 合并两个 onMounted + 删除死代码的 keydown 监听。
2. ✅ **简历去重**：`backend/api/upload.py::_parse_docx` 加全局行级去重 + 表格 cell.text 按 `\n` 拆开（避免「段落 + 表格」同一信息被提取两次）。
3. ✅ **404 错误**：前端 axios 拦截器加 URL 日志，方便定位。
4. ✅ **Dashboard 雷达图维度对不上**：前端 `DIMENSION_WEIGHTS` 用了老维度名（技能匹配/经验匹配...），后端 `multi_agent.py` 实际维度是英文（tech_stack/project_exp...）。改成英文 key + DIMENSION_LABELS 翻译成中文。
5. ✅ **Redis 永久标记不可用**：`cache.py` 改为 `_probe_redis()` 每次新建短连接 + `get_redis_status()` 实时探测，不依赖模块全局标志。

**功能增强**：
6. ✅ **Dashboard 一键全流程卡片**支持上传简历文件（按钮 + 解析自动填入）。
7. ✅ **JD 分析 Prompt** 字段从 7 个扩到 25+（薪资、行业、面试重点、风险信号、卖点等），前端展示重构。
8. ✅ **JD 分析历史侧栏**：复用 getJDAnalyses / deleteJDAnalysis API，点击重载 + 删除。
9. ✅ **简历优化加速**：max_tokens 限制 + 简历长度截断 + Prompt 精简（去 CoT + 去 optimization_suggestions 字段）。Tailor 从 20s 降到 9s。
10. 🚧 **Dashboard 顶部建议条**：基于待投递/面试中/平均匹配分/时间动态生成建议卡片（**这部分还没合到你 commit——你 clear 前需要手动保存**）。

---

## 9. 已知 TODO

1. **Tracker 路由未注册**：`router/index.ts` 缺 `/tracker` 路由，但 `Tracker.vue` 已存在。
2. **Dashboard 建议条代码**：在 Dashboard.vue 里写了 `todayAdvice` computed + 建议卡片模板（顶部欢迎条里），**未 commit**。`git status` 显示 `jobcopilot/frontend/src/views/Dashboard.vue` 是 modified 状态，包含这部分改动。
3. **后端 reload 卡死**：Uvicorn watchfiles 检测到 .py 改动后 reload 可能 hang 住，要 kill 重启。
4. **MySQL 容器**：docker-compose 只配了 MySQL，没配后端；后端是 `python main.py` 直接跑。
5. **向量库缓存**：本地有 `data/chroma_db/`，切环境时可能要删了重建。

---

## 10. 注意事项

### 10.1 Prompt 改完必须重启后端
- 修改 `backend/prompts/*.py` 或 `backend/api/*.py` → `python main.py` 用 **reload 模式**可能 hang
- 安全做��：杀掉 8000 进程 → `python main.py` 重新启
- 前端 HMR 是 OK 的，改 .vue/.ts 自动热更新

### 10.2 Redis 缓存 key
- LLM 结果缓存用 `cache_llm_result(jd_text, resume_text, operation, result)`
- key 是 md5 hash of `jd_text + resume_text + operation`
- 改 Prompt 后要清缓存：`docker exec jobcopilot-redis redis-cli FLUSHDB`

### 10.3 ChromaDB
- 路径：`backend/data/chroma_db/`
- 两个集合：`resume_store`（简历）和 `jd_store`（JD）
- BGE 模型在 `models/bge-small-zh-v1.5/`（本地离线）

### 10.4 数据库切换
- 开发默认 SQLite（`backend/data/jobcopilot.db`）
- 生产用 MySQL：设 `DATABASE_URL=mysql+pymysql://user:pwd@host:port/db`
- 切换数据库后第一次启动会自动 `Base.metadata.create_all` 建表

### 10.5 端口冲突
- 8000：后端
- 5173：前端 Vite
- 3307→3306：MySQL
- 6379：Redis

### 11.6 输出乱码问题
- 当前会话用 PowerShell bash 调 Python，stdout 是 GBK，遇到 UTF-8 中文会显示乱码
- **不影响实际数据**——Python 进程内部用的是 UTF-8，只是终端显示问题
- 如果要在 Python 脚本里正确处理中文，记得 `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`

---

## 12. 关键决策和原因

1. **为什么用 DeepSeek 而不是真的 OpenAI**：`DEEPSEEK_MODEL=glm-5.2` 配 OpenAI 兼容 base URL——是为了省钱/速度，效果差别不大。
2. **为什么 default SQLite**：本地开发零配置就能跑；部署用 MySQL 通过 env 切换。
3. **为什么后端不打包成 Docker**：开发体验，每次 reload 都几秒；Docker 化是 TODO。
4. **为什么 Dashboard 有「智能建议」**：填满空白区 + 给用户行动指引（不是空数据时好看，0 数据时也有引导）。
5. **为什么用 LangGraph 而不是 LangChain Agent**：LangGraph 状态机更可控，LangChain Agent 有 bug（之前 fix 合并的就是 LangChain 那边的问题）。

---

## 13. 常见排错

| 问题 | 排查 |
|---|---|
| 8000 端口被占 | `netstat -ano | grep ":8000"` → Win32 API kill |
| 后端 reload 卡住 | 杀进程重起 |
| ChromaDB 模型找不到 | 检查 `models/bge-small-zh-v1.5/` 目录 |
| 一键全流程报 503 | Redis 没起 → `docker start jobcopilot-redis` |
| LLM 返回乱码 | 检查 `DEEPSEEK_BASE_URL` 和 `DEEPSEEK_API_KEY` |
| 简历上传后内容为空 | 检查 .env 里 `MAX_FILE_SIZE=5MB` |
| 前端热更新挂了 | `Ctrl+Shift+R` 强刷 |

---

## 14. 部署 Checklist

- [ ] 配置生产环境 `.env`（MySQL + Redis + DeepSeek API key）
- [ ] `docker compose up -d` 起 MySQL
- [ ] 起 Redis
- [ ] `python main.py` 起后端
- [ ] `npm run build` 构建前端（产出 `frontend/dist/`）
- [ ] Nginx 代理 `/api/` → 8000，静态资源指向 `frontend/dist/`
- [ ] 配置 HTTPS（certbot）
- [ ] 后端用 gunicorn + uvicorn workers 部署
- [ ] Celery worker：`celery -A tasks worker --loglevel=info --pool=solo`

---

写于 2026-08-28，会话最后一次提交 commit `b53x07heu` 之前。所有本次改动都在 working tree（未 commit）——你 clear 前要么手动 `git stash` / `git add -p` 要么直接放弃。

需要恢复时可以重读这份文档 + 看 git log `c4b01fe..HEAD`，那些 commit 都还在。