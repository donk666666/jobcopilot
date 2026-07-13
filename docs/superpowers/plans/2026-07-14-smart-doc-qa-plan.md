# 智能技术文档问答助手 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个智能技术文档问答助手，通过 RAG + LangGraph Agent + GLM-5.2 实现从文档检索到生成的完整问答链路，支持飞书机器人和网页双入口，Docker 容器化部署。

**Architecture:** FastAPI 作为统一入口层，LangGraph 编排 Agent 工作流（意图识别→改写→检索→生成→澄清），ChromaDB 做向量存储，sentence-transformers 做本地 Embedding，lark-oapi 对接飞书，单页面 HTML 做网页聊天界面。

**Tech Stack:** Python 3.11, FastAPI, LangGraph, LangChain, ChromaDB, sentence-transformers, openai (ChatOpenAI 接入中转站), lark-oapi, feedparser, Docker, Tailwind CSS (CDN)

## Global Constraints

- Python 3.11+
- 所有 LLM 调用通过 openai 库，base_url=https://cloud.hongqiye.com/v1，model=glm-5.2
- Embedding 使用本地 sentence-transformers，模型 BAAI/bge-small-zh-v1.5
- ChromaDB 持久化目录为 ./data/chroma
- 日志输出到 ./logs/app.log，使用 RotatingFileHandler
- 容器化部署，单 Docker 镜像，8000 端口
- 中文注释、中文回答

---

### Task 1: 项目骨架搭建

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `app/__init__.py`
- Create: `app/config.py`

**Interfaces:**
- Produces: `app.config.Settings` — Pydantic BaseSettings，从 .env 读取所有配置项，供所有后续 task 使用

- [ ] **Step 1: 创建 requirements.txt**

```txt
fastapi==0.115.6
uvicorn[standard]==0.34.0
langchain==0.3.18
langgraph==0.3.5
langchain-openai==0.3.7
chromadb==0.6.3
sentence-transformers==3.4.1
pypdf==5.1.0
unstructured==0.17.2
lark-oapi==1.4.7
feedparser==6.0.11
httpx==0.28.1
python-multipart==0.0.20
pydantic-settings==2.7.1
apscheduler==3.11.0
```

- [ ] **Step 2: 创建 .env.example**

```
LLM_BASE_URL=https://cloud.hongqiye.com/v1
LLM_API_KEY=sk-your-api-key
LLM_MODEL=glm-5.2

EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5

FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_VERIFY_TOKEN=
FEISHU_ENCRYPT_KEY=

CRAWL_SCHEDULE_HOURS=6
RSS_FEEDS=https://blog.example.com/feed.xml
```

- [ ] **Step 3: 创建 app/__init__.py**（空文件）

```python
```

- [ ] **Step 4: 创建 app/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    llm_base_url: str = "https://cloud.hongqiye.com/v1"
    llm_api_key: str = ""
    llm_model: str = "glm-5.2"

    # Embedding
    embedding_model: str = "BAAI/bge-small-zh-v1.5"

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma"

    # 飞书
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_verify_token: str = ""
    feishu_encrypt_key: str = ""

    # 爬虫
    crawl_schedule_hours: int = 6
    rss_feeds: str = ""

    # 日志
    log_dir: str = "./logs"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

- [ ] **Step 5: 验证**

```bash
cd project && python -c "from app.config import settings; print(settings.llm_model)"
```
Expected: `glm-5.2`

- [ ] **Step 6: Commit**

---

### Task 2: ChromaDB 向量存储封装

**Files:**
- Create: `app/rag/__init__.py`
- Create: `app/rag/vectorstore.py`

**Interfaces:**
- Consumes: `app.config.settings` (chroma_persist_dir, embedding_model)
- Produces:
  - `get_embedding_model()` → `SentenceTransformer`
  - `get_vectorstore() → chromadb.PersistentClient`
  - `get_or_create_collection(name: str) → chromadb.Collection`

- [ ] **Step 1: 创建 app/rag/__init__.py**（空文件）

- [ ] **Step 2: 创建 app/rag/vectorstore.py**

```python
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from app.config import settings

_embedding_model = None
_vectorstore = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(settings.embedding_model)
    return _embedding_model


def get_vectorstore() -> chromadb.PersistentClient:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _vectorstore


def get_or_create_collection(name: str = "tech_docs") -> chromadb.Collection:
    client = get_vectorstore()
    model = get_embedding_model()

    def embedding_fn(texts: list[str]) -> list[list[float]]:
        return model.encode(texts).tolist()

    try:
        collection = client.get_collection(name=name, embedding_function=embedding_fn)
    except Exception:
        collection = client.create_collection(name=name, embedding_function=embedding_fn)

    return collection
```

