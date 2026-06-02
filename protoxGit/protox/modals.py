# -*- coding: utf-8 -*-
"""
PROTOX AI — Modali: Help, About.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Rule

from .config import (
    BRAND_NAME, BRAND_VERSION, BRAND_ENGINE, BRAND_MODEL,
    BRAND_QUANT, BRAND_FULL, GPU_LAYERS, CONTEXT_SIZE, THREADS,
)


class HelpModal(ModalScreen):
    """Help premium — sezioni, tips, scrollabile."""

    BINDINGS = [Binding("escape", "dismiss_me", "", show=False)]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-overlay"):
            yield Static(f"  {BRAND_FULL}  //  HELP CENTER", id="help-modal-header")
            yield Static(
                f"  {BRAND_ENGINE}  |  {BRAND_MODEL}  |  Complete Reference",
                id="help-brand-bar",
            )
            with ScrollableContainer(id="help-body"):
                yield Static(" KEYBOARD SHORTCUTS", classes="help-section-title")
                yield Static("  Navigate and control the interface", classes="help-section-sub")
                yield Rule(classes="help-divider")
                for key, desc in [
                    ("F1", "Open this help panel"),
                    ("F3", "About PROTOX"),
                    ("Ctrl+B", "Toggle sidebar panel"),
                    ("Ctrl+L", "Clear conversation"),
                    ("Ctrl+C", "Quit application"),
                ]:
                    with Horizontal(classes="help-row"):
                        yield Static(key, classes="help-key")
                        yield Static(desc, classes="help-desc")

                yield Rule(classes="help-divider")
                yield Static(" INPUT CONTROLS", classes="help-section-title")
                yield Static("  Writing and navigating input", classes="help-section-sub")
                yield Rule(classes="help-divider")
                for key, desc in [
                    ("Enter", "Send message"),
                    ("Shift+Enter", "New line (multiline input)"),
                    ("Up Arrow", "Previous input from history"),
                    ("Down Arrow", "Next input from history"),
                ]:
                    with Horizontal(classes="help-row"):
                        yield Static(key, classes="help-key")
                        yield Static(desc, classes="help-desc")

                yield Rule(classes="help-divider")
                yield Static(" SLASH COMMANDS", classes="help-section-title")
                yield Static("  Type in the input field and press Enter", classes="help-section-sub")
                yield Rule(classes="help-divider")
                for key, desc in [
                    ("/clear", "Reset conversation & context"),
                    ("/export", "Export chat to markdown file"),
                    ("/track CAT NAME", "Add entity to tracker"),
                    ("/status", "Server status info"),
                    ("/about", "Show about panel"),
                    ("/help", "Show this help panel"),
                ]:
                    with Horizontal(classes="help-row"):
                        yield Static(key, classes="help-key")
                        yield Static(desc, classes="help-desc")

                yield Rule(classes="help-divider")
                yield Static(" TIPS", classes="help-section-title")
                yield Static("  Pro tips for power users", classes="help-section-sub")
                yield Rule(classes="help-divider")
                for tip in [
                    "Use Shift+Enter for multiline code snippets",
                    "The AI keeps last 10 messages as context",
                    "Exports are saved in protox_data/exports/",
                    "/clear resets the AI context window completely",
                ]:
                    with Horizontal(classes="help-row"):
                        yield Static(" *", classes="help-tip-icon")
                        yield Static(tip, classes="help-tip-text")

            yield Static(
                f"  ESC to close  |  {BRAND_NAME} v{BRAND_VERSION}",
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
            yield Static(f"  ABOUT {BRAND_NAME}", id="about-header")
            with Vertical(id="about-body"):
                yield Static(self.MINI_LOGO, id="about-logo")
                yield Static(
                    f"{BRAND_NAME} AI  v{BRAND_VERSION}\n"
                    f"Engine: {BRAND_ENGINE}\n"
                    f"Model:  {BRAND_MODEL}\n"
                    f"Local AI Development Environment\n\n"
                    f"GPU Accelerated  |  Streaming  |  {CONTEXT_SIZE} Context\n"
                    f"{GPU_LAYERS} GPU Layers  |  {THREADS} CPU Threads",
                    id="about-info",
                )
                yield Rule(id="about-separator")
                yield Static(
                    "Built with precision.\n"
                    "No cloud dependencies. No telemetry.\n"
                    "Your code stays on your machine.",
                    id="about-credits",
                )
            yield Static("  ESC to close", id="about-footer")

    def action_dismiss_me(self):
        self.app.pop_screen()