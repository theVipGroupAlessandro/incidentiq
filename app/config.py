"""Settings read from environment variables, with .env loaded if present.

Defaults match .env.example and the SSH tunnel (databases reachable on localhost).
"""
import os
from dataclasses import dataclass
from pathlib import Path

ENV_FILE = Path(__file__).parent.parent / ".env"


def load_env_file(path=ENV_FILE):
    """Load KEY=VALUE lines from .env into os.environ, without overriding variables already set."""
    try:
        from dotenv import load_dotenv
    except ImportError:  # python-dotenv not installed: rely on the real environment only
        return
    load_dotenv(path, override=False)


@dataclass(frozen=True)
class Settings:
    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str


def get_settings():
    load_env_file()
    env = os.environ
    return Settings(
        postgres_host=env.get("POSTGRES_HOST", "localhost"),
        postgres_port=int(env.get("POSTGRES_PORT", "5432")),
        postgres_db=env.get("POSTGRES_DB", "incidentiq"),
        postgres_user=env.get("POSTGRES_USER", "incidentiq"),
        postgres_password=env.get("POSTGRES_PASSWORD", ""),
        neo4j_uri=env.get("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=env.get("NEO4J_USER", "neo4j"),
        neo4j_password=env.get("NEO4J_PASSWORD", ""),
    )