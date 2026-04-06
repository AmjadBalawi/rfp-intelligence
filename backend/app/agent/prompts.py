EXTRACT_PROMPT = """Extract event requirements from the RFP as JSON.
Output format: {{"dates": "...", "guest_count": int, "budget": {{"min": int, "max": int}}, "event_type": "...", "special_requests": [...], "rooms_needed": [...], "catering_needed": [...], "av_needed": [...]}}
RFP: {rfp}"""

PLAN_PROMPT = """Given extracted requirements and retrieved products, create a proposal plan.
Output **only** a valid JSON object with this exact structure:
{{"title": "Event Proposal", "sections": [{{"title": "section name", "product_ids": [1,2]}}], "total_estimated_cost": 0}}

Requirements: {extracted}
Retrieved products: {products}
Plan:"""

GENERATE_BLOCK_PROMPT = """Write a short, persuasive block for a proposal.
Product: {product}
Context: {context}
Requirements: {requirements}
Write 2-3 sentences including key features and price."""

EVALUATE_PROMPT = """Score the proposal against the original RFP.
Dimensions: completeness (1-10), relevance (1-10), pricing_accuracy (1-10), coherence (1-10).
Output **only** a valid JSON object with this structure:
{{"scores": {{"completeness": 8, "relevance": 7, "pricing_accuracy": 9, "coherence": 8}}, "flags": [], "overall_review": "Brief review"}}

RFP: {rfp}
Proposal: {proposal}
Evaluation:"""