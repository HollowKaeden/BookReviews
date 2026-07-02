from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения. Читаются из переменных окружения и файла .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str

    # Доступ владельца к /admin и мутирующим ручкам (HTTP Basic).
    # Пароль обязателен и без дефолта приложение не стартует без него
    admin_username: str = "admin"
    admin_password: str

    # Куда складываем загруженные обложки и предел размера файла.
    upload_dir: str = "uploads"
    max_upload_bytes: int = 5 * 1024 * 1024  # 5 MB


settings = Settings()
