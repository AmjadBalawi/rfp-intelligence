import httpx
from app.config import settings


def create_proposal_in_proposales(plan: dict, blocks: list) -> str:
    """Create a real proposal in Proposales via API."""
    # If no real key or company ID, fallback to mock
    if (settings.proposales_api_key.startswith("placeholder") or
            not settings.proposales_company_uuid):
        return "mock-uuid-12345"

    # Build the payload according to Proposales API spec
    payload = {
        "company_id": int(settings.proposales_company_uuid),  # Required number
        "language": "en",  # Required two-letter code
        "title_md": plan.get("title", "Event Proposal"),  # Use title_md, not name
        "blocks": [
            {
                "content_id": int(block["product_id"]),  # Required product ID
                "type": "product-block"  # Required type
            }
            for block in blocks
        ]
        # Optional: add description_md, recipient, data, etc.
        # "data": {"total_estimated_cost": plan.get("total_estimated_cost", 0)}  # Store custom data if needed
    }

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
            response.raise_for_status()
            data = response.json()
            # The response likely contains a 'proposal' object with 'uuid'
            return data.get("proposal", {}).get("uuid", "error-no-uuid")
    except Exception as e:
        print(f"Proposales API error: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response text: {e.response.text}")
        return "error-uuid"