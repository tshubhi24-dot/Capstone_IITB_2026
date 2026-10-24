"""Prepare or explicitly authorize one frozen critic call beyond original limits.

Preparation reads the local research API and internal gateway accounting only.
Authorization registers an append-only grant through the operator's Docker
access; the application's ordinary model token cannot create grants. Neither
action requests a model completion or reads a provider key.
"""
from copy import deepcopy
from decimal import Decimal
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desk.model_profiles import model_profile
from desk.reasoning import Reasoner
from desk.store import canonical_hash
from ops import prepare_live as prep
from ops import start_journey as base
from ops import start_live as live
from ops.journey_session import JourneyClient, DEFAULT_CREDENTIALS, DEFAULT_BASE_URL, read_token

PROPOSAL_FILE = prep.PRIVATE / "critic_extension_proposal.json"
APPROVAL_FILE = prep.PRIVATE / "critic_extension_authorization.json"
PROFILE = "live-step10-google-critic-v1"
READ_BUDGET = """import json,os,sys
from desk.provider import ModelGatewayClient
value=json.load(sys.stdin)
scoped=json.load(open(os.environ['SCOPED_CONFIG']))
print(json.dumps(ModelGatewayClient(scoped['model_token']).budget(value['run_id'])))
"""
REGISTER_GRANT = """import json,os,sys
from desk.provider import BudgetLedger
value=json.load(sys.stdin)
config=json.load(open(os.environ['MODEL_CONFIG_FILE']))
ledger=BudgetLedger(os.environ['MODEL_LEDGER_PATH'],config)
print(json.dumps(ledger.grant_run_extension(value['proposal'],value['expected_hash'],value['human_confirmation'])))
"""


def policy_hash(config):
    return canonical_hash({key: value for key, value in config.items() if key != "enabled"})


def docker_json(service, code, value):
    docker = base.docker_binary()
    result = subprocess.run(live.compose(docker) + ["exec", "-T", service, "python", "-c", code],
                            input=json.dumps(value), capture_output=True, text=True, cwd=ROOT,
                            env=live.environment(docker), timeout=30)
    if result.returncode or len(result.stdout) > 200000:
        raise ValueError("The local operator accounting operation failed; no provider request was made.")
    try:
        return json.loads(result.stdout)
    except ValueError:
        raise ValueError("The local accounting operation returned invalid metadata.") from None


def read_budget(run_id):
    return docker_json("app", READ_BUDGET, {"run_id": run_id})


def register(proposal, expected_hash, human_confirmation):
    return docker_json("model-gateway", REGISTER_GRANT,
                       {"proposal": proposal, "expected_hash": expected_hash, "human_confirmation": human_confirmation})


