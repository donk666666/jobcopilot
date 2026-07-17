# 文档处理与分块策略

## 文档加载

```python
from langchain_community.document_loaders import TextLoader, PyPDFLoader, CSVLoader

# 纯文本
loader = TextLoader("doc.txt", encoding="utf-8")

# PDF
loader = PyPDFLoader("report.pdf")

# CSV
loader = CSVLoader("data.csv")

# 目录批量加载
from langchain_community.document_loaders import DirectoryLoader
loader = DirectoryLoader("./docs/", glob="**/*.md", loader_cls=TextLoader)

docs = loader.load()
```

支持的格式：`.txt` `.md` `.pdf` `.csv` `.json` `.html` 等。`load()` 返回 `Document` 对象列表，每个包含 `page_content` 和 `metadata`。

## RecursiveCharacterTextSplitter

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,        # 每块最大字符数
    chunk_overlap=80,      # 相邻块重叠字符数
    separators=["\n\n", "\n", "。", "，", " ", ""],
    length_function=len,
    is_separator_regex=False,
)

chunks = splitter.split_documents(docs)
```

分割逻辑：从粗到细依次尝试分隔符（先按段落、再按行、再按标点），尽量在语义边界处切割，避免从句子中间截断。

## chunk_size 选择指南

| 场景 | 推荐大小 | 原因 |
|------|----------|------|
| FAQ / 短问答 | 200-300 | 问题简短，小块匹配更精准 |
| 技术文档 | 500-800 | 代码块 + 解释，保持完整性 |
| 长篇文章 | 800-1500 | 段落较长，需保留上下文 |
| 法律/合同 | 1000-2000 | 条款之间依赖强，不宜拆太碎 |

chunk_size 太小 → 语义碎片化、缺少上下文；chunk_size 太大 → 噪声多、检索精度下降。

## chunk_overlap 的作用

```
chunk_size=500, overlap=80

Chunk 1: [0...........500]
Chunk 2:        [420...............920]
Chunk 3:               [840....................1340]
```

重叠区保证：一个句子即使落在 chunk 边界附近，也能在相邻 chunk 中被完整检索到。overlap 一般取 chunk_size 的 10%～20%。

## Postgres 文档加载（示例）

```python
from langchain_community.document_loaders import DatabaseLoader

# 从数据库加载文档元数据
loader = DatabaseLoader(
    query="SELECT id, title, content FROM documents WHERE status='published'",
    connection_string="postgresql://user:pass@localhost/mydb",
)
docs = loader.load()
```

## 去重与清洗

```python
# 去重
seen = set()
unique_chunks = []
for chunk in chunks:
    key = chunk.page_content[:100]
    if key not in seen:
        seen.add(key)
        unique_chunks.append(chunk)

# 清洗空白
for chunk in unique_chunks:
    chunk.page_content = chunk.page_content.strip()
    # 移除多余空行
    chunk.page_content = "\n".join(
        line for line in chunk.page_content.split("\n") if line.strip()
    )
```

## 元数据注入

```python
for i, chunk in enumerate(chunks):
    chunk.metadata["chunk_index"] = i
    chunk.metadata["source_file"] = source
    chunk.metadata["chunk_count"] = len(chunks)
```

检索时元数据会随 chunk 一起返回，方便定位原文位置。

## 文档切分最佳实践

1. 按语义单元切分（代码做函数级、文档做段落级）
2. 对代码文件使用 `Language` 感知的 splitter
3. 保留原始文档引用（source + chunk_index 元数据）
4. 小块检索（top_k 大一点）、大块喂 LLM 时带上下文窗口
5. 评估后迭代调整参数——没有万能值
