# -*- coding: utf-8 -*-
"""
PROTOX AI — Modali: Help, About, MemoryModal (NUOVO).
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Rule, DataTable

from .config import (
    BRAND_NAME, BRAND_VERSION, BRAND_ENGINE, BRAND_MODEL,
    BRAND_QUANT, BRAND_FULL, GPU_LAYERS, CONTEXT_SIZE, THREADS,
)


class HelpModal(ModalScreen):
    """Help panel — sezioni, tips, scrollabile."""

    BINDINGS = [Binding("escape", "dismiss_me", "", show=False)]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-overlay"):
            yield Static(f" {BRAND_FULL} // HELP CENTER", id="help-modal-header")
            yield Static(
                f" {BRAND_ENGINE} | {BRAND_MODEL} | Complete Reference",
                id="help-brand-bar",
            )
            with ScrollableContainer(id="help-body"):
                yield Static(" KEYBOARD SHORTCUTS", classes="help-section-title")
                yield Static(" Naviga e controlla l'interfaccia", classes="help-section-sub")
                yield Rule(classes="help-divider")
                for key, desc in [
                    ("F1",          "Apri questo pannello"),
                    ("F3",          "About PROTOX"),
                    ("Ctrl+B",      "Mostra/nascondi sidebar"),
                    ("Ctrl+L",      "Pulisci conversazione"),
                    ("Ctrl+E",      "Esporta chat in Markdown"),
                    ("Ctrl+M",      "Visualizza grafo memoria"),
                    ("Ctrl+C",      "Chiudi applicazione"),
                ]:
                    with Horizontal(classes="help-row"):
                        yield Static(key,  classes="help-key")
                        yield Static(desc, classes="help-desc")

                yield Rule(classes="help-divider")
                yield Static(" INPUT CONTROLS", classes="help-section-title")
                yield Static(" Scrittura e navigazione input", classes="help-section-sub")
                yield Rule(classes="help-divider")
                for key, desc in [
                    ("Enter",       "Invia messaggio"),
                    ("Shift+Enter", "Nuova riga (multiline)"),
                    ("↑ / ↓",       "Naviga history input"),
                ]:
                    with Horizontal(classes="help-row"):
                        yield Static(key,  classes="help-key")
                        yield Static(desc, classes="help-desc")

                yield Rule(classes="help-divider")
                yield Static(" SLASH COMMANDS", classes="help-section-title")
                yield Static(" Scrivi nel campo input e premi Enter", classes="help-section-sub")
                yield Rule(classes="help-divider")
                for key, desc in [
                    ("/clear",             "Resetta conversazione"),
                    ("/export",            "Esporta chat in markdown"),
                    ("/status",            "Info server e sessione"),
                    ("/memory | /mem",     "Info memoria persistente"),
                    ("/memview",           "Visualizza grafo memoria"),
                    ("/memclear",          "Cancella tutta la memoria"),
                    ("/remember <fatto>",  "Memorizza un fatto esplicitamente"),
                    ("/forget",            "Alias di /memclear"),
                    ("/nodes",             "Stats memoria per categoria"),
                    ("/search <query>",    "Ricerca web esplicita"),
                    ("/track CAT NOME",    "Aggiungi al tracker"),
                    ("/about",             "Pannello About"),
                    ("/help",              "Questo pannello"),
                ]:
                    with Horizontal(classes="help-row"):
                        yield Static(key,  classes="help-key")
                        yield Static(desc, classes="help-desc")

                yield Rule(classes="help-divider")
                yield Static(" TIPS", classes="help-section-title")
                yield Static(" Consigli per power user", classes="help-section-sub")
                yield Rule(classes="help-divider")
                for tip in [
                    "Usa Shift+Enter per codice multiriga",
                    "La memoria persiste tra sessioni — usa /memview per vederla",
                    "Gli export sono salvati in protox_data/exports/",
                    "/clear resetta il contesto AI ma NON la memoria persistente",
                    "Usa /remember per forzare la memorizzazione di un fatto",
                    "La web search si attiva automaticamente per domande su notizie/prezzi",
                    "Ctrl+M apre il pannello grafico della memoria",
                ]:
                    with Horizontal(classes="help-row"):
                        yield Static(" *", classes="help-tip-icon")
                        yield Static(tip,   classes="help-tip-text")

            yield Static(
                f" ESC per chiudere | {BRAND_NAME} v{BRAND_VERSION}",
                id="help-modal-footer",
            )

    def action_dismiss_me(self):
        self.app.pop_screen()


class AboutModal(ModalScreen):
    """About screen con branding PROTOX."""

    BINDINGS = [Binding("escape", "dismiss_me", "", show=False)]

    MINI_LOGO = r"""
 ██████╗ ██████╗  ██████╗ ████████╗ ██████╗ ██╗  ██╗
 ██╔══██╗██╔══██╗██╔═══██╗╚══██╔══╝██╔═══██╗╚██╗██╔╝
 ██████╔╝██████╔╝██║   ██║   ██║   ██║   ██║ ╚███╔╝
 ██╔═══╝ ██╔══██╗██║   ██║   ██║   ██║   ██║ ██╔██╗
 ██║     ██║  ██║╚██████╔╝   ██║   ╚██████╔╝██╔╝ ██╗
 ╚═╝     ╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝ ╚═╝  ╚═╝"""

    def compose(self) -> ComposeResult:
        with Vertical(id="about-overlay"):
            yield Static(f" ABOUT {BRAND_NAME}", id="about-header")
            with Vertical(id="about-body"):
                yield Static(self.MINI_LOGO, id="about-logo")
                yield Static(
                    f"{BRAND_NAME} AI v{BRAND_VERSION}\n"
                    f"Engine: {BRAND_ENGINE}\n"
                    f"Model:  {BRAND_MODEL}\n"
                    f"Local AI Development Environment\n\n"
                    f"GPU Accelerated | Streaming | {CONTEXT_SIZE} Context\n"
                    f"{GPU_LAYERS} GPU Layers | {THREADS} CPU Threads",
                    id="about-info",
                )
                yield Rule(id="about-separator")
                yield Static(
                    "Built with precision.\n"
                    "No cloud dependencies. No telemetry.\n"
                    "Your code stays on your machine.",
                    id="about-credits",
                )
            yield Static(" ESC per chiudere", id="about-footer")

    def action_dismiss_me(self):
        self.app.pop_screen()


# ── Memory Modal ─────────────────────────────────────────────────────
class MemoryModal(ModalScreen):
    """
    Visualizzatore interattivo del grafo di memoria.
    I dati vengono caricati in on_mount() — dopo che il DOM è pronto —
    così il DataTable è visibile e navigabile correttamente.
    """

    BINDINGS = [
        Binding("escape", "dismiss_me",  "", show=False),
        Binding("d",      "delete_node", "", show=False),
    ]

    def __init__(self, memory):
        super().__init__()
        self._memory = memory

    def compose(self) -> ComposeResult:
        with Vertical(id="memory-overlay"):
            yield Static(f" {BRAND_NAME} // MEMORY GRAPH VIEWER", id="memory-modal-header")
            yield Static("", id="memory-stats-bar")
            with ScrollableContainer(id="memory-body"):
                # BUG FIX: creiamo il DataTable vuoto in compose(),
                # i dati vengono inseriti in on_mount() quando il widget
                # è già attaccato al DOM e il layout è calcolato.
                yield DataTable(id="memory-table", cursor_type="row")
            yield Static(
                " ESC chiudi  |  D elimina nodo selezionato  |  Ordinati per peso ↓",
                id="memory-modal-footer",
            )

    def on_mount(self) -> None:
        # Aggiorna la stats bar
        try:
            self.query_one("#memory-stats-bar").update(f" {self._memory.get_info()}")
        except Exception:
            pass

        # Popola la tabella
        table = self.query_one("#memory-table", DataTable)
        table.add_columns("Categoria", "Peso", "Accessi", "Contenuto", "Tag")

        nodes = sorted(self._memory.nodes.values(), key=lambda n: -n.weight)

        if not nodes:
            # Nessun nodo: mostra riga placeholder
            table.add_row("—", "—", "—", "Memoria vuota — inizia a chattare!", "—", key="__empty__")
            return

        for node in nodes:
            tags_str      = ", ".join(node.tags[:4]) if node.tags else "—"
            content_short = node.content[:65] + ("…" if len(node.content) > 65 else "")
            table.add_row(
                node.category,
                f"{node.weight:.2f}",
                str(node.access_count),
                content_short,
                tags_str,
                key=node.id,
            )

    def action_dismiss_me(self):
        self.app.pop_screen()

    def action_delete_node(self):
        """Elimina il nodo sulla riga selezionata."""
        try:
            table   = self.query_one("#memory-table", DataTable)
            row_key = table.cursor_row_key
            node_id = str(row_key.value)

            if node_id == "__empty__":
                return

            if node_id in self._memory.nodes:
                content = self._memory.nodes[node_id].content[:40]
                del self._memory.nodes[node_id]
                self._memory._save()
                table.remove_row(row_key)
                self.app.notify(f"Nodo eliminato: {content}…")
                # Aggiorna stats bar
                self.query_one("#memory-stats-bar").update(f" {self._memory.get_info()}")
        except Exception as e:
            self.app.notify(f"Errore eliminazione: {e}", severity="error")
