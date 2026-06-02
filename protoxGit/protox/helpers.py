# -*- coding: utf-8 -*-
"""
PROTOX AI — Funzioni utility v2.1
"""

import json
import socket
import datetime
import logging
from pathlib import Path
from typing import Any

from .config import TRACKER_FILE

log = logging.getLogger(__name__)


def is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    """Controlla se un host:port è raggiungibile. Thread-safe."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError):
        return False


def load_tracker_data() -> dict[str, list]:
    """Carica il tracker da disco. Ritorna struttura vuota in caso di errore."""
    try:
        return json.loads(TRACKER_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
        log.warning("Tracker load failed: %s", e)
        return {"SCRIPT": [], "PARTI": [], "GUI": [], "MISC": []}


def save_tracker_data(data: dict[str, Any]) -> bool:
    """Salva il tracker su disco. Ritorna True se ok."""
    try:
        TRACKER_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except (PermissionError, OSError) as e:
        log.error("Tracker save failed: %s", e)
        return False


def now_str() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")


def now_date() -> str:
    return datetime.datetime.now().strftime("%d/%m/%Y")


def uptime_str(start: datetime.datetime) -> str:
    delta = int((datetime.datetime.now() - start).total_seconds())
    if delta < 60:
        return f"{delta}s"
    elif delta < 3600:
        return f"{delta // 60}m {delta % 60}s"
    else:
        h = delta // 3600
        m = (delta % 3600) // 60
        return f"{h}h {m}m"


def safe_read_json(path: Path, default: Any = None) -> Any:
    """Legge un file JSON in modo sicuro."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def safe_write_json(path: Path, data: Any, indent: int = 2) -> bool:
    """Scrive un file JSON in modo atomico (write → rename)."""
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=indent, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
        return True
    except Exception as e:
        log.error("JSON write failed for %s: %s", path, e)
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        return False


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def truncate(text: str, max_len: int, suffix: str = "…") -> str:
    """Tronca una stringa al massimo max_len caratteri."""
    if len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)] + suffix
