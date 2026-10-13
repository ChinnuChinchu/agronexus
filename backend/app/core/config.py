from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "AgroNexus API"

    CORS_ORIGINS: str = "http://localhost:4200"
    
    ENVIRONMENT: str = "development"
    
    OPENWEATHER_API_KEY: str = ""
    OPENWEATHER_BASE_URL: str = "https://api.openweathermap.org"
    WEATHER_TIMEOUT_SECONDS: float = 10.0
    
    DATAGOV_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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