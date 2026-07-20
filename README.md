# JobCopilot

这是我的 AI 求职助手项目仓库，核心项目代码位于 [jobcopilot/](jobcopilot/) 目录。

## 项目简介

JobCopilot 是一个基于 **LangChain Agent + RAG + Prompt Engineering** 的智能求职平台，覆盖：

- JD 智能分析
- 简历匹配度评估
- 简历定向优化
- 求职信生成
- 投递流程管理

## 在线查看

- 项目主说明文档：[`jobcopilot/README.md`](jobcopilot/README.md)
- 核心代码目录：[`jobcopilot/`](jobcopilot/)

## 技术栈

- 前端：Vue 3 + TypeScript + Element Plus + Vite
- 后端：FastAPI + SQLAlchemy + Pydantic
- 向量检索：ChromaDB + BGE-small-zh-v1.5
- 数据库：MySQL 8.0
- 大模型调用：DeepSeek API（兼容 OpenAI 接口）

## 快速说明

如果你是面试官或访客，建议直接进入 [`jobcopilot/`](jobcopilot/) 查看完整项目说明、架构设计和启动方式。

> 完整 README 在子目录中，是因为这个仓库里还保留了我其它实验脚本与辅助文件。
