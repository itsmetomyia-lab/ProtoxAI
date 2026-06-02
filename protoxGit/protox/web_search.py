# -*- coding: utf-8 -*-
"""
PROTOX AI — Web Search v2.0
Multi-engine: DuckDuckGo + fallback su altri provider.
Auto-detect intelligente basato sulla conoscenza del modello.
"""

import re
import json
import urllib.request
import urllib.parse
from typing import Optional

from .config import BRAND_NAME

MAX_RESULTS = 5
MAX_SNIPPET_LEN = 300
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


class WebSearch:
    """Multi-engine web search con fallback automatici."""

    def __init__(self):
        self._ddgs_available = False
        try:
            from duckduckgo_search import DDGS
            self._ddgs_class = DDGS
            self._ddgs_available = True
        except ImportError:
            pass

    @property
    def available(self) -> bool:
        # Sempre disponibile grazie ai fallback HTTP
        return True

    # ── ENGINE 1: DuckDuckGo (libreria) ──────────────────────────────
    def _search_ddgs(self, query: str, max_results: int) -> list[dict]:
        if not self._ddgs_available:
            return []
        try:
            with self._ddgs_class() as ddgs:
                results = []
                for r in ddgs.text(query, max_results=max_results, region="it-it"):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", r.get("link", "")),
                        "snippet": r.get("body", r.get("snippet", ""))[:MAX_SNIPPET_LEN],
                    })
                return results
        except Exception:
            return []

    # ── ENGINE 2: DuckDuckGo Instant Answer API ──────────────────────
    def _search_ddg_api(self, query: str) -> list[dict]:
        try:
            url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            results = []

            # AbstractText (risposta diretta)
            if data.get("AbstractText"):
                results.append({
                    "title": data.get("Heading", query),
                    "url": data.get("AbstractURL", ""),
                    "snippet": data["AbstractText"][:MAX_SNIPPET_LEN],
                })

            # Answer (calcoli, conversioni, fatti)
            if data.get("Answer"):
                results.append({
                    "title": f"Risposta: {data.get('AnswerType', 'info')}",
                    "url": "",
                    "snippet": str(data["Answer"])[:MAX_SNIPPET_LEN],
                })

            # Definition
            if data.get("Definition"):
                results.append({
                    "title": "Definizione",
                    "url": data.get("DefinitionURL", ""),
                    "snippet": data["Definition"][:MAX_SNIPPET_LEN],
                })

            # RelatedTopics
            for topic in data.get("RelatedTopics", [])[:3]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append({
                        "title": topic.get("Text", "")[:80],
                        "url": topic.get("FirstURL", ""),
                        "snippet": topic.get("Text", "")[:MAX_SNIPPET_LEN],
                    })

            return results
        except Exception:
            return []

    # ── ENGINE 3: Wikipedia API ──────────────────────────────────────
    def _search_wikipedia(self, query: str) -> list[dict]:
        try:
            # Cerca prima in italiano
            for lang in ("it", "en"):
                url = (
                    f"https://{lang}.wikipedia.org/w/api.php?"
                    f"action=query&format=json&list=search&srlimit=3&"
                    f"srsearch={urllib.parse.quote(query)}"
                )
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                hits = data.get("query", {}).get("search", [])
                if hits:
                    results = []
                    for h in hits:
                        title = h.get("title", "")
                        snippet = re.sub(r"<[^>]+>", "", h.get("snippet", ""))
                        page_url = f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                        results.append({
                            "title": f"[Wikipedia {lang.upper()}] {title}",
                            "url": page_url,
                            "snippet": snippet[:MAX_SNIPPET_LEN],
                        })
                    if results:
                        return results
            return []
        except Exception:
            return []

    # ── ORCHESTRATORE ────────────────────────────────────────────────
    def search(self, query: str, max_results: int = MAX_RESULTS) -> list[dict]:
        """
        Cerca su piu' engine in sequenza finche' trova risultati.
        """
        # Engine 1: DuckDuckGo libreria
        results = self._search_ddgs(query, max_results)
        if results:
            return results

        # Engine 2: DuckDuckGo Instant Answer API
        results = self._search_ddg_api(query)
        if results:
            return results

        # Engine 3: Wikipedia
        results = self._search_wikipedia(query)
        if results:
            return results

        return []

    def search_and_format(self, query: str) -> str:
        """Cerca e formatta come contesto per LLM."""
        results = self.search(query)
        if not results:
            return ""

        lines = [f"[{BRAND_NAME} WEB SEARCH — Risultati per: \"{query}\"]", ""]
        for i, r in enumerate(results, 1):
            lines.append(f"[{i}] {r['title']}")
            if r['url']:
                lines.append(f"    URL: {r['url']}")
            if r['snippet']:
                lines.append(f"    {r['snippet']}")
            lines.append("")
        lines.append("[Fine risultati — usa queste info per rispondere]")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# DETECTION INTELLIGENTE — quando cercare e quando no
# ─────────────────────────────────────────────────────────────────────

