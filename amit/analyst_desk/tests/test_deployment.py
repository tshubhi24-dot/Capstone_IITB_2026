"""Resolve the fresh Compose model without building or contacting its daemon."""
from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
import stat
from types import SimpleNamespace
from urllib.error import HTTPError, URLError

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


@pytest.mark.parametrize("mutation", ["public_port", "worker_network", "worker_resources", "writable_source", "provider_key", "writable_models", "online_models"])
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
    elif mutation == "provider_key":
        model["services"]["app"]["environment"]["OPENROUTER_API_KEY"] = "unexpected-key"
    elif mutation == "writable_models":
        mount = next(m for m in model["services"]["filings-kb"]["volumes"] if m["target"] == "/retrieval")
        mount["read_only"] = False
    else:
        model["services"]["filings-kb"]["environment"]["HF_HUB_OFFLINE"] = "0"
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


def test_serial_start_waits_for_initializer_and_starts_one_service_per_call(monkeypatch):
    calls = []
    ready = []

    def fake_capture(command, env, token, timeout=30):
        calls.append((command, timeout))
        if command[-4:] == ["ps", "--all", "--quiet", "init-secrets"]:
            return "a" * 64 + "\n"
        if "inspect" in command:
            return "exited 0\n"
        if command[-4:] == ["ps", "--status", "running", "--services"]:
            return "\n".join(launch.START_ORDER)
        return ""

    monkeypatch.setattr(launch, "capture", fake_capture)
    monkeypatch.setattr(launch, "local_readiness", lambda: ready.append(True))
    launch.start_stack(["docker", "compose"], {}, "private-test-token")
    starts = [(command, timeout) for command, timeout in calls if "up" in command]
    assert [command[-1] for command, _ in starts] == ["init-secrets", *launch.START_ORDER]
    assert [command[-1] for command, _ in starts if "--force-recreate" in command] == ["ingress"]
    assert launch.START_ORDER.index("app") < launch.START_ORDER.index("ingress")
    assert launch.START_ORDER.index("grafana") < launch.START_ORDER.index("ingress")
    for command, timeout in starts:
        assert "--no-deps" in command and "--no-build" in command
        assert timeout in {120, 150}
        assert sum(service in command for service in ["init-secrets", *launch.START_ORDER]) == 1
    wait_at = next(i for i, (command, _) in enumerate(calls) if "wait" in command)
    worker_at = next(i for i, (command, _) in enumerate(calls) if command[-1] == "pandas-worker")
    assert wait_at < worker_at
    assert calls[0][0][-2:] == ["build", "app"] and calls[0][1] == 900
    assert ready == [True]


def test_rebuilt_app_refreshes_existing_ingress_before_readiness(monkeypatch):
    addresses = {"app": "previous-app-address", "ingress_upstream": "previous-app-address"}
    ingress_starts = []

    def capture(command, env, token, timeout=30):
        if command[-4:] == ["ps", "--all", "--quiet", "init-secrets"]:
            return "a" * 64
        if "inspect" in command:
            return "exited 0"
        if command[-4:] == ["ps", "--status", "running", "--services"]:
            return "\n".join(launch.START_ORDER)
        if "up" in command and command[-1] == "app":
            addresses["app"] = "rebuilt-app-address"
        if "up" in command and command[-1] == "ingress":
            ingress_starts.append(command)
            if "--force-recreate" in command:
                addresses["ingress_upstream"] = addresses["app"]
        return ""

    def ready():
        assert addresses["ingress_upstream"] == addresses["app"] == "rebuilt-app-address"

    monkeypatch.setattr(launch, "capture", capture)
    monkeypatch.setattr(launch, "local_readiness", ready)
    launch.start_stack(["docker", "compose"], {}, "fictional-local-token")
    assert len(ingress_starts) == 1


def test_serial_start_stops_before_other_services_if_initializer_fails(monkeypatch):
    calls = []

    def fake_capture(command, env, token, timeout=30):
        calls.append(command)
        if command[-4:] == ["ps", "--all", "--quiet", "init-secrets"]:
            return "a" * 64
        return "exited 1" if "inspect" in command else ""

    monkeypatch.setattr(launch, "capture", fake_capture)
    monkeypatch.setattr(launch, "local_readiness", lambda: pytest.fail("Must not check readiness after initialization failure"))
    with pytest.raises(RuntimeError, match="initialization did not complete"):
        launch.start_stack(["docker", "compose"], {}, "private-test-token")
    assert [command[-1] for command in calls if "up" in command] == ["init-secrets"]


@pytest.fixture
def readiness_clock(monkeypatch):
    clock = {"now": 0, "sleeps": []}

    def sleep(seconds):
        clock["sleeps"].append(seconds)
        clock["now"] += seconds

    monkeypatch.setattr(launch, "time", SimpleNamespace(monotonic=lambda: clock["now"], sleep=sleep))
    return clock


def test_readiness_retries_ingress_502_connection_refusal_and_timeout(monkeypatch, readiness_clock):
    statuses = iter([HTTPError("local", 502, "settling", {}, None), {"status": "ok"},
                     URLError(ConnectionRefusedError()), TimeoutError(), {"database": "ok"}])
    requests = []

    def opening(url, timeout):
        requests.append((url, timeout))
        outcome = next(statuses)
        if isinstance(outcome, Exception):
            raise outcome
        response = BytesIO(json.dumps(outcome).encode())
        response.status = 200
        return response

    monkeypatch.setattr(launch, "build_opener", lambda *args: SimpleNamespace(open=opening))
    launch.local_readiness()
    assert len(requests) == 5
    assert readiness_clock["sleeps"] == [2, 2, 2]
    assert readiness_clock["now"] == 6
    assert requests[0][0] == requests[1][0] == "http://127.0.0.1:18080/health"
    assert all(url == "http://127.0.0.1:13080/api/health" for url, _ in requests[2:])


def test_readiness_failure_is_bounded_to_one_30_second_window(monkeypatch, readiness_clock):
    attempts = []

    def opening(url, timeout):
        attempts.append((url, timeout))
        if readiness_clock["now"] < 28 or "13080" in url:
            raise HTTPError(url, 502, "settling", {}, None)
        response = BytesIO(b'{"status":"ok"}')
        response.status = 200
        return response

    monkeypatch.setattr(launch, "build_opener", lambda *args: SimpleNamespace(open=opening))
    with pytest.raises(RuntimeError, match="within 30 seconds"):
        launch.local_readiness()
    assert readiness_clock["now"] == 30
    assert len(attempts) == 16
    assert attempts[-1] == ("http://127.0.0.1:13080/api/health", 2)
    assert max(readiness_clock["sleeps"]) == 2


@pytest.mark.parametrize("status", [401, 500, 503])
def test_readiness_does_not_retry_other_http_failures(monkeypatch, readiness_clock, status):
    def opening(url, timeout):
        raise HTTPError(url, status, "failure", {}, None)

    monkeypatch.setattr(launch, "build_opener", lambda *args: SimpleNamespace(open=opening))
    with pytest.raises(HTTPError) as error:
        launch.local_readiness()
    assert error.value.code == status
    assert readiness_clock["sleeps"] == []
