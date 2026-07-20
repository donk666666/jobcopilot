# JobCopilot - AI求职助手 设计文档

## 项目概述

JobCopilot 是一个全栈 AI 求职助手系统，利用 LangChain Agent、RAG（检索增强生成）和 Prompt 工程技术，帮助求职者智能分析职位JD、优化简历匹配度、生成定制化求职信、管理投递全流程。

## 技术栈

| 层级 | 选型 |
|------|------|
| 前端 | Vue 3 + TypeScript + Vite + Element Plus + Pinia |
| 后端 | FastAPI + SQLAlchemy + LangChain |
| 向量数据库 | ChromaDB |
| 结构化数据库 | SQLite |
| LLM | DeepSeek API（通过 hongqiye 中转） |

## 系统架构

采用前后端分离架构，前端通过 RESTful API 与后端通信。

### 核心模块

1. **Prompt模板模块** — 使用 Few-shot Prompting、Chain-of-Thought、JSON Schema 等 Prompt 工程技术
2. **RAG向量知识库** — ChromaDB 存储简历和JD向量，检索增强生成
3. **Agent引擎** — LangChain ReAct Agent，包含4个专业工具
4. **FastAPI后端** — REST API + SQLite数据持久化
5. **Vue 3前端** — 五个核心页面

### API设计

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/jd/analyze` | POST | JD结构化分析 |
| `/api/resume/match` | POST | 简历匹配度评分 |
| `/api/resume/tailor` | POST | 简历定向优化 |
| `/api/cover-letter/generate` | POST | 求职信生成 |
| `/api/tracker/` | CRUD | 投递进度管理 |
| `/api/agent/run` | POST | Agent全流程执行 |
