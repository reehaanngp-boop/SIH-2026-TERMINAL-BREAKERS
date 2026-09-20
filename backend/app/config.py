"""Application configuration via environment variables and a .env file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root is two levels above this file: backend/app/config.py -> backend -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "DigiRaksha"
    version: str = "0.1.0"
    debug: bool = False

    api_prefix: str = "/api/v1"

    # Paths (relative paths are resolved against the project root)
    data_dir: Path = PROJECT_ROOT / "data"
    upload_dir: Path = PROJECT_ROOT / "data" / "uploads"
    model_dir: Path = PROJECT_ROOT / "data" / "models"
    dataset_dir: Path = PROJECT_ROOT / "data" / "datasets"
    reports_dir: Path = PROJECT_ROOT / "data" / "reports"
    static_dir: Path = BACKEND_ROOT / "app" / "static"

    # Database
    database_url: str = "sqlite:///./data/digiraksha.db"

    # Upload constraints
    max_upload_mb: int = 50
    max_duration_seconds: int = 600

    # ASR (Whisper)
    whisper_model_size: str = "small"  # tiny|base|small|medium (large needs a lot of RAM/disk)
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_language: str | None = None  # None => auto-detect

    # Voice anti-spoofing & cloning detection
    enable_aasist: bool = True  # gracefully falls back to heuristics when torch/model absent
    enable_dhwani: bool = True  # Multilingual Wav2Vec2 + AASIST ONNX foundation model
    dhwani_model_path: Path | None = None  # None => resolves to model_dir / "dhwani_multilingual.onnx"
    enable_wav2vec2: bool = True  # ASVspoof fine-tuned Wav2Vec2 ensemble (primary voice engine)

    # Speaker verification (Safe-Voice Registry)
    # 0.50 separates ECAPA embeddings cleanly on real data (same-speaker ~0.85,
    # different-speaker ~0.1-0.3). The old 0.42 was too low for the weaker
    # MFCC embedding and accepted every voice.
    verify_similarity_threshold: float = 0.5
    enable_ecapa: bool = True  # ECAPA-TDNN embedding; falls back to MFCC stats

    # Analysis pipeline
    job_timeout_seconds: int = 900
    max_concurrent_jobs: int = 2
    video_frame_interval: int = 5  # analyse every Nth frame for deepfake heuristics
    video_max_frames: int = 240  # hard cap on frames analysed

    # AI analysis layer (OpenRouter LLM)
    enable_llm_analysis: bool = True
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "poolside/laguna-s-2.1:free"
    openrouter_fallback_models: str = "nvidia/nemotron-3.5-lightning:free,z-ai/glm-5.2:free,minimax/minimax-m3:free,google/gemini-2.0-flash-exp:free"
    llm_timeout_seconds: float = 10.0
    llm_max_transcript_chars: int = 6000

    # Access control (police suite). Existing consumer routes stay open; when
    # enable_auth is true, the police routes (cases/evidence/people/voice-match/
    # phone/analytics/reports/export/bulk) require a Bearer token.
    enable_auth: bool = True
    token_ttl_hours: int = 12
    pin_min_length: int = 4
    pin_max_attempts: int = 5

    # CORS (comma separated) - only relevant when frontend served separately
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def ensure_dirs(self) -> None:
        """Create all data directories referenced by the app."""
        for d in (self.data_dir, self.upload_dir, self.model_dir, self.dataset_dir, self.reports_dir):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
