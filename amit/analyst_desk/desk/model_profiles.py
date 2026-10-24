"""Reviewed model pairs and fixed provider routes; no runtime dependencies."""
from copy import deepcopy


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
        if len(matches) != 1 or isinstance(configured_version, str) and configured_version in MODEL_PROFILES and configured_version != matches[0]:
            raise ValueError("Unknown or inconsistent reviewed model pair")
        version = matches[0]
    else:
        raise ValueError("A reviewed model profile is required")
    return {"version": version, **deepcopy(MODEL_PROFILES[version])}
