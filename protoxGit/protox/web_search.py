# -*- coding: utf-8 -*-
"""
PROTOX AI — Web Agent v3.0
Vero agente web: cerca, scarica pagine, estrae contenuto, riassume.
"""

import re
import json
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from .config import BRAND_NAME

# ─────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────
MAX_SEARCH_RESULTS = 6        # quanti link cercare
MAX_PAGES_TO_FETCH = 4        # quante pagine effettivamente scaricare
MAX_PAGE_CHARS = 4000         # max caratteri per pagina estratta
MAX_TOTAL_CONTEXT = 12000     # budget totale di contesto web
FETCH_TIMEOUT = 8             # timeout per pagina (secondi)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Domini da skippare (no robots / inutili / paywall)
SKIP_DOMAINS = {
    "facebook.com", "instagram.com", "twitter.com", "x.com",
    "tiktok.com", "linkedin.com", "pinterest.com",
    "youtube.com",   # serve JS
}

# ─────────────────────────────────────────────────────────────────────
# WEB AGENT
# ─────────────────────────────────────────────────────────────────────
class WebSearch:
    """Web agent: cerca → scarica → estrae → struttura."""

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
        return True

    # ── SEARCH ENGINES ───────────────────────────────────────────────
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
                        "snippet": r.get("body", r.get("snippet", "")),
                    })
                return results
        except Exception:
            return []

    def _search_ddg_api(self, query: str) -> list[dict]:
        try:
            url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            results = []
            if data.get("AbstractText") and data.get("AbstractURL"):
                results.append({
                    "title": data.get("Heading", query),
                    "url": data.get("AbstractURL", ""),
                    "snippet": data["AbstractText"],
                })
            for topic in data.get("RelatedTopics", [])[:5]:
                if isinstance(topic, dict) and topic.get("FirstURL"):
                    results.append({
                        "title": topic.get("Text", "")[:120],
                        "url": topic.get("FirstURL", ""),
                        "snippet": topic.get("Text", ""),
                    })
            return results
        except Exception:
            return []

    def _search_wikipedia(self, query: str) -> list[dict]:
        try:
            for lang in ("it", "en"):
                url = (
                    f"https://{lang}.wikipedia.org/w/api.php?"
                    f"action=query&format=json&list=search&srlimit=4&"
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
                            "title": f"Wikipedia: {title}",
                            "url": page_url,
                            "snippet": snippet,
                        })
                    if results:
                        return results
            return []
        except Exception:
            return []

    def _gather_links(self, query: str, max_results: int) -> list[dict]:
        """Raccoglie link da piu' engine, dedup per dominio."""
        all_results = []
        seen_urls = set()
        seen_domains = set()

        for engine in (self._search_ddgs, self._search_ddg_api, self._search_wikipedia):
            try:
                results = engine(query, max_results) if engine == self._search_ddgs else engine(query)
            except TypeError:
                results = engine(query)

            for r in results:
                url = r.get("url", "")
                if not url or url in seen_urls:
                    continue
                # Estrai dominio
                try:
                    domain = urllib.parse.urlparse(url).netloc.replace("www.", "")
                except Exception:
                    continue
                # Skip social/inutili
                if any(skip in domain for skip in SKIP_DOMAINS):
                    continue
                # Max 2 per dominio per diversificare
                if list(seen_domains).count(domain) >= 2:
                    continue

                seen_urls.add(url)
                seen_domains.add(domain)
                all_results.append(r)

                if len(all_results) >= max_results:
                    return all_results

        return all_results

    # ── PAGE FETCHING & EXTRACTION ───────────────────────────────────
    def _fetch_page(self, url: str) -> Optional[str]:
        """Scarica una pagina HTML."""
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
                },
            )
            with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
                # Solo HTML
                content_type = resp.headers.get("Content-Type", "")
                if "html" not in content_type.lower():
                    return None
                # Max 2MB per pagina
                raw = resp.read(2_000_000)
                # Encoding detection
                try:
                    return raw.decode("utf-8")
                except UnicodeDecodeError:
                    try:
                        return raw.decode("latin-1")
                    except Exception:
                        return None
        except Exception:
            return None

    @staticmethod
    def _extract_text(html: str) -> str:
        """Estrae testo pulito da HTML — no dipendenze esterne."""
        if not html:
            return ""

        # Rimuovi script, style, nav, footer, header
        html = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<noscript[^>]*>.*?</noscript>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<nav[^>]*>.*?</nav>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<footer[^>]*>.*?</footer>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<header[^>]*>.*?</header>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<aside[^>]*>.*?</aside>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<!--.*?-->", " ", html, flags=re.DOTALL)

        # Prova ad estrarre <main>, <article> o <body>
        priority = re.search(r"<main[^>]*>(.*?)</main>", html, flags=re.DOTALL | re.IGNORECASE)
        if not priority:
            priority = re.search(r"<article[^>]*>(.*?)</article>", html, flags=re.DOTALL | re.IGNORECASE)
        if priority:
            html = priority.group(1)

        # Mantieni line breaks su tag block
        html = re.sub(r"</?(p|div|br|li|h[1-6]|tr)[^>]*>", "\n", html, flags=re.IGNORECASE)

        # Rimuovi tutti i tag rimanenti
        text = re.sub(r"<[^>]+>", " ", html)

        # Decode entities comuni
        entities = {
            "&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">",
            "&quot;": '"', "&#39;": "'", "&apos;": "'",
            "&egrave;": "è", "&agrave;": "à", "&igrave;": "ì",
            "&ograve;": "ò", "&ugrave;": "ù", "&eacute;": "é",
        }
        for ent, char in entities.items():
            text = text.replace(ent, char)
        # Numeric entities
        text = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), text)
        text = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), text)

        # Pulizia spazi
        lines = []
        for line in text.split("\n"):
            line = re.sub(r"\s+", " ", line).strip()
            if line and len(line) > 2:
                lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def _smart_truncate(text: str, max_chars: int) -> str:
        """Tronca testo cercando di mantenere paragrafi completi."""
        if len(text) <= max_chars:
            return text
        truncated = text[:max_chars]
        # Cerca ultimo punto/newline
        for sep in ("\n\n", "\n", ". ", ".", " "):
            idx = truncated.rfind(sep)
            if idx > max_chars * 0.7:
                return truncated[:idx].strip() + "..."
        return truncated + "..."

    def _fetch_and_extract(self, result: dict) -> Optional[dict]:
        """Scarica una pagina e ne estrae il testo."""
        html = self._fetch_page(result["url"])
        if not html:
            return None
        text = self._extract_text(html)
        if not text or len(text) < 100:
            return None
        return {
            "title": result["title"],
            "url": result["url"],
            "snippet": result.get("snippet", ""),
            "content": self._smart_truncate(text, MAX_PAGE_CHARS),
        }

    # ── MAIN AGENT METHOD ────────────────────────────────────────────
    def deep_search(self, query: str, on_progress=None) -> dict:
        """
        Ricerca web profonda:
        1. Cerca link su piu' engine
        2. Scarica le pagine in parallelo
        3. Estrae il contenuto testuale
        4. Ritorna tutto strutturato per l'LLM

        Args:
            query: la query di ricerca
            on_progress: callback(stage: str, info: str) per aggiornamenti UI

        Returns:
            {
                "query": str,
                "links": list[dict],     # tutti i link trovati
                "pages": list[dict],     # pagine scaricate ed estratte
                "context": str,          # contesto formattato per LLM
            }
        """
        # Stage 1: cerca link
        if on_progress:
            on_progress("searching", f"Cerco link per: {query}")
        links = self._gather_links(query, MAX_SEARCH_RESULTS)

        if not links:
            return {"query": query, "links": [], "pages": [], "context": ""}

        if on_progress:
            on_progress("found", f"Trovati {len(links)} link, scarico pagine...")

        # Stage 2: scarica pagine in parallelo
        pages = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self._fetch_and_extract, link): link
                for link in links[:MAX_PAGES_TO_FETCH]
            }
            for future in as_completed(futures, timeout=FETCH_TIMEOUT * 2):
                try:
                    result = future.result()
                    if result:
                        pages.append(result)
                        if on_progress:
                            on_progress("fetched", f"Letta: {result['title'][:50]}")
                except Exception:
                    continue

        # Stage 3: costruisci contesto
        if on_progress:
            on_progress("analyzing", f"Analizzo {len(pages)} pagine...")

        context = self._build_context(query, pages, links)

        return {
            "query": query,
            "links": links,
            "pages": pages,
            "context": context,
        }

    def _build_context(self, query: str, pages: list[dict], links: list[dict]) -> str:
        """Costruisce un contesto ricco per l'LLM."""
        if not pages and not links:
            return ""

        parts = [
            f"[{BRAND_NAME} WEB AGENT — Ricerca approfondita]",
            f"Query: \"{query}\"",
            f"Pagine analizzate: {len(pages)}  |  Link trovati: {len(links)}",
            "",
            "=" * 60,
            "CONTENUTO ESTRATTO DALLE PAGINE WEB:",
            "=" * 60,
            "",
        ]

        total_chars = sum(len(p["content"]) for p in pages)

        # Se troppo lungo, riduci proporzionalmente
        if total_chars > MAX_TOTAL_CONTEXT:
            ratio = MAX_TOTAL_CONTEXT / total_chars
            for p in pages:
                p["content"] = self._smart_truncate(p["content"], int(len(p["content"]) * ratio))

        for i, page in enumerate(pages, 1):
            parts.append(f"### FONTE [{i}]: {page['title']}")
            parts.append(f"URL: {page['url']}")
            parts.append("")
            parts.append(page["content"])
            parts.append("")
            parts.append("-" * 60)
            parts.append("")

        # Aggiungi anche snippet dei link non scaricati
        non_fetched = [l for l in links if not any(p["url"] == l["url"] for p in pages)]
        if non_fetched:
            parts.append("ALTRI RISULTATI (solo snippet):")
            for l in non_fetched[:3]:
                if l.get("snippet"):
                    parts.append(f"- {l['title']}: {l['snippet'][:200]}")
            parts.append("")

        parts.append("=" * 60)
        parts.append("ISTRUZIONI PER LA RISPOSTA:")
        parts.append("=" * 60)
        parts.append(
            "Usa il contenuto delle pagine sopra per rispondere all'utente in modo "
            "completo, accurato e dettagliato. Sintetizza le informazioni piu' "
            "importanti da TUTTE le fonti. Cita le fonti con [1], [2], ecc. "
            "Se le fonti dicono cose diverse, segnalalo. "
            "Se l'informazione non e' nelle fonti, dillo onestamente. "
            "Rispondi in italiano, ben strutturato con titoli e bullet point quando utile."
        )

        return "\n".join(parts)

    # ── Compatibilita' con vecchio codice ────────────────────────────
    def search(self, query: str, max_results: int = MAX_SEARCH_RESULTS) -> list[dict]:
        return self._gather_links(query, max_results)

    def search_and_format(self, query: str) -> str:
        """Vecchio metodo — ora usa deep_search."""
        result = self.deep_search(query)
        return result["context"]


