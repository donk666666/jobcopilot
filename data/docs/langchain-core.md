# LangChain 核心概念

## Chain

```python
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

prompt = PromptTemplate(template="请用{language}写一个{task}", input_variables=["language", "task"])
chain = LLMChain(llm=llm, prompt=prompt)
result = chain.run(language="Python", task="读取文件")
```

## Agent

```python
from langchain.agents import create_openai_tools_agent, AgentExecutor

tools = [search_tool, calculator_tool]
agent = create_openai_tools_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
result = executor.invoke({"input": "计算 123 * 456"})
```

## Tool

```python
from langchain.tools import tool

@tool
def search(query: str) -> str:
    """搜索互联网获取信息"""
    return f"搜索结果: {query}"

@tool
def calculator(expression: str) -> str:
    """计算数学表达式"""
    return str(eval(expression))
```

## Document Loader

```python
from langchain_community.document_loaders import TextLoader, PyPDFLoader

loader = TextLoader("file.txt", encoding="utf-8")
docs = loader.load()

pdf_loader = PyPDFLoader("file.pdf")
pages = pdf_loader.load()
```

## Text Splitter

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
    separators=["\n\n", "\n", "。", "，", " ", ""]
)
chunks = splitter.split_documents(docs)
```

## LCEL (LangChain Expression Language)

```python
chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)
result = chain.invoke("什么是 RAG？")
```

## Memory

```python
from langchain.memory import ConversationBufferMemory

memory = ConversationBufferMemory(return_messages=True)
chain = LLMChain(llm=llm, prompt=prompt, memory=memory)
```

## ChromaDB

```python
import chromadb

client = chromadb.PersistentClient(path="./data/chroma")
collection = client.get_or_create_collection(name="knowledge_base")

collection.add(
    documents=["文档内容1", "文档内容2"],
    metadatas=[{"source": "doc1.txt"}, {"source": "doc2.txt"}],
    ids=["id1", "id2"]
)

results = collection.query(query_texts=["问题"], n_results=5)
print(results["documents"])
```
