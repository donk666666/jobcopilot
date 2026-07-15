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
    if not query or not query.strip():
        return []

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

    # 同一文档只保留最高分 chunk，提升结果多样性
    seen_sources: set[str] = set()
    deduped: list[dict] = []
    for r in sorted_results:
        src = r["source"]
        if src not in seen_sources:
            seen_sources.add(src)
            deduped.append(r)

    return deduped[:top_k]
