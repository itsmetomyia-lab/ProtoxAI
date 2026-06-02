# -*- coding: utf-8 -*-
"""
PROTOX AI — App principale v2.3.0
TUI con Memory persistente, Web Search, streaming LLM, /slash commands.
"""

import sys
import os
import subprocess
import time
import datetime
import atexit
import signal
import logging

from .steering import SteeringEngine
from .debate import DebateEngine, should_debate
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
    MODEL_NAME,
)
from .css_builder import write_theme_css
from .helpers import is_port_open, load_tracker_data, save_tracker_data, now_str, now_date, uptime_str
from .widgets import ProtoxInput, DashboardWidget, SessionSidebar, StreamingChatMessage
from .modals import HelpModal, AboutModal, MemoryModal
from .footer import ProtoxFooter
from .memory import MemoryGraph
from .web_search import WebSearch, detect_search_intent, should_auto_search, build_search_query

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# GLOBAL SERVER CLEANUP  (atexit + signal handler)
# ─────────────────────────────────────────────────────────────────────
_global_server_process = None
_global_log_handle     = None


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

    # BUG FIX: taskkill solo su Windows e solo se necessario
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
    for _sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(_sig, lambda *_: (_kill_server_global(), sys.exit(0)))


# ─────────────────────────────────────────────────────────────────────
# COSTANTI INTERNI
# ─────────────────────────────────────────────────────────────────────
MAX_HISTORY_MESSAGES = 16   # messaggi recenti inviati all'LLM
MAX_INPUT_HISTORY    = 200  # storia input utente


