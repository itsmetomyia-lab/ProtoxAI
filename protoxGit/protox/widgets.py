# -*- coding: utf-8 -*-
"""
PROTOX AI — Widget: Input, Dashboard, Sidebar, ChatMessage.
"""

import random
import datetime

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, Container, ScrollableContainer
from textual.widgets import Static, TextArea, Markdown, Rule

from .config import (
    BRAND_NAME, BRAND_VERSION, BRAND_ENGINE, BRAND_MODEL,
    BRAND_QUANT, GPU_LAYERS, CONTEXT_SIZE, THREADS, SPLASH_QUOTES,
)
from .helpers import now_str, now_date, uptime_str


class ProtoxInput(TextArea):
    """Input con Enter=invia, Shift+Enter=newline, frecce=history."""

    def on_key(self, event) -> None:
        key = event.key
        if key == "enter":
            event.prevent_default()
            event.stop()
            text = self.text.strip()
            if text:
                self.app.process_input(text)
                self.text = ""
                self.app._history_index = -1
        elif key in ("shift+enter", "ctrl+enter", "ctrl+n"):
            self.insert("\n")
            event.prevent_default()
            event.stop()
        elif key == "up":
            if self.app._input_history:
                if self.app._history_index < len(self.app._input_history) - 1:
                    self.app._history_index += 1
                event.prevent_default()
                self.text = self.app._input_history[-(self.app._history_index + 1)]
        elif key == "down":
            if self.app._history_index > 0:
                self.app._history_index -= 1
                event.prevent_default()
                self.text = self.app._input_history[-(self.app._history_index + 1)]
            elif self.app._history_index == 0:
                self.app._history_index = -1
                event.prevent_default()
                self.text = ""


class DashboardWidget(Container):
    """Dashboard di benvenuto — hero + cards + quote."""

    LOGO = r"""
  ██████╗ ██████╗  ██████╗ ████████╗ ██████╗ ██╗  ██╗
  ██╔══██╗██╔══██╗██╔═══██╗╚══██╔══╝██╔═══██╗╚██╗██╔╝
  ██████╔╝██████╔╝██║   ██║   ██║   ██║   ██║ ╚███╔╝
  ██╔═══╝ ██╔══██╗██║   ██║   ██║   ██║   ██║ ██╔██╗
  ██║     ██║  ██║╚██████╔╝   ██║   ╚██████╔╝██╔╝ ██╗
  ╚═╝     ╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝ ╚═╝  ╚═╝"""

    def compose(self) -> ComposeResult:
        quote = random.choice(SPLASH_QUOTES)
        with Vertical(id="dash-hero"):
            yield Static(self.LOGO, id="dash-logo")
            yield Static(
                f"{BRAND_ENGINE}  //  Local AI Development Environment",
                id="dash-tagline",
            )
            yield Static(
                f"v{BRAND_VERSION}  //  {now_date()}  //  {BRAND_MODEL}",
                id="dash-subtitle",
            )
        yield Static(f"  {BRAND_NAME} — {quote}  ", id="dash-accent-bar")

        with Horizontal(id="dash-cards"):
            with Vertical(classes="dash-card"):
                yield Static(" SYSTEM", classes="dash-card-title")
                yield Rule(classes="dash-card-sep")
                yield Static(f"  Engine     {BRAND_ENGINE}", classes="dash-card-item")
                yield Static(f"  Model      {BRAND_MODEL}", classes="dash-card-item-bright")
                yield Static(f"  Precision  {BRAND_QUANT}", classes="dash-card-item")
                yield Static(f"  GPU        {GPU_LAYERS} layers", classes="dash-card-item")
                yield Static(f"  Context    {CONTEXT_SIZE} tokens", classes="dash-card-item")
                yield Static(f"  Threads    {THREADS} cores", classes="dash-card-item")

            with Vertical(classes="dash-card"):
                yield Static(" COMMANDS", classes="dash-card-title")
                yield Rule(classes="dash-card-sep")
                yield Static("  /clear     Reset conversation", classes="dash-card-item")
                yield Static("  /export    Save to markdown", classes="dash-card-item")
                yield Static("  /track     Entity tracker", classes="dash-card-item")
                yield Static("  /theme     Change theme", classes="dash-card-item")
                yield Static("  /status    Server status", classes="dash-card-item")
                yield Static("  /about     About PROTOX", classes="dash-card-item-ai")

            with Vertical(classes="dash-card"):
                yield Static(" SHORTCUTS", classes="dash-card-title")
                yield Rule(classes="dash-card-sep")
                yield Static("  F1           Help", classes="dash-card-item")
                yield Static("  F2           Themes", classes="dash-card-item")
                yield Static("  F3           About", classes="dash-card-item")
                yield Static("  Ctrl+B       Sidebar", classes="dash-card-item")
                yield Static("  Ctrl+L       Clear", classes="dash-card-item")
                yield Static("  Shift+Enter  New line", classes="dash-card-item")

        with Horizontal(id="dash-status-bar"):
            yield Static(" *", classes="dash-status-dot")
            yield Static("ENGINE", classes="dash-status-item")
            yield Static(BRAND_ENGINE, classes="dash-status-val")
            yield Static("STREAM", classes="dash-status-item")
            yield Static("ON", classes="dash-status-val")
            yield Static("GPU", classes="dash-status-item")
            yield Static(f"{GPU_LAYERS}L", classes="dash-status-val")
            yield Static("CTX", classes="dash-status-item")
            yield Static(f"{CONTEXT_SIZE}", classes="dash-status-val")

        yield Static(f'"{quote}"', id="dash-quote")