- [ ] **Step 3: 验证 ChromaDB 能正常启动**

```bash
cd project && python -c "
from app.rag.vectorstore import get_or_create_collection
col = get_or_create_collection('test')
col.add(documents=['测试文本'], ids=['1'])
r = col.query(query_texts=['测试'], n_results=1)
print(r['documents'])
col.delete(ids=['1'])
print('OK')
"
```

- [ ] **Step 4: Commit**

---

### Task 3: 文档加载与切片

**Files:**
- Create: `app/rag/loader.py`

**Interfaces:**
- Consumes: `app.config.settings`，`app.rag.vectorstore.get_or_create_collection`
- Produces:
  - `load_and_split(file_path: str) → list[langchain.schema.Document]`
  - `index_document(file_path: str) → int` — 返回切片数
  - `index_directory(dir_path: str) → int` — 返回总切片数

- [ ] **Step 1: 创建 app/rag/loader.py**

```python
import os
import uuid
from pathlib import Path

from langchain_community.document_loaders import TextLoader, PyPDFLoader, UnstructuredMarkdownLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.rag.vectorstore import get_or_create_collection


def _get_loader(file_path: str):
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return PyPDFLoader(file_path)
    elif ext in (".md", ".markdown"):
        return UnstructuredMarkdownLoader(file_path)
    else:
        return TextLoader(file_path, encoding="utf-8")


def load_and_split(file_path: str, chunk_size: int = 800, chunk_overlap: int = 100):
    loader = _get_loader(file_path)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "，", " ", ""],
    )
    return splitter.split_documents(docs)


def index_document(file_path: str) -> int:
    chunks = load_and_split(file_path)
    if not chunks:
        return 0

    collection = get_or_create_collection()
    source = Path(file_path).name
    
    for i, chunk in enumerate(chunks):
        existing = collection.get(ids=[f"{source}_{i}"])
        if existing["ids"]:
            collection.delete(ids=[f"{source}_{i}"])

    ids = [f"{source}_{i}" for i in range(len(chunks))]
    texts = [chunk.page_content for chunk in chunks]
    metadatas = [{"source": source, "chunk_index": i} for i in range(len(chunks))]

    collection.add(documents=texts, metadatas=metadatas, ids=ids)
    return len(chunks)


def index_directory(dir_path: str) -> int:
    total = 0
    for root, _, files in os.walk(dir_path):
        for f in files:
            if f.startswith("."):
                continue
            file_path = os.path.join(root, f)
            try:
                n = index_document(file_path)
                total += n
            except Exception:
                pass
    return total
```

- [ ] **Step 2: 创建测试用的 Markdown 文件验证加载**

```bash
cd project && mkdir -p data/docs && echo "# 测试文档\n\n这是一个测试文档的内容。\n\n## 第二节\n\n更多测试文本。" > data/docs/test.md
python -c "
from app.rag.loader import load_and_split, index_document
chunks = load_and_split('data/docs/test.md')
print(f'切片数: {len(chunks)}')
n = index_document('data/docs/test.md')
print(f'入库切片数: {n}')
print('OK')
"
```

- [ ] **Step 3: Commit**

---

### Task 4: 混合检索器

**Files:**
- Create: `app/rag/retriever.py`

**Interfaces:**
- Consumes: `app.rag.vectorstore.get_or_create_collection, get_embedding_model`
- Produces:
  - `hybrid_search(query: str, top_k: int = 5) → list[dict]`
  - 每条结果格式：`{"content": str, "source": str, "score": float}`

- [ ] **Step 1: 创建 app/rag/retriever.py**

