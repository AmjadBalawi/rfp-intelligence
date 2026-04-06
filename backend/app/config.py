from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    anthropic_api_key: str = "placeholder"
    proposales_api_key: str = "placeholder"
    groq_api_key: str = "placeholder"
    proposales_company_id: int | None = None   # numeric company ID
    chroma_persist_dir: str = "./chroma_db"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()