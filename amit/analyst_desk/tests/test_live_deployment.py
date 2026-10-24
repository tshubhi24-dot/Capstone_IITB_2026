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
from desk.model_profiles import model_profile


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


def test_explicit_profile_switch_archives_policy_but_preserves_caps_keys_and_ledger(private):
    original = prep.prepare(private)
    previous = prep.load_config()
    previous.update(per_run_usd="0.40", max_calls_per_run=10, max_tokens_per_run=230000)
    prep.write_private(prep.CONFIG_FILE, json.dumps(previous), 0o444)
    old_hash = prep.proposal_hash(previous)
    prep.authorize(old_hash, "Synthetic prior human confirmation stays private")
    approved = prep.load_config()
    old_approval = prep.APPROVAL_FILE.read_bytes()
    key_bytes = prep.KEY_FILE.read_bytes()
    retired = prep.PRIVATE / "retired"
    retired.mkdir(mode=0o700)
    retired_key = retired / "synthetic.key"
    retired_key.write_text("retired-fictional-value-never-copy")
    ledger = prep.PRIVATE / "synthetic-ledger-sentinel"
    ledger.write_text("old holds and charges remain")

    result = prep.switch_profile("mistral", old_hash)
    current = prep.load_config()
    profile = model_profile("live-step10-mistral-v1")
    assert current["enabled"] is False and current["version"] == profile["version"]
    assert current["models"] == profile["models"]
    assert current["authorization_id"] != original["config"]["authorization_id"]
    for field in set(approved) - {"enabled", "authorization_id", "models", "version"}:
        assert current[field] == approved[field]
    assert current["cap_usd"] == "1.00" and current["per_run_usd"] == "0.40"
    assert prep.KEY_FILE.read_bytes() == key_bytes
    assert retired_key.read_text() == "retired-fictional-value-never-copy"
    assert ledger.read_text() == "old holds and charges remain"
    assert not prep.APPROVAL_FILE.exists()
    archives = list((prep.PRIVATE / "policy_history").iterdir())
    assert len(archives) == 1
    archive = archives[0]
    assert json.loads((archive / "model_config.json").read_text()) == approved
    assert (archive / "authorization.json").read_bytes() == old_approval
    assert stat.S_IMODE(archive.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in archive.iterdir())
    assert result["paid_calls_performed"] == 0 and result["ledger_changed"] is False
    assert result["credentials_changed"] is False and result["proposal_hash"] == prep.proposal_hash(current)
    assert "Synthetic prior human confirmation" not in json.dumps(result)
    assert key_bytes.decode().strip() not in json.dumps(result)
    # Ordinary preparation preserves the explicit replacement without enabling it.
    assert prep.prepare()["config"] == current


def test_profile_switch_needs_current_hash_and_never_reauthorizes_an_old_decision(private):
    old = prep.prepare(private)
    prep.authorize(old["proposal_hash"], "Synthetic old policy approval")
    old_receipt = prep.APPROVAL_FILE.read_text()
    with pytest.raises(ValueError, match="stale"):
        prep.switch_profile("mistral", "0" * 64)
    assert prep.load_config()["authorization_id"] == old["config"]["authorization_id"]
    assert not (prep.PRIVATE / "policy_history").exists()
    with pytest.raises(ValueError, match="Unknown"):
        prep.switch_profile("unreviewed", old["proposal_hash"])
    staged = prep.switch_profile("mistral", old["proposal_hash"])
    with pytest.raises(ValueError, match="already prepared"):
        prep.switch_profile("mistral", staged["proposal_hash"])
    assert prep.load_config()["authorization_id"] == staged["config"]["authorization_id"]
    with pytest.raises(ValueError, match="stale"):
        prep.authorize(old["proposal_hash"], "Synthetic repeated old approval")
    # An old receipt cannot enable a replacement by being copied into place.
    prep.write_private(prep.APPROVAL_FILE, old_receipt, 0o600)
    tampered = prep.load_config()
    tampered["enabled"] = True
    prep.write_private(prep.CONFIG_FILE, json.dumps(tampered), 0o444)
    with pytest.raises(ValueError, match="differs"):
        live.prepared_configuration()
    prep.disable()
    prep.authorize(staged["proposal_hash"], "Synthetic explicit replacement approval")
    assert live.prepared_configuration()["enabled"] is True


def test_profile_switch_refuses_symlink_archive_without_changing_active_policy(private, tmp_path):
    original = prep.prepare(private)
    outside = tmp_path / "outside-archive"
    outside.mkdir()
    (prep.PRIVATE / "policy_history").symlink_to(outside)
    with pytest.raises(ValueError, match="regular directory"):
        prep.switch_profile("mistral", original["proposal_hash"])
    assert prep.load_config() == original["config"] and list(outside.iterdir()) == []


@pytest.mark.parametrize("version", ["live-step6-openrouter-v1", "live-step10-mistral-v1", "live-step10-mistral-large2407-v1", "live-step10-google-critic-v1"])
def test_prepared_configuration_accepts_only_exact_reviewed_profile_prices(version):
    profile = model_profile(version)
    config = {**deepcopy(prep.DEFAULTS), "authorization_id": "b" * 32,
              "version": version, "models": profile["models"], **profile.get("limits", {})}
    assert prep.validate_config(config) == config
    config["models"]["producer"]["completion_usd_per_token"] = "0.00000001"
    with pytest.raises(ValueError, match="model and pricing"):
        prep.validate_config(config)


