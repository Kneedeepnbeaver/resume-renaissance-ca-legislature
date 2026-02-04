"""App configuration and paths."""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
SOURCES_DIR = BASE_DIR / "sources"
CHROMA_DIR = BASE_DIR / "chroma_db"
OUTPUTS_DIR = BASE_DIR / "outputs"
GENERATED_DIR = BASE_DIR / "generated"  # Resume & cover letter outputs (MD only)
RULES_DIR = BASE_DIR / "rules"

# Source subfolders for doc_type inference
RESUMES_DIR = SOURCES_DIR / "resumes"
EXPERIENCES_DIR = SOURCES_DIR / "experiences"
BOOKS_DIR = SOURCES_DIR / "books"

# ChromaDB collection name
COLLECTION_NAME = "ca_legislature_resume_rag"

# Default Ollama settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = "nomic-embed-text"
LLM_MODEL = "llama3.2"

# Chunking settings
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# Retrieval settings
DEFAULT_TOP_K = 12
