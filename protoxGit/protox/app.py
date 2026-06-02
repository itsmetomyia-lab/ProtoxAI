# -*- coding: utf-8 -*-
"""
PROTOX AI — App principale.
"""

import sys
import os
import subprocess
import time
import datetime
import atexit
import signal

from openai import OpenAI
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.widgets import Header, Static
from textual import work

from .config import (
    HOST, PORT, GPU_LAYERS, CONTEXT_SIZE, THREADS,
    MODEL_PATH, SERVER_PATH, SERVER_LOG, EXPORT_DIR, CSS_FILE,
    BRAND_NAME, BRAND_ENGINE, BRAND_MODEL, BRAND_FULL, BRAND_VERSION,
)
from .css_builder import write_theme_css
from .helpers import (
    is_port_open, load_tracker_data, save_tracker_data,
    now_str, now_date, uptime_str,
)
from .widgets import (
    ProtoxInput, DashboardWidget, SessionSidebar, StreamingChatMessage,
)
from .modals import HelpModal, AboutModal
from .footer import ProtoxFooter


# ─────────────────────────────────────────────────────────────────────
# GLOBAL SERVER CLEANUP
# ─────────────────────────────────────────────────────────────────────
_global_server_process = None
_global_log_handle = None


def _kill_server_global():
    global _global_server_process, _global_log_handle
    if _global_server_process is not None:
        try:
            _global_server_process.terminate()
            _global_server_process.wait(timeout=5)
        except Exception:
            try:
                _global_server_process.kill()
            except Exception:
                pass
        _global_server_process = None
    if _global_log_handle is not None:
        try:
            _global_log_handle.close()
        except Exception:
            pass
        _global_log_handle = None
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", "llama-server.exe"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
        except Exception:
            pass


atexit.register(_kill_server_global)

if sys.platform != "win32":
    signal.signal(signal.SIGTERM, lambda *_: (_kill_server_global(), sys.exit(0)))
    signal.signal(signal.SIGHUP, lambda *_: (_kill_server_global(), sys.exit(0)))