@pytest.mark.parametrize("prior_limits,expected_limits", [
    ({"prompt_token_ceiling": 65536, "max_message_bytes": 60000}, {"prompt_token_ceiling": 49152, "max_message_bytes": 45056}),
    ({"prompt_token_ceiling": 32768, "max_message_bytes": 28000}, {"prompt_token_ceiling": 32768, "max_message_bytes": 28000}),
])
def test_large2407_switch_only_tightens_context_and_preserves_original_authority(private, prior_limits, expected_limits):
    prep.prepare(private)
    previous = prep.load_config()
    old_profile = model_profile("live-step10-mistral-v1")
    previous.update(version=old_profile["version"], models=old_profile["models"], max_output_tokens=2000, **prior_limits)
    prep.write_private(prep.CONFIG_FILE, json.dumps(previous), 0o444)
    old_hash = prep.proposal_hash(previous)
    prep.authorize(old_hash, "Synthetic original live authorization")
    approved = prep.load_config()
    approval_bytes, key_bytes = prep.APPROVAL_FILE.read_bytes(), prep.KEY_FILE.read_bytes()
    ledger = prep.PRIVATE / "ledger-sentinel"
    ledger.write_bytes(b"existing charges and both uncertain holds")

    result = prep.switch_profile("mistral-large2407", old_hash)
    current = prep.load_config()
    assert current["version"] == "live-step10-mistral-large2407-v1" and current["enabled"] is False
    assert current["authorization_id"] != approved["authorization_id"]
    assert current["models"]["producer"] == approved["models"]["producer"]
    assert current["models"]["critic"]["id"] == "mistralai/mistral-large-2407"
    for key, value in expected_limits.items():
        assert current[key] == value and current[key] <= approved[key]
    for key in ("cap_usd", "per_run_usd", "max_calls_per_run", "max_tokens_per_run", "max_output_tokens"):
        assert current[key] == approved[key]
    assert current["cap_usd"] == "1.00" and current["per_run_usd"] == "0.50"
    assert current["max_calls_per_run"] == 12 and current["max_tokens_per_run"] == 250000
    assert prep.KEY_FILE.read_bytes() == key_bytes and ledger.read_bytes() == b"existing charges and both uncertain holds"
    assert result["ledger_changed"] is False and result["paid_calls_performed"] == 0
    assert result["proposal_hash"] != old_hash and not prep.APPROVAL_FILE.exists()
    archive = next((prep.PRIVATE / "policy_history").iterdir())
    assert json.loads((archive / "model_config.json").read_text()) == approved
    assert (archive / "authorization.json").read_bytes() == approval_bytes
    assert prep.prepare()["config"] == current
    with pytest.raises(ValueError, match="stale"):
        prep.authorize(old_hash, "Synthetic old authorization cannot enable replacement")


@pytest.mark.parametrize("limits", [
    {"prompt_token_ceiling": 49153, "max_message_bytes": 45056},
    {"prompt_token_ceiling": 49153, "max_message_bytes": 45057},
])
def test_large2407_preparation_refuses_context_above_reviewed_bounds(limits):
    profile = model_profile("live-step10-mistral-large2407-v1")
    config = {**deepcopy(prep.DEFAULTS), "authorization_id": "b" * 32,
              "version": profile["version"], "models": profile["models"], **limits}
    with pytest.raises(ValueError, match="reviewed profile limit"):
        prep.validate_config(config)


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


def test_every_python_service_uses_the_image_built_by_the_live_launcher(resolved):
    services = resolved["services"]
    expected = services["app"]["image"]
    for name in ("init-secrets", "filings-kb", "edgar", "python-sandbox", "research-portal", "pandas-worker", "model-gateway"):
        assert services[name]["image"] == expected


def test_actual_merged_compose_keeps_provider_key_and_egress_only_at_gateway(resolved):
    live.validate(resolved)
    services = resolved["services"]
    assert set(services["app"]["networks"]) == {"backend"}
    assert set(services["model-gateway"]["networks"]) == {"backend", "provider-egress"}
    assert services["pandas-worker"]["network_mode"] == "none"
    for service in ("app", "init-secrets", "model-gateway"):
        assert services[service]["image"] == "analyst-desk:amit-live-v1"
    assert services["edgar"]["image"] == services["app"]["image"]
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
    assert [command[-1] for command in starts if "--force-recreate" in command] == ["model-gateway", "ingress"]
    assert live.LIVE_ORDER.index("model-gateway") < live.LIVE_ORDER.index("app")
    assert live.LIVE_ORDER.index("app") < live.LIVE_ORDER.index("ingress")
    assert live.LIVE_ORDER.index("grafana") < live.LIVE_ORDER.index("ingress")
    assert next(i for i, (command, _) in enumerate(calls) if "wait" in command) < next(i for i, (command, _) in enumerate(calls) if command[-1] == "pandas-worker")
    assert ready == [True]


def test_live_rebuild_refreshes_existing_ingress_before_readiness(monkeypatch):
    addresses = {"app": "previous-app-address", "ingress_upstream": "previous-app-address"}
    ingress_starts = []

    def capture(command, env, token, timeout=30):
        if command[-4:] == ["ps", "--all", "--quiet", "init-secrets"]:
            return "b" * 64
        if "inspect" in command:
            return "exited 0"
        if command[-4:] == ["ps", "--status", "running", "--services"]:
            return "\n".join(live.LIVE_ORDER)
        if "up" in command and command[-1] == "app":
            addresses["app"] = "rebuilt-app-address"
        if "up" in command and command[-1] == "ingress":
            ingress_starts.append(command)
            if "--force-recreate" in command:
                addresses["ingress_upstream"] = addresses["app"]
        return ""

    def ready():
        assert addresses["ingress_upstream"] == addresses["app"] == "rebuilt-app-address"

    monkeypatch.setattr(base, "capture", capture)
    monkeypatch.setattr(base, "local_readiness", ready)
    live.start_stack(["docker", "compose"], {}, "fictional-local-token")
    assert len(ingress_starts) == 1


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
