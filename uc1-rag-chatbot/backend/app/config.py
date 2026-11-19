from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    database_url: str = "sqlite:///./uc1.db"
    app_api_key: str
    gemini_api_key: str
    gemini_model: str = "gemini-3.1-flash-lite"
    # "vector" = vector search with keyword fallback; "hybrid" = keywords plus vectors merged
    search_backend: str = "vector"


settings = Settings()
