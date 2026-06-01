from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FICCT Diagramador API"
    app_env: str = "development"
    app_debug: bool = True
    api_prefix: str = "/api"
    protected_admin_email: str = "administrador@acb.com"
    protected_admin_password: str = "123ppp+++"
    protected_admin_full_name: str = "Administrador ACB"
    protected_admin_phone: str = "70000000"
    workshop_initial_password: str = "acb123*"

    postgres_db: str = "diagramador"
    postgres_user: str = "diagramador"
    postgres_password: str = "diagramador"
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_connect_timeout: int = 5
    uploads_dir: str = "uploads"
    whisper_enabled: bool = True
    whisper_model: str = "base"
    whisper_language: str | None = "es"
    photo_classification_enabled: bool = False
    photo_classification_model: str = "gpt-5-mini"
    fcm_enabled: bool = False
    firebase_credentials_path: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