class SessionSidebar(Container):
    """Sidebar con sessione, modello, server, shortcuts."""

    def __init__(self):
        super().__init__(id="sidebar")
        self._start = datetime.datetime.now()
        self._msg_count = 0
        self._tok_est = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="sidebar-header"):
            yield Static(f"  {BRAND_NAME}  ", id="sidebar-brand-line")
            yield Static(BRAND_NAME, id="sidebar-brand")
            yield Static(f"v{BRAND_VERSION}", id="sidebar-version")
            yield Static(BRAND_ENGINE, id="sidebar-engine")

        with ScrollableContainer(id="session-body"):
            with Vertical(classes="sb-section"):
                yield Static(" SESSION", classes="sb-section-head")
                with Horizontal(classes="sb-row"):
                    yield Static("Start", classes="sb-key")
                    yield Static("--:--", classes="sb-val", id="sess-start")
                with Horizontal(classes="sb-row"):
                    yield Static("Uptime", classes="sb-key")
                    yield Static("0s", classes="sb-val", id="sess-dur")
                with Horizontal(classes="sb-row"):
                    yield Static("Messages", classes="sb-key")
                    yield Static("0", classes="sb-val-bright", id="sess-msgs")
                with Horizontal(classes="sb-row"):
                    yield Static("Tokens", classes="sb-key")
                    yield Static("~0", classes="sb-val", id="sess-toks")
                with Horizontal(classes="sb-row"):
                    yield Static("Avg/msg", classes="sb-key")
                    yield Static("-", classes="sb-val", id="sess-avg")
            yield Static("", classes="sb-spacer")
            with Vertical(classes="sb-section"):
                yield Static(" ENGINE", classes="sb-section-head")
                with Horizontal(classes="sb-row"):
                    yield Static("Core", classes="sb-key")
                    yield Static(BRAND_ENGINE, classes="sb-val-ai")
                with Horizontal(classes="sb-row"):
                    yield Static("Model", classes="sb-key")
                    yield Static(BRAND_MODEL, classes="sb-val-bright")
                with Horizontal(classes="sb-row"):
                    yield Static("Precision", classes="sb-key")
                    yield Static(BRAND_QUANT, classes="sb-val")
                with Horizontal(classes="sb-row"):
                    yield Static("GPU", classes="sb-key")
                    yield Static(f"{GPU_LAYERS} layers", classes="sb-val")
                with Horizontal(classes="sb-row"):
                    yield Static("Context", classes="sb-key")
                    yield Static(f"{CONTEXT_SIZE} tok", classes="sb-val")
            yield Static("", classes="sb-spacer")
            with Vertical(classes="sb-section"):
                yield Static(" SERVER", classes="sb-section-head")
                with Horizontal(classes="sb-row"):
                    yield Static("Endpoint", classes="sb-key")
                    yield Static(f"localhost:{CONTEXT_SIZE}", classes="sb-val")
                with Horizontal(classes="sb-row"):
                    yield Static("Stream", classes="sb-key")
                    yield Static("ON", classes="sb-val-ok")
                with Horizontal(classes="sb-row"):
                    yield Static("Status", classes="sb-key")
                    yield Static("...", classes="sb-val-warn", id="sess-srv")
            yield Static("", classes="sb-spacer")
            with Vertical(classes="sb-section"):
                yield Static(" SHORTCUTS", classes="sb-section-head")
                with Horizontal(classes="sb-row"):
                    yield Static("Ctrl+B", classes="sb-key")
                    yield Static("Sidebar", classes="sb-val")
                with Horizontal(classes="sb-row"):
                    yield Static("Ctrl+L", classes="sb-key")
                    yield Static("Clear", classes="sb-val")
                with Horizontal(classes="sb-row"):
                    yield Static("F1", classes="sb-key")
                    yield Static("Help", classes="sb-val")
                with Horizontal(classes="sb-row"):
                    yield Static("F2", classes="sb-key")
                    yield Static("Themes", classes="sb-val")
                with Horizontal(classes="sb-row"):
                    yield Static("F3", classes="sb-key")
                    yield Static("About", classes="sb-val")

        yield Static("Ctrl+B to close", id="sidebar-footer")

    def on_mount(self) -> None:
        try:
            self.query_one("#sess-start").update(self._start.strftime("%H:%M"))
        except Exception:
            pass

    def update_stats(self, msg_count: int, tok_est: int):
        self._msg_count = msg_count
        self._tok_est = tok_est
        try:
            self.query_one("#sess-msgs").update(str(msg_count))
            self.query_one("#sess-toks").update(f"~{tok_est}")
            self.query_one("#sess-dur").update(uptime_str(self._start))
            avg = tok_est // msg_count if msg_count > 0 else 0
            self.query_one("#sess-avg").update(f"~{avg} tok" if avg else "-")
        except Exception:
            pass

    def set_server_status(self, online: bool):
        try:
            w = self.query_one("#sess-srv")
            if online:
                w.update("ONLINE")
                w.remove_class("sb-val-warn")
                w.add_class("sb-val-ok")
            else:
                w.update("OFFLINE")
                w.remove_class("sb-val-ok")
                w.add_class("sb-val-warn")
        except Exception:
            pass


