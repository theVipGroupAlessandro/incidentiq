"""Apply the SQL migrations in infra/migrations to PostgreSQL, in order, each at most once.

Run from the project root:  python -m app.migrate
Applied versions are recorded in the table schema_migrations, so running it again is safe.
"""
from pathlib import Path

from app.db import postgres_connection

MIGRATIONS_DIR = Path(__file__).parent.parent / "infra" / "migrations"


def migration_files(folder=MIGRATIONS_DIR):
    """Migration files sorted by name: 001_..., 002_..., so the order is explicit."""
    return sorted(Path(folder).glob("[0-9][0-9][0-9]_*.sql"))


def pending(files, applied_versions):
    return [path for path in files if path.stem not in applied_versions]


def migrate(connection, folder=MIGRATIONS_DIR):
    connection.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())")
    connection.commit()
    applied = {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
    done = []
    for path in pending(migration_files(folder), applied):
        # One transaction per migration: if any statement fails, nothing of that file is applied.
        with connection.transaction():
            connection.execute(path.read_text(encoding="utf-8"))
            connection.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.stem,))
        done.append(path.stem)
    return done


def main():
    with postgres_connection() as connection:
        done = migrate(connection)
    print("Applied: " + ", ".join(done) if done else "Database already up to date.")


if __name__ == "__main__":
    main()