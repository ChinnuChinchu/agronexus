from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "AgroNexus API"
    ENVIRONMENT: str = "development"

    CORS_ORIGINS: str = "http://localhost:4200"

    OPENWEATHER_API_KEY: str = ""
    OPENWEATHER_BASE_URL: str = "https://api.openweathermap.org"
    WEATHER_TIMEOUT_SECONDS: float = 10.0
    DATAGOV_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # @field_validator("DATABASE_URL")
    # @classmethod
    # def normalise_database_url(cls, value: str) -> str:
    #     # some hosts hand out postgres://..., which SQLAlchemy 2 no longer accepts
    #     if value.startswith("postgres://"):
    #         return "postgresql://" + value[len("postgres://") :]
    #     return value
    @field_validator("DATABASE_URL")
    @classmethod
    def normalise_database_url(cls, value: str) -> str:
        # Hosts hand out postgres:// or postgresql:// URLs. Name the driver explicitly, because
        # the default driver for a bare postgresql:// URL differs between SQLAlchemy versions.
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg2://" + value[len(prefix) :]
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @model_validator(mode="after")
    def check_production_secret(self):
        if self.ENVIRONMENT.strip().lower() == "production":
            weak = len(self.SECRET_KEY) < 32 or self.SECRET_KEY.lower().startswith(
                ("change", "generate", "secret")
            )
            if weak:
                raise ValueError(
                    "SECRET_KEY must be a random string of at least 32 characters in production"
                )
        return self


settings = Settings()