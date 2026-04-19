"""
Unified configuration management
Centralized application configuration
"""

from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import AliasChoices, BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseModel):
    """API configuration"""
    dashscope_api_key: str = Field(default='', validation_alias=AliasChoices('API_DASHSCOPE_API_KEY'))
    model_name: str = Field(default='qwen-plus', validation_alias=AliasChoices('API_MODEL_NAME'))
    max_tokens: int = Field(default=4096, validation_alias=AliasChoices('API_MAX_TOKENS'))
    timeout: int = Field(default=30, validation_alias=AliasChoices('API_TIMEOUT'))

class DatabaseSettings(BaseModel):
    """Database configuration"""
    url: str = Field(default='sqlite:///./data/autoclip.db', validation_alias=AliasChoices('DATABASE_URL'))

class RedisSettings(BaseModel):
    """Redis configuration"""
    url: str = Field(default='redis://localhost:6379/0', validation_alias=AliasChoices('REDIS_URL'))

class ProcessingSettings(BaseModel):
    """processingconfiguration"""
    chunk_size: int = Field(default=5000, validation_alias=AliasChoices('PROCESSING_CHUNK_SIZE'))
    min_score_threshold: float = Field(default=0.7, validation_alias=AliasChoices('PROCESSING_MIN_SCORE_THRESHOLD'))
    max_clips_per_collection: int = Field(default=5, validation_alias=AliasChoices('PROCESSING_MAX_CLIPS_PER_COLLECTION'))
    max_retries: int = Field(default=3, validation_alias=AliasChoices('PROCESSING_MAX_RETRIES'))

class LoggingSettings(BaseModel):
    """Logging configuration"""
    level: str = Field(default='INFO', validation_alias=AliasChoices('LOG_LEVEL'))
    fmt: str = Field(default='%(asctime)s - %(name)s - %(levelname)s - %(message)s', validation_alias=AliasChoices('LOG_FORMAT'))
    file: str = Field(default='backend.log', validation_alias=AliasChoices('LOG_FILE'))

class Settings(BaseSettings):
    """Applicationset"""
    # Allow .env + Ignore undeclared keys，Avoid"Extra inputs are not permitted"
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    environment: str = Field(default='development', validation_alias=AliasChoices('ENVIRONMENT'))
    debug: bool = Field(default=True, validation_alias=AliasChoices('DEBUG'))
    encryption_key: str = Field(default='', validation_alias=AliasChoices('ENCRYPTION_KEY'))

    # Direct field definition，don't use nestedBaseModel
    database_url: str = Field(default='sqlite:///./data/autoclip.db', validation_alias=AliasChoices('DATABASE_URL'))
    redis_url: str = Field(default='redis://localhost:6379/0', validation_alias=AliasChoices('REDIS_URL'))
    api_dashscope_api_key: str = Field(default='', validation_alias=AliasChoices('API_DASHSCOPE_API_KEY'))
    api_model_name: str = Field(default='qwen-plus', validation_alias=AliasChoices('API_MODEL_NAME'))
    api_max_tokens: int = Field(default=4096, validation_alias=AliasChoices('API_MAX_TOKENS'))
    api_timeout: int = Field(default=30, validation_alias=AliasChoices('API_TIMEOUT'))
    processing_chunk_size: int = Field(default=5000, validation_alias=AliasChoices('PROCESSING_CHUNK_SIZE'))
    processing_min_score_threshold: float = Field(default=0.7, validation_alias=AliasChoices('PROCESSING_MIN_SCORE_THRESHOLD'))
    processing_max_clips_per_collection: int = Field(default=5, validation_alias=AliasChoices('PROCESSING_MAX_CLIPS_PER_COLLECTION'))
    processing_max_retries: int = Field(default=3, validation_alias=AliasChoices('PROCESSING_MAX_RETRIES'))
    log_level: str = Field(default='INFO', validation_alias=AliasChoices('LOG_LEVEL'))
    log_format: str = Field(default='%(asctime)s - %(name)s - %(levelname)s - %(message)s', validation_alias=AliasChoices('LOG_FORMAT'))
    log_file: str = Field(default='backend.log', validation_alias=AliasChoices('LOG_FILE'))

    # ── Agent Pipeline Settings ──
    openai_api_key: str = Field(default='', validation_alias=AliasChoices('OPENAI_API_KEY'))
    anthropic_api_key: str = Field(default='', validation_alias=AliasChoices('ANTHROPIC_API_KEY'))
    google_api_key: str = Field(default='', validation_alias=AliasChoices('GOOGLE_API_KEY'))
    pexels_api_key: str = Field(default='', validation_alias=AliasChoices('PEXELS_API_KEY'))
    elevenlabs_api_key: str = Field(default='', validation_alias=AliasChoices('ELEVENLABS_API_KEY'))

    # Video defaults
    video_width_vertical: int = Field(default=1080)
    video_height_vertical: int = Field(default=1920)
    video_width_horizontal: int = Field(default=1920)
    video_height_horizontal: int = Field(default=1080)

    # TTS
    tts_voice_vi: str = Field(default='vi-VN-HoaiMyNeural')
    tts_voice_en: str = Field(default='en-US-AriaNeural')

    # LLM
    llm_provider: str = Field(default='openai', validation_alias=AliasChoices('LLM_PROVIDER'))
    llm_model: str = Field(default='gpt-4o-mini')
    llm_temperature: float = Field(default=0.7)

    # Pipeline
    agent_max_retries: int = Field(default=3)
    ffmpeg_timeout: int = Field(default=120)

