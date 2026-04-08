# ----------------- Extract Prompt -----------------
EXTRACT_PROMPT = """Extract all event requirements from the RFP below as a JSON object.
Output **only** valid JSON – no extra text, no markdown, no explanation.
Use the exact keys and types shown. If a field is missing, use empty string, 0, or empty list.

Format:
{{
  "dates": "...",                       # string or date range
  "guest_count": 0,                     # integer
  "budget": {{"min": 0, "max": 0}},     # object with min/max integers
  "event_type": "...",                  # string
  "special_requests": [],               # list of strings
  "rooms_needed": [],                   # list of strings
  "catering_needed": [],                # list of strings
  "av_needed": []                       # list of strings
}}

RFP: {rfp}
JSON:"""

# ----------------- Plan Prompt -----------------
PLAN_PROMPT = """You are an event proposal planner AI. Based on the extracted requirements and the list of retrieved products (each product has an "id" field), create a proposal plan.

Requirements (extracted from RFP): {extracted}
Retrieved products: {products}

Instructions:
1. Select relevant product IDs for each needed category (venue, catering, AV, etc.).
2. Assign products only if they match the requirements (e.g., guest count, type).
3. Calculate a rough total_estimated_cost (sum of product prices if available).
4. Output **only** valid JSON – no markdown, no explanation.
5. Maintain the exact JSON structure below, even if a section is empty.

Structure:
{{
  "title": "Event Proposal",
  "sections": [
    {{"title": "Meeting Room", "product_ids": [123, 456]}},
    {{"title": "Catering", "product_ids": [789]}},
    {{"title": "AV", "product_ids": []}}
  ],
  "total_estimated_cost": 0
}}

Plan JSON:"""

# ----------------- Generate Block Prompt -----------------
GENERATE_BLOCK_PROMPT = """You are writing a persuasive proposal block (2-3 sentences) for a product.
Include key features, price, and how it meets the extracted requirements.

Product: {product}
Context/Section: {context}
Requirements: {requirements}

Instructions:
- Output plain text only (no markdown, no JSON).
- Be concise, clear, and persuasive.
- Mention price if available.
- Highlight why the product is suitable for the event.
Block:"""

# ----------------- Evaluate Prompt -----------------
EVALUATE_PROMPT = """Evaluate the generated proposal against the original RFP.
Score objectively on dimensions 1-10: completeness, relevance, pricing_accuracy, coherence.

Instructions:
- Output **only** valid JSON, no extra text or markdown.
- Include flags if any major issues exist.
- Provide a short overall_review (1-2 sentences).

Structure:
{{
  "scores": {{"completeness": 8, "relevance": 7, "pricing_accuracy": 9, "coherence": 8}},
  "flags": [],
  "overall_review": "Brief review"
}}

RFP: {rfp}
Proposal (first few blocks): {proposal}
Evaluation JSON:"""