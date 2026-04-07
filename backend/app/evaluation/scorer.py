import json
import logging
import re
from langchain_groq import ChatGroq
from app.config import settings
from app.agent.prompts import EVALUATE_PROMPT

logger = logging.getLogger(__name__)
llm = ChatGroq(
    api_key=settings.groq_api_key,
    model="llama-3.1-8b-instant",
    temperature=0.0
)

def _clean_json(content: str) -> str:
    """Extract JSON from markdown or plain text."""
    content = content.strip()
    # Remove markdown code fences
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    # Try to find JSON object using regex
    match = re.search(r'\{.*\}(?=\s*$|\s*```)', content, re.DOTALL)
    if match:
        content = match.group(0)
    return content.strip()

def heuristic_checks(rfp: str, proposal_blocks: list, plan: dict) -> dict:
    flags = []
    rfp_lower = rfp.lower()
    if "accommodation" not in str(proposal_blocks).lower() and ("hotel" in rfp_lower or "room" in rfp_lower):
        flags.append("Missing accommodation options")
    budget_match = True  # placeholder
    return {"flags": flags, "budget_match": budget_match}

def evaluate_proposal(rfp: str, proposal_blocks: list, plan: dict) -> dict:
    heuristic = heuristic_checks(rfp, proposal_blocks, plan)
    # Limit proposal length to avoid token overflow
    proposal_text = json.dumps(proposal_blocks[:3], indent=2)
    prompt = EVALUATE_PROMPT.format(rfp=rfp, proposal=proposal_text)

    # Retry up to 2 times
    for attempt in range(2):
        try:
            response = llm.invoke(prompt)
            raw = response.content
            logger.info(f"Evaluation raw response (attempt {attempt+1}): {raw[:300]}")
            cleaned = _clean_json(raw)
            llm_scores = json.loads(cleaned)
            # Validate required fields
            if "scores" not in llm_scores:
                llm_scores["scores"] = {}
            required = ["completeness", "relevance", "pricing_accuracy", "coherence"]
            for k in required:
                if k not in llm_scores["scores"]:
                    llm_scores["scores"][k] = 5
            llm_scores.setdefault("flags", [])
            llm_scores.setdefault("overall_review", "No review provided.")
            break  # Success
        except Exception as e:
            logger.exception(f"Evaluation parse error (attempt {attempt+1}): {e}")
            if attempt == 0:
                # Add extra instruction to enforce JSON output
                prompt += "\n\nRemember: Output **only** the JSON object, no other text."
            else:
                # Final fallback: use heuristic scores
                base_score = 7.0 if heuristic["budget_match"] else 5.0
                llm_scores = {
                    "scores": {k: base_score for k in required},
                    "flags": heuristic["flags"],
                    "overall_review": "Evaluation performed with fallback due to parsing error."
                }

    combined = sum(llm_scores["scores"].values()) / 4.0
    return {
        "heuristic": heuristic,
        "llm": llm_scores,
        "combined_score": combined
    }