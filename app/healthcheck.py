"""Check that both databases are reachable from this machine.

Run from the project root (with the SSH tunnel open when Docker runs on the remote server):
    python -m app.healthcheck
Exit code 0 = everything OK, 1 = at least one check failed.
"""
import sys

from app.config import get_settings
from app.db import neo4j_driver, postgres_connection


def check_postgres(settings):
    with postgres_connection(settings) as connection:
        version = connection.execute("SHOW server_version").fetchone()[0]
        vector = connection.execute(
            "SELECT default_version FROM pg_available_extensions WHERE name = 'vector'").fetchone()
    if vector is None:
        raise RuntimeError("pgvector extension is not available in this PostgreSQL")
    return f"PostgreSQL {version}, pgvector {vector[0]} available"


def check_neo4j(settings):
    with neo4j_driver(settings) as driver:
        driver.verify_connectivity()
        record, _, _ = driver.execute_query(
            "CALL dbms.components() YIELD name, versions, edition "
            "RETURN name, versions[0] AS version, edition")
    component = record[0]
    return f"{component['name']} {component['version']} ({component['edition']})"


def main():
    settings = get_settings()
    checks = {
        f"PostgreSQL at {settings.postgres_host}:{settings.postgres_port}": check_postgres,
        f"Neo4j at {settings.neo4j_uri}": check_neo4j,
    }
    failed = False
    for name, check in checks.items():
        try:
            print(f"[ OK ] {name}: {check(settings)}")
        except Exception as error:  # report every failure, do not stop at the first one
            failed = True
            print(f"[FAIL] {name}: {type(error).__name__}: {error}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()