# -*- coding: utf-8 -*-
"""
PROTOX AI — CSS Builder v3.1
Genera il file TCSS da THEME dict. Aggiunti stili per memory modal e DataTable.
"""

from .config import CSS_FILE, THEME


def build_css(t: dict) -> str:
    return f"""
/* ================================================================
   PROTOX AI v3.1 — ULTRA PREMIUM THEME
   Auto-generated — do not edit manually
   ================================================================ */

/* ── SCREEN ──────────────────────────────────────────────────────── */
Screen {{
    background: {t['bg']};
    color:      {t['txt']};
    overflow:   hidden;
}}

/* ── HEADER ──────────────────────────────────────────────────────── */
Header {{
    dock:         top;
    height:       1;
    background:   {t['bg']};
    color:        {t['acc']};
    text-style:   bold;
    border-bottom: hkey {t['brd']};
}}
Header .header--icon {{ display: none; }}

/* ── FOOTER ──────────────────────────────────────────────────────── */
#custom-footer {{
    dock:       bottom;
    height:     3;
    background: {t['bg3']};
    color:      {t['mut']};
    layout:     vertical;
    padding:    0;
    border-top: hkey {t['acc']} 50%;
}}
#footer-accent-line {{
    height:     1;
    background: {t['acc']};
    color:      {t['bg']};
    text-style: bold;
    text-align: center;
    padding:    0 2;
}}
#footer-line-top {{
    height:     1;
    layout:     horizontal;
    padding:    0 1;
    background: {t['bg3']};
}}
#footer-line-bot {{
    height:     1;
    layout:     horizontal;
    padding:    0 1;
    background: {t['bg2']};
    border-top: solid {t['brd']};
}}
.fkey {{
    color:      {t['bg']};
    background: {t['acc']};
    text-style: bold;
    padding:    0 1;
}}
.fkey-dim {{
    color:      {t['txt2']};
    background: {t['bg4']};
    text-style: bold;
    padding:    0 1;
}}
.flabel {{
    color:        {t['txt3']};
    padding:      0 1;
    margin-right: 1;
}}
.fright {{
    dock:       right;
    color:      {t['acc']};
    text-style: bold;
    padding:    0 1;
}}
.fright-dim {{
    dock:       right;
    color:      {t['mut']};
    padding:    0 1;
    text-style: italic;
}}

/* ── MAIN LAYOUT ─────────────────────────────────────────────────── */
#main-layout {{
    layout: horizontal;
    height: 1fr;
}}

/* ── SIDEBAR ─────────────────────────────────────────────────────── */
#sidebar {{
    width:        34;
    height:       100%;
    border-right: tall {t['brd']};
    background:   {t['bg2']};
    layout:       vertical;
}}
#sidebar.hidden {{ display: none; }}
#sidebar-header {{
    height:        5;
    background:    {t['bg']};
    border-bottom: hkey {t['acc']} 50%;
    layout:        vertical;
    content-align: center middle;
    padding:       0 1;
}}
#sidebar-brand-line {{
    height:     1;
    background: {t['acc']};
    color:      {t['bg']};
    text-style: bold;
    text-align: center;
    width:      100%;
}}
#sidebar-brand {{
    color:      {t['acc']};
    text-style: bold;
    text-align: center;
    width:      100%;
    margin-top: 1;
}}
#sidebar-version {{
    color:      {t['mut2']};
    text-align: center;
    width:      100%;
    text-style: italic;
}}
#sidebar-engine {{
    color:      {t['ai']};
    text-align: center;
    width:      100%;
    text-style: bold;
}}
#session-body {{
    height:     1fr;
    padding:    0;
    layout:     vertical;
    overflow-y: auto;
}}
.sb-section {{
    height: auto;
    layout: vertical;
}}
.sb-section-head {{
    color:        {t['acc']};
    background:   {t['bg']};
    text-style:   bold;
    padding:      0 2;
    height:       1;
    border-bottom: solid {t['brd']};
    border-top:   solid {t['brd']};
}}
.sb-row {{
    layout:     horizontal;
    height:     1;
    padding:    0 2;
    background: {t['bg2']};
}}
.sb-row:hover {{ background: {t['bg3']}; }}
.sb-key     {{ color: {t['mut']};  width: 12; text-style: italic; }}
.sb-val     {{ color: {t['txt2']}; width: 1fr; }}
.sb-val-bright {{ color: {t['acc']}; text-style: bold; width: 1fr; }}
.sb-val-ok  {{ color: {t['ok']};   text-style: bold; width: 1fr; }}
.sb-val-warn {{ color: {t['warn']}; text-style: bold; width: 1fr; }}
.sb-val-ai  {{ color: {t['ai']};   text-style: bold; width: 1fr; }}
.sb-spacer  {{ height: 1; background: {t['bg2']}; }}
#sidebar-footer {{
    height:        1;
    background:    {t['bg']};
    color:         {t['mut2']};
    text-align:    center;
    content-align: center middle;
    border-top:    hkey {t['acc']} 50%;
    padding:       0 1;
    text-style:    italic;
}}

/* ── CONTENT AREA ────────────────────────────────────────────────── */
#content-area {{
    width:  1fr;
    height: 100%;
    layout: vertical;
}}

/* ── DASHBOARD ───────────────────────────────────────────────────── */
#dashboard {{
    width:      100%;
    height:     auto;
    layout:     vertical;
    background: {t['bg']};
}}
#dash-hero {{
    height:        auto;
    background:    {t['bg']};
    layout:        vertical;
    padding:       1 4;
    border-bottom: hkey {t['acc']} 50%;
}}
#dash-logo {{
    color:      {t['acc']};
    text-style: bold;
    text-align: center;
    width:      100%;
}}
#dash-tagline {{
    color:      {t['ai']};
    text-align: center;
    width:      100%;
    text-style: bold;
    margin-top: 1;
}}
#dash-subtitle {{
    color:      {t['mut']};
    text-align: center;
    width:      100%;
    text-style: italic;
}}
#dash-accent-bar {{
    height:     1;
    background: {t['acc']};
    color:      {t['bg']};
    text-style: bold;
    text-align: center;
}}
#dash-cards {{
    layout:     horizontal;
    height:     auto;
    padding:    1 2;
    background: {t['bg']};
}}
.dash-card {{
    width:      1fr;
    height:     auto;
    background: {t['bg2']};
    border:     tall {t['brd']};
    padding:    1 2;
    margin:     0 1;
    layout:     vertical;
}}
.dash-card:hover {{ border: tall {t['acc']} 50%; }}
.dash-card-title {{
    color:      {t['acc']};
    text-style: bold;
    height:     1;
    border-bottom: solid {t['brd']};
}}
.dash-card-sep       {{ color: {t['brd']}; height: 1; }}
.dash-card-item      {{ color: {t['txt3']}; height: 1; padding: 0 0 0 1; }}
.dash-card-item:hover {{ color: {t['txt']}; background: {t['bg3']}; }}
.dash-card-item-bright {{ color: {t['acc']}; height: 1; text-style: bold; padding: 0 0 0 1; }}
.dash-card-item-ai   {{ color: {t['ai']};   height: 1; text-style: italic; padding: 0 0 0 1; }}
#dash-status-bar {{
    height:        1;
    background:    {t['bg2']};
    layout:        horizontal;
    padding:       0 3;
    border-top:    solid {t['brd']};
    border-bottom: solid {t['brd']};
}}
.dash-status-dot  {{ color: {t['ok']};   text-style: bold; width: 3; }}
.dash-status-item {{ color: {t['mut2']}; margin-right: 1; text-style: italic; }}
.dash-status-val  {{ color: {t['acc']};  text-style: bold; margin-right: 3; }}
#dash-quote {{
    height:     2;
    color:      {t['ai']};
    text-style: italic;
    text-align: center;
    padding:    1 4;
    background: {t['bg']};
}}

/* ── CHAT ────────────────────────────────────────────────────────── */
#chat-scroll {{
    height:     1fr;
    width:      100%;
    overflow-y: auto;
    background: {t['bg']};
    layout:     vertical;
    padding:    1 3;
}}
.chat-message {{
    width:  100%;
    height: auto;
    layout: vertical;
    margin: 0 0 1 0;
}}
/* user */
.msg-user-header {{ layout: horizontal; height: 1; margin-bottom: 0; }}
.msg-user-icon   {{ color: {t['acc']}; text-style: bold; width: 4; }}
.msg-user-name   {{ color: {t['acc']}; text-style: bold; width: auto; }}
.msg-user-time   {{ color: {t['mut2']}; margin-left: 2; width: auto; text-style: italic; }}
.chat-bubble-user {{
    background:  {t['bg3']};
    border-left: tall {t['acc']};
    padding:     1 2;
    color:       {t['txt']};
    margin:      0 2 0 4;
}}
/* ai */
.msg-ai-header  {{ layout: horizontal; height: 1; margin-bottom: 0; }}
.msg-ai-icon    {{ color: {t['ai']}; text-style: bold; width: 4; }}
.msg-ai-name    {{ color: {t['ai']}; text-style: bold; width: auto; }}
.msg-ai-time    {{ color: {t['mut2']}; margin-left: 2; width: auto; text-style: italic; }}
.msg-ai-engine  {{ color: {t['mut2']}; margin-left: 1; text-style: italic; width: auto; }}
.chat-bubble-ai {{
    background:  {t['bg2']};
    border-left: tall {t['ai']};
    padding:     1 2;
    color:       {t['txt']};
    margin:      0 0 0 4;
}}
/* system */
.msg-sys-header {{ layout: horizontal; height: 1; margin-bottom: 0; }}
.msg-sys-icon   {{ color: {t['warn']}; text-style: bold; width: 4; }}
.msg-sys-tag    {{ color: {t['mut']};  text-style: italic; }}
.chat-bubble-sys {{
    background:  {t['bg2']};
    border-left: tall {t['warn']};
    padding:     0 2;
    color:       {t['mut']};
    margin:      0 0 0 4;
    text-style:  italic;
}}
/* error */
.msg-err-header {{ layout: horizontal; height: 1; margin-bottom: 0; }}
.msg-err-icon   {{ color: {t['err']}; text-style: bold; width: 4; }}
.msg-err-tag    {{ color: {t['err']}; text-style: bold; }}
.chat-bubble-err {{
    background:  {t['bg']};
    border-left: tall {t['err']};
    padding:     1 2;
    color:       {t['err']};
    margin:      0 0 0 4;
}}

/* ── INPUT AREA ──────────────────────────────────────────────────── */
#input-wrapper {{
    height: auto;
    layout: vertical;
    border-top: hkey {t['brd']};
}}
#input-status-line {{
    height:     1;
    layout:     horizontal;
    padding:    0 2;
    background: {t['bg2']};
}}
.input-status-text  {{ color: {t['mut']}; text-style: italic; width: auto; }}
.input-status-ready {{ color: {t['ok']};  text-style: bold; width: auto; }}
.input-status-busy  {{ color: {t['warn']}; text-style: bold; width: auto; }}
.input-status-stream {{ color: {t['ai']}; text-style: bold; width: auto; }}
.input-status-error {{ color: {t['err']}; text-style: bold; width: auto; }}

#input-container {{
    height:     auto;
    layout:     horizontal;
    padding:    0 1;
    background: {t['bg2']};
}}
#prompt-sym {{
    color:      {t['acc']};
    text-style: bold;
    width:      3;
    height:     auto;
    padding:    1 0;
}}
ProtoxInput {{
    width:          1fr;
    height:         auto;
    min-height:     3;
    max-height:     10;
    background:     {t['cbg']};
    color:          {t['txt']};
    border:         tall {t['brd']};
    padding:        0 1;
    scrollbar-size: 1 1;
}}
ProtoxInput:focus {{
    border: tall {t['acc']};
}}

/* ── MODALS BASE ─────────────────────────────────────────────────── */
ModalScreen {{
    background: {t['bg']} 75%;
    align: center middle;
}}

/* ── HELP MODAL ──────────────────────────────────────────────────── */
#help-overlay {{
    width:      80;
    height:     40;
    background: {t['bg2']};
    border:     tall {t['acc']};
    layout:     vertical;
}}
#help-modal-header {{
    height:     1;
    background: {t['acc']};
    color:      {t['bg']};
    text-style: bold;
    padding:    0 2;
}}
#help-brand-bar {{
    height:     1;
    background: {t['bg3']};
    color:      {t['ai']};
    padding:    0 2;
    text-style: italic;
}}
#help-body {{
    height:   1fr;
    padding:  1 2;
    overflow-y: auto;
}}
.help-section-title {{
    color:      {t['acc']};
    text-style: bold;
    margin-top: 1;
}}
.help-section-sub {{
    color:      {t['mut']};
    text-style: italic;
}}
.help-divider {{ color: {t['brd']}; }}
.help-row     {{ layout: horizontal; height: 1; }}
.help-key     {{ color: {t['acc']}; text-style: bold; width: 22; }}
.help-desc    {{ color: {t['txt2']}; width: 1fr; }}
.help-tip-icon {{ color: {t['ai']};  width: 4; }}
.help-tip-text {{ color: {t['txt3']}; width: 1fr; }}
#help-modal-footer {{
    height:     1;
    background: {t['bg']};
    color:      {t['mut2']};
    text-align: center;
    text-style: italic;
}}

/* ── ABOUT MODAL ─────────────────────────────────────────────────── */
#about-overlay {{
    width:      70;
    height:     30;
    background: {t['bg2']};
    border:     tall {t['acc']};
    layout:     vertical;
}}
#about-header {{
    height:     1;
    background: {t['acc']};
    color:      {t['bg']};
    text-style: bold;
    padding:    0 2;
}}
#about-body {{
    height:   1fr;
    padding:  1 4;
    layout:   vertical;
}}
#about-logo {{
    color:      {t['acc']};
    text-style: bold;
    text-align: center;
    width:      100%;
}}
#about-info {{
    color:      {t['txt2']};
    margin-top: 1;
    text-align: center;
    width:      100%;
}}
#about-separator {{ color: {t['brd']}; }}
#about-credits {{
    color:      {t['mut']};
    text-style: italic;
    text-align: center;
    width:      100%;
}}
#about-footer {{
    height:     1;
    background: {t['bg']};
    color:      {t['mut2']};
    text-align: center;
    text-style: italic;
}}

/* ── MEMORY MODAL (NUOVO) ────────────────────────────────────────── */
#memory-overlay {{
    width:      95%;
    height:     85%;
    background: {t['bg2']};
    border:     tall {t['ai']};
    layout:     vertical;
}}
#memory-modal-header {{
    height:     1;
    background: {t['ai']};
    color:      {t['bg']};
    text-style: bold;
    padding:    0 2;
}}
#memory-stats-bar {{
    height:     1;
    background: {t['bg3']};
    color:      {t['mut']};
    padding:    0 2;
    text-style: italic;
}}
#memory-body {{
    height:   1fr;
    padding:  1 1;
    overflow-y: auto;
}}
#memory-modal-footer {{
    height:     1;
    background: {t['bg']};
    color:      {t['mut2']};
    text-align: center;
    text-style: italic;
}}
DataTable {{
    background:     {t['bg2']};
    color:          {t['txt']};
    border:         tall {t['brd']};
}}
DataTable > .datatable--header {{
    background: {t['bg']};
    color:      {t['acc']};
    text-style: bold;
}}
DataTable > .datatable--cursor {{
    background: {t['bg3']};
    color:      {t['txt']};
}}
DataTable > .datatable--hover {{
    background: {t['bg3']};
}}
"""


def write_theme_css():
    """Scrive il file CSS del tema corrente."""
    css = build_css(THEME)
    try:
        CSS_FILE.write_text(css, encoding="utf-8")
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("CSS write failed: %s", e)
