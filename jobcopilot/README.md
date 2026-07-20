# JobCopilot — AI 求职助手

基于 **LangChain Agent + RAG + Prompt Engineering** 的全栈智能求职平台，覆盖 JD 解析、简历匹配度分析、简历定向优化、求职信生成、投递管理全流程。

## 功能模块

| 模块 | 说明 |
|------|------|
| **JD 智能分析** | Few-shot Prompting + JSON Schema 约束输出，结构化提取职位名称、技能要求、经验年限、学历等 |
| **简历匹配度评估** | RAG 检索增强 + Chain-of-Thought 推理，输出匹配度评分、雷达图、匹配点/差距点 |
| **简历定向优化** | 基于匹配结果自动改写简历，支持改动注释开关 |
| **求职信生成** | 链式 Prompt（公司分析 → 经历匹配 → 生成），支持 3 种风格 |
| **投递管理** | 全流程状态追踪（待投递 → 已投递 → 初筛中 → 面试中 → Offer） |
| **Agent 模式** | ReAct Agent 自动编排多步骤任务（Thought → Action → Observation 循环） |

## 技术栈

| 层级 | 选型 |
|------|------|
| 前端 | Vue 3 + TypeScript + Element Plus + Pinia + Vite |
| 后端 | FastAPI + SQLAlchemy + Pydantic |
| AI 框架 | LangChain + ReAct Agent |
| 向量库 | ChromaDB + BGE-small-zh-v1.5（512d） |
| 业务数据库 | MySQL 8.0（Docker） |
| LLM | DeepSeek API（兼容 OpenAI 接口，支持中转站） |
| Prompt 策略 | Few-shot / Chain-of-Thought / Prompt Chaining |

## 项目架构

```
用户 → Vue 3 前端 (5173)
         │
         ▼
    FastAPI 后端 (8000)
         │
    ┌────┼────────────┐
    ▼    ▼            ▼
  MySQL  ChromaDB   DeepSeek API
(业务数据) (向量检索)  (LLM 推理)
```

### Agent 工作流

```
用户提问 → ReAct Agent
              │
   ┌──────────┼──────────┐
   ▼          ▼          ▼          ▼
JD分析器   简历匹配器  简历改写器  求职信生成器
   │          │          │          │
   └──────────┴──────────┴──────────┘
              │
              ▼
         RAG 检索增强
    (ChromaDB 双集合：简历库 + JD库)
```

## 项目结构

```
jobcopilot/
├── backend/
│   ├── main.py                # FastAPI 入口
│   ├── config.py              # 配置管理（环境变量加载）
│   ├── database.py            # SQLAlchemy ORM 模型 + 会话管理
│   ├── requirements.txt       # Python 依赖
│   ├── agent/
│   │   ├── core.py            # ReAct Agent 引擎 + 工具注册
│   │   └── tools.py           # 4 个自定义工具（JD分析/匹配/改写/求职信）
│   ├── api/
│   │   ├── jd.py              # JD 分析 API
│   │   ├── resume.py          # 简历匹配 + 优化 API
│   │   ├── cover_letter.py    # 求职信生成 API
│   │   └── tracker.py         # 投递管理 CRUD API
│   ├── prompts/               # Prompt 模板库
│   │   ├── jd_analyzer.py     # Few-shot JD 分析 Prompt
│   │   ├── resume_tailor.py   # CoT 匹配 + 简历改写 Prompt
│   │   └── cover_letter.py    # 链式 Prompt 求职信生成
│   └── rag/
│       └── vector_store.py    # ChromaDB 双集合向量库
├── frontend/
│   ├── src/
│   │   ├── views/             # 5 个页面（Dashboard/JD分析/简历优化/求职信/投递管理）
│   │   ├── components/        # 通用组件（RadarChart/ProgressBar/EmptyState 等）
│   │   ├── api/index.ts       # Axios 接口层
│   │   └── router/index.ts    # Vue Router 路由
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml         # MySQL 容器配置
├── .env.example               # 环境变量模板（不含真实密钥）
└── README.md
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- Docker Desktop

### 1. 启动 MySQL

```bash
docker-compose up -d
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 DeepSeek API Key 和 MySQL 密码
```

### 3. 启动后端

```bash
cd backend
pip install -r requirements.txt
python main.py
# → http://localhost:8000
# API 文档 → http://localhost:8000/docs
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

## 核心设计亮点

- **双集合向量检索**：简历和 JD 分库存储，避免语义混淆，提升匹配精度
- **优雅降级**：Embedding 模型加载失败时自动降级为纯 LLM 模式，不阻塞核心功能
- **Prompt 工程**：Few-shot 示例 + JSON Schema 约束输出一致性，CoT 推理提升匹配分析质量
- **安全设计**：API Key 通过 `.env` 环境变量管理，不进入版本控制
