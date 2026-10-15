"""
Configuration & Settings Management
==================================
Manages environment variables, directory paths, scraper parameters,
and Lakehouse thresholds using Pydantic Settings.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Academic Project Metadata
    project_name: str = "eRaktKosh Blood Lakehouse"
    project_subtitle: str = "National Blood Inventory Intelligence & Emergency Finder"
    version: str = "1.0.0"
    institution: str = "Charotar University of Science and Technology (CHARUSAT)"
    department: str = "Faculty of Computer Science and Applications (FCA) - MCA"
    academic_guide: str = "Academic Project Mentor"
    author_name: str = "Radhey Gajera"

    # Base Paths
    base_dir: Path = Path(__file__).resolve().parent.parent.parent
    warehouse_path: Path = base_dir / "blood_warehouse.duckdb"
    serving_path: Path = base_dir / "serving.duckdb"
    serving_staging_path: Path = base_dir / "serving.duckdb.tmp"
    metadata_path: Path = base_dir / "eraktkosh_all_metadata.json"
    web_dir: Path = base_dir / "web"
    dbt_project_dir: Path = base_dir / "dbt"

    # Data Tier Landing Directories
    data_landing_dir: Path = base_dir / "data" / "landing"
    data_archive_dir: Path = base_dir / "data" / "archive"
    data_raw_dir: Path = base_dir / "data" / "raw"

    # Scraper Parameters (Polite & Resilient)
    eraktkosh_base_url: str = (
        "https://eraktkosh.mohfw.gov.in/eraktkoshPortal/eraktkosh/blood-availability"
    )
    scraper_concurrency: int = 10
    scraper_timeout_seconds: int = 30
    scraper_max_retries: int = 3
    min_run_interval_hours: float = 6.0
    user_agent: str = (
        "BloodLake/1.0 (Academic Research; CHARUSAT MCA Mini Project; "
        "mailto:radheygajera@gmail.com)"
    )

    # Data Quality & Anomaly Gate Threshold
    # Pipeline publish aborts if current count < 80% of prior successful run
    min_facility_threshold_ratio: float = 0.80

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = ["*"]


settings = Settings()

# Ensure critical data directories exist
settings.data_landing_dir.mkdir(parents=True, exist_ok=True)
settings.data_archive_dir.mkdir(parents=True, exist_ok=True)
settings.data_raw_dir.mkdir(parents=True, exist_ok=True)
