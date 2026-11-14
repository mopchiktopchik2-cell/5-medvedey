from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Значения, с которыми нельзя выходить в production: ключ подписи JWT
# должен быть случайным и длинным, иначе токен можно подделать.
WEAK_SECRETS = {
    "",
    "secret",
    "dev-secret-change-me-in-production",
    "change-me-in-production",
}


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
    # None — secure-cookie включаются автоматически в production.
    # false нужен, если сервис временно работает по HTTP без TLS.
    cookie_secure: bool | None = None

    # Защита от перебора пароля
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15

    # Сколько живёт публичная ссылка на КП
    share_token_ttl_days: int = 30

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

    @field_validator("cookie_secure", mode="before")
    @classmethod
    def _empty_cookie_secure_is_none(cls, value: object) -> object:
        """Пустая переменная окружения означает «решить автоматически»."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @property
    def secure_cookies(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.is_production

    def validate_production(self) -> None:
        """Не даём запустить production с дефолтным ключом подписи JWT."""
        if not self.is_production:
            return
        if self.secret_key in WEAK_SECRETS or len(self.secret_key) < 32:
            raise RuntimeError(
                "SECRET_KEY не задан или слишком короткий. Сгенерируйте ключ: "
                'python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )


settings = Settings()
