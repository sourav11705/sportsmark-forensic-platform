"""
watermark/registry.py
JSON file-based asset / session / detection registry (no external DB).
All data persisted in registry/ subfolder as three JSON files.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

# ─────────────────────────────────────────────
# File paths
# ─────────────────────────────────────────────

_REGISTRY_DIR = os.path.join(os.path.dirname(__file__), "..", "registry")
_ASSETS_FILE = os.path.join(_REGISTRY_DIR, "assets.json")
_SESSIONS_FILE = os.path.join(_REGISTRY_DIR, "sessions.json")
_DETECTIONS_FILE = os.path.join(_REGISTRY_DIR, "detections.json")


def _ensure_dir() -> None:
    os.makedirs(_REGISTRY_DIR, exist_ok=True)


def _load(filepath: str) -> list:
    """Load JSON list from file, returning [] if missing or empty."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []


def _save(filepath: str, data: list) -> None:
    """Persist list to JSON file (pretty-printed)."""
    _ensure_dir()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────
# Asset operations
# ─────────────────────────────────────────────

def register_asset(
    asset_id: str,
    title: str,
    fingerprint: dict,
    original_path: str,
) -> dict:
    """Append a new asset record and return it."""
    _ensure_dir()
    assets = _load(_ASSETS_FILE)
    record = {
        "asset_id": asset_id,
        "title": title,
        "fingerprint": fingerprint,
        "original_path": original_path,
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "sessions_count": 0,
    }
    assets.append(record)
    _save(_ASSETS_FILE, assets)
    return record


def get_asset(asset_id: str) -> Optional[dict]:
    """Find an asset by its ID."""
    for asset in _load(_ASSETS_FILE):
        if asset.get("asset_id") == asset_id:
            return asset
    return None


def list_assets() -> list:
    """Return all registered assets."""
    return _load(_ASSETS_FILE)


# ─────────────────────────────────────────────
# Session operations
# ─────────────────────────────────────────────

def register_session(session: dict, asset_id: str) -> dict:
    """Append a watermark session and increment asset sessions_count."""
    _ensure_dir()
    sessions = _load(_SESSIONS_FILE)
    record = dict(session)          # copy to avoid mutating caller's dict
    record["asset_id"] = asset_id
    record["registered_at"] = datetime.now(timezone.utc).isoformat()
    sessions.append(record)
    _save(_SESSIONS_FILE, sessions)

    # Increment sessions_count on the asset
    assets = _load(_ASSETS_FILE)
    for asset in assets:
        if asset.get("asset_id") == asset_id:
            asset["sessions_count"] = asset.get("sessions_count", 0) + 1
            break
    _save(_ASSETS_FILE, assets)

    return record


def lookup_session(session_id: str) -> Optional[dict]:
    """Find a session by its session_id field."""
    for sess in _load(_SESSIONS_FILE):
        if sess.get("session_id") == session_id:
            return sess
    return None


def list_sessions(asset_id: Optional[str] = None) -> list:
    """Return all sessions, optionally filtered by asset_id."""
    sessions = _load(_SESSIONS_FILE)
    if asset_id is not None:
        sessions = [s for s in sessions if s.get("asset_id") == asset_id]
    return sessions


# ─────────────────────────────────────────────
# Detection operations
# ─────────────────────────────────────────────

def log_detection(
    asset_id: str,
    source_url: str,
    platform: str,
    session_data: dict,
    fingerprint_match: dict,
) -> dict:
    """Append a piracy detection record and return it."""
    _ensure_dir()
    detections = _load(_DETECTIONS_FILE)
    record = {
        "detection_id": str(uuid.uuid4()),
        "asset_id": asset_id,
        "source_url": source_url,
        "platform": platform,
        "session_data": session_data,
        "fingerprint_match": fingerprint_match,
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "status": "FLAGGED",
        "dmca_sent": False,
    }
    detections.append(record)
    _save(_DETECTIONS_FILE, detections)
    return record


# ─────────────────────────────────────────────
# Stats
# ─────────────────────────────────────────────

def get_stats() -> dict:
    """Return aggregate statistics across all registry data."""
    assets = _load(_ASSETS_FILE)
    sessions = _load(_SESSIONS_FILE)
    detections = _load(_DETECTIONS_FILE)

    flagged = sum(1 for d in detections if d.get("status") == "FLAGGED")
    platforms = list({d.get("platform", "Unknown") for d in detections})

    return {
        "total_assets": len(assets),
        "total_sessions": len(sessions),
        "total_detections": len(detections),
        "flagged": flagged,
        "platforms_affected": platforms,
    }
