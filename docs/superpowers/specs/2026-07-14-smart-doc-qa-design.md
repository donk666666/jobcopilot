# 智能技术文档问答助手 — 设计规格

> 日期：2026-07-14  
> 状态：已确认

## 一、项目概述

构建一个智能客服/知识库助手，以通用技术文档（如某开源框架文档）为知识库，用户通过飞书机器人或网页聊天界面提问，系统通过 RAG 检索 + GLM-5.2 大模型生成专业回答。

**目标人群**：面试官（简历项目展示）。
**核心价值**：一次展示 FastAPI 部署、LangGraph Agent 工作流、RAG 全链路、飞书集成、Docker 容器化五大能力。

---

## 二、整体架构

```
┌──────────────┐     ┌──────────────┐
│  飞书机器人   │     │  网页聊天界面  │
│  (飞书 SDK)   │     │  (HTML/Tailwind)│
└──────┬───────┘     └──────┬───────┘
       │                    │
       └──────────┬─────────┘
                  │ HTTP
                  ▼
┌─────────────────────────────────────┐
│          FastAPI 服务层              │
│  POST /api/chat      对话接口       │
│  POST /api/knowledge/upload 文档上传 │
│  POST /api/knowledge/crawl  触发抓取 │
│  GET  /api/knowledge/stats  统计    │
│  POST /feishu/callback 飞书回调     │
│  GET  /health          健康检查     │
└──────────────────┬──────────────────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
┌───────────┐ ┌─────────┐ ┌──────────┐
│  Agent    │ │  RAG    │ │ 爬虫模块  │
│ 工作流引擎 │ │ 检索模块 │ │  RSS抓取  │
│(LangGraph)│ │(ChromaDB)│ │(feedparser)│
└─────┬─────┘ └────┬────┘ └────┬─────┘
      │            │           │
      └────────────┼───────────┘
                   ▼
             ┌──────────┐
             │  GLM-5.2 │
             │(中转站API)│
             └──────────┘
```

---

## 三、技术栈

| 层级 | 选型 | 理由 |
|------|------|------|
| Web 框架 | FastAPI | 异步、自带文档、JD 明确提到 |
| Agent 框架 | LangGraph | 状态流转+条件分支 |
| LLM 调用 | openai 库 (ChatOpenAI) | OpenAI 兼容格式，base_url 指向中转站，model=glm-5.2 |
| 向量数据库 | ChromaDB | 嵌入式、轻量、2C4G 友好 |
| 文档处理 | LangChain Document Loaders | PDF/MD/TXT 加载 + 自动分片 |
| Embedding | sentence-transformers + BAAI/bge-small-zh-v1.5 | 本地 CPU 推理，~100MB，中文效果好 |
| 飞书 SDK | lark-oapi | 官方 Python SDK |
| 前端 | 单页面 HTML + Tailwind（CDN） | 无需构建 |
| 爬虫 | feedparser + httpx | RSS 抓取技术博客 |
| 容器化 | Docker + Docker Compose | 单容器部署 |
| 日志 | logging + RotatingFileHandler | 文件轮转，便于排查 |
| 部署 | Nginx 反向代理 + Let's Encrypt SSL | 免费、国内可操作 |

---

## 四、Agent 工作流

LangGraph StateGraph，5 个节点 + 3 个条件分支：

```
用户消息 → [意图识别] → 非技术问题 → 拒绝引导
              ↓ 技术问题
          [问题改写]
              ↓
          [混合检索] (向量 + 关键词)
              ↓
          [相关性判断] → 全不相关 → "知识库未收录"
              ↓ 有相关内容
          [生成回答]
              ↓
          [反问澄清] → 不够清晰 → 追问
              ↓ 够清晰
           返回用户
```

**状态定义**：
- `messages`: 对话历史
- `intent`: 意图分类结果
- `rewritten_query`: 改写后检索语句
- `retrieved_docs`: 检索结果列表
- `final_answer`: 最终回复
- `need_clarify`: 是否需要反问

---

## 五、目录结构

```
project/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置（环境变量 + .env）
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── graph.py         # LangGraph 状态图
│   │   └── nodes.py         # 各节点实现
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── loader.py        # 文档加载+切片
│   │   ├── retriever.py     # 混合检索
│   │   └── vectorstore.py   # ChromaDB 封装
│   ├── crawler/
│   │   ├── __init__.py
│   │   └── feed.py          # RSS 抓取+入库
│   ├── feishu/
│   │   ├── __init__.py
│   │   └── bot.py           # 飞书消息处理
│   └── web/
│       └── static/
│           └── index.html   # 网页聊天界面
├── data/                    # ChromaDB + 原始文档
├── logs/                    # 日志文件
├── .env.example             # 环境变量模板
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 六、API 接口

| 方法 | 路径 | 请求体/参数 | 响应 |
|------|------|-----------|------|
| POST | `/api/chat` | `{"message":"...","session_id":"..."}` | `{"reply":"...","sources":[...],"session_id":"..."}` |
| POST | `/api/knowledge/upload` | `multipart/form-data file` | `{"status":"ok","chunks":42}` |
| POST | `/api/knowledge/crawl` | `{}` | `{"status":"ok","new_docs":3}` |
| GET | `/api/knowledge/stats` | — | `{"doc_count":12,"chunk_count":450}` |
| POST | `/feishu/callback` | 飞书事件 JSON | 飞书卡片消息 JSON |
| GET | `/health` | — | `{"status":"healthy","version":"1.0.0"}` |

---

## 七、Docker 部署

**Dockerfile**：
- 基础镜像 `python:3.11-slim`
- 安装系统依赖，`pip install -r requirements.txt`
- 复制源码，暴露 8000 端口
- CMD: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

**docker-compose.yml**：
- 单服务，挂载 `./data:/app/data`、`./logs:/app/logs`
- 环境变量从 `.env` 读取
- `restart: unless-stopped`

**部署流程**：
1. 云服务器安装 Docker + Docker Compose
2. 上传项目代码
3. `docker compose up -d`
4. 安装 Nginx，配置反向代理到 `127.0.0.1:8000`
5. certbot 签发 Let's Encrypt SSL 证书
6. 飞书开放平台配置回调地址为 `https://域名/feishu/callback`

---

## 八、配置项 (.env)

```
# LLM
LLM_BASE_URL=https://cloud.hongqiye.com/v1
LLM_API_KEY=sk-xxx
LLM_MODEL=glm-5.2

# Embedding (本地)
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5

# 飞书
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_VERIFY_TOKEN=
FEISHU_ENCRYPT_KEY=

# 爬虫
CRAWL_SCHEDULE_HOURS=6
RSS_FEEDS=https://blog.example.com/feed.xml,https://another.com/rss
```

---

## 九、边界约束

- 单用户并发：面试演示场景，不需要处理高并发
- 知识库初始规模：20-50 篇文档，切片约 500-2000
- 响应时间：Agent 完整链路目标 <5 秒（含 LLM 调用）
- 支持格式：PDF、Markdown、TXT
- 浏览器兼容：Chrome/Firefox/Edge 最新两版
