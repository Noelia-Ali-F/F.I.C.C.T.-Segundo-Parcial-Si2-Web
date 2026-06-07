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

    # JWT / Multi-tenant
    jwt_secret_key: str = "ficct-jwt-secret-change-in-production-2026"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    default_tenant_name: str = "Tenant Principal"

    # SaaS Master database (tenant registry — separate DB from diagramador)
    saas_master_db: str = "saas_master"
    # Initial password assigned to SUPERADMIN_TENANT on empresa registration
    superadmin_tenant_initial_password: str = "acb2026*saas"

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

    @property
    def saas_master_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.saas_master_db}"
        )

    @property
    def postgres_maintenance_url(self) -> str:
        """Connects to 'postgres' maintenance DB — used for CREATE DATABASE commands."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/postgres"
        )


settings = Settings()
