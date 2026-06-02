# -*- coding: utf-8 -*-
"""
PROTOX AI — Configurazione centrale.
"""

import os
import json
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────
# ROOT del progetto
# ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent

# ─────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────
DATA_DIR     = PROJECT_ROOT / "protox_data"
TRACKER_FILE = DATA_DIR / "entity_tracker.json"
EXPORT_DIR   = DATA_DIR / "exports"
SERVER_LOG   = DATA_DIR / "server_log.txt"
CSS_FILE     = DATA_DIR / "active_theme.tcss"

# ─────────────────────────────────────────────────────────────────────
# SERVER & MODEL
# ─────────────────────────────────────────────────────────────────────
MODEL_PATH   = r"C:\AIVulkan\qwen2.5-coder-7b-instruct-q4_k_m.gguf"
SERVER_PATH  = r"C:\AIVulkan\llama-server.exe"

PORT         = 1234
HOST         = "127.0.0.1"
GPU_LAYERS   = 35
CONTEXT_SIZE = 2048
THREADS      = max(4, (os.cpu_count() or 8) // 2)

# ─────────────────────────────────────────────────────────────────────
# BRANDING
# ─────────────────────────────────────────────────────────────────────
BRAND_NAME    = "PROTOX"
BRAND_VERSION = "2.2.0"
BRAND_ENGINE  = "NeuralCore"
BRAND_MODEL   = "ProtoX-7B"
BRAND_QUANT   = "Q4 Optimized"
BRAND_FULL    = f"{BRAND_NAME} AI  //  v{BRAND_VERSION}"

# ─────────────────────────────────────────────────────────────────────
# SPLASH QUOTES
# ─────────────────────────────────────────────────────────────────────
SPLASH_QUOTES = [
    "Build fast. Break nothing.",
    "Code is poetry with side effects.",
    "Local AI. Zero compromise.",
    "Your machine. Your rules.",
    "Intelligence at the speed of thought.",
    "No cloud. No limits. No excuses.",
    "Precision-engineered for developers.",
    "Think local. Build global.",
    "Every keystroke matters.",
    "Where silicon meets intention.",
]

# ─────────────────────────────────────────────────────────────────────
# TEMA UNICO — colori PROTOX
# ─────────────────────────────────────────────────────────────────────
THEME = {
    "bg":   "#0e0c0a", "bg2":  "#181512", "bg3":  "#252017",
    "bg4":  "#1e1a14", "bg5":  "#12100d",
    "acc":  "#ef7c53", "acc2": "#d4693f", "acc3": "#ff9b75",
    "ai":   "#00e5b8", "ai2":  "#00c49e",
    "txt":  "#e8e3dd", "txt2": "#c8c0b8", "txt3": "#a8a098",
    "mut":  "#7a7268", "mut2": "#5a524a",
    "cbg":  "#080604", "brd":  "#2a2520",
    "brd2": "#ef7c53", "ok":   "#4ecb71", "err":  "#ff4444",
    "warn": "#e8c41a", "glow": "#ef7c53",
}

# ─────────────────────────────────────────────────────────────────────
# INIT
# ─────────────────────────────────────────────────────────────────────
DATA_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)

if not TRACKER_FILE.exists():
    with open(TRACKER_FILE, "w") as f:
        json.dump({"SCRIPT": [], "PARTI": [], "GUI": [], "MISC": []}, f)