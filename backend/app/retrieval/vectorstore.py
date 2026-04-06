import chromadb
from fastembed import TextEmbedding
from app.config import settings

client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
collection = client.get_or_create_collection("products")
model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")


def index_products(products: list[dict]):
    ids = [str(p["id"]) for p in products]
    texts = [
        f"{p['title']} {p.get('description', '')} {p.get('category', '')}"
        for p in products
    ]

    embeddings = list(model.embed(texts))  # key change

    metadatas = [
        {k: v for k, v in p.items() if isinstance(v, (str, int, float, bool, type(None)))}
        for p in products
    ]

    collection.upsert(
        ids=ids,
        embeddings=[e.tolist() for e in embeddings],
        metadatas=metadatas
    )


def multi_query_retrieve(extracted: dict, top_k=5) -> list[dict]:
    queries = []

    if extracted.get("rooms_needed"):
        queries.append("venue meeting room " + " ".join(extracted["rooms_needed"]))
    if extracted.get("catering_needed"):
        queries.append("catering " + " ".join(extracted["catering_needed"]))
    if extracted.get("av_needed"):
        queries.append("AV equipment " + " ".join(extracted["av_needed"]))

    if not queries:
        queries = [f"{extracted.get('event_type', '')} {extracted.get('guest_count', 0)} guests"]

    all_results = []

    for q in queries:
        emb = list(model.embed([q]))[0]

        results = collection.query(
            query_embeddings=[emb.tolist()],
            n_results=top_k
        )

        if results["ids"] and results["ids"][0]:
            all_results.extend(zip(
                results["ids"][0],
                results["metadatas"][0],
                results["distances"][0]
            ))

    best = {}
    for pid, meta, dist in all_results:
        if pid not in best or dist < best[pid][1]:
            best[pid] = (meta, dist)

    sorted_results = sorted(best.values(), key=lambda x: x[1])
    return [meta for meta, _ in sorted_results]