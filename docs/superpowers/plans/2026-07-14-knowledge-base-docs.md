# 知识库文档入库 实现计划

> **For agentic workers:** 使用 subagent-driven-development 或 executing-plans 按任务逐个执行。步骤使用 checkbox (`- [ ]`) 语法追踪。

**目标:** 为 RAG 知识库配置 3 个中文 RSS 源和 5 份核心技术速查文档

**架构:** 纯数据内容任务，不涉及代码改动。RSS 配置写 `.env`；Markdown 文档放 `data/docs/` 目录，由现有 `index_directory` 接口批量导入向量库

**技术栈:** 无新依赖，使用现有 feedparser、langchain TextLoader、ChromaDB

## 全局约束

- 所有文档使用 Markdown 格式，UTF-8 编码
- RSS 源必须国内可稳定访问
- 文档导入后需验证在向量库中可检索

---

### Task 1: 配置 RSS 订阅源

**文件:**
- 修改: `.env:13`

**接口:**
- 无依赖
- 产出: `.env` 中 `RSS_FEEDS` 为 3 个 RSS 地址（逗号分隔）

- [ ] **Step 1: 修改 .env 中的 RSS_FEEDS**

将 `RSS_FEEDS=https://blog.example.com/feed.xml` 改为：

```
RSS_FEEDS=https://www.ruanyifeng.com/blog/atom.xml,https://tech.meituan.com/feed/,https://www.infoq.cn/feed
```

- [ ] **Step 2: 重启 Docker 容器使配置生效**

```bash
docker compose up -d --build
```

容器重建后验证：
```bash
docker logs smart-doc-qa --tail 10
```
应看到 "爬虫定时器已启动，间隔 6 小时"

- [ ] **Step 3: 手动触发一次 RSS 抓取验证**

```bash
curl -X POST http://localhost:8000/api/knowledge/crawl
```

返回应包含 `new_docs` 字段。

- [ ] **Step 4: Commit**

```bash
git add .env
git commit -m "配置中文技术 RSS 订阅源（阮一峰、美团技术、InfoQ）"
```

---

### Task 2: 编写核心速查文档

**文件:**
- 创建: `data/docs/fastapi-quickref.md`
- 创建: `data/docs/langchain-core.md`
- 创建: `data/docs/prompt-engineering.md`
- 创建: `data/docs/docker-cheatsheet.md`
- 创建: `data/docs/linux-cheatsheet.md`

**接口:**
- 无依赖
- 产出: 5 个 UTF-8 Markdown 文件，后续由 `index_directory('./data/docs')` 导入

- [ ] **Step 1: 创建 fastapi-quickref.md** — 路由、依赖注入、Pydantic 模型、中间件、异常处理、后台任务

- [ ] **Step 2: 创建 langchain-core.md** — Chain、Agent、Tool、Document Loader、Text Splitter、LCEL、Memory

- [ ] **Step 3: 创建 prompt-engineering.md** — 角色设定、Few-shot、Chain of Thought、RAG 模板、结构化输出、System Prompt 原则

- [ ] **Step 4: 创建 docker-cheatsheet.md** — 镜像/容器管理、日志调试、compose、Dockerfile 最佳实践

- [ ] **Step 5: 创建 linux-cheatsheet.md** — 文件操作、进程管理、权限、systemd、网络、压缩传输

- [ ] **Step 6: Commit**

```bash
git add data/docs/
git commit -m "添加五份核心技术速查文档（FastAPI/LangChain/Prompt/Docker/Linux）"
```

---

### Task 3: 批量导入文档并验证检索

**文件:**
- 无修改

**接口:**
- 消费: `data/docs/` 下的 `.md` 文件，`index_directory()` 函数
- 产出: 向量库中可检索到的文档 chunks

- [ ] **Step 1: 批量导入所有文档到向量库**

```bash
docker exec smart-doc-qa python -c "
from app.rag.loader import index_directory
total = index_directory('/app/data/docs')
print(f'导入完成: {total} chunks')
"
```

预期输出：`导入完成: N chunks`（N > 5）

- [ ] **Step 2: 验证向量库状态**

```bash
docker exec smart-doc-qa python -c "
from app.rag.vectorstore import get_or_create_collection
col = get_or_create_collection()
print(f'向量库总 chunks: {col.count()}')
"
```

- [ ] **Step 3: 验证 FastAPI 文档检索 — hybrid_search("FastAPI 中间件怎么写")，应命中 fastapi-quickref.md，得分 >= 0.5**

- [ ] **Step 4: 验证 Docker 文档检索 — hybrid_search("Docker 构建镜像的命令")，应命中 docker-cheatsheet.md**

- [ ] **Step 5: 验证跨文档检索 — hybrid_search("怎么写 RAG 的 prompt 模板")，应命中 prompt-engineering.md**

- [ ] **Step 6: Commit**

```bash
git status  # 应为干净状态
```

---

### Task 4: 端到端 RAG 问答验证

**文件:**
- 无修改

**接口:**
- 消费: Agent 完整流程（classify → rewrite → retrieve → judge → generate）

- [ ] **Step 1: 验证 RAG 问答 — run_agent("FastAPI 怎么定义路由？")，应返回含代码示例的答案，来源包含 fastapi-quickref.md**

- [ ] **Step 2: 验证跨文档问答 — run_agent("Docker 和 FastAPI 怎么配合使用？")，应从两份文档中检索并综合回答**

- [ ] **Step 3: 验证 Prompt 相关 — run_agent("写 RAG 的 prompt 模板应该注意什么？")，应引用 prompt-engineering.md 中的模板**

- [ ] **Step 4: 验证无关问题拒绝 — run_agent("今天天气怎么样？")，系统应回复知识库中无相关信息**

- [ ] **Step 5: Commit**

```bash
git status
```

---

### Task 5: 清理测试文档

**文件:**
- 归档: `data/docs/test.md`

**接口:**
- 无

- [ ] **Step 1: 归档测试文件 — `mv data/docs/test.md data/docs/test.md.bak`**

- [ ] **Step 2: Commit**

```bash
git add data/docs/.
git commit -m "清理测试文档，归档 test.md"
```
