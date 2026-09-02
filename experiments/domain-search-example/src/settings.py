from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    allowed_domains: str = Field(alias="ALLOWED_DOMAINS")
    searxng_base_url: str = Field(default="http://searxng:8080", alias="SEARXNG_BASE_URL")
    search_service_base_url: str = Field(
        default="http://search-service:8000",
        alias="SEARCH_SERVICE_BASE_URL",
    )
    ollama_base_url: str = Field(
        default="http://host.docker.internal:11434",
        alias="OLLAMA_BASE_URL",
    )
    ollama_model: str = Field(default="qwen3:8b", alias="OLLAMA_MODEL")
    search_result_limit: int = Field(default=10, alias="SEARCH_RESULT_LIMIT", ge=1, le=20)
    fetch_page_limit: int = Field(default=3, alias="FETCH_PAGE_LIMIT", ge=1, le=5)
    max_chars_per_page: int = Field(default=4000, alias="MAX_CHARS_PER_PAGE", ge=500)
    request_timeout_seconds: float = Field(default=60.0, alias="REQUEST_TIMEOUT_SECONDS", gt=0)

    @field_validator("allowed_domains")
    @classmethod
    def allowed_domains_must_not_be_empty(cls, value: str) -> str:
        """Reject empty domain configuration."""
        domains = [domain.strip() for domain in value.split(",") if domain.strip()]
        if not domains:
            raise ValueError("ALLOWED_DOMAINS must contain at least one domain")
        return ",".join(domains)

    @property
    def allowed_domain_list(self) -> tuple[str, ...]:
        """Return normalized allowed domains."""
        return tuple(
            domain.strip().lower()
            for domain in self.allowed_domains.split(",")
            if domain.strip()
        )


@lru_cache
def load_settings() -> AppSettings:
    """Load application settings once per process."""
    return AppSettings()
