import json
import re
from langchain_groq import ChatGroq
from app.config import settings
from app.agent.prompts import EVALUATE_PROMPT

llm = ChatGroq(
    api_key=settings.groq_api_key,
    model="llama-3.3-70b-versatile",
    temperature=0.0
)

def _clean_json(content: str) -> str:
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()

def heuristic_checks(rfp: str, proposal_blocks: list, plan: dict) -> dict:
    flags = []
    rfp_lower = rfp.lower()
    if "accommodation" not in str(proposal_blocks).lower() and ("hotel" in rfp_lower or "room" in rfp_lower):
        flags.append("Missing accommodation options")
    # Budget check: compare plan total with extracted budget if available
    budget_match = True
    # Simple placeholder
    return {"flags": flags, "budget_match": budget_match}

def evaluate_proposal(rfp: str, proposal_blocks: list, plan: dict) -> dict:
    heuristic = heuristic_checks(rfp, proposal_blocks, plan)
    prompt = EVALUATE_PROMPT.format(
        rfp=rfp,
        proposal=json.dumps(proposal_blocks[:3])  # limit length
    )
    try:
        response = llm.invoke(prompt)
        cleaned = _clean_json(response.content)
        llm_scores = json.loads(cleaned)
        # Ensure scores dict has required keys
        scores = llm_scores.get("scores", {})
        required = ["completeness", "relevance", "pricing_accuracy", "coherence"]
        for k in required:
            if k not in scores:
                scores[k] = 5
        llm_scores["scores"] = scores
    except Exception as e:
        print(f"Evaluation LLM error: {e}")
        llm_scores = {
            "scores": {"completeness": 7, "relevance": 7, "pricing_accuracy": 7, "coherence": 7},
            "flags": [],
            "overall_review": "Evaluation performed with fallback due to parsing error."
        }
    combined = sum(llm_scores["scores"].values()) / 4.0
    return {
        "heuristic": heuristic,
        "llm": llm_scores,
        "combined_score": combined
    }