# ─────────────────────────────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────────────────────────────
class ProtoxIDE(App):
    TITLE                 = BRAND_FULL
    ENABLE_COMMAND_PALETTE = False
    CSS_PATH              = [CSS_FILE]

    BINDINGS = [
        Binding("ctrl+c",     "quit",             "",     show=False),
        Binding("ctrl+b",     "toggle_sidebar",   "",     show=False),
        Binding("ctrl+l",     "clear_chat",        "",     show=False),
        Binding("ctrl+e",     "export_chat",       "",     show=False),
        Binding("ctrl+m",     "show_memory",       "",     show=False),
        Binding("f1",         "show_help",         "",     show=False),
        Binding("f3",         "show_about",        "",     show=False),
    ]

    def __init__(self, **kwargs):
        write_theme_css()
        super().__init__(**kwargs)

        self._chat_history:   list[dict]  = []
        self._input_history:  list[str]   = []
        self._history_index:  int         = -1
        self._waiting:        bool        = False
        self._streaming:      bool        = False
        self._client:         OpenAI | None = None
        self._server_process: subprocess.Popen | None = None
        self._log_file_handle             = None
        self.dashboard_active             = True
        self._msg_count                   = 0
        self._tok_est                     = 0
        self._session_start               = datetime.datetime.now()

        self._memory = MemoryGraph()
        self._web    = WebSearch()

                # Steering e Debate
        self._steering = SteeringEngine()
        self._debate: DebateEngine | None = None  # creato dopo il client

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
            _global_log_handle    = None

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
            api_key="protox-local",
            timeout=120.0,
        )
                # Inizializza debate engine
        self._debate = DebateEngine(self._client, "qwen2.5-coder-7b-instruct")
        self._reset_context()
        self.query_one("#user-input").focus()
        self._boot_backend_server()
        self.set_interval(10, self._tick_session)
        

        mem_nodes = len(self._memory.nodes)
        if mem_nodes > 0:
            self.notify(f"Memoria: {mem_nodes} nodi caricati", timeout=3)
        web_status = "attivo" if self._web.available else "installa duckduckgo-search"
        self.notify(f"Web Search: {web_status}", timeout=2)

    def _tick_session(self):
        """Aggiorna statistiche sidebar ogni 10s."""
        try:
            self.query_one(SessionSidebar).update_stats(self._msg_count, self._tok_est)
        except Exception:
            pass

    @work(thread=True, exclusive=True)
    def _boot_backend_server(self):
        global _global_server_process, _global_log_handle

        if is_port_open(HOST, PORT):
            self.call_from_thread(self.notify, f"{BRAND_ENGINE} già in esecuzione", timeout=3)
            self.call_from_thread(self._set_sidebar_server_status, True)
            return

        if not os.path.exists(MODEL_PATH):
            self.call_from_thread(
                self.notify, f"Modello non trovato: {MODEL_PATH}", severity="error"
            )
            return
        if not os.path.exists(SERVER_PATH):
            self.call_from_thread(
                self.notify, f"Server non trovato: {SERVER_PATH}", severity="error"
            )
            return

        self.call_from_thread(self.notify, f"Avvio {BRAND_ENGINE}...", timeout=5)

        cmd = [
            SERVER_PATH,
            "--model",    MODEL_PATH,
            "--host",     HOST,
            "--port",     str(PORT),
            "-ngl",       str(GPU_LAYERS),
            "-c",         str(CONTEXT_SIZE),
            "-t",         str(THREADS),
            "--parallel", "1",
            "--mmap",
        ]

        try:
            self._log_file_handle  = open(SERVER_LOG, "w", encoding="utf-8")
            _global_log_handle     = self._log_file_handle
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            self._server_process   = subprocess.Popen(
                cmd,
                stdout=self._log_file_handle,
                stderr=subprocess.STDOUT,
                creationflags=flags,
            )
            _global_server_process = self._server_process

            for _ in range(40):
                time.sleep(1)
                if self._server_process.poll() is not None:
                    self.call_from_thread(
                        self.notify, f"Engine crashed. Log: {SERVER_LOG}", severity="error"
                    )
                    return
                if is_port_open(HOST, PORT):
                    self.call_from_thread(
                        self.notify,
                        f"{BRAND_ENGINE} pronto | GPU:{GPU_LAYERS}L CTX:{CONTEXT_SIZE}",
                        severity="information", timeout=4,
                    )
                    self.call_from_thread(
                        self.add_chat_bubble, "system",
                        f"{BRAND_ENGINE} online | {BRAND_MODEL} | "
                        f"GPU {GPU_LAYERS}L | CTX {CONTEXT_SIZE} | "
                        f"Memoria {len(self._memory.nodes)} nodi | "
                        f"Web {'ON' if self._web.available else 'OFF'}",
                    )
                    self.call_from_thread(self._set_sidebar_server_status, True)
                    return

            self.call_from_thread(
                self.notify, f"{BRAND_ENGINE} lento ad avviarsi...", severity="warning"
            )

        except Exception as e:
            self.call_from_thread(self.notify, f"Errore avvio: {e}", severity="error")
            log.exception("Boot failed")

    def _set_sidebar_server_status(self, online: bool):
        try:
            self.query_one(SessionSidebar).set_server_status(online)
        except Exception:
            pass

    def _reset_context(self):
        self._chat_history = []
        self._waiting      = False
        self._streaming    = False

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

    def action_show_memory(self) -> None:
        self.push_screen(MemoryModal(self._memory))

    def action_clear_chat(self) -> None:
        self._reset_context()
        self._msg_count = 0
        self._tok_est   = 0
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
        self.notify("Conversazione resettata (memoria preserved)")

    def action_export_chat(self) -> None:
        self._do_export()

    def _do_export(self):
        if not self._chat_history:
            self.notify("Nulla da esportare", severity="warning")
            return
        ts       = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = EXPORT_DIR / f"protox_chat_{ts}.md"
        try:
            lines = [
                f"# {BRAND_FULL} // Chat Export",
                f"**Data:** {now_date()} **Ora:** {now_str()}",
                f"**Messaggi:** {self._msg_count} | **Token stimati:** ~{self._tok_est}",
                "",
                "---",
                "",
            ]
            for msg in self._chat_history:
                role = "**Tu**" if msg["role"] == "user" else f"**{BRAND_NAME}**"
                lines.append(f"### {role}")
                lines.append(msg["content"])
                lines.append("")
                lines.append("---")
                lines.append("")
            filename.write_text("\n".join(lines), encoding="utf-8")
            self.notify(f"Esportato: {filename.name}")
            self.add_chat_bubble("system", f"Chat esportata in: {filename}")
        except Exception as e:
            self.notify(f"Errore export: {e}", severity="error")

    # ── STATUS & MEMORY INFO ─────────────────────────────────────────

    def _show_status(self):
        online = is_port_open(HOST, PORT)
        status = "ONLINE" if online else "OFFLINE"
        up     = uptime_str(self._session_start)
        self.add_chat_bubble(
            "system",
            f"**{BRAND_ENGINE}** {status} | {HOST}:{PORT} | "
            f"GPU:{GPU_LAYERS}L CTX:{CONTEXT_SIZE} | "
            f"Sessione: {self._msg_count} msg ~{self._tok_est} tok | "
            f"Uptime: {up}\n"
            f"**Memoria:** {self._memory.get_info()}\n"
            f"**Web Search:** {'Disponibile' if self._web.available else 'Non installata'}",
        )

    def _show_memory_info(self):
        self.add_chat_bubble("system", f"**Memory Graph:**\n{self._memory.get_info()}")

    # ── INPUT STATUS ─────────────────────────────────────────────────

    def _set_input_status(self, state: str):
        labels = {
            "ready":     ("Ready",          "input-status-ready"),
            "thinking":  ("Thinking...",    "input-status-busy"),
            "streaming": ("Streaming...",   "input-status-stream"),
            "searching": ("Web search...",  "input-status-busy"),
            "error":     ("Error",          "input-status-error"),
        }
        try:
            w = self.query_one("#input-ready-label")
            for cls in ("input-status-ready", "input-status-busy",
                        "input-status-stream", "input-status-error"):
                w.remove_class(cls)
            text, cls = labels.get(state, ("Ready", "input-status-ready"))
            w.update(text)
            w.add_class(cls)
        except Exception:
            pass

    # ── INPUT PROCESSING ─────────────────────────────────────────────

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
            elif cmd == "/steer":
                result = self._steering.parse_command(parts[1:])
                self.add_chat_bubble("system", result)
            elif cmd == "/debate":
                if len(parts) < 2:
                    # Solo /debate -> mostra stato e aiuto
                    self.add_chat_bubble(
                        "system",
                        f"{self._debate.get_status()}\n\n"
                        f"Comandi:\n"
                        f"  /debate off    -> mai attivo\n"
                        f"  /debate auto   -> solo su domande di decisione\n"
                        f"  /debate on     -> SEMPRE attivo (force)\n"
                        f"  /debate toggle -> cicla tra le modalita'\n"
                    )
                elif parts[1].lower() == "toggle":
                    new_state = self._debate.toggle()
                    self.add_chat_bubble("system", new_state)
                else:
                    # /debate on | off | auto | force | always
                    result = self._debate.set_mode(parts[1])
                    self.add_chat_bubble("system", result)
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
            self.notify("Web Search non disponibile", severity="error")
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

    # ── STREAMING con MEMORY + WEB + STEERING + DEBATE ───────────────
    @work(thread=True)
    def _llm_call_stream(self, user_msg: str) -> None:
        # ── 1. Memoria persistente ──
        memory_context = self._memory.get_context(user_msg)

        # ── 2. Web search ──
        web_context = ""
        explicit_query = detect_search_intent(user_msg)
        auto_search = should_auto_search(user_msg)

        if explicit_query and self._web.available:
            search_q = explicit_query
        elif auto_search and self._web.available:
            search_q = build_search_query(user_msg)
        else:
            search_q = None

        if search_q:
            self.call_from_thread(self._set_input_status, "searching")
            self.call_from_thread(
                self.add_chat_bubble, "system",
                f"Web Agent attivato — query: \"{search_q}\""
            )

            def progress_callback(stage: str, info: str):
                self.call_from_thread(self.notify, info, timeout=2)

            search_result = self._web.deep_search(search_q, on_progress=progress_callback)
            web_context = search_result["context"]
            n_pages = len(search_result["pages"])
            n_links = len(search_result["links"])
            self.call_from_thread(
                self.add_chat_bubble, "system",
                f"Web Agent: scaricate {n_pages} pagine, {n_links} link totali."
            )

        # ── 3. Data/ora del sistema ──
        now = datetime.datetime.now()
        weekday_it = ["lunedì", "martedì", "mercoledì", "giovedì",
                      "venerdì", "sabato", "domenica"][now.weekday()]
        month_it = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
                    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"][now.month - 1]
        date_info = (
            f"Data e ora attuali del sistema utente:\n"
            f"- Oggi è {weekday_it} {now.day} {month_it} {now.year}\n"
            f"- Sono le {now.strftime('%H:%M')}\n"
            f"- Data ISO: {now.strftime('%Y-%m-%d')}"
        )

        # ── 4. Steering ──
        steering_instructions = self._steering.build_instructions()

        # ── 5. Debate Mode ──
        debate_context = ""
        if self._debate and self._debate.should_run(user_msg):
            self.call_from_thread(self._set_input_status, "thinking")
            self.call_from_thread(
                self.add_chat_bubble, "system",
                "Debate Mode attivato — 3 prospettive in analisi parallela..."
            )

            def debate_progress(stage: str, info: str):
                self.call_from_thread(self.notify, info, timeout=2)

            agent_extra_context = ""
            if memory_context:
                agent_extra_context += memory_context + "\n\n"
            if web_context:
                agent_extra_context += web_context

            debate_result = self._debate.run_debate(
                user_msg,
                extra_context=agent_extra_context,
                on_progress=debate_progress,
            )
            debate_context = debate_result["judge_context"]

            self.call_from_thread(
                self.add_chat_bubble, "system",
                "Sintesi multi-agent completata. Genero risposta finale..."
            )

        # ── 6. Costruisci system prompt completo ──
        system_parts = [
            f"Sei {BRAND_NAME}, un assistente AI di sviluppo software di livello professionale. "
            f"Rispondi in italiano, tono tecnico e conciso. "
            f"Usa markdown con code blocks quando serve. Sii diretto e preciso. "
            f"Non menzionare mai il modello sottostante o la tua architettura interna. "
            f"Il tuo engine si chiama {BRAND_ENGINE}.",
            "",
            date_info,
        ]

        if steering_instructions:
            system_parts.append("")
            system_parts.append(steering_instructions)

        if memory_context:
            system_parts.append("")
            system_parts.append(memory_context)

        if web_context:
            system_parts.append("")
            system_parts.append(web_context)

        if debate_context:
            system_parts.append("")
            system_parts.append(debate_context)

        system_instruction = "\n".join(system_parts)

        msgs = [{"role": "system", "content": system_instruction}]
        msgs.extend(self._chat_history[-10:])
        msgs.append({"role": "user", "content": user_msg})

        ai_widget = self.call_from_thread(self.add_chat_bubble, "ai", "")
        self.call_from_thread(self._set_input_status, "streaming")

        # max_tokens piu' alto se debate o web (risposte piu' ricche)
        max_tok = 2048 if (debate_context or web_context) else 1024

        full_response = ""
        try:
            stream = self._client.chat.completions.create(
                model="qwen2.5-coder-7b-instruct",
                messages=msgs,
                temperature=0.5 if web_context else 0.7,
                max_tokens=max_tok,
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

        # Processa nella memoria persistente
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
