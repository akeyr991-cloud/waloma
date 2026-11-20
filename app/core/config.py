from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "WALOMA"
    app_env: str = "development"
    secret_key: str = "development-only-change-this-secret-key"
    access_token_expire_minutes: int = 30
    database_url: str = "sqlite:///./waloma.db"
    cors_origins: str = "http://localhost:8000"
    bootstrap_admin_email: str = ""
    bootstrap_admin_password: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
