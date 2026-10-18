from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = ""
    postgres_user: str = ""
    postgres_password: str = ""
    postgres_db: str = ""
    jwt_secret_key: str = ""
    jwt_algorithm: str = ""
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7


settings = Settings()
