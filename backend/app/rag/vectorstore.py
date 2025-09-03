import json, os
import chromadb
from chromadb.config import Settings
from ..config import settings
from ..llm.mistral_client import client as mistral

COLLECTION = "content_bank"

def _client():
    os.makedirs(settings.vector_db_dir, exist_ok=True)
    return chromadb.PersistentClient(path=settings.vector_db_dir, settings=Settings(allow_reset=True))

def _collection():
    c = _client()
    try:
        return c.get_collection(COLLECTION)
    except:
        return c.create_collection(COLLECTION)

def add_docs(docs: list[dict]):
    col = _collection()
    texts = [d["text"] for d in docs]
    embs = mistral.embed(texts)
    col.add(
        documents=texts,
        embeddings=embs,
        ids=[d["id"] for d in docs],
        metadatas=[{"topic": d.get("topic",""), "skill": d.get("skill",""), "level": d.get("level","")} for d in docs]
    )

def query(text: str, n: int = 5, topic: str | None = None):
    col = _collection()
    q_emb = mistral.embed([text])[0]
    where = {"topic": topic} if topic else None
    res = col.query(query_embeddings=[q_emb], n_results=n, where=where)
    hits = []
    for i in range(len(res["ids"][0])):
        hits.append({
            "id": res["ids"][0][i],
            "text": res["documents"][0][i],
            "meta": res["metadatas"][0][i],
            "distance": res["distances"][0][i] if "distances" in res else None
        })
    return hits

def seed_if_empty():
    col = _collection()
    if col.count() > 0:
        return
    with open(settings.content_bank_path, "r", encoding="utf-8") as f:
        bank = json.load(f)
    docs = []
    for i, item in enumerate(bank):
        docs.append({
            "id": f"seed-{i}",
            "text": item["content"],
            "topic": item["topic"],
            "skill": item.get("skill", "general"),
            "level": item.get("level", "remember")
        })
    add_docs(docs)
