from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "botica"
    MYSQL_PASSWORD: str = "botica123!"
    MYSQL_DB: str = "botica"
    SQLALCHEMY_ECHO: bool = False  # True si quieres ver las queries

    # Lee variables desde .env en la raíz del proyecto
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
