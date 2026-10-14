"""
BloodGrid Configuration Management
==================================
Centralized application settings powered by Pydantic Settings.
Reads configuration from environment variables and local .env files.
"""

from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application Environment
    env: str = Field(default="development", alias="BLOODGRID_ENV")
    log_level: str = Field(default="INFO", alias="BLOODGRID_LOG_LEVEL")
    host: str = Field(default="0.0.0.0", alias="BLOODGRID_HOST")
    port: int = Field(default=8000, alias="BLOODGRID_PORT")
    allowed_origins: List[str] = Field(
        default=["http://localhost:8000", "http://127.0.0.1:8000", "https://bloodgrid.in"],
        alias="BLOODGRID_ALLOWED_ORIGINS"
    )

    # Core Directories & Database Paths
    base_dir: Path = BASE_DIR
    warehouse_path: Path = Field(default=BASE_DIR / "blood_warehouse.duckdb", alias="BLOODGRID_WAREHOUSE_PATH")
    serving_path: Path = Field(default=BASE_DIR / "serving.duckdb", alias="BLOODGRID_SERVING_PATH")
    serving_staging_path: Path = Field(default=BASE_DIR / "serving.duckdb.tmp")
    landing_dir: Path = Field(default=BASE_DIR / "data" / "landing", alias="BLOODGRID_LANDING_DIR")
    archive_dir: Path = Field(default=BASE_DIR / "data" / "archive")
    dbt_project_dir: Path = Field(default=BASE_DIR / "dbt")
    web_dir: Path = Field(default=BASE_DIR / "web")
    static_dir: Path = Field(default=BASE_DIR / "static")

    # PostgreSQL Application State (Users, API Keys, Subscriptions, Alerts)
    postgres_url: str = Field(
        default="postgresql://bloodgrid:bloodgrid_pass@localhost:5432/bloodgrid_app",
        alias="BLOODGRID_POSTGRES_URL"
    )

    # Scraper Ingestion Parameters (Polite Collection)
    scraper_user_agent: str = Field(
        default="BloodGrid-DataCollector/1.0 (+https://bloodgrid.in; data@bloodgrid.in)",
        alias="BLOODGRID_SCRAPER_USER_AGENT"
    )
    scraper_concurrency: int = Field(default=10, alias="BLOODGRID_SCRAPER_CONCURRENCY")
    scraper_timeout_sec: int = Field(default=15, alias="BLOODGRID_SCRAPER_TIMEOUT_SEC")
    scraper_max_retries: int = Field(default=3, alias="BLOODGRID_SCRAPER_MAX_RETRIES")
    min_run_interval_hours: float = Field(default=3.0, alias="BLOODGRID_MIN_RUN_INTERVAL_HOURS")
    circuit_breaker_max_error_pct: float = Field(default=20.0, alias="BLOODGRID_CIRCUIT_BREAKER_MAX_ERROR_PCT")
    anomaly_min_facility_ratio: float = Field(default=0.80)  # Publish gate: abort if < 80% facilities

    # Geocoding & Map Configuration
    carto_api_key: str = Field(default="cb1_4kjs_1_d65cb9aedbd3050cfd5fd35a", alias="BLOODGRID_CARTO_API_KEY")
    nominatim_user_agent: str = Field(default="BloodGrid-Geocoder/1.0 (geocoding@bloodgrid.in)", alias="BLOODGRID_NOMINATIM_USER_AGENT")

    # Security & Authentication
    jwt_secret: str = Field(default="super-secret-dev-key-change-in-production-min-32-chars", alias="BLOODGRID_JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="BLOODGRID_JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=1440, alias="BLOODGRID_JWT_EXPIRE_MINUTES")
    api_key_secret: str = Field(default="dev-api-key-signing-secret-change-in-production", alias="BLOODGRID_API_KEY_SECRET")

    # Rate Limiting Tiers
    rate_limit_public: str = Field(default="60/minute", alias="BLOODGRID_RATE_LIMIT_PUBLIC")
    rate_limit_pro: str = Field(default="300/minute", alias="BLOODGRID_RATE_LIMIT_PRO")
    rate_limit_enterprise: str = Field(default="1200/minute", alias="BLOODGRID_RATE_LIMIT_ENTERPRISE")

    # Alerting Dispatch Channels
    telegram_bot_token: Optional[str] = Field(default=None, alias="BLOODGRID_TELEGRAM_BOT_TOKEN")
    telegram_chat_id: Optional[str] = Field(default=None, alias="BLOODGRID_TELEGRAM_CHAT_ID")
    smtp_host: Optional[str] = Field(default=None, alias="BLOODGRID_SMTP_HOST")
    smtp_port: int = Field(default=587, alias="BLOODGRID_SMTP_PORT")
    smtp_user: Optional[str] = Field(default=None, alias="BLOODGRID_SMTP_USER")
    smtp_password: Optional[str] = Field(default=None, alias="BLOODGRID_SMTP_PASSWORD")
    alert_from_email: str = Field(default="alerts@bloodgrid.in", alias="BLOODGRID_ALERT_FROM_EMAIL")

    # Razorpay Payment Integration (Test Mode)
    razorpay_key_id: str = Field(default="rzp_test_placeholder_key_id", alias="BLOODGRID_RAZORPAY_KEY_ID")
    razorpay_key_secret: str = Field(default="placeholder_razorpay_secret", alias="BLOODGRID_RAZORPAY_KEY_SECRET")
    razorpay_webhook_secret: str = Field(default="placeholder_webhook_secret", alias="BLOODGRID_RAZORPAY_WEBHOOK_SECRET")

    # Pricing Configuration (in INR, easy to adapt)
    pricing_plans: dict = Field(
        default={
            "free": {"name": "Community Finder", "price_inr": 0, "alerts": 0, "api_rate": 60},
            "pro": {"name": "Pro Alerts", "price_inr": 299, "alerts": 10, "api_rate": 300},
            "developer": {"name": "Developer API", "price_inr": 999, "alerts": 25, "api_rate": 1200},
            "organization": {"name": "NGO & Hospital Team", "price_inr": 2999, "alerts": 100, "api_rate": 5000}
        }
    )

    # Mandatory Legal Source Attribution
    source_attribution: str = (
        "Data sourced from eRaktKosh (Ministry of Health & Family Welfare, Govt. of India). "
        "Not an official service. Always call the blood bank to confirm before travelling."
    )


settings = Settings()
