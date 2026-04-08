import chromadb
import logging
from fastembed import TextEmbedding
from app.config import settings
from rank_bm25 import BM25Okapi
from functools import lru_cache

# -------------------- SETUP --------------------
logger = logging.getLogger(__name__)

bm25 = None
bm25_corpus = []
bm25_docs = []

# Persistent ChromaDB client
client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
collection = client.get_or_create_collection("products")

# Embedding model
model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")


# -------------------- CACHING --------------------
@lru_cache(maxsize=128)
def embed_query(q: str):
    """Cache embeddings for query strings."""
    return list(model.embed([q]))[0]


# -------------------- INDEXING --------------------
def index_products(products: list[dict]):
    """Index products in ChromaDB and initialize BM25 corpus."""
    global bm25, bm25_corpus, bm25_docs

    ids = [str(p["id"]) for p in products]

    # Structured BM25 corpus for better retrieval
    texts = [
        f"{p['title']} {p.get('description', '')} "
        f"category:{p.get('category', '')} "
        f"price:{p.get('price_eur', '')} "
        f"capacity:{p.get('available_capacity', '')}"
        for p in products
    ]

    # Vector embeddings
    embeddings = list(model.embed(texts))

    # Clean metadata for ChromaDB
    metadatas = [
        {k: v for k, v in p.items() if isinstance(v, (str, int, float, bool, type(None)))}
        for p in products
    ]

    collection.upsert(
        ids=ids,
        embeddings=[e.tolist() for e in embeddings],
        metadatas=metadatas
    )

    # Initialize BM25
    bm25_corpus = [t.lower().split() for t in texts]
    bm25 = BM25Okapi(bm25_corpus)
    bm25_docs = metadatas

    logger.info(f"Indexed {len(products)} products (vector + BM25)")


# -------------------- RETRIEVAL --------------------
def multi_query_retrieve(extracted: dict, top_k=5) -> list[dict]:
    """
    Hybrid retrieval using BM25 + embeddings with normalized scores.
    Returns a list of top_k product dicts after filtering and reranking.
    """
    if bm25 is None:
        logger.warning("BM25 not initialized, using vector-only retrieval")
        emb = embed_query(extracted.get("event_type", ""))
        results = collection.query(
            query_embeddings=[emb.tolist()],
            n_results=top_k
        )
        return results["metadatas"][0]

    # Build queries from extracted requirements
    queries = []
    if extracted.get("rooms_needed"):
        queries.append("venue meeting room " + " ".join(extracted["rooms_needed"]))
    if extracted.get("catering_needed"):
        queries.append("catering " + " ".join(extracted["catering_needed"]))
    if extracted.get("av_needed"):
        queries.append("AV equipment " + " ".join(extracted["av_needed"]))
    if not queries:
        queries = [f"{extracted.get('event_type', '')} {extracted.get('guest_count', 0)} guests"]

    logger.info(f"Queries: {queries}")
    hybrid_results = {}

    # Precompute query embeddings
    query_embeddings = [embed_query(q) for q in queries]

    for q, emb in zip(queries, query_embeddings):
        q_tokens = q.lower().split()

        # Query-type weight
        weight = 1.0
        if "venue" in q:
            weight = 1.2
        elif "catering" in q:
            weight = 1.1
        elif "av" in q:
            weight = 1.05

        # BM25 scoring with normalization
        bm25_scores = bm25.get_scores(q_tokens).tolist()
        max_score = max(bm25_scores) if bm25_scores else 1
        for i, score in enumerate(bm25_scores):
            pid = str(bm25_docs[i]["id"])
            normalized_score = score / max_score if max_score > 0 else 0
            if pid not in hybrid_results:
                hybrid_results[pid] = {"meta": bm25_docs[i], "score": 0}
            hybrid_results[pid]["score"] += normalized_score * 0.4 * weight  # BM25 contribution

        # Vector similarity contribution
        results = collection.query(
            query_embeddings=[emb.tolist()],
            n_results=top_k
        )
        if results["ids"] and results["ids"][0]:
            for pid, meta, dist in zip(results["ids"][0], results["metadatas"][0], results["distances"][0]):
                similarity = 1 - dist
                if pid not in hybrid_results:
                    hybrid_results[pid] = {"meta": meta, "score": 0}
                hybrid_results[pid]["score"] += similarity * 0.6 * weight  # embedding contribution

    # Sort by hybrid score
    ranked = sorted(hybrid_results.values(), key=lambda x: x["score"], reverse=True)

    # Metadata filtering by budget & guest capacity
    budget = extracted.get("budget", {})
    max_budget = budget.get("max")
    guest_count = extracted.get("guest_count")
    filtered = [
        r["meta"] for r in ranked
        if (not max_budget or r["meta"].get("price_eur", 0) <= max_budget) and
           (not guest_count or r["meta"].get("available_capacity", 0) >= guest_count)
    ]

    # Fallback if too few results
    if not filtered:
        filtered = [r["meta"] for r in ranked[:top_k * 2]]

    # Re-rank based on capacity
    for r in filtered:
        capacity = r.get("available_capacity", 0)
        r["_boost"] = 1.2 if guest_count and capacity >= guest_count else 1.0
    final = sorted(filtered, key=lambda x: x["_boost"], reverse=True)

    return final[:top_k]