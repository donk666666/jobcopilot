# RAG 完整流程：从向量检索到生成回答

## 整体架构

```
用户问题 → Embedding → 向量检索 → 混合排序 → LLM 生成 → 回答
```

## Step 1: Embedding — 文本转向量

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
query = "FastAPI 怎么处理文件上传"
query_vector = model.encode(query)  # → shape: (384,)
```

BGE-small 将文本映射为 384 维向量，中文场景推荐 `bge-small-zh-v1.5`（轻量、中文效果好）或 `bge-large-zh-v1.5`（更高精度，更大显存）。

## Step 2: 向量检索 — 相似度搜索

```python
import chromadb

client = chromadb.PersistentClient(path="./data/chroma")
collection = client.get_collection(name="tech_docs")

results = collection.query(
    query_texts=["FastAPI 怎么处理文件上传"],
    n_results=10,
)
# results["documents"]  → 文档内容列表
# results["metadatas"]  → 元数据（source, chunk_index）
# results["distances"]  → 向量距离（越小越相似）
```

ChromaDB 默认使用余弦距离。距离转相似度：`score = max(0, 1 - distance)`，范围 [0, 1]。

## Step 3: 混合检索 — 向量 + 关键词

```python
def hybrid_search(query: str, top_k: int = 5) -> list[dict]:
    vec_results = vector_search(query, top_k * 2)
    kw_results = keyword_search(query, top_k * 2)

    merged = {}
    for r in vec_results:
        key = r["content"][:100]
        merged[key] = r
        merged[key]["_vec_score"] = r["score"]

    for r in kw_results:
        key = r["content"][:100]
        if key in merged:
            # 已有的：向量 0.6 + 关键词 0.4
            merged[key]["score"] = merged[key].get("_vec_score", 0) * 0.6 + r["score"] * 0.4
        else:
            # 纯关键词匹配：降权
            r["score"] = r["score"] * 0.3
            merged[key] = r

    # 按 source 去重，同一文档只留最高分
    seen = set()
    deduped = []
    for r in sorted(merged.values(), key=lambda x: x["score"], reverse=True):
        if r["source"] not in seen:
            seen.add(r["source"])
            deduped.append(r)

    return deduped[:top_k]
```

**为什么混合？** 纯向量对语义相似但内容不相关的文本（如"WebSocket 实时通信"命中 `fastapi-quickref`）会产生虚高分数，关键词匹配可以在精确术语上做补充。

**为什么去重？** 同一文档的多个 chunk 会霸占 Top-K 位置，去重后用户看到的是不同的文档，提高结果多样性。

## Step 4: OOD 门控 — 过滤知识库外问题

```python
docs = hybrid_search(query, top_k=5)
if not docs or docs[0]["score"] < 0.50:
    return "抱歉，知识库中未找到相关内容。请尝试换个方式提问。"
```

阈值设置需要根据实际评估数据调整：
- 太低（0.3）→ OOD 问题大量漏过
- 太高（0.6）→ 可能误杀低分的合法命中
- 推荐用评估集扫出最优阈值（ROC 曲线找 F1 最高点）

## Step 5: LLM 生成 — 基于检索结果回答

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

llm = ChatOpenAI(
    base_url="https://your-api.com/v1",
    api_key="sk-xxx",
    model="glm-5.2",
    temperature=0.5,
)

contexts = "\n---\n".join(
    f"[来源: {d['source']}]\n{d['content']}"
    for d in docs[:2]  # 只取最相关的 2 个 chunk
)

system = SystemMessage(content=f"""你是一个技术文档问答助手。
根据以下检索到的文档片段回答用户问题。

规则：
- 回答基于文档内容，不要编造信息
- 如果文档信息不足以完整回答，诚实说明
- 回答末尾引用来源文件名
- 使用中文回答

文档片段：
{contexts}""")

resp = llm.invoke([system, HumanMessage(content=user_question)])
answer = resp.content
```

**温度参数**：0.3-0.5 适合 RAG 场景（需要准确但不僵硬），0.0 完全确定性（适合分类/判断），0.7+ 适合创意写作。

**为什么只喂 Top-2 个 chunk？** LLM 上下文窗口有限，太多 chunk 反而引入噪声，而且当前 chunk_size=500，2 个 chunk 约 1000 字符已经包含足够信息。

## 回答质量自检清单

- 答案是否引用了文档内容？（不是凭空生成）
- 引用的来源文件名是否正确？
- 如果文档不足以回答，是否诚实说明了？
- OOD 问题是否被正确拦截？

## RAG 评估关键指标

| 指标 | 含义 | 目标 |
|------|------|------|
| Hit Rate@5 | 正确答案在 Top-5 中出现 | > 90% |
| MRR | 第一个正确答案的排名倒数均值 | > 0.8 |
| Precision@5 | Top-5 结果中相关文档占比 | 取决于去重策略 |
| Recall@5 | 所有相关文档被检出的比例 | > 90% |
| OOD Rejection | 知识库外问题被正确拒绝的比例 | > 80% |

## 没有 LangGraph 也能跑 RAG

最简实现仅需 ChromaDB + LLM：

```python
def simple_rag(question: str) -> str:
    docs = hybrid_search(question, top_k=3)
    if not docs or docs[0]["score"] < 0.5:
        return "未找到相关内容"
    context = "\n".join(d["content"] for d in docs[:2])
    return llm.invoke(f"根据文档回答：\n{context}\n\n问题：{question}")
```

LangGraph 的价值在于需要多步决策时（条件分支、循环检索、状态持久化），简单场景直接用函数调用即可。
