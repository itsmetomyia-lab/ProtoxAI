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

    def process_input(self, text: str) -> None:
        if self._waiting:
            self.notify("Attendi la risposta...", severity="warning")
            return

        # Aggiungi alla history senza duplicati consecutivi
        if not self._input_history or self._input_history[-1] != text:
            self._input_history.append(text)
        if len(self._input_history) > MAX_INPUT_HISTORY:
            self._input_history = self._input_history[-MAX_INPUT_HISTORY:]
        self._history_index = -1

        if text.startswith("/"):
            self._handle_command(text)
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

    def _handle_command(self, text: str):
        parts = text.split()
        cmd   = parts[0].lower()

        simple_dispatch = {
            "/clear":    self.action_clear_chat,
            "/c":        self.action_clear_chat,
            "/export":   self._do_export,
            "/help":     self.action_show_help,
            "/status":   self._show_status,
            "/about":    self.action_show_about,
            "/memory":   self._show_memory_info,
            "/mem":      self._show_memory_info,
            "/memview":  lambda: self.push_screen(MemoryModal(self._memory)),
            "/memclear": self._clear_memory,
            "/forget":   self._clear_memory,
        }

        if cmd in simple_dispatch:
            simple_dispatch[cmd]()
            return

        if cmd in ("/search", "/cerca", "/web"):
            query = " ".join(parts[1:])
            if query:
                self._do_explicit_search(query)
            else:
                self.notify("Uso: /search <query>", severity="error")

        elif cmd == "/track":
            self._handle_track_command(parts[1:])

        elif cmd == "/remember":
            fact = " ".join(parts[1:])
            if fact:
                tags = self._memory._extract_tags(fact)
                self._memory.add_node(fact, "fact", tags)
                self.notify(f"Memorizzato: {fact[:50]}")
                self.add_chat_bubble("system", f"Memorizzato: {fact}")
            else:
                self.notify("Uso: /remember <fatto>", severity="error")

        elif cmd == "/nodes":
            # NUOVA FEATURE: mostra conteggio nodi per categoria
            stats = self._memory.get_stats_dict()
            self.add_chat_bubble("system",
                f"Memoria: {stats['nodes']} nodi | "
                f"{stats['messages']} messaggi | "
                f"{stats['compressions']} compressioni | "
                f"{stats['sessions']} sessioni")

        elif cmd == "/export":
            self._do_export()

        else:
            self.notify(f"Comando sconosciuto: {cmd}", severity="error")

    def _handle_track_command(self, args: list[str]):
        if len(args) < 2:
            self.notify("Uso: /track CATEGORIA NOME", severity="error")
            return
        category    = args[0].upper()
        entity_name = " ".join(args[1:])
        data        = load_tracker_data()
        if category not in data:
            data[category] = []
        if entity_name not in data[category]:
            data[category].append(entity_name)
            save_tracker_data(data)
            self.notify(f"Tracciato: {entity_name} → {category}")
        else:
            self.notify(f"Già tracciato: {entity_name}")

    # ── WEB SEARCH ESPLICITA ─────────────────────────────────────────

    def _do_explicit_search(self, query: str):
        self.add_chat_bubble("system", f'Ricerca web: "{query}"...')
        self._explicit_search_worker(query)

    @work(thread=True)
    def _explicit_search_worker(self, query: str):
        results = self._web.search(query)
        if results:
            lines = [f'**Risultati per:** "{query}"\n']
            for i, r in enumerate(results, 1):
                lines.append(f"**{i}. {r['title']}**")
                if r["url"]:
                    lines.append(f"   {r['url']}")
                if r["snippet"]:
                    lines.append(f"   {r['snippet']}")
                lines.append("")
            self.call_from_thread(self.add_chat_bubble, "ai", "\n".join(lines))
        else:
            self.call_from_thread(self.add_chat_bubble, "system", "Nessun risultato trovato.")

    # ── MEMORY CLEAR ─────────────────────────────────────────────────

    def _clear_memory(self):
        self._memory.clear()
        self.notify("Memoria cancellata completamente")
        self.add_chat_bubble("system", "Memoria persistente cancellata.")

    # ── CHAT BUBBLE ──────────────────────────────────────────────────

    def add_chat_bubble(self, role: str, content: str) -> "StreamingChatMessage":
        container = self.query_one("#chat-scroll")
        widget    = StreamingChatMessage(role=role, content=content)
        container.mount(widget)
        self.call_after_refresh(lambda: container.scroll_end(animate=False))
        return widget

    # ── LLM STREAMING (CUORE DELL'APP) ───────────────────────────────

    @work(thread=True)
    def _llm_call_stream(self, user_msg: str) -> None:
        # 1. Memoria
        memory_context = self._memory.get_context(user_msg)

        # 2. Web search (se necessaria)
        web_context = ""
        explicit_query = detect_search_intent(user_msg)
        auto_search    = should_auto_search(user_msg)

        if explicit_query and self._web.available:
            self.call_from_thread(self._set_input_status, "searching")
            self.call_from_thread(self.notify, f"Cerco: {explicit_query[:40]}...", timeout=2)
            web_context = self._web.search_and_format(explicit_query)
        elif auto_search and self._web.available:
            self.call_from_thread(self._set_input_status, "searching")
            sq = build_search_query(user_msg)
            self.call_from_thread(self.notify, f"Aggiorno info: {sq[:40]}...", timeout=2)
            web_context = self._web.search_and_format(sq)

        # 3. Data/ora sistema
        now = datetime.datetime.now()
        WEEKDAYS_IT = ["lunedì","martedì","mercoledì","giovedì","venerdì","sabato","domenica"]
        MONTHS_IT   = ["gennaio","febbraio","marzo","aprile","maggio","giugno",
                       "luglio","agosto","settembre","ottobre","novembre","dicembre"]
        date_info = (
            f"Data e ora del sistema:\n"
            f"- Oggi è {WEEKDAYS_IT[now.weekday()]} {now.day} {MONTHS_IT[now.month-1]} {now.year}\n"
            f"- Ora: {now.strftime('%H:%M')}\n"
            f"- ISO: {now.strftime('%Y-%m-%d')}\n"
            f"Usa queste info se l'utente chiede data, orario o riferimenti temporali."
        )

        # 4. System prompt
        system_parts = [
            f"Sei {BRAND_NAME}, un assistente AI di sviluppo software professionale. "
            f"Rispondi in italiano, tono tecnico e conciso. "
            f"Usa markdown con code blocks quando appropriato. "
            f"Non rivelare mai il modello sottostante o l'architettura interna. "
            f"Il tuo motore si chiama {BRAND_ENGINE}.",
            "",
            date_info,
        ]

        if memory_context:
            system_parts += ["", memory_context]

        if web_context:
            system_parts += [
                "",
                web_context,
                "",
                "Usa i risultati web sopra per dare informazioni aggiornate. "
                "Cita le fonti quando rilevante.",
            ]

        system_prompt = "\n".join(system_parts)

        # 5. Messaggi (ultime MAX_HISTORY_MESSAGES)
        msgs = [{"role": "system", "content": system_prompt}]
        msgs.extend(self._chat_history[-MAX_HISTORY_MESSAGES:])
        msgs.append({"role": "user", "content": user_msg})

        # 6. Crea bubble AI e avvia streaming
        ai_widget = self.call_from_thread(self.add_chat_bubble, "ai", "")
        self.call_from_thread(self._set_input_status, "streaming")

        full_response = ""
        try:
            stream = self._client.chat.completions.create(
                model=MODEL_NAME,
                messages=msgs,
                temperature=0.7,
                max_tokens=2048,   # BUG FIX: era 1024, troppo basso
                stream=True,
            )

            for chunk in stream:
                # BUG FIX: guard su choices vuote (edge case llama.cpp)
                if not chunk.choices:
                    continue
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
            self.call_from_thread(self._save_to_memory, user_msg, full_response)

        except Exception as e:
            err = f"{BRAND_ENGINE} Error: {e}\nLog: {SERVER_LOG}"
            self.call_from_thread(self.add_chat_bubble, "error", err)
            # BUG FIX: rimuovi la bubble vuota se c'è stato un errore
            if ai_widget and not full_response:
                try:
                    self.call_from_thread(ai_widget.remove)
                except Exception:
                    pass
            log.exception("LLM stream failed")

        finally:
            self.call_from_thread(self._reset_wait_state)

    def _save_to_memory(self, user_msg: str, ai_msg: str):
        """Aggiorna history e memoria persistente. Chiamata dal main thread."""
        self._chat_history.append({"role": "user",      "content": user_msg})
        self._chat_history.append({"role": "assistant", "content": ai_msg})
        self._msg_count += 1
        self._tok_est   += (len(user_msg) + len(ai_msg)) // 4

        # Mantieni history in memoria limitata
        if len(self._chat_history) > MAX_HISTORY_MESSAGES * 2:
            self._chat_history = self._chat_history[-MAX_HISTORY_MESSAGES * 2:]

        # Processa nella memoria persistente (thread-safe)
        self._memory.process_message("user",      user_msg)
        self._memory.process_message("assistant", ai_msg)

        try:
            self.query_one(SessionSidebar).update_stats(self._msg_count, self._tok_est)
        except Exception:
            pass

    def _reset_wait_state(self):
        self._waiting   = False
        self._streaming = False
        self._set_input_status("ready")
        try:
            self.query_one("#user-input").focus()
        except Exception:
            pass
