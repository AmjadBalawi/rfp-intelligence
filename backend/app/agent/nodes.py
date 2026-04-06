import json
import re
import httpx
from langchain_groq import ChatGroq
from app.config import settings
from app.agent.state import AgentState
from app.agent.prompts import *
from app.retrieval.vectorstore import multi_query_retrieve
from app.evaluation.scorer import evaluate_proposal

llm = ChatGroq(
    api_key=settings.groq_api_key,
    model="llama-3.3-70b-versatile",
    temperature=0.1
)

def _clean_json(content: str) -> str:
    """Remove markdown code fences and extra whitespace."""
    content = content.strip()
    # Remove ```json or ``` at start
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()


def create_proposal_in_proposales(plan: dict, blocks: list) -> str:
    # If no real key or company ID, fallback to mock
    if (settings.proposales_api_key.startswith("placeholder") or
            not settings.proposales_company_id):
        return "mock-uuid-12345"

    payload = {
        "company_id": settings.proposales_company_id,
        "language": "en",
        "title_md": plan.get("title", "Event Proposal"),
        "blocks": [
            {
                "content_id": int(block["product_id"]),
                "type": "product-block"
            }
            for block in blocks
        ]
    }

    print(f"Proposal payload: {json.dumps(payload, indent=2)}")

    try:
        with httpx.Client() as client:
            headers = {
                "Authorization": f"Bearer {settings.proposales_api_key}",
                "Content-Type": "application/json"
            }
            response = client.post(
                "https://api.proposales.com/v3/proposals",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            if response.status_code != 200:
                print(f"Proposales error response: {response.text}")
            response.raise_for_status()
            data = response.json()
            return data.get("proposal", {}).get("uuid", "error-no-uuid")
    except Exception as e:
        print(f"Proposales API error: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response text: {e.response.text}")
        return "error-uuid"

def extract_node(state: AgentState):
    prompt = EXTRACT_PROMPT.format(rfp=state["rfp_text"])
    response = llm.invoke(prompt)
    try:
        cleaned = _clean_json(response.content)
        extracted = json.loads(cleaned)
    except Exception as e:
        print(f"Extract parse error: {e}")
        extracted = {"error": "Failed to parse", "raw": response.content}
    return {"extracted": extracted}

def retrieve_node(state: AgentState):
    products = multi_query_retrieve(state["extracted"])
    return {"retrieved_products": products}

def plan_node(state: AgentState):
    extracted = state.get("extracted")
    products = state.get("retrieved_products")
    if not extracted or not products:
        print(f"Missing data: extracted={extracted}, products={products}")
        return {"plan": {"title": "Event Proposal", "sections": [], "total_estimated_cost": 0}}
    prompt = PLAN_PROMPT.format(
        extracted=json.dumps(state["extracted"]),
        products=json.dumps(state["retrieved_products"])
    )
    try:
        response = llm.invoke(prompt)
    except Exception as e:
        print(f"Plan node LLM error: {e}")
        return {"plan": {"title": "Error", "sections": [], "total_estimated_cost": 0}}
    try:
        cleaned = _clean_json(response.content)
        try:
            plan = json.loads(cleaned)
        except Exception as e:
            print(f"Plan JSON error: {e}\nRaw: {cleaned}")
            plan = {"title": "Fallback Plan", "sections": [], "total_estimated_cost": 0}
        # Ensure required keys exist
        if "sections" not in plan:
            plan["sections"] = []
        if "total_estimated_cost" not in plan:
            plan["total_estimated_cost"] = 0
        if "title" not in plan:
            plan["title"] = "Event Proposal"
    except Exception as e:
        print(f"Plan parse error: {e}")
        plan = {"title": "Event Proposal", "sections": [], "total_estimated_cost": 0}
    return {"plan": plan}

def generate_node(state: AgentState):
    blocks = []
    for section in state["plan"].get("sections", []):
        for pid in section.get("product_ids", []):
            # Find product by id (convert to string for comparison)
            product = next(
                (p for p in state["retrieved_products"] if str(p.get("id")) == str(pid)),
                None
            )
            if not product:
                continue
            prompt = GENERATE_BLOCK_PROMPT.format(
                product=json.dumps(product),
                context=section["title"],
                requirements=json.dumps(state["extracted"])
            )
            content = llm.invoke(prompt).content
            blocks.append({
                "section": section["title"],
                "product_id": pid,
                "content": content
            })
    return {"generated_blocks": blocks}

def create_proposal_node(state: AgentState):
    uuid = create_proposal_in_proposales(state["plan"], state["generated_blocks"])
    return {"proposal_uuid": uuid}

def evaluate_node(state: AgentState):
    evaluation = evaluate_proposal(state["rfp_text"], state["generated_blocks"], state["plan"])
    return {"evaluation": evaluation}