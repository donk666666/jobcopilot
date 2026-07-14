# 知识库文档入库方案设计

**日期**: 2026-07-14  
**主题**: 为智能文档问答助手配置 RSS 订阅源和核心参考文档

## 目标

为 RAG 知识库配置实用内容，覆盖 FastAPI、LangChain、ChromaDB、Prompt Engineering、Docker、Linux 六大技术栈。

## 方案

### 一、RSS 订阅源（自动积累）

配置三个中文技术 RSS 源，每 6 小时自动抓取：

| RSS 地址 | 内容方向 | 更新频率 |
|----------|----------|----------|
| `https://www.ruanyifeng.com/blog/atom.xml` | 综合技术 | 周更 |
| `https://tech.meituan.com/feed/` | 后端/AI 工程 | 月更 |
| `https://www.infoq.cn/feed` | 架构/AI/运维 | 日更 |

在 `.env` 中配置 `RSS_FEEDS` 即可生效。

### 二、核心参考文档（手动入库）

创建 5 份 Markdown 速查文档，放到 `data/docs/` 目录：

| 文件 | 内容 | 预估大小 |
|------|------|----------|
| `fastapi-quickref.md` | 路由、依赖注入、中间件、异常处理常用写法 | ~5KB |
| `langchain-core.md` | Chain/Agent/Tool 核心概念和常用模式 | ~5KB |
| `prompt-engineering.md` | 常用 Prompt 模板、技巧、角色设定 | ~3KB |
| `docker-cheatsheet.md` | 常用命令、Dockerfile 最佳实践、compose 写法 | ~4KB |
| `linux-cheatsheet.md` | 常用命令、systemd、日志查看、权限管理 | ~3KB |

文档格式：Markdown，用标题分层，代码块用语法高亮标记。

### 三、技术要点

- RSS 抓取后自动保存为 `.md` 文件，MD5 去重，避免重复入库
- 核心文档支持手动更新后重新 `index_directory`
- 文档分词使用中文友好的分隔符：`\n\n`、`\n`、`。`、`，`
- 混合检索：向量相似度（权重 0.6）+ 关键词匹配（权重 0.4）
