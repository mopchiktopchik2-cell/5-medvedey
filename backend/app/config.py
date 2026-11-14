from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_port: int = 8000
    database_url: str = "sqlite:///./data/app.db"
    cors_origins: str = "http://localhost:5173"

    # Авторизация
    secret_key: str = "dev-secret-change-me-in-production"
    access_token_ttl_minutes: int = 720

    # Демо-данные: создаются при пустой базе
    seed_demo_data: bool = True

    # Куда складывать сгенерированные PDF, если SMTP не настроен
    outbox_dir: str = "./data/outbox"

    # Загруженные файлы (логотип цеха для КП)
    uploads_dir: str = "./data/uploads"

    # SMTP для отправки КП. Пока хост не задан, письма складываются в outbox.
    smtp_host: str | None = None
    smtp_port: int = 465
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_use_ssl: bool = True
    smtp_starttls: bool = False
    smtp_timeout_seconds: int = 15

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}


settings = Settings()
