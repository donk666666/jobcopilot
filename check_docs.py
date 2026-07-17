from app.rag.vectorstore import get_or_create_collection
col = get_or_create_collection()
data = col.get()
sources = set()
if data.get("metadatas"):
    for m in data["metadatas"]:
        sources.add(m.get("source", "??"))
print(f"文档数: {len(sources)}")
for s in sorted(sources):
    print(f"  - {s}")
print(f"总chunk数: {col.count()}")
