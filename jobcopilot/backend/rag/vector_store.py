"""
RAG 向量存储模块

使用 ChromaDB + LangChain 实现简历和JD的向量化存储与检索。
嵌入模型加载失败时自动降级，不阻塞核心功能。
"""

import os
import logging
from typing import List, Optional, Dict

logger = logging.getLogger("jobcopilot.rag")

# 向量库持久化目录
CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chroma_db")

_embeddings = None
_embeddings_error = None


def _get_embeddings():
    """延迟加载嵌入模型，失败则返回 None"""
    global _embeddings, _embeddings_error
    if _embeddings is not None:
        return _embeddings
    if _embeddings_error is not None:
        return None

    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        _embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-zh-v1.5",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
        return _embeddings
    except Exception as e:
        _embeddings_error = str(e)
        logger.warning(f"嵌入模型加载失败，RAG 功能降级: {e}")
        return None


class VectorStore:
    """
    向量存储管理器。
    嵌入模型不可用时自动降级为空操作，所有检索返回空结果。
    """

    def __init__(self, persist_dir: str = CHROMA_DIR):
        self.persist_dir = persist_dir
        self.ready = False

        try:
            os.makedirs(persist_dir, exist_ok=True)
            self.embeddings = _get_embeddings()

            from langchain.text_splitter import RecursiveCharacterTextSplitter
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
                separators=["\n\n", "\n", "。", "；", "，", " ", ""]
            )

            if self.embeddings is not None:
                self.resume_store: Optional["Chroma"] = None
                self.jd_store: Optional["Chroma"] = None
                self.ready = True
            else:
                self.resume_store = None
                self.jd_store = None
        except Exception as e:
            logger.warning(f"向量库初始化失败: {e}")
            self.embeddings = None
            self.resume_store = None
            self.jd_store = None
            self.text_splitter = None

    def _get_or_create_store(self, collection_name: str):
        if not self.ready:
            return None
        from langchain_community.vectorstores import Chroma
        return Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_dir
        )

    def _ensure_stores(self):
        if not self.ready:
            return
        if self.resume_store is None:
            self.resume_store = self._get_or_create_store("resumes")
        if self.jd_store is None:
            self.jd_store = self._get_or_create_store("jds")

    def add_resume(self, resume_text: str, metadata: Optional[Dict] = None) -> int:
        if not self.ready:
            return 0
        try:
            self._ensure_stores()
            chunks = self.text_splitter.split_text(resume_text)
            from langchain.schema import Document
            docs = [
                Document(page_content=chunk, metadata=metadata or {}, id=f"resume_chunk_{i}")
                for i, chunk in enumerate(chunks)
            ]
            try:
                self.resume_store.delete_collection()
                self.resume_store = self._get_or_create_store("resumes")
            except Exception:
                pass
            self.resume_store.add_documents(docs)
            return len(chunks)
        except Exception as e:
            logger.warning(f"添加简历到向量库失败: {e}")
            return 0

    def search_resume(self, query: str, top_k: int = 5):
        if not self.ready:
            return []
        try:
            self._ensure_stores()
            return self.resume_store.similarity_search(query, k=top_k)
        except Exception:
            return []

    def add_jd(self, jd_text: str, metadata: Optional[Dict] = None) -> int:
        if not self.ready:
            return 0
        try:
            self._ensure_stores()
            chunks = self.text_splitter.split_text(jd_text)
            from langchain.schema import Document
            docs = [
                Document(page_content=chunk, metadata=metadata or {}, id=f"jd_chunk_{i}")
                for i, chunk in enumerate(chunks)
            ]
            self.jd_store.add_documents(docs)
            return len(chunks)
        except Exception as e:
            logger.warning(f"添加JD到向量库失败: {e}")
            return 0

    def search_jd(self, query: str, top_k: int = 5):
        if not self.ready:
            return []
        try:
            self._ensure_stores()
            return self.jd_store.similarity_search(query, k=top_k)
        except Exception:
            return []

    def search_all(self, query: str, top_k: int = 5) -> str:
        if not self.ready:
            return "RAG 向量库未就绪，使用纯 LLM 分析。"
        try:
            self._ensure_stores()
            resume_docs = self.search_resume(query, top_k)
            jd_docs = self.search_jd(query, top_k)
            context_parts = []
            if resume_docs:
                context_parts.append("## 简历相关片段")
                for i, doc in enumerate(resume_docs, 1):
                    context_parts.append(f"{i}. {doc.page_content}")
            if jd_docs:
                context_parts.append("## 相关职位信息")
                for i, doc in enumerate(jd_docs, 1):
                    context_parts.append(f"{i}. {doc.page_content}")
            return "\n\n".join(context_parts) if context_parts else "暂无相关检索结果。"
        except Exception as e:
            logger.warning(f"向量检索失败: {e}")
            return "RAG 检索异常，使用纯 LLM 分析。"

    def get_store_stats(self) -> Dict:
        if not self.ready:
            return {"status": "degraded", "reason": _embeddings_error or "嵌入模型未加载"}
        try:
            self._ensure_stores()
            return {
                "resume_chunks": self.resume_store._collection.count() if self.resume_store else 0,
                "jd_chunks": self.jd_store._collection.count() if self.jd_store else 0,
                "status": "ok"
            }
        except Exception:
            return {"status": "error"}


_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