# ─────────────────────────────────────────────────────────────────────
# INTENT DETECTION
# ─────────────────────────────────────────────────────────────────────

NEEDS_WEB_PATTERNS = [
    r"\bultim[ao]\s+versione\b",
    r"\blatest\s+version\b",
    r"\bnov(?:ità|ita')\b",
    r"\baggiornament[oi]\b",
    r"\bappena\s+(?:uscito|rilasciato|pubblicato)\b",
    r"\brilasciato\s+(?:di\s+)?recente\b",
    r"\bquest'?anno\b",
    r"\bquesto\s+mese\b",
    r"\bprezz[oi]\b",
    r"\bcosto\b",
    r"\bquanto\s+costa\b",
    r"\bpricing\b",
    r"\bnotizi[ae]\b",
    r"\bnews\b",
    r"\bdocumentazione\s+(?:ufficiale|aggiornata)\b",
    r"\bofficial\s+docs?\b",
    r"\b202[4-9]\b",
    r"\bdove\s+scaricare\b",
    r"\bdownload\s+(?:di|per)\b",
    r"\bchi\s+(?:e'|è|sia)\s+(?!tu\b)(?!io\b)\w+",      # "chi è X" (non "chi sei tu")
    r"\bcosa\s+(?:e'|è)\s+(?!questo\b|quello\b)\w{4,}",  # "cosa è X"
    r"\bcos'?(?:e'|è)\s+(?!questo\b|quello\b)\w{4,}",
    r"\bdimmi\s+(?:di|su)\s+\w+",
    r"\bspiegami\s+(?:cosa|chi|come)\s+\w+",
    r"\bcome\s+funziona\s+(?!questo\b)\w+",
    r"\binformazioni\s+(?:su|riguardo)\b",
]