```python
from app.rag.vectorstore import get_or_create_collection, get_embedding_model


def _vector_search(query: str, top_k: int = 10) -> list[dict]:
    """向量相似度检索"""
    collection = get_or_create_collection()
    results = collection.query(query_texts=[query], n_results=top_k)
    docs = []
    if results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            distance = results["distances"][0][i] if results.get("distances") else 0
            docs.append({
                "content": doc,
                "source": metadata.get("source", "unknown"),
                "score": max(0, 1 - distance) if distance else 1.0,
            })
    return docs


def _keyword_search(query: str, top_k: int = 10) -> list[dict]:
    """关键词检索：对 query 分词后，用 ChromaDB 的 where_document 做包含匹配"""
    collection = get_or_create_collection()
    keywords = query.replace("？", "").replace("?", "").replace("，", " ").replace(",", " ").split()
    keywords = [kw.strip() for kw in keywords if len(kw.strip()) >= 2]
    
    if not keywords:
        return []

    all_docs: dict[str, dict] = {}
    for kw in keywords:
        try:
            results = collection.query(query_texts=[kw], n_results=top_k)
        except Exception:
            continue
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                doc_id = results["ids"][0][i]
                if doc_id not in all_docs:
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    all_docs[doc_id] = {
                        "content": doc,
                        "source": metadata.get("source", "unknown"),
                        "score": 1,
                        "hits": 0,
                    }
                all_docs[doc_id]["hits"] += 1
    
    results_list = sorted(all_docs.values(), key=lambda d: d["hits"], reverse=True)
    for d in results_list:
        d["score"] = min(d["hits"] / len(keywords), 1.0)
        del d["hits"]
    
    return results_list


def hybrid_search(query: str, top_k: int = 5) -> list[dict]:
    """混合检索：向量检索 + 关键词检索，合并去重排序"""
    vec_results = _vector_search(query, top_k * 2)
    kw_results = _keyword_search(query, top_k * 2)

    merged: dict[str, dict] = {}
    for r in vec_results:
        key = r["content"][:100]
        merged[key] = r
        merged[key]["_vec_score"] = r["score"]

    for r in kw_results:
        key = r["content"][:100]
        if key in merged:
            merged[key]["score"] = merged[key].get("_vec_score", 0) * 0.6 + r["score"] * 0.4
        else:
            r["score"] = r["score"] * 0.3
            merged[key] = r

    for r in merged.values():
        r.pop("_vec_score", None)

    sorted_results = sorted(merged.values(), key=lambda r: r["score"], reverse=True)
    return sorted_results[:top_k]
```

- [ ] **Step 2: 验证检索功能**

```bash
cd project && python -c "
from app.rag.retriever import hybrid_search
# 依赖已有入库的测试文档
results = hybrid_search('测试文档', top_k=3)
print(f'检索到 {len(results)} 条结果')
for r in results:
    print(f'  [{r[\"score\"]:.3f}] {r[\"source\"]}: {r[\"content\"][:50]}...')
print('OK')
"
```

- [ ] **Step 3: Commit**

---

### Task 5: LangGraph Agent 节点

**Files:**
- Create: `app/agent/__init__.py`
- Create: `app/agent/nodes.py`

**Interfaces:**
- Consumes: `app.config.settings`, `app.rag.retriever.hybrid_search`, `langchain_openai.ChatOpenAI`
- Produces:
  - `create_llm() → ChatOpenAI`
  - `classify_intent(state: AgentState) → dict` — 意图识别节点
  - `rewrite_query(state: AgentState) → dict` — 问题改写节点
  - `retrieve(state: AgentState) → dict` — 检索节点
  - `judge_relevance(state: AgentState) → dict` — 相关性判断节点
  - `generate(state: AgentState) → dict` — 生成回答节点
  - `clarify(state: AgentState) → dict` — 反问澄清节点

- [ ] **Step 1: 创建 app/agent/__init__.py**

```python
from typing import TypedDict, Annotated


class RetrievedDoc(TypedDict):
    content: str
    source: str
    score: float


class AgentState(TypedDict):
    messages: Annotated[list, "对话历史"]
    intent: str
    rewritten_query: str
    retrieved_docs: list[RetrievedDoc]
    final_answer: str
    need_clarify: bool
```

- [ ] **Step 2: 创建 app/agent/nodes.py**

