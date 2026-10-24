"""Resolve the fresh Compose model without building or contacting its daemon."""
from copy import deepcopy
import json
from pathlib import Path
import stat

import pytest

from ops import start_journey as launch
from ops.bootstrap import initialize, SERVICE_ROLES


@pytest.fixture
def resolved(tmp_path, monkeypatch):
    try:
        docker = launch.docker_binary()
    except RuntimeError:
        pytest.skip("Docker CLI required only to render configuration")
    env_file = tmp_path / "credentials.env"
    env_file.write_text("ANALYST_API_TOKEN=" + "test-token-" * 4 + "\n")
    monkeypatch.setattr(launch, "ENV_FILE", env_file)
    monkeypatch.setenv("OPENROUTER_API_KEY", "never-forward-this-value")
    monkeypatch.setenv("COMPOSE_FILE", "unrelated.yaml")
    env = launch.clean_environment(docker)
    return json.loads(launch.capture(launch.compose(docker) + ["config", "--format", "json"], env, "test-token-" * 4))


def test_resolved_stack_has_dedicated_ports_volumes_and_safe_runtime(resolved):
    launch.validate(resolved)
    assert "never-forward-this-value" not in json.dumps(resolved)
    assert all(v["name"].startswith("analyst-desk-journey_") for v in resolved["volumes"].values())
    assert all(not s.get("privileged") for s in resolved["services"].values())
    assert all(s.get("read_only") for s in resolved["services"].values())


@pytest.mark.parametrize("mutation", ["public_port", "worker_network", "worker_resources", "writable_source", "provider_key"])
def test_configuration_rejects_boundary_regressions(resolved, mutation):
    model = deepcopy(resolved)
    if mutation == "public_port":
        model["services"]["ingress"]["ports"][0]["host_ip"] = "0.0.0.0"
    elif mutation == "worker_network":
        model["services"]["pandas-worker"]["network_mode"] = "host"
    elif mutation == "worker_resources":
        model["services"]["pandas-worker"].pop("mem_limit")
    elif mutation == "writable_source":
        source = next(m for m in model["services"]["edgar"]["volumes"] if m["target"] == "/sources")
        source["read_only"] = False
    else:
        model["services"]["app"]["environment"]["OPENROUTER_API_KEY"] = "unexpected-key"
    with pytest.raises(ValueError):
        launch.validate(model)


def test_private_api_credential_survives_reprepare_without_disclosure(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(launch, "PRIVATE", tmp_path / "private")
    monkeypatch.setattr(launch, "ENV_FILE", tmp_path / "private/credentials.env")
    original = launch.private_token()
    assert launch.private_token() == original
    assert stat.S_IMODE(launch.ENV_FILE.stat().st_mode) == 0o600
    assert original not in capsys.readouterr().out


def test_credentials_are_service_scoped_and_not_rotated_on_restart(tmp_path, capsys):
    initialize(tmp_path)
    app = json.loads((tmp_path / "app/config.json").read_text())
    for service, allowed in SERVICE_ROLES.items():
        config = json.loads((tmp_path / service / "config.json").read_text())
        assert set(config["roles"]) == set(allowed)
        assert ("publication_secret" in config) == (service == "research-portal")
        assert "metrics_token" not in config
        assert stat.S_IMODE((tmp_path / service / "config.json").stat().st_mode) == 0o600
    initialize(tmp_path)
    assert json.loads((tmp_path / "app/config.json").read_text()) == app
    assert not any(secret in capsys.readouterr().out for secret in app["roles"].values())


def test_parent_environment_cannot_select_another_daemon_or_pass_provider_keys(monkeypatch):
    for name in ("OPENROUTER_API_KEY", "DOCKER_HOST", "DOCKER_CONTEXT", "COMPOSE_FILE", "ANALYST_API_TOKEN"):
        monkeypatch.setenv(name, "unrelated-value")
    env = launch.clean_environment("docker")
    assert all(name not in env for name in ("OPENROUTER_API_KEY", "DOCKER_HOST", "DOCKER_CONTEXT", "COMPOSE_FILE", "ANALYST_API_TOKEN"))
    command = launch.compose("docker")
    assert command[:3] == ["docker", "--context", "desktop-linux"]
    assert "--env-file" in command
