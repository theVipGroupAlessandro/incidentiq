from app import config


def test_defaults_match_the_ssh_tunnel(monkeypatch):
    monkeypatch.setattr(config, "load_env_file", lambda path=None: None)
    for name in ("POSTGRES_HOST", "POSTGRES_PORT", "NEO4J_URI"):
        monkeypatch.delenv(name, raising=False)
    settings = config.get_settings()
    assert (settings.postgres_host, settings.postgres_port) == ("localhost", 5432)
    assert settings.neo4j_uri == "bolt://localhost:7687"


def test_environment_variables_override_defaults(monkeypatch):
    monkeypatch.setattr(config, "load_env_file", lambda path=None: None)
    monkeypatch.setenv("POSTGRES_PORT", "15432")
    monkeypatch.setenv("NEO4J_URI", "bolt://devsrv01:17687")
    settings = config.get_settings()
    assert settings.postgres_port == 15432
    assert settings.neo4j_uri == "bolt://devsrv01:17687"