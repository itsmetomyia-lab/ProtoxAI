# -*- coding: utf-8 -*-
"""
PROTOX AI — Footer widget.
"""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

from .config import (
    BRAND_NAME, BRAND_ENGINE, BRAND_MODEL, BRAND_QUANT,
    GPU_LAYERS, CONTEXT_SIZE,
)


class ProtoxFooter(Static):
    """Footer a 3 righe: accent bar + shortcuts + comandi slash."""

    DEFAULT_CSS = ""

    def __init__(self):
        super().__init__(id="custom-footer")

    def compose(self) -> ComposeResult:
        yield Static(
            f" {BRAND_NAME} AI | {BRAND_ENGINE} | "
            f"GPU:{GPU_LAYERS}L CTX:{CONTEXT_SIZE} STREAM:ON MEM:ON",
            id="footer-accent-line",
        )
        with Horizontal(id="footer-line-top"):
            yield Static("F1",     classes="fkey")
            yield Static("Help",   classes="flabel")
            yield Static("F3",     classes="fkey")
            yield Static("About",  classes="flabel")
            yield Static("^B",     classes="fkey-dim")
            yield Static("Sidebar",classes="flabel")
            yield Static("^L",     classes="fkey-dim")
            yield Static("Clear",  classes="flabel")
            yield Static("^E",     classes="fkey-dim")
            yield Static("Export", classes="flabel")
            yield Static("^M",     classes="fkey-dim")
            yield Static("Memory", classes="flabel")
            yield Static("^C",     classes="fkey-dim")
            yield Static("Quit",   classes="flabel")
        with Horizontal(id="footer-line-bot"):
            yield Static("/clear",    classes="fkey-dim")
            yield Static("/export",   classes="fkey-dim")
            yield Static("/search",   classes="fkey-dim")
            yield Static("/remember", classes="fkey-dim")
            yield Static("/memory",   classes="fkey-dim")
            yield Static("/memview",  classes="fkey-dim")
            yield Static("/track",    classes="fkey-dim")
            yield Static("/status",   classes="fkey-dim")
            yield Static(
                f" {BRAND_MODEL} | {BRAND_QUANT}",
                classes="fright-dim",
            )
