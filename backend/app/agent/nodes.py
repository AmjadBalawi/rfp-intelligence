import json
import logging
import httpx
import numpy as np
from langchain_groq import ChatGroq
from app.config import settings
from app.agent.state import AgentState
from app.agent.prompts import *
from app.retrieval.vectorstore import multi_query_retrieve
from app.evaluation.scorer import evaluate_proposal

# ------------------ Setup Logging ------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------ LLM Setup ------------------
llm = ChatGroq(
    api_key=settings.groq_api_key,
    model="llama-3.1-8b-instant",
    temperature=0.1
)

# ------------------ JSON Parsing Utility ------------------
def _clean_json(content: str) -> str:
    """Remove markdown fences and extra whitespace."""
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()

def safe_json_parse(text: str, retries: int = 2) -> dict:
    """Parse JSON with retries and cleaning."""
    for _ in range(retries):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            text = _clean_json(text)
    logger.warning("Failed to parse JSON after retries")
    return {}

# ------------------ Proposales API ------------------
def create_proposal_in_proposales(plan: dict, blocks: list) -> str:
    if settings.proposales_api_key.startswith("placeholder") or not settings.proposales_company_id:
        return "mock-uuid-12345"

    payload = {
        "company_id": settings.proposales_company_id,
        "language": "en",
        "title_md": plan.get("title", "Event Proposal"),
        "blocks": [{"content_id": int(block["product_id"]), "type": "product-block"} for block in blocks]
    }

    logger.info(f"Proposal payload: {json.dumps(payload, indent=2)}")
    try:
        with httpx.Client() as client:
            headers = {"Authorization": f"Bearer {settings.proposales_api_key}", "Content-Type": "application/json"}
            response = client.post("https://api.proposales.com/v3/proposals", json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            return data.get("proposal", {}).get("uuid", "error-no-uuid")
    except Exception as e:
        logger.exception(f"Proposales API error: {e}")
        return "error-uuid"

# ------------------ Agent Nodes ------------------
def extract_node(state: AgentState):
    logger.info("=== extract_node ===")
    prompt = EXTRACT_PROMPT.format(rfp=state["rfp_text"])
    response = llm.invoke(prompt)
    logger.info(f"Raw extract response (first 500 chars): {response.content[:500]}")
    extracted = safe_json_parse(response.content)
    logger.info(f"Extracted: {extracted}")
    return {"extracted": extracted}

def retrieve_node(state: AgentState):
    logger.info("=== retrieve_node ===")
    extracted = state.get("extracted", {})
    if not extracted:
        logger.warning("No extracted requirements, returning empty products")
        return {"retrieved_products": [], "retrieval_debug": {}}

    products = multi_query_retrieve(extracted, top_k=8)
    logger.info(f"Retrieved {len(products)} products")

    categories = {}
    for p in products:
        cat = p.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    logger.info(f"Category distribution: {categories}")
    return {"retrieved_products": products, "retrieval_debug": {"count": len(products), "categories": categories}}

def plan_node(state: AgentState):
    logger.info("=== plan_node ===")
    extracted = state.get("extracted", {})
    products = state.get("retrieved_products", [])

    if not extracted or not products:
        logger.error(f"Missing data: extracted={extracted}, products={products}")
        return {"plan": {"title": "Event Proposal", "sections": [], "total_estimated_cost": 0}}

    top_products = products[:6]
    prompt = PLAN_PROMPT.format(extracted=json.dumps(extracted), products=json.dumps(top_products))
    logger.info(f"Prompt length: {len(prompt)}")

    try:
        response = llm.invoke(prompt)
        logger.info(f"Raw plan response (first 500 chars): {response.content[:500]}")
        plan = safe_json_parse(response.content)

        # Ensure required keys
        plan.setdefault("sections", [])
        plan.setdefault("total_estimated_cost", 0)
        plan.setdefault("title", "Event Proposal")

        # Validate product IDs
        valid_ids = {str(p.get("id")) for p in products}
        for section in plan["sections"]:
            section["product_ids"] = [pid for pid in section.get("product_ids", []) if str(pid) in valid_ids]
        plan["sections"] = [s for s in plan["sections"] if s.get("product_ids")]

        if not plan["sections"]:
            raise ValueError("No valid sections after filtering")

        logger.info(f"LLM plan created with {len(plan['sections'])} sections")

    except Exception as e:
        logger.exception(f"Plan node error: {e}, using fallback plan")
        # Build fallback plan
        categories = {}
        for p in products:
            cat = p.get("category", "other")
            categories.setdefault(cat, []).append(p)

        needed_cats = extracted.get("rooms_needed", []) and ["venue"] or []
        if extracted.get("catering_needed"):
            needed_cats.append("catering")
        if extracted.get("av_needed"):
            needed_cats.append("av")
        if not needed_cats:
            needed_cats = list(categories.keys())[:3]

        fallback_sections = []
        total_cost = 0
        for cat in needed_cats:
            if categories.get(cat):
                prod = categories[cat][0]
                fallback_sections.append({"title": cat.capitalize(), "product_ids": [prod["id"]]})
                total_cost += prod.get("price_eur", 0)

        plan = {"title": "Event Proposal (Auto-Generated)", "sections": fallback_sections, "total_estimated_cost": total_cost}
        logger.info(f"Fallback plan created with {len(plan['sections'])} sections")

    return {"plan": plan}

def generate_node(state: AgentState):
    logger.info("=== generate_node ===")
    blocks = []
    plan = state.get("plan", {})
    products = state.get("retrieved_products", [])
    sections = plan.get("sections", [])
    logger.info(f"Generating blocks for {len(sections)} sections")

    for section in sections:
        for pid in section.get("product_ids", []):
            product = next((p for p in products if str(p.get("id")) == str(pid)), None)
            if not product:
                logger.warning(f"Product ID {pid} not found")
                continue
            prompt = GENERATE_BLOCK_PROMPT.format(
                product=json.dumps(product),
                context=section["title"],
                requirements=json.dumps(state.get("extracted", {}))
            )
            try:
                content = llm.invoke(prompt).content
                blocks.append({"section": section["title"], "product_id": pid, "content": content})
                logger.info(f"Generated block for product {pid}")
            except Exception as e:
                logger.exception(f"Failed to generate block for product {pid}: {e}")

    if not blocks and products:
        first = products[0]
        blocks.append({
            "section": "General",
            "product_id": first["id"],
            "content": f"We recommend {first['title']} - {first.get('description', '')} at €{first.get('price_eur', 0)}."
        })
        logger.info("Fallback block created")

    logger.info(f"Generated {len(blocks)} proposal blocks")
    return {"generated_blocks": blocks}

def create_proposal_node(state: AgentState):
    logger.info("=== create_proposal_node ===")
    uuid = create_proposal_in_proposales(state["plan"], state["generated_blocks"])
    logger.info(f"Proposal UUID: {uuid}")
    return {"proposal_uuid": uuid}

def evaluate_node(state: AgentState):
    logger.info("=== evaluate_node ===")
    evaluation = evaluate_proposal(state["rfp_text"], state["generated_blocks"], state["plan"])
    logger.info(f"Evaluation combined score: {evaluation.get('combined_score')}")
    return {"evaluation": evaluation}