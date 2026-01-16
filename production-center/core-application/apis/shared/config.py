from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def load_yaml_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def get_parameter(
    payload: dict[str, Any],
    key: str,
    default: Any = None,
    required: bool = False,
) -> Any:
    if key in payload and payload[key] not in (None, ""):
        return payload[key]
    if required:
        raise ValueError(f"Missing required parameter: {key}")
    return default


def parse_secret_payload(payload: str) -> Any:
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return payload
