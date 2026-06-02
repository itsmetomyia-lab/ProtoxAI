# -*- coding: utf-8 -*-
"""
PROTOX AI — Funzioni utility.
"""

import json
import socket
import datetime
from .config import TRACKER_FILE


def is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def load_tracker_data() -> dict:
    try:
        return json.loads(TRACKER_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"SCRIPT": [], "PARTI": [], "GUI": [], "MISC": []}


def save_tracker_data(data: dict):
    TRACKER_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


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