NO_WEB_PATTERNS = [
    # Data/ora (gestite dal system prompt)
    r"\bche\s+(?:giorno|data|ora)\s+(?:e'|è|sia)?\b",
    r"\bche\s+(?:ore|orario)\s+(?:sono|e'|è)?\b",
    r"\boggi\s+(?:e'|è)?\s+(?:il|che|quale)\b",
    r"^\s*data\s*$",
    r"^\s*ora\s*$",
    # Saluti e meta
    r"^\s*(?:ciao|hey|hi|hello|yo|salve|buongiorno|buonasera|buonanotte)\b",
    r"\bcome\s+stai\b",
    r"\bcome\s+va\b",
    r"\bcome\s+ti\s+chiami\b",
    r"\bchi\s+sei\s+tu\b",
    r"^\s*(?:grazie|thanks|ok|okay)\s*[!.?]?\s*$",
    # Comandi di codifica (no web)
    r"^\s*(?:fai|crea|scrivi|genera|fammi|implementa)\s+",
    r"^\s*(?:spiegami|dimmi)\s+(?:il|la|lo)\s+codice\b",
    r"^\s*(?:traduci|traduco)\s+",
    r"^\s*(?:debug|correggi|fix)\b",
    # Math/logic
    r"^\s*(?:calcola|quanto\s+fa|risultato\s+di)\s+",
    # Riferimenti a messaggi precedenti
    r"\b(?:il|la|lo|i|gli|le)\s+(?:risultat[oi]|risposta|messaggio|codice)\s+(?:di\s+)?(?:prima|sopra|precedente)\b",
    r"\briesc(?:i|ono)\s+ad?\s+\w+\s+(?:i|gli|le)\s+\w+\s+(?:che|trovat[oi])\b",
]


def detect_search_intent(text: str) -> Optional[str]:
    """Solo comandi espliciti."""
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
    """Decide auto-search basandosi su pattern."""
    text_lower = text.lower().strip()
    for pattern in NO_WEB_PATTERNS:
        if re.search(pattern, text_lower):
            return False
    for pattern in NEEDS_WEB_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def build_search_query(text: str) -> str:
    """Pulisce il testo per usarlo come query."""
    text = text.strip()
    text = re.sub(
        r"^(?:per favore|please|puoi|potresti|dimmi|sai dirmi|spiegami|raccontami)\s+",
        "", text, flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^(?:cos'?(?:e'|è)|che\s+(?:cos'?)?(?:e'|è)|chi\s+(?:e'|è))\s+",
        "", text, flags=re.IGNORECASE,
    )
    if len(text) > 120:
        text = text[:120]
    return text.strip()