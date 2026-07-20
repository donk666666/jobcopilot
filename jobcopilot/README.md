# JobCopilot - AI求职助手

全栈AI求职助手系统，利用 LangChain Agent、RAG 和 Prompt 工程技术，帮助求职者智能管理求职全流程。

## 功能

- **JD智能分析** — Few-shot Prompting 结构化提取职位信息
- **简历优化** — RAG检索增强 + Chain-of-Thought匹配度分析
- **求职信生成** — 链式Prompt（公司分析→经历匹配→生成），支持3种风格
- **投递管理** — SQLite持久化，全流程状态追踪
- **Agent模式** — ReAct Agent自动规划执行多步骤任务

## 技术栈

| 层级 | 选型 |
|------|------|
| 前端 | Vue 3 + TypeScript + Element Plus + Pinia |
| 后端 | FastAPI + SQLAlchemy |
| AI框架 | LangChain + ReAct Agent |
| 向量库 | ChromaDB + BGE中文嵌入模型 |
| 数据库 | SQLite |
| LLM | DeepSeek API |

## 快速启动

### 环境要求
- Python 3.10+
- Node.js 18+

### 1. 安装后端依赖
```bash
cd backend
pip install -r requirements.txt --break-system-packages
```

### 2. 启动后端
```bash
cd backend
python main.py
```
后端运行在 http://localhost:8000

### 3. 安装前端依赖
```bash
cd frontend
npm install
```

### 4. 启动前端
```bash
cd frontend
npm run dev
```
前端运行在 http://localhost:5173

### 5. 打开浏览器
访问 http://localhost:5173 即可使用