def capture_critic_request(run_id, draft, grant_id, config):
    """Build exactly the Reasoner's bounded request without invoking a model."""
    captured = {}
    purpose = "critic:" + canonical_hash({key: value for key, value in draft.items() if key != "semantic_verdict"}) + ":explicit-approved-extension:" + grant_id

    class Captured(Exception):
        pass

    def capture(role, *, system, context, schema, max_output_tokens):
        messages = [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(context, ensure_ascii=False)}]
        identifier = canonical_hash({"run": run_id, "purpose": purpose, "role": role, "messages": messages, "schema": schema})
        captured.update(run_id=run_id, call_id=identifier, role=role, messages=messages,
                        response_schema=schema, max_output_tokens=max_output_tokens,
                        model=config["models"]["critic"]["id"], config_version=config["version"])
        raise Captured

    try:
        Reasoner(capture).critique(draft, draft["ai_evidence"])
    except Captured:
        pass
    if not captured or captured["role"] != "critic" or captured["max_output_tokens"] != 2000:
        raise ValueError("The frozen draft did not produce the reviewed critic request.")
    bounded = {"messages": captured["messages"], "response_schema": captured["response_schema"]}
    if len(json.dumps(bounded, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()) > config["max_message_bytes"]:
        raise ValueError("The frozen critic context exceeds its reviewed message limit.")
    return captured


def build_proposal(run, budget, config, grant_id):
    profile = model_profile(config)
    draft = deepcopy(run.get("draft"))
    if (profile["version"] != PROFILE or not isinstance(draft, dict) or draft.get("semantic_verdict")
            or run.get("status") != "error" or run.get("request", {}).get("mode") != "live"
            or not str(run.get("error", "")).startswith("ReviewError: provider_http_429:")
            or run.get("request", {}).get("max_model_calls") != 12 or run.get("request", {}).get("max_tokens") != 250000
            or config["max_calls_per_run"] != 12 or config["max_tokens_per_run"] != 250000
            or config["prompt_token_ceiling"] != 49152 or config["max_output_tokens"] < 2000
            or budget.get("run_id") != run.get("id") or budget.get("policy_hash") != policy_hash(config)
            or budget.get("model_profile") != PROFILE or budget.get("providers") != profile["providers"]
            or budget.get("model_calls") != 12 or budget.get("tokens") != 246409 or budget.get("uncertain_calls") != 3
            or budget.get("blocked") is not False or budget.get("original_max_calls_per_run") != 12
            or budget.get("original_max_tokens_per_run") != 250000
            or not re.fullmatch(r"[a-f0-9]{64}", budget.get("ledger_checkpoint_hash", ""))):
        raise ValueError("The exact frozen critic checkpoint, reviewed policy and retained holds are required.")
    if (Decimal(str(budget["cap_usd"])) > 1 or Decimal(str(budget["per_run_usd"])) > Decimal(".50")
            or Decimal(str(budget["cap_usd"])) != Decimal(config["cap_usd"])
            or Decimal(str(budget["per_run_usd"])) != Decimal(config["per_run_usd"])):
        raise ValueError("The original dollar ceilings must remain unchanged.")
    request = capture_critic_request(run["id"], draft, grant_id, config)
    price = profile["models"]["critic"]
    reservation = Decimal(price["prompt_usd_per_token"]) * 49152 + Decimal(price["completion_usd_per_token"]) * 2000
    if (Decimal(str(budget["committed_usd"])) + reservation > Decimal(str(budget["per_run_usd"]))
            or reservation > Decimal(str(budget["remaining_authorization_usd"]))):
        raise ValueError("The unchanged dollar budget cannot cover the proposed critic call.")
    proposal = {"grant_id": grant_id, "run_id": run["id"], "policy_hash": policy_hash(config),
                "plan_hash": canonical_hash(run["plan"]), "draft_hash": canonical_hash(draft), "call_id": request["call_id"],
                "request_hash": canonical_hash(request), "checkpoint_hash": budget["ledger_checkpoint_hash"],
                "original_calls": 12, "original_tokens": 250000, "max_calls": 13, "max_tokens": 300000,
                "checkpoint_calls": 12, "checkpoint_tokens": 246409, "checkpoint_uncertain": 3,
                "checkpoint_reported_spend_usd": budget["reported_spend_usd"], "checkpoint_held_usd": budget["held_usd"],
                "cap_usd": budget["cap_usd"], "per_run_usd": budget["per_run_usd"], "model_profile": PROFILE,
                "critic_model": profile["models"]["critic"]["id"], "role": "critic", "reserved_tokens": 51152,
                "reservation_usd": str(reservation)}
    return {"proposal_hash": canonical_hash(proposal), "proposal": proposal, "request": request,
            "paid_calls_performed": 0, "approved": False, "next_reserved_token_total": 297561}


def private_proposal():
    if PROPOSAL_FILE.is_symlink() or not PROPOSAL_FILE.is_file() or PROPOSAL_FILE.stat().st_mode & 0o077:
        raise ValueError("Prepare the private extension proposal first.")
    return json.loads(PROPOSAL_FILE.read_text())


def prepare(run_id, *, client=None, budget_reader=None, grant_id=None):
    config = prep.load_config()
    existing = private_proposal() if PROPOSAL_FILE.exists() else None
    if existing and existing["proposal"]["run_id"] != run_id:
        raise ValueError("The private proposal belongs to another run; preserve it before continuing.")
    grant_id = grant_id or (existing["proposal"]["grant_id"] if existing else uuid.uuid4().hex)
    if not re.fullmatch(r"[a-f0-9]{32}", grant_id):
        raise ValueError("The extension grant identifier is invalid.")
    client = client or JourneyClient(token=read_token(DEFAULT_CREDENTIALS), mode="live", base_url=DEFAULT_BASE_URL)
    run = client.request("GET", "/api/runs/" + run_id)
    result = build_proposal(run, (budget_reader or read_budget)(run_id), config, grant_id)
    if existing and existing != result:
        raise ValueError("The prepared extension is stale; its exact checkpoint or critic request changed.")
    prep.ensure_private_directory()
    prep.write_private(PROPOSAL_FILE, json.dumps(result, indent=2) + "\n", 0o600)
    return {key: value for key, value in result.items() if key != "request"}


def authorize(expected_hash, human_confirmation, *, client=None, budget_reader=None, registrar=None):
    existing = private_proposal()
    if (not re.fullmatch(r"[a-f0-9]{64}", expected_hash or "") or existing.get("proposal_hash") != expected_hash
            or canonical_hash(existing["proposal"]) != expected_hash
            or not isinstance(human_confirmation, str) or not human_confirmation.strip()):
        raise ValueError("Authorize the exact reviewed extension hash with explicit human confirmation.")
    fresh = prepare(existing["proposal"]["run_id"], client=client, budget_reader=budget_reader,
                    grant_id=existing["proposal"]["grant_id"])
    if fresh["proposal_hash"] != expected_hash:
        raise ValueError("The reviewed extension changed before authorization.")
    result = (registrar or register)(existing["proposal"], expected_hash, human_confirmation.strip())
    if result.get("approved") is not True or result.get("proposal_hash") != expected_hash:
        raise ValueError("The trusted ledger did not register the exact reviewed grant.")
    receipt = {**result, "human_confirmation": human_confirmation.strip(), "paid_calls_performed": 0}
    prep.write_private(APPROVAL_FILE, json.dumps(receipt, indent=2) + "\n", 0o600)
    return {key: value for key, value in receipt.items() if key != "human_confirmation"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true")
    action.add_argument("--authorize", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--expected-hash")
    parser.add_argument("--human-confirmation")
    args = parser.parse_args()
    try:
        if args.prepare:
            if not args.run_id or args.expected_hash or args.human_confirmation:
                raise ValueError("Preparation needs only the stopped run ID; it cannot approve an extension.")
            result = prepare(args.run_id)
        else:
            if args.run_id:
                raise ValueError("Authorization uses the prepared proposal's exact run ID.")
            result = authorize(args.expected_hash, args.human_confirmation)
        print(json.dumps(result, indent=2))
    except Exception:
        # Never print private API responses, confirmations or command stderr.
        print("The critic extension operation was refused; check its exact prepared hash, checkpoint and operator approval.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
