"""
AI Teacher Configuration
Loads environment variables and provides application settings
"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Project paths
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    TEXTBOOK_DIR: Path = DATA_DIR / "textbooks"
    MODELS_DIR: Path = DATA_DIR / "models"
    DATABASES_DIR: Path = DATA_DIR / "databases"
    EMBEDDINGS_DIR: Path = DATA_DIR / "embeddings"
    LOG_DIR: Path = PROJECT_ROOT / "logs"

    # LLM Server
    LLAMA_SERVER_URL: str = Field(default="http://localhost:8080")
    LLAMA_API_KEY: Optional[str] = Field(default=None)

    # Model Configuration
    MODEL_NAME: str = Field(default="lfm2-7b-q8")
    MODEL_PATH: Optional[str] = Field(default=None)
    EMBEDDING_MODEL: str = Field(
        default="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    )
    EMBEDDING_DIMENSION: int = Field(default=768)

    # Database Configuration (POC)
    DUCKDB_PATH: str = Field(default="./data/databases/ai_teacher.duckdb")

    # Neo4j Configuration (POC)
    NEO4J_URI: str = Field(default="bolt://localhost:7687")
    NEO4J_USER: str = Field(default="neo4j")
    NEO4J_PASSWORD: str = Field(default="password")

    # Application Settings
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    LOG_LEVEL: str = Field(default="INFO")

    # RAG Configuration
    RETRIEVAL_TOP_K: int = Field(default=5)
    CHUNK_SIZE: int = Field(default=512)
    CHUNK_OVERLAP: int = Field(default=50)
    SIMILARITY_THRESHOLD: float = Field(default=0.7)

    # LLM Generation Settings
    MAX_TOKENS: int = Field(default=512)
    TEMPERATURE: float = Field(default=0.7)
    TOP_P: float = Field(default=0.9)
    CONTEXT_WINDOW: int = Field(default=4096)

    # Memory Settings
    CONVERSATION_BUFFER_SIZE: int = Field(default=10)
    ENABLE_ADAPTIVE_LEARNING: bool = Field(default=True)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if they don't exist
        self._create_directories()

    def _create_directories(self):
        """Create necessary directories"""
        for directory in [
            self.DATA_DIR,
            self.TEXTBOOK_DIR,
            self.MODELS_DIR,
            self.DATABASES_DIR,
            self.EMBEDDINGS_DIR,
            self.LOG_DIR,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    @property
    def duckdb_absolute_path(self) -> Path:
        """Get absolute path for DuckDB"""
        path = Path(self.DUCKDB_PATH)
        if not path.is_absolute():
            path = self.PROJECT_ROOT / path
        return path


# Singleton instance
settings = Settings()


if __name__ == "__main__":
    # Test configuration loading
    print("=== AI Teacher Configuration ===")
    print(f"Project Root: {settings.PROJECT_ROOT}")
    print(f"Data Directory: {settings.DATA_DIR}")
    print(f"DuckDB Path: {settings.duckdb_absolute_path}")
    print(f"Neo4j URI: {settings.NEO4J_URI}")
    print(f"Embedding Model: {settings.EMBEDDING_MODEL}")
    print(f"LLM Server: {settings.LLAMA_SERVER_URL}")
    print(f"Debug Mode: {settings.DEBUG}")
