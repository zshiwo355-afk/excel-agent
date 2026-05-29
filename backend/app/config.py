from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]
STORAGE_DIR = BASE_DIR / "storage"


class Settings(BaseSettings):
    app_name: str = "Excel Agent Studio API"
    app_env: str = "development"
    use_mock_llm: bool = Field(default=False, alias="USE_MOCK_LLM")
    auto_execute_default: bool = Field(default=True, alias="EXCEL_AGENT_AUTO_EXECUTE")
    excel_agent_step_debug_delay_ms: int = Field(default=0, alias="EXCEL_AGENT_STEP_DEBUG_DELAY_MS")
    deepseek_api_key: str | None = Field(default=None, alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com/v1",
        alias="DEEPSEEK_BASE_URL",
    )
    deepseek_model: str = Field(default="deepseek-chat", alias="DEEPSEEK_MODEL")

    uploads_dir: Path = STORAGE_DIR / "uploads"
    outputs_dir: Path = STORAGE_DIR / "outputs"
    tasks_dir: Path = STORAGE_DIR / "tasks"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.outputs_dir.mkdir(parents=True, exist_ok=True)
    settings.tasks_dir.mkdir(parents=True, exist_ok=True)
    return settings