# ─────────────────────────────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────────────────────────────
class ProtoxIDE(App):
    TITLE = BRAND_FULL
    ENABLE_COMMAND_PALETTE = False
    CSS_PATH = [CSS_FILE]

    BINDINGS = [
        Binding("ctrl+c", "quit",           "", show=False),
        Binding("ctrl+b", "toggle_sidebar", "", show=False),
        Binding("ctrl+l", "clear_chat",     "", show=False),
        Binding("f1",     "show_help",      "", show=False),
        Binding("f3",     "show_about",     "", show=False),
    ]

    def __init__(self, **kwargs):
        write_theme_css()
        super().__init__(**kwargs)

        self._chat_history:   list[dict] = []
        self._input_history:  list[str]  = []
        self._history_index:  int        = -1
        self._waiting:        bool       = False
        self._streaming:      bool       = False
        self._client:         OpenAI | None = None
        self._server_process: subprocess.Popen | None = None
        self._log_file_handle = None
        self.dashboard_active = True
        self._msg_count = 0
        self._tok_est   = 0
        self._session_start = datetime.datetime.now()

    # ── CLEANUP ──────────────────────────────────────────────────────
    def on_unmount(self) -> None:
        self._cleanup_server()

    def action_quit(self) -> None:
        self._cleanup_server()
        super().action_quit()

    def _cleanup_server(self):
        global _global_server_process, _global_log_handle
        if self._server_process is not None:
            try:
                self._server_process.terminate()
                self._server_process.wait(timeout=5)
            except Exception:
                try:
                    self._server_process.kill()
                except Exception:
                    pass
            self._server_process = None
            _global_server_process = None
        if self._log_file_handle is not None:
            try:
                self._log_file_handle.close()
            except Exception:
                pass
            self._log_file_handle = None
            _global_log_handle = None
        if sys.platform == "win32":
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", "llama-server.exe"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
            except Exception:
                pass

    # ── BOOT ─────────────────────────────────────────────────────────
    def on_mount(self) -> None:
        self._client = OpenAI(
            base_url=f"http://{HOST}:{PORT}/v1",
            api_key="protox",
            timeout=120.0,
        )
        self._reset_system_context()
        self.query_one("#user-input").focus()
        self._boot_backend_server()
        self.set_interval(10, self._tick_session)

    def _tick_session(self):
        try:
            self.query_one(SessionSidebar).update_stats(
                self._msg_count, self._tok_est
            )
        except Exception:
            pass

    @work(thread=True, exclusive=True)
    def _boot_backend_server(self):
        global _global_server_process, _global_log_handle

        if is_port_open(HOST, PORT):
            self.call_from_thread(
                self.notify, f"{BRAND_ENGINE} already running", timeout=3
            )
            self.call_from_thread(self._set_sidebar_server_status, True)
            return

        if not os.path.exists(MODEL_PATH):
            self.call_from_thread(self.notify, "Model not found", severity="error")
            return
        if not os.path.exists(SERVER_PATH):
            self.call_from_thread(self.notify, "Engine binary not found", severity="error")
            return

        self.call_from_thread(self.notify, f"Starting {BRAND_ENGINE}...", timeout=5)

        cmd = [
            SERVER_PATH,
            "--model", MODEL_PATH,
            "--host", HOST,
            "--port", str(PORT),
            "-ngl", str(GPU_LAYERS),
            "-c", str(CONTEXT_SIZE),
            "-t", str(THREADS),
            "--parallel", "1",
            "--mmap",
            "--no-kv-offload",
        ]

        try:
            self._log_file_handle = open(SERVER_LOG, "w")
            _global_log_handle = self._log_file_handle
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            self._server_process = subprocess.Popen(
                cmd,
                stdout=self._log_file_handle,
                stderr=subprocess.STDOUT,
                creationflags=flags,
            )
            _global_server_process = self._server_process

            for _ in range(30):
                time.sleep(1)
                if self._server_process.poll() is not None:
                    self.call_from_thread(
                        self.notify,
                        f"Engine crashed. Check: {SERVER_LOG}",
                        severity="error",
                    )
                    return
                if is_port_open(HOST, PORT):
                    self.call_from_thread(
                        self.notify,
                        f"{BRAND_ENGINE} ready  |  GPU:{GPU_LAYERS}L  CTX:{CONTEXT_SIZE}",
                        severity="information", timeout=4,
                    )
                    self.call_from_thread(
                        self.add_chat_bubble, "system",
                        f"{BRAND_ENGINE} online  |  {BRAND_MODEL}  |  "
                        f"GPU {GPU_LAYERS}L  |  CTX {CONTEXT_SIZE}  |  Streaming ON",
                    )
                    self.call_from_thread(self._set_sidebar_server_status, True)
                    return
            self.call_from_thread(
                self.notify,
                f"{BRAND_ENGINE} slow to start...",
                severity="warning",
            )
        except Exception as e:
            self.call_from_thread(self.notify, f"Boot error: {e}", severity="error")

    def _set_sidebar_server_status(self, online: bool):
        try:
            self.query_one(SessionSidebar).set_server_status(online)
        except Exception:
            pass

    def _reset_system_context(self):
        self._chat_history = []
        self._waiting = False
        self._streaming = False

    # ── LAYOUT ───────────────────────────────────────────────────────
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-layout"):
            yield SessionSidebar()
            with Vertical(id="content-area"):
                with ScrollableContainer(id="chat-scroll"):
                    yield DashboardWidget(id="dashboard")
                with Vertical(id="input-wrapper"):
                    with Horizontal(id="input-status-line"):
                        yield Static(f"{BRAND_ENGINE}: ", classes="input-status-text")
                        yield Static("Ready", classes="input-status-ready", id="input-ready-label")
                    with Horizontal(id="input-container"):
                        yield Static(" > ", id="prompt-sym")
                        yield ProtoxInput(id="user-input")
        yield ProtoxFooter()

    # ── TRACKER ──────────────────────────────────────────────────────
    def handle_track_command(self, args: list[str]):
        if len(args) < 2:
            self.notify("Usage: /track CATEGORY NAME", severity="error")
            return
        category = args[0].upper()
        entity_name = " ".join(args[1:])
        data = load_tracker_data()
        if category not in data:
            data[category] = []
        if entity_name not in data[category]:
            data[category].append(entity_name)
            save_tracker_data(data)
            self.notify(f"Tracked: {entity_name} -> {category}")

    # ── ACTIONS ──────────────────────────────────────────────────────
    def action_toggle_sidebar(self) -> None:
        try:
            self.query_one(SessionSidebar).toggle_class("hidden")
        except Exception:
            pass

    def action_show_help(self) -> None:
        self.push_screen(HelpModal())

    def action_show_about(self) -> None:
        self.push_screen(AboutModal())

    def action_clear_chat(self) -> None:
        self._reset_system_context()
        self._msg_count = 0
        self._tok_est = 0
        container = self.query_one("#chat-scroll")
        for child in container.query(StreamingChatMessage):
            child.remove()
        self.dashboard_active = True
        try:
            self.query_one("#dashboard").remove_class("hidden")
        except Exception:
            pass
        try:
            self.query_one(SessionSidebar).update_stats(0, 0)
        except Exception:
            pass
        self._set_input_status("ready")
        self.notify("Conversation cleared")

    def action_export_chat(self) -> None:
        if not self._chat_history:
            self.notify("Nothing to export", severity="warning")
            return
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = EXPORT_DIR / f"protox_chat_{ts}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# {BRAND_FULL}  //  Chat Export\n")
            f.write(f"**Date:** {now_date()}  **Time:** {now_str()}\n\n---\n\n")
            for msg in self._chat_history:
                role = "You" if msg["role"] == "user" else BRAND_NAME
                f.write(f"### {role}\n{msg['content']}\n\n---\n\n")
        self.notify(f"Exported: {filename.name}")

    def _show_status(self):
        online = is_port_open(HOST, PORT)
        status = "ONLINE" if online else "OFFLINE"
        up = uptime_str(self._session_start)
        self.add_chat_bubble(
            "system",
            f"{BRAND_ENGINE} {status}  |  {HOST}:{PORT}  |  "
            f"GPU:{GPU_LAYERS}L  CTX:{CONTEXT_SIZE}  |  "
            f"Session: {self._msg_count} msgs  ~{self._tok_est} tok  |  "
            f"Uptime: {up}",
        )

    # ── INPUT STATUS ─────────────────────────────────────────────────
    def _set_input_status(self, state: str):
        try:
            w = self.query_one("#input-ready-label")
            w.remove_class("input-status-ready")
            w.remove_class("input-status-busy")
            w.remove_class("input-status-stream")
            if state == "ready":
                w.update("Ready")
                w.add_class("input-status-ready")
            elif state == "thinking":
                w.update("Thinking...")
                w.add_class("input-status-busy")
            elif state == "streaming":
                w.update("Streaming...")
                w.add_class("input-status-stream")
        except Exception:
            pass

    # ── INPUT ────────────────────────────────────────────────────────
    def process_input(self, text: str) -> None:
        if self._waiting:
            self.notify("Wait for response...", severity="warning")
            return
        if not self._input_history or self._input_history[-1] != text:
            self._input_history.append(text)

        if text.startswith("/"):
            parts = text.split()
            cmd = parts[0].lower()
            dispatch = {
                "/clear": self.action_clear_chat,
                "/c": self.action_clear_chat,
                "/export": self.action_export_chat,
                "/help": self.action_show_help,
                "/status": self._show_status,
                "/about": self.action_show_about,
            }
            if cmd in dispatch:
                dispatch[cmd]()
            elif cmd == "/track":
                self.handle_track_command(parts[1:])
            else:
                self.notify(f"Unknown command: {cmd}", severity="error")
            return

        if self.dashboard_active:
            self.dashboard_active = False
            try:
                self.query_one("#dashboard").add_class("hidden")
            except Exception:
                pass

        self.add_chat_bubble("user", text)
        self._waiting = True
        self._set_input_status("thinking")
        self._llm_call_stream(text)

    def add_chat_bubble(self, role: str, content: str) -> StreamingChatMessage:
        container = self.query_one("#chat-scroll")
        widget = StreamingChatMessage(role=role, content=content)
        container.mount(widget)
        self.call_after_refresh(lambda: container.scroll_end(animate=False))
        return widget

    # ── STREAMING ────────────────────────────────────────────────────
    @work(thread=True)
    def _llm_call_stream(self, user_msg: str) -> None:
        system_instruction = (
            f"Sei {BRAND_NAME}, un assistente AI di sviluppo software di livello professionale. "
            f"Rispondi in italiano, tono tecnico e conciso. "
            f"Usa markdown con code blocks quando serve. Sii diretto e preciso. "
            f"Non menzionare mai il modello sottostante o la tua architettura interna. "
            f"Il tuo engine si chiama {BRAND_ENGINE}."
        )
        msgs = [{"role": "system", "content": system_instruction}]
        msgs.extend(self._chat_history[-10:])
        msgs.append({"role": "user", "content": user_msg})

        ai_widget = self.call_from_thread(self.add_chat_bubble, "ai", "")
        self.call_from_thread(self._set_input_status, "streaming")

        full_response = ""
        try:
            stream = self._client.chat.completions.create(
                model="qwen2.5-coder-7b-instruct",
                messages=msgs,
                temperature=0.7,
                max_tokens=1024,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    full_response += delta.content
                    if ai_widget:
                        self.call_from_thread(ai_widget.update_stream, full_response)
                    self.call_from_thread(
                        lambda: self.query_one("#chat-scroll").scroll_end(animate=False)
                    )

            if ai_widget:
                self.call_from_thread(ai_widget.finalize_stream, full_response)
            self.call_from_thread(self._save_memory_state, user_msg, full_response)

        except Exception as e:
            err = f"{BRAND_ENGINE} Error: {e}\nCheck: {SERVER_LOG}"
            self.call_from_thread(self.add_chat_bubble, "error", err)
            if ai_widget:
                try:
                    self.call_from_thread(ai_widget.remove)
                except Exception:
                    pass
        finally:
            self.call_from_thread(self._reset_wait_state)

    def _save_memory_state(self, user_msg: str, ai_msg: str):
        self._chat_history.append({"role": "user", "content": user_msg})
        self._chat_history.append({"role": "assistant", "content": ai_msg})
        self._msg_count += 1
        self._tok_est += (len(user_msg) + len(ai_msg)) // 4
        try:
            self.query_one(SessionSidebar).update_stats(self._msg_count, self._tok_est)
        except Exception:
            pass

    def _reset_wait_state(self):
        self._waiting = False
        self._streaming = False
        self._set_input_status("ready")
        try:
            self.query_one("#user-input").focus()
        except Exception:
            pass