from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    github_token: str = ""
    cache_ttl_seconds: int = 900  # 15 minutes
    db_path: str = "portfolio_cache.db"
    github_rest_url: str = "https://api.github.com"
    github_graphql_url: str = "https://api.github.com/graphql"
    http_timeout: float = 15.0


settings = Settings()