class StreamingChatMessage(Container):
    """Messaggio chat — streaming per AI."""

    def __init__(self, role: str, content: str = ""):
        super().__init__()
        self.role = role
        self._content = content
        self._ts = now_str()
        self.add_class("chat-message")

    def compose(self) -> ComposeResult:
        if self.role == "user":
            with Horizontal(classes="msg-user-header"):
                yield Static(" > ", classes="msg-user-icon")
                yield Static("YOU", classes="msg-user-name")
                yield Static(self._ts, classes="msg-user-time")
            yield Static(self._content, classes="chat-bubble-user", id="bubble-text")
        elif self.role == "ai":
            with Horizontal(classes="msg-ai-header"):
                yield Static(" < ", classes="msg-ai-icon")
                yield Static(BRAND_NAME, classes="msg-ai-name")
                yield Static(self._ts, classes="msg-ai-time")
                yield Static(BRAND_ENGINE, classes="msg-ai-engine")
            yield Markdown(self._content or "...", classes="chat-bubble-ai", id="bubble-md")
        elif self.role == "system":
            with Horizontal(classes="msg-sys-header"):
                yield Static(" * ", classes="msg-sys-icon")
                yield Static(f"SYS  {self._ts}", classes="msg-sys-tag")
            yield Static(self._content, classes="chat-bubble-sys", id="bubble-text")
        else:
            with Horizontal(classes="msg-err-header"):
                yield Static(" ! ", classes="msg-err-icon")
                yield Static(f"ERR  {self._ts}", classes="msg-err-tag")
            yield Static(self._content, classes="chat-bubble-err", id="bubble-text")

    def update_stream(self, full_text: str):
        try:
            self.query_one("#bubble-md", Markdown).update(full_text + " |")
        except Exception:
            pass

    def finalize_stream(self, full_text: str):
        try:
            self.query_one("#bubble-md", Markdown).update(full_text)
        except Exception:
            pass