```python
import json
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from app.config import settings
from app.rag.retriever import hybrid_search
from app.agent import AgentState


def create_llm(temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=temperature,
    )


def _get_last_user_message(state: AgentState) -> str:
    for msg in reversed(state["messages"]):
        if isinstance(msg, dict) and msg.get("role") == "user":
            return msg["content"]
        elif hasattr(msg, "type") and msg.type == "human":
            return msg.content
    return ""


def classify_intent(state: AgentState) -> dict:
    """判断用户意图：是技术问题还是非技术闲聊"""
    user_msg = _get_last_user_message(state)
    llm = create_llm(temperature=0.0)

    system = SystemMessage(content="""你是一个意图分类器。判断用户消息是否属于技术问题。
技术问题包括：编程、框架、工具、计算机科学、软件开发、DevOps、算法、数据库等。
非技术问题包括：闲聊、天气、新闻、娱乐等。

请只回复 JSON：{"is_tech": true/false}""")
    
    resp = llm.invoke([system, HumanMessage(content=user_msg)])
    try:
        result = json.loads(resp.content)
    except Exception:
        result = {"is_tech": True}

    return {"intent": "tech" if result.get("is_tech") else "non_tech"}


def rewrite_query(state: AgentState) -> dict:
    """将上下文相关的问题改写为独立检索语句"""
    user_msg = _get_last_user_message(state)
    
    # 收集最近几轮对话作为上下文
    recent_msgs = state["messages"][-6:]
    context = "\n".join(
        f"{m.get('role', 'unknown')}: {m.get('content', '')[:200]}"
        for m in recent_msgs if isinstance(m, dict)
    )

    llm = create_llm(temperature=0.1)
    system = SystemMessage(content=f"""你是一个查询改写器。将用户问题结合对话上下文，改写为一个适合向量检索的独立查询语句。
规则：
- 如果问题是追问（如"那怎么用"），请补全它指代的内容
- 保持技术术语的准确性
- 只输出改写后的查询语句，不要加额外说明

对话上下文：
{context}""")
    
    resp = llm.invoke([system, HumanMessage(content=user_msg)])
    rewritten = resp.content.strip().strip('"').strip("'")
    return {"rewritten_query": rewritten}


def retrieve(state: AgentState) -> dict:
    """执行混合检索"""
    query = state.get("rewritten_query") or _get_last_user_message(state)
    docs = hybrid_search(query, top_k=5)
    return {"retrieved_docs": docs}


def judge_relevance(state: AgentState) -> dict:
    """判断检索结果与问题的相关性"""
    query = state.get("rewritten_query") or _get_last_user_message(state)
    docs = state.get("retrieved_docs", [])

    if not docs:
        return {"need_clarify": False, "final_answer": "抱歉，知识库中未找到相关内容。"}

    # 最高分高于阈值则视为相关
    max_score = docs[0]["score"]
    is_relevant = max_score >= 0.3

    if not is_relevant:
        return {"need_clarify": False, "final_answer": "抱歉，知识库中暂无与您问题相关的文档。请尝试换个方式提问，或上传相关文档后再试。"}

    return {"need_clarify": False, "final_answer": ""}


def generate(state: AgentState) -> dict:
    """基于检索结果生成回答"""
    query = state.get("rewritten_query") or _get_last_user_message(state)
    docs = state.get("retrieved_docs", [])

    contexts = "\n---\n".join(
        f"[来源: {d['source']}]\n{d['content']}"
        for d in docs[:3]
    )

    llm = create_llm(temperature=0.5)
    system = SystemMessage(content=f"""你是一个技术文档问答助手。根据以下检索到的文档片段回答用户问题。

规则：
- 回答基于文档内容，不要编造信息
- 如果文档信息不足以完整回答，诚实说明
- 回答末尾引用来源文件名
- 使用中文回答

文档片段：
{contexts}""")

    recent = [m for m in state["messages"] if isinstance(m, dict)][-4:]
    resp = llm.invoke([system] + [HumanMessage(content=m["content"]) if m["role"] == "user" else SystemMessage(content=m["content"]) for m in recent] + [HumanMessage(content=query)])
    
    return {"final_answer": resp.content}


def clarify(state: AgentState) -> dict:
    """判断回答是否够清晰，是否需要反问"""
    answer = state.get("final_answer", "")
    query = state.get("rewritten_query") or _get_last_user_message(state)

    if not answer or answer.startswith("抱歉"):
        return {"need_clarify": False}

    # 回答过短可能不够清晰，但不强制追问
    if len(answer) < 60:
        prompt = f"问题：{query}\n回答：{answer}\n这个回答是否信息不足、需要追问？只回复 true 或 false"
        llm = create_llm(temperature=0.0)
        resp = llm.invoke([HumanMessage(content=prompt)])
        return {"need_clarify": "true" in resp.content.lower()}

    return {"need_clarify": False}
```

- [ ] **Step 3: 验证 LLM 连接和意图识别**

```bash
cd project && python -c "
from app.agent.nodes import create_llm
llm = create_llm()
resp = llm.invoke('你好，请回复OK')
print(resp.content)
"
```

- [ ] **Step 4: Commit**

---

### Task 6: LangGraph 状态图编排

**Files:**
- Create: `app/agent/graph.py`

**Interfaces:**
- Consumes: `app.agent.nodes.*`, `app.agent.AgentState`
- Produces:
  - `get_agent_graph() → langgraph.graph.StateGraph`
  - `run_agent(message: str, history: list[dict]) → dict` — 执行完整工作流，返回 `{"answer": str, "sources": list[dict]}`

- [ ] **Step 1: 创建 app/agent/graph.py**

