"""Live-overlay authority and preparation checks; no paid calls or daemon startup."""
from copy import deepcopy
import json
from pathlib import Path
import stat

import pytest

from ops import prepare_live as prep
from ops import start_live as live
from ops import start_journey as base
from ops.bootstrap import initialize, SERVICE_ROLES


@pytest.fixture
def private(tmp_path, monkeypatch):
    root = tmp_path / "live"
    monkeypatch.setattr(prep, "PRIVATE", root)
    monkeypatch.setattr(prep, "CONFIG_FILE", root / "model_config.json")
    monkeypatch.setattr(prep, "KEY_FILE", root / "provider.key")
    monkeypatch.setattr(prep, "APPROVAL_FILE", root / "authorization.json")
    source = tmp_path / "source.env"
    source.write_text('OPENROUTER_API_KEY="' + "invented-key-value-" * 3 + '"\nUNRELATED_PASSWORD=must-stay-here\n')
    return source


def test_preparation_extracts_only_provider_key_and_stays_disabled(private):
    receipt = prep.prepare(private)
    original = prep.read_provider_key(private)
    assert receipt["config"]["enabled"] is False and receipt["paid_calls_performed"] == 0
    assert prep.KEY_FILE.read_text().strip() == original
    assert original not in json.dumps(receipt)
    assert "must-stay-here" not in prep.KEY_FILE.read_text()
    assert not prep.APPROVAL_FILE.exists()
    assert stat.S_IMODE(prep.PRIVATE.stat().st_mode) == 0o700
    assert stat.S_IMODE(prep.KEY_FILE.stat().st_mode) == 0o444
    assert stat.S_IMODE(prep.CONFIG_FILE.stat().st_mode) == 0o444
    repeated = prep.prepare()
    assert repeated["proposal_hash"] == receipt["proposal_hash"]
    assert repeated["config"]["authorization_id"] == receipt["config"]["authorization_id"]


def test_authorization_requires_exact_proposal_and_explicit_confirmation(private):
    prepared = prep.prepare(private)
    with pytest.raises(ValueError, match="stale"):
        prep.authorize("0" * 64, "Human approved a different version")
    with pytest.raises(ValueError, match="Explicit human"):
        prep.authorize(prepared["proposal_hash"], " ")
    assert prep.load_config()["enabled"] is False and not prep.APPROVAL_FILE.exists()
    result = prep.authorize(prepared["proposal_hash"], "Test-only operator confirmation")
    assert result["enabled"] and result["changed"]
    assert prep.load_config()["authorization_id"] == prepared["config"]["authorization_id"]
    assert prep.proposal_hash(prep.load_config()) == prepared["proposal_hash"]
    assert stat.S_IMODE(prep.APPROVAL_FILE.stat().st_mode) == 0o600
    assert not prep.authorize(prepared["proposal_hash"], "Repeated test-only confirmation")["changed"]
    assert "Test-only operator confirmation" not in json.dumps(result)


def test_reprepare_never_activates_and_cannot_silently_replace_provider_key(private):
    original = prep.prepare(private)
    private.write_text("OPENROUTER_API_KEY=" + "different-invented-key-" * 3 + "\n")
    with pytest.raises(ValueError, match="not replaced"):
        prep.prepare(private)
    assert prep.load_config()["enabled"] is False
    assert prep.proposal_hash(prep.load_config()) == original["proposal_hash"]


def test_tampering_with_authorized_cap_is_detected_before_start(private):
    receipt = prep.prepare(private)
    prep.authorize(receipt["proposal_hash"], "Test-only approval")
    assert live.prepared_configuration()["enabled"]
    config = prep.load_config()
    config["cap_usd"] = "100.00"
    prep.write_private(prep.CONFIG_FILE, json.dumps(config), 0o444)
    with pytest.raises(ValueError, match="differs"):
        live.prepared_configuration()


def test_disabling_keeps_authorization_identity_and_preserves_usage_namespace(private):
    receipt = prep.prepare(private)
    prep.authorize(receipt["proposal_hash"], "Test-only approval")
    disabled = prep.disable()
    assert disabled["enabled"] is False
    assert prep.proposal_hash(prep.load_config()) == receipt["proposal_hash"]
    assert prep.load_config()["authorization_id"] == receipt["config"]["authorization_id"]
    assert prep.APPROVAL_FILE.is_file()


def test_prepared_files_refuse_symlinks(private, tmp_path):
    prep.prepare(private)
    outside = tmp_path / "outside"
    outside.write_text("do-not-change")
    prep.CONFIG_FILE.unlink()
    prep.CONFIG_FILE.symlink_to(outside)
    with pytest.raises(ValueError, match="first"):
        prep.load_config()
    assert outside.read_text() == "do-not-change"


def test_live_bootstrap_upgrades_stably_without_giving_model_token_to_tools(tmp_path, capsys):
    initialize(tmp_path)
    old = json.loads((tmp_path / "app/config.json").read_text())
    assert "model_token" not in old
    initialize(tmp_path, include_model_gateway=True)
    current = json.loads((tmp_path / "app/config.json").read_text())
    assert {key: current[key] for key in old} == old
    gateway = json.loads((tmp_path / "model-gateway/config.json").read_text())
    assert gateway == {"model_token": current["model_token"]}
    assert len(current["model_token"]) >= 32
    initialize(tmp_path, include_model_gateway=True)
    assert json.loads((tmp_path / "app/config.json").read_text()) == current
    for service in SERVICE_ROLES:
        assert "model_token" not in json.loads((tmp_path / service / "config.json").read_text())
    assert current["model_token"] not in capsys.readouterr().out


