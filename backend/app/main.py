from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

app = FastAPI(title="RFP Intelligence")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://rfp-intelligence-2.onrender.com"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    expose_headers=["Content-Type"],
)
app.include_router(router, prefix="/api")

@app.get("/health")
def health():
    return {"ok": True}