```python
from langgraph.graph import StateGraph, END
from app.agent import AgentState
from app.agent.nodes import (
    classify_intent,
    rewrite_query,
    retrieve,
    judge_relevance,
    generate,
    clarify,
)


def _route_by_intent(state: AgentState) -> str:
    if state.get("intent") == "tech":
        return "rewrite_query"
    return "fallback"


def _route_by_relevance(state: AgentState) -> str:
    answer = state.get("final_answer", "")
    if answer and answer.startswith("抱歉"):
        return "fallback"
    return "generate"


def _route_by_clarity(state: AgentState) -> str:
    if state.get("need_clarify"):
        return "rephrase"
    return END


def _fallback_node(state: AgentState) -> dict:
    answer = state.get("final_answer") or "请提出技术相关问题，我会基于知识库为您解答。"
    return {"final_answer": answer, "need_clarify": False}


def _rephrase_node(state: AgentState) -> dict:
    answer = state.get("final_answer", "")
    return {"final_answer": f"{answer}\n\n如果您的问题还未解决，可以尝试更具体地描述，或者换个问法。"}


def get_agent_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("classify_intent", classify_intent)
    graph.add_node("rewrite_query", rewrite_query)
    graph.add_node("retrieve", retrieve)
    graph.add_node("judge_relevance", judge_relevance)
    graph.add_node("generate", generate)
    graph.add_node("clarify", clarify)
    graph.add_node("fallback", _fallback_node)
    graph.add_node("rephrase", _rephrase_node)

    graph.set_entry_point("classify_intent")

    graph.add_conditional_edges("classify_intent", _route_by_intent, {
        "rewrite_query": "rewrite_query",
        "fallback": "fallback",
    })

    graph.add_edge("rewrite_query", "retrieve")
    graph.add_edge("retrieve", "judge_relevance")

    graph.add_conditional_edges("judge_relevance", _route_by_relevance, {
        "generate": "generate",
        "fallback": "fallback",
    })

    graph.add_edge("generate", "clarify")

    graph.add_conditional_edges("clarify", _route_by_clarity, {
        "rephrase": "rephrase",
        END: END,
    })

    graph.add_edge("fallback", END)
    graph.add_edge("rephrase", END)

    return graph.compile()


def run_agent(message: str, history: list[dict] | None = None) -> dict:
    graph = get_agent_graph()
    state: AgentState = {
        "messages": (history or []) + [{"role": "user", "content": message}],
        "intent": "",
        "rewritten_query": "",
        "retrieved_docs": [],
        "final_answer": "",
        "need_clarify": False,
    }
    result = graph.invoke(state)
    return {
        "answer": result.get("final_answer", ""),
        "sources": [
            {"source": d["source"], "score": round(d["score"], 3)}
            for d in result.get("retrieved_docs", [])
        ],
    }
```

- [ ] **Step 3: 验证 Agent 完整链路**

```bash
cd project && python -c "
from app.agent.graph import run_agent
result = run_agent('什么是测试文档？', history=[{
    'role': 'user', 'content': '测试文档里讲了什么？'
}])
print(f'回答: {result[\"answer\"][:100]}...')
print(f'来源: {result[\"sources\"]}')
print('OK')
"
```

- [ ] **Step 4: Commit**

---

### Task 7: RSS 爬虫模块

**Files:**
- Create: `app/crawler/__init__.py`
- Create: `app/crawler/feed.py`

**Interfaces:**
- Consumes: `app.config.settings` (rss_feeds), `app.rag.loader.index_document`
- Produces:
  - `fetch_feeds() → int` — 抓取所有 RSS 源，解析文章摘要，返回新增篇数
  - `start_scheduler()` — 启动定时任务（APScheduler，每隔 crawl_schedule_hours 小时执行一次）

- [ ] **Step 1: 创建 app/crawler/__init__.py**（空文件）

- [ ] **Step 2: 创建 app/crawler/feed.py**

```python
import os
import hashlib
import feedparser
import httpx
from pathlib import Path
from datetime import datetime
from app.config import settings

RSS_STORE_DIR = "./data/rss"


def _fetch_entries(feed_url: str) -> list[dict]:
    """拉取 RSS 条目"""
    try:
        resp = httpx.get(feed_url, timeout=30, follow_redirects=True)
        resp.raise_for_status()
    except Exception:
        return []

    feed = feedparser.parse(resp.text)
    entries = []
    for entry in feed.entries:
        title = entry.get("title", "未命名")
        summary = entry.get("summary", entry.get("description", ""))
        link = entry.get("link", "")

        content = f"# {title}\n\n来源：{link}\n\n{summary}"
        entry_id = hashlib.md5(content.encode()).hexdigest()

        entries.append({"id": entry_id, "content": content, "title": title})
    return entries


def fetch_feeds() -> int:
    """抓取所有 RSS 源，将新文章保存为 Markdown 文件并入库，返回新增篇数"""
    feed_urls = [u.strip() for u in settings.rss_feeds.split(",") if u.strip()]
    if not feed_urls:
        return 0

    os.makedirs(RSS_STORE_DIR, exist_ok=True)
    new_count = 0

    for feed_url in feed_urls:
        entries = _fetch_entries(feed_url)
        for entry in entries:
            filepath = Path(RSS_STORE_DIR) / f"{entry['id']}.md"
            if filepath.exists():
                continue  # 已存在，跳过

            filepath.write_text(entry["content"], encoding="utf-8")
            try:
                from app.rag.loader import index_document
                index_document(str(filepath))
                new_count += 1
            except Exception:
                pass

    return new_count


def start_scheduler():
    """启动定时爬虫任务"""
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        fetch_feeds,
        "interval",
        hours=settings.crawl_schedule_hours,
        id="rss_crawler",
        replace_existing=True,
    )
    scheduler.start()
```

