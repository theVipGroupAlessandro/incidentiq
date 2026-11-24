"""Connections to PostgreSQL and Neo4j, built from the settings."""
from app.config import get_settings


def postgres_connection(settings=None):
    import psycopg  # imported here so the rest of the app works without the driver installed

    s = settings or get_settings()
    return psycopg.connect(host=s.postgres_host, port=s.postgres_port, dbname=s.postgres_db,
                           user=s.postgres_user, password=s.postgres_password, connect_timeout=5)


def neo4j_driver(settings=None):
    from neo4j import GraphDatabase

    s = settings or get_settings()
    return GraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password))