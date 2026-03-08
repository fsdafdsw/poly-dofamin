import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Set


@dataclass(frozen=True)
class AlertState:
    alerted_keys: Set[str]
    last_checked_at: str


def load_state(path: str) -> AlertState:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        return AlertState(alerted_keys=set(), last_checked_at="")
    except (ValueError, TypeError):
        return AlertState(alerted_keys=set(), last_checked_at="")

    alerted_keys = payload.get("alerted_keys")
    if not isinstance(alerted_keys, list):
        alerted_keys = []

    return AlertState(
        alerted_keys={str(item) for item in alerted_keys if item},
        last_checked_at=str(payload.get("last_checked_at") or ""),
    )


def save_state(path: str, alerted_keys: Set[str]) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    payload = {
        "alerted_keys": sorted(alerted_keys),
        "last_checked_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