- [ ] **Step 3: 验证爬虫能正常抓取**

```bash
cd project && python -c "
from app.crawler.feed import fetch_feeds
n = fetch_feeds()
print(f'新增: {n} 篇')
print('OK')
"
```

- [ ] **Step 4: Commit**

---

### Task 8: 飞书机器人集成

**Files:**
- Create: `app/feishu/__init__.py`
- Create: `app/feishu/bot.py`

**Interfaces:**
- Consumes: `app.config.settings` (feishu_*), `app.agent.graph.run_agent`, `lark_oapi`
- Produces:
  - `handle_event(body: bytes, headers: dict) → dict` — 飞书事件回调处理器，返回响应 JSON
  - 支持 URL 验证 + 消息接收 + 调用 Agent 回复

- [ ] **Step 1: 创建 app/feishu/__init__.py**（空文件）

- [ ] **Step 2: 创建 app/feishu/bot.py**

```python
import json
import logging
from lark_oapi import Config as LarkConfig
from lark_oapi.api.im.v1 import (
    P2ImMessageReceiveV1,
    ReplyMessageRequest,
    ReplyMessageRequestBody,
)
from lark_oapi.event.callback.handler.handler import (
    CustomTypeEventHandler,
    P2ImMessageReceiveV1Handler,
)
from app.config import settings
from app.agent.graph import run_agent

logger = logging.getLogger(__name__)

_session_store: dict[str, list[dict]] = {}


def _init_lark_client():
    return LarkConfig(
        app_id=settings.feishu_app_id,
        app_secret=settings.feishu_app_secret,
        encrypt_key=settings.feishu_encrypt_key,
        verification_token=settings.feishu_verify_token,
    )


def handle_event(body: bytes, headers: dict) -> dict:
    """处理飞书事件回调，返回响应 JSON"""
    config = _init_lark_client()
    body_dict = json.loads(body)

    # URL 验证
    if body_dict.get("type") == "url_verification":
        token = body_dict.get("token", "")
        challenge = body_dict.get("challenge", "")
        if token == settings.feishu_verify_token:
            return {"challenge": challenge}
        return {"challenge": ""}

    # 消息事件
    event = body_dict.get("event", {})
    msg_type = event.get("message", {}).get("message_type", "")

    if msg_type == "text":
        content = json.loads(event.get("message", {}).get("content", "{}"))
        user_text = content.get("text", "")
        chat_id = event.get("message", {}).get("chat_id", "")
        msg_id = event.get("message", {}).get("message_id", "")
        user_id = event.get("sender", {}).get("sender_id", {}).get("user_id", "")

        if user_text:
            session_id = f"feishu_{chat_id}"
            history = _session_store.get(session_id, [])

            result = run_agent(user_text, history=history)

            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": result["answer"]})
            _session_store[session_id] = history[-10:]

            # 异步回复
            try:
                _reply_message(msg_id, result["answer"])
            except Exception as e:
                logger.error(f"飞书回复失败: {e}")

    return {}


def _reply_message(msg_id: str, content: str):
    """通过飞书 API 回复消息"""
    import lark_oapi as lark
    from lark_oapi.api.im.v1 import ReplyMessageRequest, ReplyMessageRequestBody

    client = lark.Client.builder() \
        .app_id(settings.feishu_app_id) \
        .app_secret(settings.feishu_app_secret) \
        .build()

    body = ReplyMessageRequestBody()
    body.content = json.dumps({"text": content})
    body.msg_type = "text"

    request = ReplyMessageRequest()
    request.message_id = msg_id
    request.request_body = body

    client.im.v1.message.reply(request)
```

- [ ] **Step 3: Commit**

---

### Task 9: FastAPI 主应用 + 网页聊天界面

**Files:**
- Create: `app/main.py`
- Create: `app/web/__init__.py`（空文件）
- Create: `app/web/static/index.html`

**Interfaces:**
- Consumes: `app.agent.graph.run_agent`, `app.rag.loader.*`, `app.crawler.feed.*`, `app.feishu.bot.handle_event`
- Produces: FastAPI app 实例，6 个路由 + 静态文件

- [ ] **Step 1: 创建 app/main.py**

