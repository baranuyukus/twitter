"""Persistent desktop UI configuration."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import tweeter

CONFIG_FILE = Path(os.environ.get("TWEETER_DATA_DIR", Path(__file__).parent)).expanduser() / "app_config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "aiProvider": "oauth",
    "aiBaseUrl": tweeter.DEFAULT_AI_BASE_URL,
    "aiModel": tweeter.DEFAULT_AI_MODEL,
    "aiTimeout": tweeter.DEFAULT_AI_TIMEOUT,
    "aiApiKey": "",
}


def mask_secret(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    return value[:7] + "..." + value[-4:] if len(value) > 14 else value[:3] + "..."


def load_config() -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                config.update(data)
        except (json.JSONDecodeError, OSError):
            pass
    return config


def save_config(updates: dict[str, Any]) -> dict[str, Any]:
    config = load_config()
    allowed = {"aiProvider", "aiBaseUrl", "aiModel", "aiTimeout", "aiApiKey"}
    for key, value in updates.items():
        if key in allowed:
            config[key] = value
    if not str(config.get("aiBaseUrl") or "").strip():
        config["aiBaseUrl"] = DEFAULT_CONFIG["aiBaseUrl"]
    if not str(config.get("aiModel") or "").strip():
        config["aiModel"] = DEFAULT_CONFIG["aiModel"]
    config["aiTimeout"] = int(config.get("aiTimeout") or DEFAULT_CONFIG["aiTimeout"])
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    apply_ai_env(config)
    return config


def public_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or load_config()
    return {
        "aiProvider": config.get("aiProvider") or "oauth",
        "aiBaseUrl": config.get("aiBaseUrl") or DEFAULT_CONFIG["aiBaseUrl"],
        "aiModel": config.get("aiModel") or DEFAULT_CONFIG["aiModel"],
        "aiTimeout": int(config.get("aiTimeout") or DEFAULT_CONFIG["aiTimeout"]),
        "aiApiKeyPreview": mask_secret(str(config.get("aiApiKey") or "")),
        "hasAiApiKey": bool(str(config.get("aiApiKey") or "").strip()),
    }


def apply_ai_env(config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or load_config()
    provider = str(config.get("aiProvider") or "oauth")
    api_key = str(config.get("aiApiKey") or "").strip()
    os.environ["TWEETER_AI_BASE_URL"] = str(config.get("aiBaseUrl") or DEFAULT_CONFIG["aiBaseUrl"])
    os.environ["TWEETER_AI_MODEL"] = str(config.get("aiModel") or DEFAULT_CONFIG["aiModel"])
    os.environ["TWEETER_AI_TIMEOUT"] = str(config.get("aiTimeout") or DEFAULT_CONFIG["aiTimeout"])
    if provider == "api-key" and api_key:
        os.environ["TWEETER_AI_API_KEY"] = api_key
    else:
        os.environ.pop("TWEETER_AI_API_KEY", None)
    return config


def ai_request_options(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    config = apply_ai_env(load_config())
    payload = payload or {}
    return {
        "base_url": payload.get("aiBaseUrl") or config.get("aiBaseUrl") or DEFAULT_CONFIG["aiBaseUrl"],
        "model": payload.get("aiModel") or config.get("aiModel") or DEFAULT_CONFIG["aiModel"],
        "timeout": int(payload.get("aiTimeout") or config.get("aiTimeout") or DEFAULT_CONFIG["aiTimeout"]),
    }
