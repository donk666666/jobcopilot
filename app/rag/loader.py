import os
import uuid
from pathlib import Path

from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from app.rag.vectorstore import get_or_create_collection


def _get_loader(file_path: str):
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return PyPDFLoader(file_path)
    elif ext in (".md", ".markdown"):
        return TextLoader(file_path, encoding="utf-8")
    else:
        return TextLoader(file_path, encoding="utf-8")


def load_and_split(file_path: str, chunk_size: int = 500, chunk_overlap: int = 80):
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
