import json
import asyncio
import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.agent.graph import build_graph
from app.config import settings
from app.retrieval.vectorstore import index_products

router = APIRouter()


async def event_stream(rfp_text: str):
    graph = build_graph()
    state = {"rfp_text": rfp_text}
    for event in graph.stream(state):
        node_name = list(event.keys())[0]
        yield f"data: {json.dumps({'node': node_name, 'state': event[node_name]})}\n\n"
        await asyncio.sleep(0.01)


@router.post("/generate")
async def generate_proposal(rfp: dict):
    return StreamingResponse(event_stream(rfp["text"]), media_type="text/event-stream")


@router.post("/catalog/seed")
async def seed_catalog():
    # Local product definitions (used for retrieval & evaluation)
    local_products = [
        {"id": 1, "title": "Grand Ballroom", "description": "Elegant ballroom for 200 guests", "category": "venue", "price_eur": 2500, "available_capacity": 200},
        {"id": 2, "title": "Executive Boardroom", "description": "Private boardroom for 14", "category": "venue", "price_eur": 800, "available_capacity": 14},
        {"id": 3, "title": "Garden Terrace", "description": "Outdoor terrace for ceremonies", "category": "venue", "price_eur": 1500, "available_capacity": 120},
        {"id": 4, "title": "Premium Lunch Package", "description": "Three-course lunch with coffee", "category": "catering", "price_eur": 45, "available_capacity": 200},
        {"id": 5, "title": "Evening Dinner Buffet", "description": "Hot and cold buffet", "category": "catering", "price_eur": 65, "available_capacity": 150},
        {"id": 6, "title": "HD Projector & Screen", "description": "High-definition projector", "category": "av", "price_eur": 200, "available_capacity": 0},
        {"id": 7, "title": "Sound System Package", "description": "Wireless microphones and speakers", "category": "av", "price_eur": 350, "available_capacity": 0},
        {"id": 8, "title": "Deluxe King Room", "description": "Spacious room with king bed", "category": "accommodation", "price_eur": 180, "available_capacity": 40},
        {"id": 9, "title": "Executive Suite", "description": "Suite with separate living area", "category": "accommodation", "price_eur": 320, "available_capacity": 10},
        {"id": 10, "title": "Wedding Package", "description": "Full wedding coordination", "category": "service", "price_eur": 5000, "available_capacity": 0},
    ]

    # If real API key and company ID are provided, push products to Proposales
    if (not settings.proposales_api_key.startswith("placeholder")
        and settings.proposales_company_id):
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {settings.proposales_api_key}"}
            for p in local_products:
                payload = {
                    "company_id": settings.proposales_company_id,
                    "language": "en",
                    "title": p["title"],
                    "description": p["description"]
                }
                resp = await client.post("https://api.proposales.com/v3/content", json=payload, headers=headers)
                if resp.status_code in (200, 201):
                    created = resp.json()
                    # The API returns { "data": { "variation_id": ..., "product_id": ... } }
                    real_id = created.get("data", {}).get("variation_id")
                    if real_id:
                        p["id"] = real_id
                        print(f"Updated product '{p['title']}' with real ID {real_id}")
                    else:
                        print(f"Warning: No variation_id returned for '{p['title']}'")
                else:
                    print(f"Failed to create product '{p['title']}': {resp.text}")

    # Index the products (now with real IDs if available) into ChromaDB
    index_products(local_products)
    return {"status": "seeded", "count": len(local_products), "real_ids": not settings.proposales_api_key.startswith("placeholder")}


@router.post("/catalog/sync")
async def sync_catalog():
    if settings.proposales_api_key.startswith("placeholder"):
        return {"status": "mock sync - no real API", "count": 0}

    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {settings.proposales_api_key}"}
        resp = await client.get("https://api.proposales.com/v3/content", headers=headers)
        data = resp.json()

        # Proposales API returns {"data": [...]}
        if isinstance(data, dict) and "data" in data:
            products = data["data"]
        elif isinstance(data, list):
            products = data
        else:
            raise ValueError(f"Unexpected response structure: {data}")

        if not isinstance(products, list):
            raise ValueError("Products is not a list")

        if len(products) == 0:
            return {"status": "synced", "count": 0, "message": "No products found in Proposales"}

    index_products(products)
    return {"status": "synced", "count": len(products)}