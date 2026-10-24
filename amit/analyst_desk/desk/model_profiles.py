"""Reviewed model pairs and fixed provider routes; no runtime dependencies."""
from copy import deepcopy
from decimal import Decimal


MODEL_PROFILES = {
    "live-step6-openrouter-v1": {
        "models": {
            "producer": {"id": "openai/gpt-4.1-mini", "prompt_usd_per_token": "0.0000004", "completion_usd_per_token": "0.0000016"},
            "critic": {"id": "openai/gpt-4.1", "prompt_usd_per_token": "0.000002", "completion_usd_per_token": "0.000008"},
        },
        "provider": "openai",
    },
    "live-step10-mistral-v1": {
        "models": {
            "producer": {"id": "mistralai/mistral-medium-3.1", "prompt_usd_per_token": "0.0000004", "completion_usd_per_token": "0.000002"},
            "critic": {"id": "mistralai/mistral-large-2512", "prompt_usd_per_token": "0.0000005", "completion_usd_per_token": "0.0000015"},
        },
        "provider": "mistral/zdr",
    },
    "live-step10-mistral-large2407-v1": {
        "models": {
            "producer": {"id": "mistralai/mistral-medium-3.1", "prompt_usd_per_token": "0.0000004", "completion_usd_per_token": "0.000002"},
            "critic": {"id": "mistralai/mistral-large-2407", "prompt_usd_per_token": "0.000002", "completion_usd_per_token": "0.000006"},
        },
        "provider": "mistral/zdr",
        "limits": {"prompt_token_ceiling": 49152, "max_message_bytes": 45056},
    },
    "live-step10-google-critic-v1": {
        "models": {
            "producer": {"id": "mistralai/mistral-medium-3.1", "prompt_usd_per_token": "0.0000004", "completion_usd_per_token": "0.000002"},
            "critic": {"id": "google/gemini-2.5-flash", "prompt_usd_per_token": "0.0000003", "completion_usd_per_token": "0.0000025"},
        },
        "provider": "role-specific",
        "providers": {"producer": "mistral/zdr", "critic": "google-ai-studio"},
        "limits": {"prompt_token_ceiling": 49152, "max_message_bytes": 45056},
        "critic_reasoning": {"enabled": False},
    },
    "live-step16-fallbacks-v1": {
        "models": {
            "producer": {"id": "openai/gpt-4.1-mini", "prompt_usd_per_token": "0.0000004", "completion_usd_per_token": "0.0000016"},
            "critic": {"id": "google/gemini-2.5-flash", "prompt_usd_per_token": "0.0000003", "completion_usd_per_token": "0.0000025"},
        },
        "provider": "role-specific",
        "providers": {"producer": "openai", "critic": "google-ai-studio"},
        "routes": {
            "producer": {"models": ["openai/gpt-4.1-mini", "mistralai/mistral-medium-3.1"],
                         "providers": ["openai", "azure", "mistral/zdr"], "allow_fallbacks": True},
        },
        "limits": {"prompt_token_ceiling": 49152, "max_message_bytes": 45056},
        "critic_reasoning": {"enabled": False},
    },
}


def model_profile(value):
    """Return a copy of an allowlisted profile by version or exact model pair.

    Configurations may retain their own immutable policy version. Model IDs
    determine the reviewed pair; a known catalogue version must match it.
    Price and budget validation is performed separately by the gateway.
    """
    if isinstance(value, str):
        if value not in MODEL_PROFILES:
            raise ValueError("Unknown reviewed model profile")
        version = value
    elif isinstance(value, dict):
        models = value.get("models")
        if not isinstance(models, dict) or set(models) != {"producer", "critic"}:
            raise ValueError("A reviewed model pair is required")
        matches = [name for name, profile in MODEL_PROFILES.items()
                   if all(isinstance(models.get(role), dict) and models[role].get("id") == profile["models"][role]["id"]
                          for role in ("producer", "critic"))]
        configured_version = value.get("version")
        if isinstance(configured_version, str) and configured_version in MODEL_PROFILES:
            if configured_version not in matches:
                raise ValueError("Unknown or inconsistent reviewed model pair")
            version = configured_version
        else:
            # Custom policy versions historically identify an exact legacy pair.
            # A routing change requires its explicit reviewed profile version.
            matches = [name for name in matches if "routes" not in MODEL_PROFILES[name]]
            if len(matches) != 1:
                raise ValueError("Unknown or inconsistent reviewed model pair")
            version = matches[0]
    else:
        raise ValueError("A reviewed model profile is required")
    return {"version": version, **deepcopy(MODEL_PROFILES[version])}


def model_route(value, role):
    """Return the fixed role route and its maximum reviewed token prices.

    The producer envelope includes every permitted backup; no caller-provided
    routing fields are accepted. Legacy profiles retain their single route.
    """
    if role not in {"producer", "critic"}:
        raise ValueError("A producer or critic model route is required")
    profile = model_profile(value)
    route = deepcopy(profile.get("routes", {}).get(role, {
        "models": [profile["models"][role]["id"]],
        "providers": [profile.get("providers", {}).get(role, profile["provider"])],
        "allow_fallbacks": False,
    }))
    policies = {policy["id"]: policy for entry in MODEL_PROFILES.values() for policy in entry["models"].values()}
    for field in ("prompt_usd_per_token", "completion_usd_per_token"):
        route[field] = str(max(Decimal(policies[model][field]) for model in route["models"]))
    return route
