from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    database_url: str = "sqlite:///./uc1.db"
    app_api_key: str
    gemini_api_key: str
    gemini_model: str = "gemini-3.1-flash-lite"
    # Used when the main model is overloaded or no longer served. Empty turns the fallback off.
    gemini_fallback_model: str = "gemini-3.5-flash-lite"
    # "vector" = local vector search with keyword fallback; "hybrid" = keywords plus vectors merged;
    # "pinecone" = Pinecone first, then the local vector search if Pinecone cannot be used
    search_backend: str = "vector"
    pinecone_api_key: str = ""
    pinecone_index_host: str = ""  # shown in the Pinecone console, like xxxx.svc.xxxx.pinecone.io
    pinecone_namespace: str = "uc1"


settings = Settings()