# Domande che l'LLM NON sa rispondere (servono info esterne)
NEEDS_WEB_PATTERNS = [
    # Versioni e novita'
    r"\bultim[ao]\s+versione\b",
    r"\blatest\s+version\b",
    r"\bnov(?:ità|ita')\b",
    r"\baggiornament[oi]\b",
    r"\bappena\s+(?:uscito|rilasciato|pubblicato)\b",
    r"\brilasciato\s+(?:di\s+)?recente\b",
    r"\bquest'?anno\b",
    r"\bquesto\s+mese\b",
    r"\bdi\s+recente\b",

    # Prezzi e dati commerciali
    r"\bprezz[oi]\b",
    r"\bcosto\b",
    r"\bquanto\s+costa\b",
    r"\bpricing\b",

    # Eventi correnti
    r"\bnotizi[ae]\b",
    r"\bnews\b",
    r"\baccadut[oi]\s+(?:oggi|ieri|recente)\b",

    # Documentazione live
    r"\bdocumentazione\s+(?:ufficiale|aggiornata)\b",
    r"\bofficial\s+docs?\b",

    # Confronti aggiornati
    r"\bconfront[oi]\b.+\b(?:2024|2025|2026)\b",
    r"\bmigliore?\s+(?:framework|libreria|tool)\s+\b(?:2024|2025|2026)\b",

    # Anni espliciti recenti
    r"\b202[4-9]\b",

    # Download
    r"\bdove\s+scaricare\b",
    r"\bdownload\s+(?:di|per)\b",
]

# Domande che NON richiedono web (l'LLM o il sistema sanno gia')
NO_WEB_PATTERNS = [
    # Data/ora — gestite dal system prompt
    r"\bche\s+(?:giorno|data|ora)\s+(?:e'|è|sia)?\b",
    r"\bche\s+(?:ore|orario)\s+(?:sono|e'|è)?\b",
    r"\boggi\s+(?:e'|è)?\s+(?:il|che|quale)\b",
    r"^\s*data\s*$",
    r"^\s*ora\s*$",

    # Saluti e conversazione
    r"^\s*(?:ciao|hey|hi|hello|yo|salve|buongiorno|buonasera)\b",
    r"\bcome\s+stai\b",
    r"\bcome\s+va\b",
    r"\bcome\s+ti\s+chiami\b",
    r"\bchi\s+sei\b",
    r"\bcosa\s+(?:puoi|sai)\s+fare\b",

    # Comandi diretti al sistema/codice
    r"^\s*(?:fai|crea|scrivi|genera|fammi)\s+",
    r"^\s*(?:spiega|dimmi|raccontami)\s+",
    r"^\s*(?:traduci|traduco)\s+",

    # Domande matematiche/logiche
    r"^\s*(?:calcola|quanto\s+fa|risultato\s+di)\s+",

    # Programmazione generica
    r"\bfunzione\s+python\b",
    r"\bclasse\s+java\b",
    r"\bcome\s+(?:funziona|usare)\s+(?:un|una|il|la|lo)\b",
]


def detect_search_intent(text: str) -> Optional[str]:
    """
    Detecta SOLO comandi espliciti di ricerca.
    Per auto-search usa should_auto_search().
    """
    text_lower = text.lower().strip()

    explicit_patterns = [
        r"^/(?:search|cerca|web|google)\s+(.+)",
        r"^(?:cerca|cercami|ricerca|trova|trovami)\s+(?:sul\s+web|online|su\s+internet)\s+(.+)",
        r"^(?:cerca|cercami|ricerca|trova|trovami)\s+(.+?)\s+(?:sul\s+web|online|su\s+internet)\s*$",
    ]
    for pattern in explicit_patterns:
        match = re.match(pattern, text_lower)
        if match:
            return match.group(1).strip()

    return None


def should_auto_search(text: str) -> bool:
    """
    Decide se fare auto-search basandosi su:
    1. NO se matcha NO_WEB_PATTERNS (saluti, data, comandi)
    2. SI se matcha NEEDS_WEB_PATTERNS (versioni, prezzi, news)
    3. NO altrimenti (lascia rispondere l'LLM)
    """
    text_lower = text.lower().strip()

    # Veto: se matcha un pattern "no web", non cercare mai
    for pattern in NO_WEB_PATTERNS:
        if re.search(pattern, text_lower):
            return False

    # Trigger: se matcha un pattern "needs web", cerca
    for pattern in NEEDS_WEB_PATTERNS:
        if re.search(pattern, text_lower):
            return True

    return False


def build_search_query(text: str) -> str:
    """
    Costruisce una query di ricerca pulita dal messaggio utente.
    Rimuove parole inutili e si concentra sui termini significativi.
    """
    text = text.strip()
    # Rimuovi domande iniziali generiche
    text = re.sub(
        r"^(?:per favore|please|puoi|potresti|dimmi|sai dirmi)\s+",
        "", text, flags=re.IGNORECASE,
    )
    # Limita lunghezza
    if len(text) > 100:
        text = text[:100]
    return text