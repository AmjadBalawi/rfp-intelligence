# AI Proposal Intelligence System – Architecture

## System Diagram
[User] → Angular UI → FastAPI SSE → LangGraph pipeline (extract → retrieve → plan → generate → create → evaluate) → GROQ LLM & ChromaDB (embeddings).  
Proposal creation calls the Proposales API if a valid API key and company ID are provided; otherwise returns a mock UUID.  
Retrieval now combines **BM25 lexical search + semantic embeddings**, with query normalization and guest-count-based re-ranking for better accuracy.

## Deployment
The frontend is hosted on Vercel: https://rfp-intelligence-orcin.vercel.app/

The backend is hosted on Render: https://rfp-intelligence-2.onrender.com/health

The backend on Render goes to sleep after a few minutes of inactivity on the free tier.

GitHub Repo: https://github.com/AmjadBalawi/rfp-intelligence

## Model Selection
- **GROQ (llama-3.1-8b-instant)** for extraction, planning, generation, and evaluation – free tier, excellent JSON adherence, low latency.  
  Fallback blocks are generated automatically if LLM block generation fails, ensuring proposals are always created.  
- **BAAI/bge-small-en-v1.5** for embeddings with Model Size around ~133 MB and its architecture is BERT-like (384 dims, runs locally, no API cost).  
- Fallback logic ensures pipeline continues even if LLM JSON parsing fails.

## Retrieval Strategy
- **Multi‑query semantic search + BM25 hybrid**: separate query per requirement category (venue, catering, AV, accommodation).  
  BM25 scores are normalized and combined with embedding similarity (weight BM25 0.4, embeddings 0.6).  
- **ChromaDB** with cosine similarity and persistent storage (`./chroma_db`).  
- Query tokens are lowercased and normalized; fallback to embeddings only if BM25 is not initialized.  
- Products are indexed via `/catalog/seed` (mock products by default, or pushed to Proposales if real API is configured).  
- Index can be refreshed on demand via `/catalog/sync` (fetches real products from Proposales when a valid key is provided).  

## Evaluation Methodology
- **Heuristic**: budget range match, missing accommodation flag, guest count presence.  
- **LLM (GROQ)**: 4 dimensions (completeness, relevance, pricing accuracy, coherence) each 1‑10 + free-text review.  
- **Combined score** = average of LLM dimensions; heuristic flags shown separately.  
- Robust fallback: if LLM evaluation or block generation fails, fallback blocks and scores are automatically generated from retrieved products.

## Production Considerations
- **Scale**: ChromaDB is suitable for thousands of products; for larger scale, migrate to Pinecone/Qdrant. Use async task queue (Celery) for long pipelines.  
- **Cost**: GROQ offers a generous free tier; for high volume, route simple RFPs to `llama-3.1-8b-instant` (cheaper/faster).  
- **Observability**: Add LangSmith tracing, structured logging, and Sentry for errors.  
- **Security**: Input sanitisation, rate limiting, API key rotation, prompt injection protection via explicit JSON schemas.  
- Retrieval is now hybrid BM25 + embeddings, normalized, and re-ranked automatically to reduce mismatches and errors.  

## Trade‑offs & Future Work
- *Cut*: Real Proposales API integration is fully implemented and can be enabled by setting `PROPOSALES_API_KEY` and `PROPOSALES_COMPANY_ID` in `.env`. By default, the system uses a mock to avoid external dependencies.  
- *Would improve*: Better budget parsing, hybrid search (BM25 + semantic) with normalized scores, automatic re-ranking, fallback block generation, user feedback loop for fine-tuning evaluation.  
- *Honest*: The evaluation LLM is not fine‑tuned; for production we’d gather human‑rated examples. ChromaDB persistence is local – for distributed deployments use a cloud vector DB.