# Global configuration instance
settings = Settings()

def get_project_root() -> Path:
    """Get project root directory"""
    # Use new path utility
    from ..core.path_utils import get_project_root as get_root
    return get_root()

def get_data_directory() -> Path:
    """getdatadirectory"""
    project_root = get_project_root()
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir

def get_uploads_directory() -> Path:
    """getuploadfiledirectory"""
    data_dir = get_data_directory()
    uploads_dir = data_dir / "uploads"
    uploads_dir.mkdir(exist_ok=True)
    return uploads_dir

def get_temp_directory() -> Path:
    """getTemporary filesdirectory"""
    data_dir = get_data_directory()
    temp_dir = data_dir / "temp"
    temp_dir.mkdir(exist_ok=True)
    return temp_dir

def get_output_directory() -> Path:
    """Get output file directory"""
    data_dir = get_data_directory()
    output_dir = data_dir / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir

def get_database_url() -> str:
    """Get database URL"""
    return settings.database_url

def get_redis_url() -> str:
    """getRedis URL"""
    return settings.redis_url

def get_api_key() -> Optional[str]:
    """Get API key"""
    return settings.api_dashscope_api_key if settings.api_dashscope_api_key else None

def get_model_config() -> Dict[str, Any]:
    """Get model configuration"""
    return {
        "model_name": settings.api_model_name,
        "max_tokens": settings.api_max_tokens,
        "timeout": settings.api_timeout
    }

def get_processing_config() -> Dict[str, Any]:
    """getprocessingconfiguration"""
    return {
        "chunk_size": settings.processing_chunk_size,
        "min_score_threshold": settings.processing_min_score_threshold,
        "max_clips_per_collection": settings.processing_max_clips_per_collection,
        "max_retries": settings.processing_max_retries
    }

def get_logging_config() -> Dict[str, Any]:
    """getLogging configuration"""
    return {
        "level": settings.log_level,
        "format": settings.log_format,
        "file": settings.log_file
    }

# initializationpathconfiguration
def init_paths():
    """initializationpathconfiguration"""
    project_root = get_project_root()
    data_dir = get_data_directory()
    uploads_dir = get_uploads_directory()
    temp_dir = get_temp_directory()
    output_dir = get_output_directory()

    print(f"Project root directory: {project_root}")
    print(f"datadirectory: {data_dir}")
    print(f"uploaddirectory: {uploads_dir}")
    print(f"Temp directory: {temp_dir}")
    print(f"Output directory: {output_dir}")

if __name__ == "__main__":
    # Test configuration loading
    init_paths()
    print(f"Database URL: {get_database_url()}")
    print(f"Redis URL: {get_redis_url()}")
    print(f"API configuration: {get_model_config()}")
    print(f"processingconfiguration: {get_processing_config()}")
