from app.migrate import migration_files, pending


def test_migrations_are_sorted_by_number(tmp_path):
    for name in ("002_b.sql", "001_a.sql", "010_c.sql", "notes.sql"):
        (tmp_path / name).write_text("SELECT 1;")
    assert [path.name for path in migration_files(tmp_path)] == ["001_a.sql", "002_b.sql", "010_c.sql"]


def test_only_unapplied_migrations_are_pending(tmp_path):
    for name in ("001_a.sql", "002_b.sql"):
        (tmp_path / name).write_text("SELECT 1;")
    assert [path.stem for path in pending(migration_files(tmp_path), {"001_a"})] == ["002_b"]


def test_project_has_an_initial_schema():
    assert [path.name for path in migration_files()][0] == "001_initial_schema.sql"