```python
import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import settings
from app.agent.graph import run_agent
from app.rag.loader import index_document, index_directory
from app.rag.vectorstore import get_or_create_collection
from app.crawler.feed import fetch_feeds, start_scheduler
from app.feishu.bot import handle_event

# 日志配置
os.makedirs(settings.log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(Path(settings.log_dir) / "app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("应用启动")
    start_scheduler()
    logger.info(f"爬虫定时器已启动，间隔 {settings.crawl_schedule_hours} 小时")
    yield
    logger.info("应用关闭")


app = FastAPI(title="智能文档问答助手", version="1.0.0", lifespan=lifespan)

# 静态文件
static_dir = Path(__file__).parent / "web" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# --- 模型 ---
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


__session_store: dict[str, list[dict]] = {}


# --- 路由 ---
@app.get("/")
async def root():
    return FileResponse(str(static_dir / "index.html"))


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    history = __session_store.get(req.session_id, [])
    result = run_agent(req.message, history=history)
    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": result["answer"]})
    __session_store[req.session_id] = history[-20:]
    return {"reply": result["answer"], "sources": result["sources"], "session_id": req.session_id}


@app.post("/api/knowledge/upload")
async def upload_knowledge(file: UploadFile = File(...)):
    os.makedirs("./data/docs", exist_ok=True)
    file_path = Path("./data/docs") / file.filename
    content = await file.read()
    file_path.write_bytes(content)
    chunks = index_document(str(file_path))
    return {"status": "ok", "chunks": chunks, "filename": file.filename}


@app.post("/api/knowledge/crawl")
async def trigger_crawl():
    new_docs = fetch_feeds()
    return {"status": "ok", "new_docs": new_docs}


@app.get("/api/knowledge/stats")
async def knowledge_stats():
    try:
        col = get_or_create_collection()
        count = col.count()
    except Exception:
        count = 0
    return {"doc_count": "未知", "chunk_count": count}


@app.post("/feishu/callback")
async def feishu_callback(request: Request):
    body = await request.body()
    result = handle_event(body, dict(request.headers))
    return JSONResponse(content=result)
```

- [ ] **Step 2: 创建 app/web/static/index.html**

```html
<!DOCTYPE html>
<html lang=zh-CN>
<head>
<meta charset=UTF-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>智能文档问答助手</title>
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/font-awesome@4.7.0/css/font-awesome.min.css">
</head>
<body class="bg-gray-100 min-h-screen flex items-center justify-center p-4">
<div class="w-full max-w-2xl bg-white rounded-2xl shadow-lg flex flex-col" style="height: 90vh">

  <!-- Header -->
  <div class="px-6 py-4 border-b flex items-center gap-3">
    <i class="fa fa-comments-o text-2xl text-blue-600"></i>
    <div>
      <h1 class="text-lg font-semibold">智能文档问答助手</h1>
      <p class="text-xs text-gray-400">基于 RAG + GLM-5.2</p>
    </div>
  </div>

  <!-- Messages -->
  <div id=messages class="flex-1 overflow-y-auto px-6 py-4 space-y-4"></div>

  <!-- Input -->
  <div class="px-6 py-4 border-t">
    <div class="flex gap-2">
      <input id=input type=text placeholder="输入你的问题…" autofocus
       class="flex-1 border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-400 text-sm">
      <button id=send class="bg-blue-600 text-white px-5 py-3 rounded-xl hover:bg-blue-700 text-sm font-medium">
        <i class="fa fa-paper-plane"></i>
      </button>
    </div>
  </div>

</div>

<script>
const msgs = document.getElementById('messages');
const input = document.getElementById('input');
const send = document.getElementById('send');

function addMsg(role, text, sources) {
  const div = document.createElement('div');
  div.className = role === 'user'
    ? 'flex justify-end'
    : 'flex gap-3';
  
  const bubble = document.createElement('div');
  bubble.className = role === 'user'
    ? 'bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 max-w-[75%] text-sm'
    : 'bg-gray-100 text-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 max-w-[85%] text-sm';
  bubble.textContent = text;

  if (role === 'bot') {
    const avatar = document.createElement('div');
    avatar.className = 'w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0';
    avatar.innerHTML = '<i class="fa fa-robot text-blue-600 text-xs"></i>';
    div.appendChild(avatar);
  }
  div.appendChild(bubble);
  msgs.appendChild(div);

  if (sources && sources.length) {
    const src = document.createElement('div');
    src.className = 'text-xs text-gray-400 mt-1 ml-10';
    src.textContent = '来源: ' + sources.map(s => s.source).join(', ');
    msgs.appendChild(src);
  }

  msgs.scrollTop = msgs.scrollHeight;
}

async function doSend() {
  const text = input.value.trim();
  if (!text) return;
  addMsg('user', text);
  input.value = '';

  const thinking = document.createElement('div');
  thinking.className = 'text-gray-400 text-sm ml-10';
  thinking.textContent = '思考中...';
  msgs.appendChild(thinking);

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text, session_id: 'web'}),
    });
    const data = await res.json();
    thinking.remove();
    addMsg('bot', data.reply, data.sources);
  } catch(e) {
    thinking.remove();
    addMsg('bot', '请求失败: ' + e.message);
  }
}

send.onclick = doSend;
input.onkeydown = e => { if (e.key==='Enter') doSend(); };
</script>
</body>
</html>
```

