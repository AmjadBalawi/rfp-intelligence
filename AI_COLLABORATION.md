# AI Collaboration Log – Proposal Intelligence System

## 1. Starting point: single‑prompt disaster

**My prompt:**  
> “I have an RFP and a list of hotel products. Write a proposal in one go.”

**AI output:** A long, generic proposal that ignored pricing and often hallucinated products.  
**Lesson:** One‑shot prompting fails for complex, structured tasks. Need decomposition.

---

## 2. Designing a multi‑agent pipeline

**My prompt:**  
> “Design a LangGraph pipeline for RFP processing with separate nodes: extract requirements, retrieve relevant products, plan sections, generate copy, create proposal, evaluate. Use Claude 3.”

**AI output:** Provided the state schema, node stubs, and suggested using `StateGraph`. This became the backbone of the system.  
**Iteration:** Later swapped Claude 3 for GROQ (`llama-3.3-70b`) because of cost and speed.

---

## 3. Retrieval: from dumb keyword to multi‑query semantic

**My prompt:**  
> “Single‑query retrieval gives poor results for mixed requirements (venue + catering + AV). How can I improve?”

**AI suggested:** Multi‑query – one query per category (venue, catering, AV, accommodation), then deduplicate by highest similarity.  
**Implementation:** ChromaDB + `all-MiniLM-L6-v2` embeddings. This lifted relevance dramatically.

---

## 4. Handling LLM JSON failures

**Problem:** The LLM sometimes returned markdown‑wrapped JSON (````json ... ````) or extra text, crashing `json.loads()`.  

**My prompt:**  
> “How can I robustly parse LLM output that may contain markdown code fences or stray commentary?”

**AI solution:** `_clean_json()` helper – strip backticks, remove `json` language hint, and try‑except with fallback to raw content. Implemented in every node.

---

## 5. Evaluation: heuristic + LLM scoring

**My prompt:**  
> “Give me a hybrid evaluator: heuristic checks for obvious gaps (budget, missing accommodation) + LLM scoring on 4 dimensions (completeness, relevance, pricing accuracy, coherence).”

**AI output:** Provided `heuristic_checks()` and a prompt for LLM scoring, plus a fallback if the LLM response fails. The final combined score is the average of the four dimensions.

---

## 6. Proposales API integration (the painful part)

**My prompt (after getting 400 errors):**  
> “The API keeps rejecting my payload with ‘Unknown error’. The documentation says `company_id` and `language` are required, and `blocks` must contain `content_id`. What am I missing?”

**AI:** Helped debug step by step:  
- First, the `company_id` was wrong (I was using a placeholder).  
- Then, product IDs didn’t exist in Proposales.  
- Then, I discovered that `/catalog/seed` was creating duplicates because I ran it multiple times.

**Final working payload:**  
```json
{
  "company_id": 5263,
  "language": "en",
  "title_md": "Event Proposal",
  "blocks": [{"content_id": 178071, "type": "product-block"}]
}