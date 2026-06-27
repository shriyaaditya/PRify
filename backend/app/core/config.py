from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "PRify"
    OPENAI_API_KEY: str = ""
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/prify"
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    GITHUB_APP_ID: str = ""
    GITHUB_PRIVATE_KEY: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    JWT_SECRET: str = "changeme"

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

settings = Settings()