- [ ] **Step 3: 启动服务验证所有路由**

```bash
cd project && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
sleep 3
curl -s http://localhost:8000/health
curl -s http://localhost:8000/api/knowledge/stats
curl -s -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"message":"你好"}'
```

- [ ] **Step 4: Commit**

---

### Task 10: Docker 容器化

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.dockerignore`

- [ ] **Step 1: 创建 Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 源码
COPY app/ ./app/

# 创建数据和日志目录
RUN mkdir -p data logs

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: 创建 docker-compose.yml**

```yaml
version: "3.8"

services:
  qa-bot:
    build: .
    container_name: smart-doc-qa
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    env_file:
      - .env
    restart: unless-stopped
```

- [ ] **Step 3: 创建 .dockerignore**

```
__pycache__
*.pyc
.git
.env
.venv
venv
logs
data
*.md
```

- [ ] **Step 4: 本地构建并启动验证**

```bash
cd project && docker compose up -d --build
sleep 5
curl -s http://localhost:8000/health
docker compose logs --tail 20
```

Expected: `{"status":"healthy","version":"1.0.0"}`

- [ ] **Step 5: Commit**

---

### Task 11: 部署文档

**Files:**
- Create: `docs/deploy.md`

- [ ] **Step 1: 创建 docs/deploy.md**

````markdown
# 部署指南

## 前置条件
- 腾讯云轻量服务器 2C4G，Ubuntu 22.04
- 已连接 SSH

## 1. 服务器初始化

```bash
ssh root@<服务器IP>

apt update && apt upgrade -y
apt install -y docker.io docker-compose nginx certbot python3-certbot-nginx

systemctl enable docker --now
```

## 2. 上传项目

```bash
# 在本地
scp -r project/ root@<服务器IP>:/opt/smart-doc-qa/
```

## 3. 配置环境变量

```bash
ssh root@<服务器IP>
cd /opt/smart-doc-qa
cp .env.example .env
vim .env  # 填入 API Key 等信息
```

## 4. 启动服务

```bash
docker compose up -d --build
# 验证
curl http://localhost:8000/health
```

## 5. 配置 Nginx + SSL

```bash
# 创建 Nginx 配置
vim /etc/nginx/sites-available/qa-bot
```

```nginx
server {
    listen 80;
    server_name <你的域名>;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 120s;
    }
}
```

```bash
ln -s /etc/nginx/sites-available/qa-bot /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# SSL 证书
certbot --nginx -d <你的域名>
```

## 6. 配置飞书回调

1. 飞书开放平台 → 创建企业自建应用
2. 添加"机器人"能力
3. 事件订阅 → 请求网址填 `https://<域名>/feishu/callback`
4. 订阅 `im.message.receive_v1` 事件
5. 发布应用

## 7. 导入知识库

```bash
# 手动上传文档
curl -X POST https://<域名>/api/knowledge/upload -F "file=@文档.pdf"

# 或放到 data/docs 目录批量导入
```

## 故障排查

```bash
docker compose logs -f --tail 100
tail -f logs/app.log
```
````

- [ ] **Step 2: Commit**

---

### Task 12: 最终端到端验证

- [ ] **Step 1: 完整链路测试**

```bash
# 启动服务
docker compose up -d --build
sleep 5

# 健康检查
curl -s http://localhost:8000/health | grep healthy

# 上传测试文档
echo "# Python 入门\n\n## 变量\n\nPython 中变量无需声明类型，直接赋值即可。\n\
x = 10\nname = 'hello'\n\n## 函数\n\n使用 def 关键字定义函数。\ndef greet(name):\n    return f'Hello, {name}'" > /tmp/test_python.md
curl -s -X POST http://localhost:8000/api/knowledge/upload -F "file=@/tmp/test_python.md"

# 对话测试
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Python 中如何定义函数？","session_id":"test"}'

# 知识库统计
curl -s http://localhost:8000/api/knowledge/stats

# 网页界面
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/
```

- [ ] **Step 2: 确认所有输出正常，无报错**

- [ ] **Step 3: Commit**

---