@pytest.fixture
def resolved(tmp_path, monkeypatch):
    try:
        docker = base.docker_binary()
    except RuntimeError:
        pytest.skip("Docker CLI needed only for Compose rendering; no daemon startup")
    credentials = tmp_path / "credentials.env"
    credentials.write_text("ANALYST_API_TOKEN=" + "fictional-local-token-" * 3 + "\n")
    monkeypatch.setattr(base, "ENV_FILE", credentials)
    env = live.environment(docker)
    return json.loads(base.capture(live.compose(docker) + ["config", "--format", "json"], env, "fictional-local-token-" * 3))


def test_actual_merged_compose_keeps_provider_key_and_egress_only_at_gateway(resolved):
    live.validate(resolved)
    services = resolved["services"]
    assert set(services["app"]["networks"]) == {"backend"}
    assert set(services["model-gateway"]["networks"]) == {"backend", "provider-egress"}
    assert services["pandas-worker"]["network_mode"] == "none"
    for service in ("app", "init-secrets", "model-gateway"):
        assert services[service]["image"] == "analyst-desk:amit-live-v1"
    assert services["edgar"]["image"] == "analyst-desk:amit-step4"
    key_mounts = [(name, mount) for name, service in services.items() for mount in service.get("volumes", []) if mount["target"] == "/run/provider/key"]
    assert len(key_mounts) == 1 and key_mounts[0][0] == "model-gateway" and key_mounts[0][1]["read_only"]
    assert all(volume["name"].startswith(base.PROJECT + "_") for volume in resolved["volumes"].values())


@pytest.mark.parametrize("mutation", ["app_egress", "gateway_port", "raw_key_env", "writable_key", "shared_history", "root_gateway"])
def test_live_configuration_rejects_authority_and_secret_boundary_regressions(resolved, mutation):
    model = deepcopy(resolved)
    gateway = model["services"]["model-gateway"]
    if mutation == "app_egress":
        model["services"]["app"]["networks"]["provider-egress"] = None
    elif mutation == "gateway_port":
        gateway["ports"] = [{"host_ip": "127.0.0.1", "published": "18020", "target": 8020}]
    elif mutation == "raw_key_env":
        gateway["environment"]["OPENROUTER_API_KEY"] = "invented-secret-must-not-be-forwarded"
    elif mutation == "writable_key":
        next(mount for mount in gateway["volumes"] if mount["target"] == "/run/provider/key")["read_only"] = False
    elif mutation == "shared_history":
        next(mount for mount in gateway["volumes"] if mount["target"] == "/runtime")["source"] = "runtime"
    else:
        gateway["user"] = "0:0"
    with pytest.raises(ValueError):
        live.validate(model)


def test_launcher_drops_ambient_provider_credentials_and_config_overrides(monkeypatch):
    for key in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "MODEL_GATEWAY_URL", "DOCKER_HOST", "COMPOSE_FILE"):
        monkeypatch.setenv(key, "unrelated-secret-value")
    env = live.environment("docker")
    assert all(key not in env for key in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "MODEL_GATEWAY_URL", "DOCKER_HOST", "COMPOSE_FILE"))


def test_live_start_is_serial_waits_for_initializer_and_reloads_gateway(monkeypatch):
    calls = []
    ready = []

    def capture(command, env, token, timeout=30):
        calls.append((command, timeout))
        if command[-4:] == ["ps", "--all", "--quiet", "init-secrets"]:
            return "b" * 64
        if "inspect" in command:
            return "exited 0"
        if command[-4:] == ["ps", "--status", "running", "--services"]:
            return "\n".join(live.LIVE_ORDER)
        return ""

    monkeypatch.setattr(base, "capture", capture)
    monkeypatch.setattr(base, "local_readiness", lambda: ready.append(True))
    live.start_stack(["docker", "compose"], {}, "fictional-local-token")
    starts = [command for command, timeout in calls if "up" in command]
    assert [command[-1] for command in starts] == ["init-secrets", *live.LIVE_ORDER]
    assert all("--no-deps" in command and "--no-build" in command for command in starts)
    assert sum("--force-recreate" in command for command in starts) == 1
    assert "--force-recreate" in next(command for command in starts if command[-1] == "model-gateway")
    assert live.LIVE_ORDER.index("model-gateway") < live.LIVE_ORDER.index("app")
    assert next(i for i, (command, _) in enumerate(calls) if "wait" in command) < next(i for i, (command, _) in enumerate(calls) if command[-1] == "pandas-worker")
    assert ready == [True]


def test_failed_initializer_stops_before_gateway_and_other_services(monkeypatch):
    calls = []

    def capture(command, env, token, timeout=30):
        calls.append(command)
        if command[-4:] == ["ps", "--all", "--quiet", "init-secrets"]:
            return "c" * 64
        return "exited 1" if "inspect" in command else ""

    monkeypatch.setattr(base, "capture", capture)
    with pytest.raises(RuntimeError, match="initialization failed"):
        live.start_stack(["docker", "compose"], {}, "fictional-local-token")
    assert [command[-1] for command in calls if "up" in command] == ["init-secrets"]
