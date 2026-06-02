# -*- coding: utf-8 -*-
"""
PROTOX AI — App principale con Memory + Web Search.
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
from .memory import MemoryGraph
from .web_search import WebSearch, detect_search_intent, should_auto_search, build_search_query


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
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5,
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

        # ── NUOVI MODULI ──
        self._memory = MemoryGraph()
        self._web = WebSearch()

    # ── CLEANUP ──────────────────────────────────────────────────────
    def on_unmount(self) -> None:
        self._memory.flush()
        self._cleanup_server()

    def action_quit(self) -> None:
        self._memory.flush()
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
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5,
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

        # Notifica stato moduli
        mem_nodes = len(self._memory.nodes)
        if mem_nodes > 0:
            self.notify(f"Memory: {mem_nodes} nodi caricati", timeout=3)
        if self._web.available:
            self.notify("Web Search: attivo", timeout=2)
        else:
            self.notify("Web Search: pip install duckduckgo-search", severity="warning", timeout=5)

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
            self.call_from_thread(self.notify, f"{BRAND_ENGINE} already running", timeout=3)
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
                cmd, stdout=self._log_file_handle,
                stderr=subprocess.STDOUT, creationflags=flags,
            )
            _global_server_process = self._server_process

            for _ in range(30):
                time.sleep(1)
                if self._server_process.poll() is not None:
                    self.call_from_thread(self.notify, f"Engine crashed. Check: {SERVER_LOG}", severity="error")
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
                        f"GPU {GPU_LAYERS}L  |  CTX {CONTEXT_SIZE}  |  "
                        f"Memory {len(self._memory.nodes)} nodi  |  "
                        f"Web {'ON' if self._web.available else 'OFF'}",
                    )
                    self.call_from_thread(self._set_sidebar_server_status, True)
                    return
            self.call_from_thread(self.notify, f"{BRAND_ENGINE} slow to start...", severity="warning")
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
        self.notify("Conversation cleared (memory preserved)")

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
        mem_info = self._memory.get_info()
        self.add_chat_bubble(
            "system",
            f"{BRAND_ENGINE} {status}  |  {HOST}:{PORT}  |  "
            f"GPU:{GPU_LAYERS}L  CTX:{CONTEXT_SIZE}  |  "
            f"Session: {self._msg_count} msgs  ~{self._tok_est} tok  |  "
            f"Uptime: {up}\n"
            f"Memory: {mem_info}\n"
            f"Web Search: {'Available' if self._web.available else 'Not installed'}",
        )

    def _show_memory_info(self):
        info = self._memory.get_info()
        self.add_chat_bubble("system", f"Memory Graph: {info}")

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
            elif state == "searching":
                w.update("Searching web...")
                w.add_class("input-status-busy")
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
                "/clear":      self.action_clear_chat,
                "/c":          self.action_clear_chat,
                "/export":     self.action_export_chat,
                "/help":       self.action_show_help,
                "/status":     self._show_status,
                "/about":      self.action_show_about,
                "/memory":     self._show_memory_info,
                "/memclear":   self._clear_memory,
            }
            if cmd in dispatch:
                dispatch[cmd]()
            elif cmd in ("/search", "/cerca", "/web"):
                query = " ".join(parts[1:])
                if query:
                    self._do_explicit_search(query)
                else:
                    self.notify("Usage: /search <query>", severity="error")
            elif cmd == "/track":
                self.handle_track_command(parts[1:])
            elif cmd == "/remember":
                fact = " ".join(parts[1:])
                if fact:
                    self._memory.add_node(fact, "fact", self._memory._extract_tags(fact))
                    self.notify(f"Remembered: {fact[:50]}")
                    self.add_chat_bubble("system", f"Memorizzato: {fact}")
                else:
                    self.notify("Usage: /remember <fatto>", severity="error")
            elif cmd == "/forget":
                self._clear_memory()
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

    def _do_explicit_search(self, query: str):
        """Ricerca web esplicita — mostra risultati nella chat."""
        if not self._web.available:
            self.notify("Web Search non disponibile: pip install duckduckgo-search", severity="error")
            return
        self.add_chat_bubble("system", f"Ricerca web: \"{query}\"...")
        self._explicit_search_worker(query)

    @work(thread=True)
    def _explicit_search_worker(self, query: str):
        results = self._web.search(query)
        if results:
            lines = [f"**Risultati per:** \"{query}\"\n"]
            for i, r in enumerate(results, 1):
                lines.append(f"**{i}. {r['title']}**")
                if r['url']:
                    lines.append(f"   {r['url']}")
                if r['snippet']:
                    lines.append(f"   {r['snippet']}")
                lines.append("")
            self.call_from_thread(self.add_chat_bubble, "ai", "\n".join(lines))
        else:
            self.call_from_thread(self.add_chat_bubble, "system", "Nessun risultato trovato")

    def _clear_memory(self):
        self._memory.clear()
        self.notify("Memory cleared completely")
        self.add_chat_bubble("system", "Memoria persistente cancellata")

    def add_chat_bubble(self, role: str, content: str) -> StreamingChatMessage:
        container = self.query_one("#chat-scroll")
        widget = StreamingChatMessage(role=role, content=content)
        container.mount(widget)
        self.call_after_refresh(lambda: container.scroll_end(animate=False))
        return widget

    # ── STREAMING con MEMORY + WEB ───────────────────────────────────
    @work(thread=True)
    def _llm_call_stream(self, user_msg: str) -> None:
        # ── 1. Recupera contesto dalla memoria ──
        memory_context = self._memory.get_context(user_msg)

        # ── 2. Decidi se cercare sul web ──
        web_context = ""

        # Solo se l'utente lo chiede esplicitamente OPPURE
        # se è una domanda che l'LLM probabilmente non sa
        explicit_query = detect_search_intent(user_msg)
        auto_search = should_auto_search(user_msg)

        if explicit_query and self._web.available:
            self.call_from_thread(self._set_input_status, "searching")
            self.call_from_thread(
                self.notify, f"Cerco: {explicit_query[:40]}...", timeout=2
            )
            web_context = self._web.search_and_format(explicit_query)
        elif auto_search and self._web.available:
            self.call_from_thread(self._set_input_status, "searching")
            search_q = build_search_query(user_msg)
            self.call_from_thread(
                self.notify, f"Info aggiornate: {search_q[:40]}...", timeout=2
            )
            web_context = self._web.search_and_format(search_q)

        # ── 3. Data/ora del sistema (sempre disponibili) ──
        now = datetime.datetime.now()
        weekday_it = [
            "lunedì", "martedì", "mercoledì", "giovedì",
            "venerdì", "sabato", "domenica"
        ][now.weekday()]
        month_it = [
            "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
            "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"
        ][now.month - 1]
        date_info = (
            f"Data e ora attuali del sistema utente:\n"
            f"- Oggi è {weekday_it} {now.day} {month_it} {now.year}\n"
            f"- Sono le {now.strftime('%H:%M')}\n"
            f"- Data formato ISO: {now.strftime('%Y-%m-%d')}\n"
            f"- Timezone: locale del sistema\n"
            f"Usa queste informazioni se l'utente chiede data, giorno, ora o riferimenti temporali."
        )

        # ── 4. Costruisci system prompt ──
        system_parts = [
            f"Sei {BRAND_NAME}, un assistente AI di sviluppo software di livello professionale. "
            f"Rispondi in italiano, tono tecnico e conciso. "
            f"Usa markdown con code blocks quando serve. Sii diretto e preciso. "
            f"Non menzionare mai il modello sottostante o la tua architettura interna. "
            f"Il tuo engine si chiama {BRAND_ENGINE}.",
            "",
            date_info,
        ]

        if memory_context:
            system_parts.append("")
            system_parts.append(memory_context)

        if web_context:
            system_parts.append("")
            system_parts.append(web_context)
            system_parts.append("")
            system_parts.append(
                "Usa i risultati web sopra per dare informazioni aggiornate e accurate. "
                "Se i risultati sono utili, basa la risposta su quelli. "
                "Cita le fonti quando rilevante."
            )

        system_instruction = "\n".join(system_parts)

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

        # ── Processa nella memoria persistente ──
        self._memory.process_message("user", user_msg)
        self._memory.process_message("assistant", ai_msg)

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