# -*- coding: utf-8 -*-
"""
PROTOX AI — CSS Builder v3.0 Ultra Premium
Generatore CSS dai temi. Sostituisci SOLO questo file per upgrade grafico.
"""

from .config import CSS_FILE, THEME


def build_css(t: dict) -> str:
    """Genera il CSS completo da un dizionario tema."""
    return f"""\
/* ================================================================
   PROTOX AI v3.0 — ULTRA PREMIUM THEME
   Generated — Do not edit manually
   ================================================================ */

/* ── SCREEN ──────────────────────────────────────────────────────── */
Screen {{
    background: {t['bg']};
    color: {t['txt']};
    overflow: hidden;
}}

/* ── HEADER ──────────────────────────────────────────────────────── */
Header {{
    dock: top;
    height: 1;
    background: {t['bg']};
    color: {t['acc']};
    text-style: bold;
    border-bottom: hkey {t['brd']};
}}
Header .header--icon {{ display: none; }}

/* ================================================================
   FOOTER — 3 righe: accent band + keys + commands
   ================================================================ */
#custom-footer {{
    dock: bottom;
    height: 3;
    background: {t['bg3']};
    color: {t['mut']};
    layout: vertical;
    padding: 0;
    border-top: hkey {t['acc']} 50%;
}}
#footer-accent-line {{
    height: 1;
    background: {t['acc']};
    color: {t['bg']};
    text-style: bold;
    text-align: center;
    padding: 0 2;
}}
#footer-line-top {{
    height: 1;
    layout: horizontal;
    padding: 0 1;
    background: {t['bg3']};
}}
#footer-line-bot {{
    height: 1;
    layout: horizontal;
    padding: 0 1;
    background: {t['bg2']};
    border-top: solid {t['brd']};
}}
.fkey {{
    color: {t['bg']};
    background: {t['acc']};
    text-style: bold;
    padding: 0 1;
}}
.fkey-dim {{
    color: {t['txt2']};
    background: {t['bg4']};
    text-style: bold;
    padding: 0 1;
}}
.flabel {{
    color: {t['txt3']};
    padding: 0 1;
    margin-right: 1;
}}
.fright {{
    dock: right;
    color: {t['acc']};
    text-style: bold;
    padding: 0 1;
}}
.fright-dim {{
    dock: right;
    color: {t['mut']};
    padding: 0 1;
    text-style: italic;
}}

/* ================================================================
   MAIN LAYOUT
   ================================================================ */
#main-layout {{
    layout: horizontal;
    height: 1fr;
}}

/* ================================================================
   SIDEBAR — premium panel
   ================================================================ */
#sidebar {{
    width: 34;
    height: 100%;
    border-right: tall {t['brd']};
    background: {t['bg2']};
    layout: vertical;
}}
#sidebar.hidden {{ display: none; }}

#sidebar-header {{
    height: 5;
    background: {t['bg']};
    border-bottom: hkey {t['acc']} 50%;
    layout: vertical;
    content-align: center middle;
    padding: 0 1;
}}
#sidebar-brand-line {{
    height: 1;
    background: {t['acc']};
    color: {t['bg']};
    text-style: bold;
    text-align: center;
    width: 100%;
}}
#sidebar-brand {{
    color: {t['acc']};
    text-style: bold;
    text-align: center;
    width: 100%;
    margin-top: 1;
}}
#sidebar-version {{
    color: {t['mut2']};
    text-align: center;
    width: 100%;
    text-style: italic;
}}
#sidebar-engine {{
    color: {t['ai']};
    text-align: center;
    width: 100%;
    text-style: bold;
}}
#session-body {{
    height: 1fr;
    padding: 0;
    layout: vertical;
    overflow-y: auto;
}}

/* sidebar sections */
.sb-section {{
    height: auto;
    margin-bottom: 0;
    layout: vertical;
}}
.sb-section-head {{
    color: {t['acc']};
    background: {t['bg']};
    text-style: bold;
    padding: 0 2;
    height: 1;
    border-bottom: solid {t['brd']};
    border-top: solid {t['brd']};
}}
.sb-row {{
    layout: horizontal;
    height: 1;
    padding: 0 2;
    background: {t['bg2']};
}}
.sb-row:hover {{
    background: {t['bg3']};
}}
.sb-key {{
    color: {t['mut']};
    width: 12;
    text-style: italic;
}}
.sb-val {{
    color: {t['txt2']};
    width: 1fr;
}}
.sb-val-bright {{
    color: {t['acc']};
    text-style: bold;
    width: 1fr;
}}
.sb-val-ok {{
    color: {t['ok']};
    text-style: bold;
    width: 1fr;
}}
.sb-val-warn {{
    color: {t['warn']};
    text-style: bold;
    width: 1fr;
}}
.sb-val-ai {{
    color: {t['ai']};
    text-style: bold;
    width: 1fr;
}}
.sb-divider {{
    height: 1;
    color: {t['brd']};
}}
.sb-spacer {{
    height: 1;
    background: {t['bg2']};
}}

#sidebar-footer {{
    height: 1;
    background: {t['bg']};
    color: {t['mut2']};
    text-align: center;
    content-align: center middle;
    border-top: hkey {t['acc']} 50%;
    padding: 0 1;
    text-style: italic;
}}

/* ================================================================
   CONTENT AREA
   ================================================================ */
#content-area {{
    width: 1fr;
    height: 100%;
    layout: vertical;
}}

/* ================================================================
   DASHBOARD — hero + cards + status
   ================================================================ */
#dashboard {{
    width: 100%;
    height: auto;
    layout: vertical;
    background: {t['bg']};
}}
#dash-hero {{
    height: auto;
    background: {t['bg']};
    layout: vertical;
    padding: 1 4;
    border-bottom: hkey {t['acc']} 50%;
}}
#dash-logo {{
    color: {t['acc']};
    text-style: bold;
    text-align: center;
    width: 100%;
}}
#dash-tagline {{
    color: {t['ai']};
    text-align: center;
    width: 100%;
    text-style: bold;
    margin-top: 1;
}}
#dash-subtitle {{
    color: {t['mut']};
    text-align: center;
    width: 100%;
    text-style: italic;
}}
#dash-accent-bar {{
    height: 1;
    background: {t['acc']};
    color: {t['bg']};
    text-style: bold;
    text-align: center;
}}
#dash-cards {{
    layout: horizontal;
    height: auto;
    padding: 1 2;
    background: {t['bg']};
}}
.dash-card {{
    width: 1fr;
    height: auto;
    background: {t['bg2']};
    border: tall {t['brd']};
    padding: 1 2;
    margin: 0 1;
    layout: vertical;
}}
.dash-card:hover {{
    border: tall {t['acc']} 50%;
}}
.dash-card-title {{
    color: {t['acc']};
    text-style: bold;
    height: 1;
    border-bottom: solid {t['brd']};
}}
.dash-card-sep {{
    color: {t['brd']};
    height: 1;
}}
.dash-card-item {{
    color: {t['txt3']};
    height: 1;
    padding: 0 0 0 1;
}}
.dash-card-item:hover {{
    color: {t['txt']};
    background: {t['bg3']};
}}
.dash-card-item-bright {{
    color: {t['acc']};
    height: 1;
    text-style: bold;
    padding: 0 0 0 1;
}}
.dash-card-item-ai {{
    color: {t['ai']};
    height: 1;
    text-style: italic;
    padding: 0 0 0 1;
}}
#dash-status-bar {{
    height: 1;
    background: {t['bg2']};
    layout: horizontal;
    padding: 0 3;
    border-top: solid {t['brd']};
    border-bottom: solid {t['brd']};
}}
.dash-status-dot {{
    color: {t['ok']};
    text-style: bold;
    width: 3;
}}
.dash-status-item {{
    color: {t['mut2']};
    margin-right: 1;
    text-style: italic;
}}
.dash-status-val {{
    color: {t['acc']};
    text-style: bold;
    margin-right: 3;
}}
#dash-quote {{
    height: 2;
    color: {t['ai']};
    text-style: italic;
    text-align: center;
    padding: 1 4;
    background: {t['bg']};
}}

/* ================================================================
   CHAT — messages area
   ================================================================ */
#chat-scroll {{
    height: 1fr;
    width: 100%;
    overflow-y: auto;
    background: {t['bg']};
    layout: vertical;
    padding: 1 3;
}}

.chat-message {{
    width: 100%;
    height: auto;
    layout: vertical;
    margin: 0 0 1 0;
}}

/* ── user message ────────────────────────────────────────────────── */
.msg-user-header {{
    layout: horizontal;
    height: 1;
    margin-bottom: 0;
}}
.msg-user-icon {{
    color: {t['acc']};
    text-style: bold;
    width: 4;
}}
.msg-user-name {{
    color: {t['acc']};
    text-style: bold;
    width: auto;
}}
.msg-user-time {{
    color: {t['mut2']};
    margin-left: 2;
    width: auto;
    text-style: italic;
}}
.chat-bubble-user {{
    background: {t['bg3']};
    border-left: tall {t['acc']};
    padding: 1 2;
    color: {t['txt']};
    margin: 0 2 0 4;
}}

/* ── ai message ──────────────────────────────────────────────────── */
.msg-ai-header {{
    layout: horizontal;
    height: 1;
    margin-bottom: 0;
}}
.msg-ai-icon {{
    color: {t['ai']};
    text-style: bold;
    width: 4;
}}
.msg-ai-name {{
    color: {t['ai']};
    text-style: bold;
    width: auto;
}}
.msg-ai-time {{
    color: {t['mut2']};
    margin-left: 2;
    width: auto;
    text-style: italic;
}}
.msg-ai-engine {{
    color: {t['mut2']};
    text-style: italic;
    margin-left: 2;
    width: auto;
}}
.chat-bubble-ai {{
    background: {t['bg2']};
    border-left: tall {t['ai']};
    padding: 1 2;
    margin: 0 2 0 4;
}}

/* ── system message ──────────────────────────────────────────────── */
.msg-sys-header {{
    layout: horizontal;
    height: 1;
}}
.msg-sys-icon {{
    color: {t['ok']};
    text-style: bold;
    width: 4;
}}
.msg-sys-tag {{
    color: {t['ok']};
    text-style: italic;
    width: auto;
}}
.chat-bubble-sys {{
    border-left: tall {t['ok']} 50%;
    padding: 0 2;
    color: {t['mut']};
    background: {t['bg2']};
    margin: 0 2 0 4;
    text-style: italic;
}}

/* ── error message ───────────────────────────────────────────────── */
.msg-err-header {{
    layout: horizontal;
    height: 1;
}}
.msg-err-icon {{
    color: {t['err']};
    text-style: bold;
    width: 4;
}}
.msg-err-tag {{
    color: {t['err']};
    text-style: bold;
    width: auto;
}}
.chat-bubble-err {{
    border-left: tall {t['err']};
    padding: 1 2;
    color: {t['err']};
    background: {t['bg3']};
    margin: 0 2 0 4;
    border: solid {t['err']} 30%;
}}

/* ================================================================
   MARKDOWN rendering inside chat bubbles
   ================================================================ */
Markdown {{
    background: transparent;
    color: {t['txt']};
    margin: 0;
    padding: 0;
}}
MarkdownFence {{
    background: {t['cbg']};
    color: {t['ai']};
    border: tall {t['brd']};
    margin: 1 0;
    padding: 1 2;
}}
MarkdownCodeBlock {{
    background: {t['cbg']};
    color: {t['ai']};
    border: tall {t['brd']};
    margin: 1 0;
    padding: 1 2;
}}
Markdown > .code_inline {{
    background: {t['bg4']};
    color: {t['ai']};
    padding: 0 1;
}}
MarkdownH1 {{
    color: {t['acc']};
    text-style: bold;
    margin: 1 0 0 0;
    padding: 0 0 0 0;
    border-bottom: solid {t['acc']} 40%;
}}
MarkdownH2 {{
    color: {t['acc']};
    text-style: bold;
    margin: 1 0 0 0;
}}
MarkdownH3 {{
    color: {t['acc2']};
    text-style: bold;
    margin: 1 0 0 0;
}}
MarkdownH4 {{
    color: {t['ai']};
    text-style: bold italic;
    margin: 1 0 0 0;
}}
MarkdownBullet {{
    color: {t['acc']};
}}
MarkdownBlockQuote {{
    border-left: tall {t['ai']} 60%;
    background: {t['bg4']};
    color: {t['txt2']};
    padding: 0 2;
    margin: 1 0;
}}
MarkdownHorizontalRule {{
    color: {t['brd']};
}}
MarkdownTable {{
    background: {t['bg2']};
    color: {t['txt']};
    border: solid {t['brd']};
    margin: 1 0;
    padding: 0 1;
}}

/* ================================================================
   INPUT AREA — status line + prompt
   ================================================================ */
#input-wrapper {{
    height: auto;
    layout: vertical;
    background: {t['bg2']};
    border-top: hkey {t['acc']} 50%;
}}
#input-status-line {{
    height: 1;
    layout: horizontal;
    padding: 0 3;
    background: {t['bg']};
    border-bottom: solid {t['brd']};
}}
.input-status-text {{
    color: {t['mut2']};
    width: auto;
    text-style: italic;
}}
.input-status-ready {{
    color: {t['ok']};
    text-style: bold;
    width: auto;
}}
.input-status-busy {{
    color: {t['warn']};
    text-style: bold;
    width: auto;
}}
.input-status-stream {{
    color: {t['ai']};
    text-style: bold italic;
    width: auto;
}}
#input-container {{
    height: auto;
    min-height: 3;
    max-height: 12;
    background: {t['bg2']};
    layout: horizontal;
    padding: 0 2;
}}
#prompt-sym {{
    color: {t['acc']};
    text-style: bold;
    width: 4;
    content-align: left middle;
    height: 100%;
}}
ProtoxInput {{
    width: 1fr;
    height: auto;
    min-height: 3;
    border: none;
    background: transparent;
    color: {t['txt']};
    padding: 0;
}}
ProtoxInput:focus {{
    border: none;
}}

/* ================================================================
   HELP MODAL — premium scrollable reference
   ================================================================ */
HelpModal {{
    align: center middle;
}}
#help-overlay {{
    background: {t['bg']};
    border: tall {t['acc']};
    width: 70;
    height: auto;
    max-height: 42;
    padding: 0;
}}
#help-modal-header {{
    background: {t['acc']};
    color: {t['bg']};
    text-style: bold;
    text-align: center;
    padding: 0 2;
    height: 1;
}}
#help-brand-bar {{
    height: 1;
    background: {t['bg2']};
    color: {t['ai']};
    text-align: center;
    text-style: italic;
    border-bottom: solid {t['brd']};
}}
#help-body {{
    padding: 1 2;
    layout: vertical;
    height: auto;
    max-height: 34;
    overflow-y: auto;
    background: {t['bg']};
}}
.help-section-title {{
    color: {t['acc']};
    background: {t['bg2']};
    text-style: bold;
    margin-top: 1;
    padding: 0 2;
    height: 1;
    border-left: tall {t['acc']};
}}
.help-section-sub {{
    color: {t['mut']};
    text-style: italic;
    padding: 0 2;
    height: 1;
    margin-bottom: 0;
}}
.help-row {{
    layout: horizontal;
    height: 1;
    padding: 0 2;
}}
.help-row:hover {{
    background: {t['bg3']};
}}
.help-key {{
    color: {t['acc']};
    text-style: bold;
    width: 20;
}}
.help-desc {{
    color: {t['txt2']};
    width: 1fr;
}}
.help-divider {{
    color: {t['brd']};
    height: 1;
    margin: 0 2;
}}
.help-tip-icon {{
    color: {t['ai']};
    text-style: bold;
    width: 4;
}}
.help-tip-text {{
    color: {t['ai']};
    text-style: italic;
    width: 1fr;
}}
#help-modal-footer {{
    background: {t['bg2']};
    color: {t['mut']};
    text-align: center;
    height: 1;
    border-top: solid {t['brd']};
    padding: 0 1;
    text-style: italic;
}}

/* ================================================================
   THEME MODAL — preview + list + custom
   ================================================================ */
ThemeModal {{
    align: center middle;
}}
#theme-overlay {{
    background: {t['bg']};
    border: tall {t['acc']};
    width: 68;
    height: auto;
    max-height: 42;
    padding: 0;
}}
#theme-modal-header {{
    background: {t['acc']};
    color: {t['bg']};
    text-style: bold;
    text-align: center;
    padding: 0 2;
    height: 1;
}}
#theme-brand-bar {{
    height: 1;
    background: {t['bg2']};
    color: {t['ai']};
    text-align: center;
    text-style: italic;
    border-bottom: solid {t['brd']};
}}
#theme-modal-body {{
    padding: 1 2;
    layout: vertical;
    background: {t['bg']};
}}
#theme-preview {{
    height: 5;
    background: {t['bg2']};
    border: tall {t['brd']};
    layout: vertical;
    padding: 0 2;
    margin-bottom: 1;
}}
#preview-title {{
    color: {t['acc']};
    text-style: bold;
    height: 1;
}}
#preview-bar {{
    height: 1;
    layout: horizontal;
    margin-top: 1;
}}
#preview-codes {{
    color: {t['mut']};
    height: 1;
    text-style: italic;
}}
.preview-swatch-acc {{
    background: {t['acc']};
    color: {t['bg']};
    text-style: bold;
    width: 10;
    height: 1;
    margin-right: 1;
    text-align: center;
}}
.preview-swatch-ai {{
    background: {t['ai']};
    color: {t['bg']};
    text-style: bold;
    width: 10;
    height: 1;
    margin-right: 1;
    text-align: center;
}}
.preview-swatch-bg {{
    background: {t['bg']};
    color: {t['txt']};
    border: solid {t['brd']};
    width: 10;
    height: 1;
    margin-right: 1;
    text-align: center;
}}
.preview-swatch-txt {{
    background: {t['txt']};
    color: {t['bg']};
    width: 10;
    height: 1;
    text-align: center;
}}
#theme-section-label {{
    color: {t['acc']};
    background: {t['bg2']};
    text-style: bold;
    padding: 0 2;
    height: 1;
    border-left: tall {t['acc']};
}}
#theme-list {{
    height: auto;
    max-height: 18;
    background: {t['bg']};
    border: tall {t['brd']};
    margin-bottom: 1;
}}
ListView > ListItem {{
    background: transparent;
    color: {t['txt2']};
    padding: 0 2;
    height: 2;
}}
ListView > ListItem:hover {{
    background: {t['bg3']};
    color: {t['txt']};
}}
ListView > ListItem.--highlight {{
    background: {t['acc']} 20%;
    color: {t['acc']};
    text-style: bold;
}}
#custom-section-label {{
    color: {t['ai']};
    background: {t['bg2']};
    text-style: bold;
    padding: 0 2;
    height: 1;
    margin-top: 1;
    border-left: tall {t['ai']};
}}
#custom-accent-input {{
    border: solid {t['brd']};
    background: {t['bg2']};
    color: {t['txt']};
    margin-top: 1;
    height: 3;
}}
#custom-accent-input:focus {{
    border: tall {t['acc']};
    background: {t['bg3']};
}}
#theme-hint {{
    color: {t['mut2']};
    text-align: center;
    margin-top: 1;
    text-style: italic;
}}
#theme-modal-footer {{
    background: {t['bg2']};
    color: {t['mut']};
    text-align: center;
    height: 1;
    border-top: solid {t['brd']};
    padding: 0 1;
    text-style: italic;
}}

/* ================================================================
   ABOUT MODAL
   ================================================================ */
AboutModal {{
    align: center middle;
}}
#about-overlay {{
    background: {t['bg']};
    border: tall {t['acc']};
    width: 58;
    height: auto;
    padding: 0;
}}
#about-header {{
    background: {t['acc']};
    color: {t['bg']};
    text-style: bold;
    text-align: center;
    padding: 0 2;
    height: 1;
}}
#about-body {{
    padding: 2 3;
    layout: vertical;
    background: {t['bg']};
}}
#about-logo {{
    color: {t['acc']};
    text-style: bold;
    text-align: center;
    margin-bottom: 1;
}}
#about-info {{
    color: {t['txt2']};
    text-align: center;
}}
#about-separator {{
    color: {t['brd']};
    margin: 1 0;
}}
#about-credits {{
    color: {t['ai']};
    text-align: center;
    text-style: italic;
}}
#about-footer {{
    background: {t['bg2']};
    color: {t['mut']};
    text-align: center;
    height: 1;
    border-top: solid {t['brd']};
    padding: 0 1;
    text-style: italic;
}}

/* ── UTILITY ─────────────────────────────────────────────────────── */
.hidden {{
    display: none;
}}
"""


def write_theme_css():
    """Scrive il CSS del tema unico su disco."""
    CSS_FILE.write_text(build_css(THEME), encoding="utf-8")