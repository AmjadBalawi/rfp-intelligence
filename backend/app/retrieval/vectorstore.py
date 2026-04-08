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

client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
collection = client.get_or_create_collection("products")

model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")


# -------------------- CACHING --------------------
@lru_cache(maxsize=128)
def embed_query(q: str):
    return list(model.embed([q]))[0]


# -------------------- INDEXING --------------------
def index_products(products: list[dict]):
    global bm25, bm25_corpus, bm25_docs

    ids = [str(p["id"]) for p in products]

    #  Improved BM25 text (structured tokens)
    texts = [
        f"{p['title']} {p.get('description', '')} "
        f"category:{p.get('category', '')} "
        f"price:{p.get('price_eur', '')} "
        f"capacity:{p.get('available_capacity', '')}"
        for p in products
    ]

    embeddings = list(model.embed(texts))

    metadatas = [
        {k: v for k, v in p.items()
         if isinstance(v, (str, int, float, bool, type(None)))}
        for p in products
    ]

    collection.upsert(
        ids=ids,
        embeddings=[e.tolist() for e in embeddings],
        metadatas=metadatas
    )

    # BM25 initialization
    bm25_corpus = [t.lower().split() for t in texts]
    bm25 = BM25Okapi(bm25_corpus)
    bm25_docs = metadatas

    logger.info(f"Indexed {len(products)} products (vector + BM25)")


# -------------------- RETRIEVAL --------------------
def multi_query_retrieve(extracted: dict, top_k=5) -> list[dict]:
    # -------- FALLBACK --------
    if bm25 is None:
        logger.warning("BM25 not initialized, using vector-only retrieval")
        emb = embed_query(extracted.get("event_type", ""))
        results = collection.query(
            query_embeddings=[emb.tolist()],
            n_results=top_k
        )
        return results["metadatas"][0]

    # -------- BUILD QUERIES --------
    queries = []

    if extracted.get("rooms_needed"):
        queries.append("venue meeting room " + " ".join(extracted["rooms_needed"]))
    if extracted.get("catering_needed"):
        queries.append("catering " + " ".join(extracted["catering_needed"]))
    if extracted.get("av_needed"):
        queries.append("AV equipment " + " ".join(extracted["av_needed"]))

    if not queries:
        queries = [
            f"{extracted.get('event_type', '')} {extracted.get('guest_count', 0)} guests"
        ]

    logger.info(f"Queries: {queries}")

    hybrid_results = {}

    # -------- PRECOMPUTE EMBEDDINGS --------
    query_embeddings = [embed_query(q) for q in queries]

    for q, emb in zip(queries, query_embeddings):
        q_tokens = q.lower().split()

        # -------- QUERY-TYPE WEIGHTING --------
        weight = 1.0
        if "venue" in q:
            weight = 1.2
        elif "catering" in q:
            weight = 1.1
        elif "av" in q:
            weight = 1.05

        # -------- BM25 --------
        bm25_scores = bm25.get_scores(q_tokens)
        bm25_scores = bm25_scores.tolist()  # convert to Python list
        max_score = max(bm25_scores) if bm25_scores else 1

        bm25_top_idx = sorted(
            range(len(bm25_scores)),
            key=lambda i: bm25_scores[i],
            reverse=True
        )[:top_k]

        for i in bm25_top_idx:
            doc = bm25_docs[i]
            pid = str(doc["id"])

            normalized_score = (
                bm25_scores[i] / max_score if max_score > 0 else 0
            )

            if pid not in hybrid_results:
                hybrid_results[pid] = {"meta": doc, "score": 0}

            hybrid_results[pid]["score"] += normalized_score * 0.4 * weight

        # -------- VECTOR --------
        results = collection.query(
            query_embeddings=[emb.tolist()],
            n_results=top_k
        )

        if results["ids"] and results["ids"][0]:
            for pid, meta, dist in zip(
                results["ids"][0],
                results["metadatas"][0],
                results["distances"][0]
            ):
                similarity = 1 - dist

                if pid not in hybrid_results:
                    hybrid_results[pid] = {"meta": meta, "score": 0}

                hybrid_results[pid]["score"] += similarity * 0.6 * weight

        # -------- LIMIT CANDIDATES (SCALABILITY) --------
        if len(hybrid_results) > 100:
            hybrid_results = dict(
                sorted(
                    hybrid_results.items(),
                    key=lambda x: x[1]["score"],
                    reverse=True
                )[:50]
            )

    # -------- SORT --------
    ranked = sorted(
        hybrid_results.values(),
        key=lambda x: x["score"],
        reverse=True
    )

    logger.info(f"Candidates before filtering: {len(ranked)}")

    # -------- METADATA FILTERING --------
    budget = extracted.get("budget", {})
    max_budget = budget.get("max")
    guest_count = extracted.get("guest_count")

    filtered = []

    for r in [r["meta"] for r in ranked]:
        price = r.get("price_eur", 0)
        capacity = r.get("available_capacity", 0)

        if max_budget and price > max_budget:
            continue

        if guest_count and capacity and capacity < guest_count:
            continue

        filtered.append(r)

    # fallback if too aggressive
    if not filtered:
        filtered = [r["meta"] for r in ranked[:top_k * 2]]

    logger.info(f"Candidates after filtering: {len(filtered)}")

    # -------- RERANK --------
    def rerank(results):
        for r in results:
            capacity = r.get("available_capacity", 0)

            if guest_count and capacity:
                r["_boost"] = 1.2 if capacity >= guest_count else 1.0
            else:
                r["_boost"] = 1.0

        return sorted(results, key=lambda x: x["_boost"], reverse=True)

    final = rerank(filtered[:top_k * 2])

    return final[:top_k]