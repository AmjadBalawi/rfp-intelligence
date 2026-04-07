EXTRACT_PROMPT = """Extract event requirements from the RFP as JSON.
Output **only** a valid JSON object – no extra text, no markdown.
Format:
{
  "dates": "...",
  "guest_count": 0,
  "budget": {"min": 0, "max": 0},
  "event_type": "...",
  "special_requests": [],
  "rooms_needed": [],
  "catering_needed": [],
  "av_needed": []
}
RFP: {rfp}
JSON:"""

PLAN_PROMPT = """You are a proposal planner. Based on the extracted requirements and the list of retrieved products (each has an "id" field), create a proposal plan.

Requirements: {extracted}
Retrieved products: {products}

Select relevant product IDs from the retrieved products for each needed category (venue, catering, AV, etc.).
Output **only** a valid JSON object with this exact structure – no markdown, no explanation:
{
  "title": "Event Proposal",
  "sections": [
    {"title": "Meeting Room", "product_ids": [123, 456]},
    {"title": "Catering", "product_ids": [789]}
  ],
  "total_estimated_cost": 0
}
Plan JSON:"""

GENERATE_BLOCK_PROMPT = """Write a short, persuasive block for a proposal (2-3 sentences). Include key features, price, and how it meets the requirements.

Product: {product}
Context: {context}
Requirements: {requirements}
Write the block as plain text (no markdown)."""

EVALUATE_PROMPT = """Score the generated proposal against the original RFP. Be objective.
Dimensions (1-10): completeness, relevance, pricing_accuracy, coherence.
Output **only** a valid JSON object – no extra text, no markdown.
Structure:
{
  "scores": {"completeness": 8, "relevance": 7, "pricing_accuracy": 9, "coherence": 8},
  "flags": [],
  "overall_review": "Brief review"
}

RFP: {rfp}
Proposal (first few blocks): {proposal}
Evaluation JSON:"""