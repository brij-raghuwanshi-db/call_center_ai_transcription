from __future__ import annotations

import logging
from importlib import resources
from pathlib import Path
from typing import ClassVar

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..._metadata import app_name, app_slug

# --- Config ---

project_root = Path(__file__).parent.parent.parent.parent.parent
env_file = project_root / ".env"

if env_file.exists():
    load_dotenv(dotenv_path=env_file)


class AppConfig(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=env_file,
        env_prefix=f"{app_slug.upper()}_",
        extra="ignore",
        env_nested_delimiter="__",
    )
    app_name: str = Field(default=app_name)
    llm_endpoint_name: str = Field(default="databricks-gpt-5-5")
    asr_endpoint_name: str = Field(default="callcenter-asr-faster-whisper")
    embedding_endpoint_name: str = Field(default="databricks-gte-large-en")
    vector_search_endpoint_name: str = Field(default="carenet-vs-so")
    vector_search_index_name: str = Field(
        default="classic_stable_84t3jv_catalog.callcenter.kb_index"
    )
    uc_catalog: str = Field(default="classic_stable_84t3jv_catalog")
    uc_schema: str = Field(default="callcenter")
    volume_name: str = Field(default="demo_assets")
    audio_volume_path: str = Field(
        default="/Volumes/classic_stable_84t3jv_catalog/callcenter/demo_assets/callcenter_audio"
    )
    delta_schema_name: str = Field(default="callcenter")
    use_databricks_asr: bool = Field(default=False)
    use_mock_asr: bool = Field(default=True)
    use_scripted_transcript_fallback: bool = Field(default=False)
    use_mock_llm: bool = Field(default=True)
    enable_redaction: bool = Field(default=False)
    enable_acoustic_features: bool = Field(default=True)

    @property
    def static_assets_path(self) -> Path:
        return Path(str(resources.files(app_slug))).joinpath("__dist__")

    def __hash__(self) -> int:
        return hash(self.app_name)


# --- Logger ---

logger = logging.getLogger(app_name)
