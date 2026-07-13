import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from app.config import settings

_embedding_model = None
_vectorstore = None


def get_embedding_model() -> SentenceTransformer:
    """获取或初始化嵌入模型（单例模式）。"""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(settings.embedding_model)
    return _embedding_model


def get_vectorstore() -> chromadb.PersistentClient:
    """获取或初始化 ChromaDB 持久化客户端（单例模式）。"""
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _vectorstore


def get_or_create_collection(name: str = "tech_docs") -> chromadb.Collection:
    """获取已存在的集合，若不存在则创建。返回带嵌入函数的 Collection 对象。"""
    client = get_vectorstore()
    model = get_embedding_model()

    def embedding_fn(texts: list[str]) -> list[list[float]]:
        return model.encode(texts).tolist()

    try:
        collection = client.get_collection(name=name, embedding_function=embedding_fn)
    except Exception:
        collection = client.create_collection(name=name, embedding_function=embedding_fn)

    return collection
