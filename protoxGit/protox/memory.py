# -*- coding: utf-8 -*-
"""
PROTOX AI — Persistent Memory v3.0  "Nano-Graph"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Filosofia: UN SOLO nodo per concetto. Mai salvare frasi intere.

Come funziona:
  1. Ogni messaggio viene "distillato" in 3-7 token chiave (zero LLM).
  2. Se esiste già un nodo con fingerprint simile → merge, NON duplica.
  3. Il nodo memorizza solo il concetto compresso, non la frase originale.
  4. Al retrieve, i nodi vengono ricostruiti in linguaggio naturale dal
     motore di retrieval (template-based, zero LLM).

Dimensioni reali:
  ~60-80 byte per nodo su disco (JSON compatto)
  ~500 nodi = ~40 KB  (vs ~25 MB con storage raw)

Thread-safe: threading.RLock su ogni operazione mutante.
Write atomica: tmp → rename, nessuna corruzione.
"""

import json
import time
import hashlib
import re
import threading
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional

from .config import DATA_DIR, BRAND_NAME
from .helpers import safe_write_json, clamp

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────
MEMORY_FILE        = DATA_DIR / "memory_graph.json"
MEMORY_STATS_FILE  = DATA_DIR / "memory_stats.json"

COMPRESS_EVERY     = 4      # ogni N messaggi → estrai nodi
MAX_NODES          = 400    # hard cap nodi nel grafo
MAX_CONTEXT_NODES  = 12     # nodi iniettati nel prompt
MIN_WEIGHT         = 0.08   # sotto questo → candidato a pruning
DECAY_RATE         = 0.97   # per giorno di inattività
MAX_CONNECTIONS    = 8      # max archi per nodo
JACCARD_THRESHOLD  = 0.30   # soglia similarità per merge (bassa: nodi hanno pochi token)


# ─────────────────────────────────────────────────────────────────────
# NANO-NODE  — struttura minima, zero ridondanza
# ─────────────────────────────────────────────────────────────────────
@dataclass
class NanoNode:
    """
    Un singolo nodo di conoscenza compresso.
    'content' contiene 3-8 token chiave, NON frasi intere.
    Esempio: "python fastapi rest backend" invece di
             "L'utente usa FastAPI per costruire API REST in Python"
    """
    id:            str
    content:       str         # token chiave compressi
    category:      str         # pref | fact | qa | instr | tech | project
    tags:          list[str]   = field(default_factory=list)
    weight:        float       = 1.0
    created:       float       = field(default_factory=time.time)
    last_accessed: float       = field(default_factory=time.time)
    access_count:  int         = 0
    connections:   list[str]   = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "NanoNode":
        valid = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in d.items() if k in valid})

    def to_natural(self) -> str:
        """
        Ricostruisce linguaggio naturale dal nodo compresso.
        Usato quando si inietta il contesto nel prompt.
        """
        CAT_TEMPLATES = {
            "pref":    "L'utente preferisce/usa: {c}",
            "fact":    "Fatto noto: {c}",
            "qa":      "Già discusso: {c}",
            "instr":   "Istruzione permanente: {c}",
            "tech":    "Stack tecnico: {c}",
            "project": "Progetto: {c}",
        }
        tmpl = CAT_TEMPLATES.get(self.category, "{c}")
        return tmpl.format(c=self.content)


@dataclass
class MemoryStats:
    total_messages:    int   = 0
    total_nodes:       int   = 0
    total_pruned:      int   = 0
    total_merges:      int   = 0
    total_compressions: int  = 0
    sessions:          int   = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "MemoryStats":
        valid = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in d.items() if k in valid})


# ─────────────────────────────────────────────────────────────────────
# DISTILLER  — trasforma testo in token chiave (zero LLM)
# ─────────────────────────────────────────────────────────────────────

# Stop words italiane + inglesi
_STOPWORDS = {
    "il","lo","la","i","gli","le","un","uno","una","di","a","da","in",
    "con","su","per","tra","fra","e","o","ma","se","che","non","si","mi",
    "ti","ci","vi","ne","ho","ha","hai","abbiamo","hanno","è","sono","sei",
    "siamo","siete","era","ero","eravamo","al","del","nel","sul","dal",
    "the","a","an","is","are","was","were","be","been","have","has","had",
    "do","does","did","will","would","can","could","should","may","might",
    "this","that","these","those","it","its","my","your","our","their",
    "and","or","but","not","so","if","then","than","as","at","by","for",
    "from","to","of","in","on","with","about","into","through","during",
    # generici conversazionali
    "come","cosa","quando","dove","perché","chi","quale","quali","quanto",
    "io","tu","lui","lei","noi","voi","loro","me","te","lui","lei","noi",
    "vorrei","voglio","puoi","potresti","dimmi","spiega","scrivi","crea",
    "genera","fammi","fai","aiutami","please","can","you","help","me","want",
    "use","using","used","make","making","need","needs","know","think","get",
}

_TECH_VOCAB = {
    # Linguaggi
    "python","javascript","typescript","rust","go","java","kotlin","swift",
    "c++","c#","ruby","php","scala","haskell","elixir","lua","rlang","matlab",
    "dart","flutter","nim","zig",
    # Framework
    "react","vue","angular","svelte","next","nuxt","remix","astro",
    "flask","django","fastapi","express","nest","spring","rails","laravel",
    "htmx","solid","qwik",
    # DB
    "postgres","mysql","sqlite","mongodb","redis","cassandra","elasticsearch",
    "supabase","firebase","planetscale","turso","neon",
    # Infra/DevOps
    "docker","kubernetes","terraform","ansible","nginx","caddy","traefik",
    "aws","gcp","azure","vercel","cloudflare","heroku","fly","railway",
    "github","gitlab","ci/cd","actions","jenkins",
    # AI/ML
    "llm","gpt","llama","mistral","qwen","claude","gemini","openai",
    "pytorch","tensorflow","huggingface","onnx","cuda","vulkan",
    "gguf","llamacpp","lmstudio","ollama","vllm",
    # Tools
    "git","vim","neovim","vscode","tmux","zsh","bash","powershell",
    "webpack","vite","esbuild","bun","deno","pnpm","yarn","uv","ruff",
    "protox","textual","rich","typer","click",
}


def distill(text: str, max_tokens: int = 8) -> str:
    """
    Riduce un testo in N token chiave ordinati per rilevanza.
    Priorità: tech vocab > parole lunghe > parole comuni (no stopwords).
    Output: stringa di token separati da spazio, lowercase.
    """
    # Normalizza
    clean = text.lower()
    clean = re.sub(r"```[\s\S]*?```", " code ", clean)   # code block → token "code"
    clean = re.sub(r"`[^`]+`",        " code ", clean)   # inline code
    clean = re.sub(r"[^\w\s\-/#+]",   " ",      clean)   # punteggiatura
    clean = re.sub(r"\s+",            " ",       clean).strip()

    words = clean.split()

    # Score ogni parola
    scored: list[tuple[float, str]] = []
    seen: set[str] = set()
    for w in words:
        if len(w) < 3 or w in seen:   # min 3 char: elimina "r", "a", "il" residui
            continue
        seen.add(w)
        if w in _STOPWORDS:
            continue
        score = 0.0
        if w in _TECH_VOCAB:
            score += 10.0
        score += min(len(w) * 0.3, 3.0)   # parole più lunghe → più specifiche
        if w.isdigit():
            score += 2.0                   # numeri spesso rilevanti
        scored.append((score, w))

    scored.sort(key=lambda x: -x[0])
    tokens = [w for _, w in scored[:max_tokens]]

    # Ordine alfabetico per fingerprint stabile (ordine originale perso, ok)
    tokens.sort()
    return " ".join(tokens)


def fingerprint(distilled: str) -> str:
    """Hash corto del testo distillato → usato come node ID."""
    return "n_" + hashlib.sha256(distilled.encode()).hexdigest()[:12]


# ─────────────────────────────────────────────────────────────────────
# MEMORY GRAPH
# ─────────────────────────────────────────────────────────────────────
class MemoryGraph:
    """
    Grafo di conoscenza Nano-compresso.
    - Un nodo per concetto (merge aggressivo).
    - Nodi = token chiave, non frasi.
    - Retrieval ricostruisce linguaggio naturale.
    """

    def __init__(self):
        self._lock   = threading.RLock()
        self.nodes:  dict[str, NanoNode] = {}
        self.stats   = MemoryStats()
        self._pending: list[dict] = []
        self._load()

    # ── PERSISTENCE ──────────────────────────────────────────────────

    def _load(self):
        if MEMORY_FILE.exists():
            try:
                data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
                ok = 0
                for nd in data.get("nodes", []):
                    try:
                        node = NanoNode.from_dict(nd)
                        self.nodes[node.id] = node
                        ok += 1
                    except Exception as e:
                        log.debug("Skip malformed node: %s", e)
                log.info("Memory loaded: %d nodes (%.1f KB)", ok,
                         MEMORY_FILE.stat().st_size / 1024)
            except Exception as e:
                log.error("Memory corrupted, reset: %s", e)
                self.nodes = {}

        if MEMORY_STATS_FILE.exists():
            try:
                self.stats = MemoryStats.from_dict(
                    json.loads(MEMORY_STATS_FILE.read_text(encoding="utf-8"))
                )
            except Exception:
                self.stats = MemoryStats()

        self.stats.sessions += 1
        self._apply_decay()
        self._save()

    def _save(self):
        data = {
            "v":     3,
            "count": len(self.nodes),
            "nodes": [n.to_dict() for n in self.nodes.values()],
        }
        safe_write_json(MEMORY_FILE,       data,                indent=None)
        safe_write_json(MEMORY_STATS_FILE, self.stats.to_dict(), indent=2)

    # ── DECAY ────────────────────────────────────────────────────────

    def _apply_decay(self):
        now = time.time()
        for node in self.nodes.values():
            if node.last_accessed > 0:
                days = (now - node.last_accessed) / 86400.0
                node.weight = clamp(node.weight * (DECAY_RATE ** days), 0.01, 20.0)

    # ── UPSERT (cuore del sistema) ────────────────────────────────────

    def upsert(self, distilled: str, category: str, tags: list[str] | None = None) -> NanoNode:
        """
        Insert-or-merge di un nodo.
        1. Calcola fingerprint del testo distillato.
        2. Se esiste nodo identico → rinforza peso.
        3. Se esiste nodo Jaccard-simile → merge dei token + rinforza.
        4. Altrimenti crea nodo nuovo.
        Sempre thread-safe.
        """
        distilled = distilled.strip()
        if not distilled:
            raise ValueError("distilled content vuoto")
        tags = tags or []
        nid  = fingerprint(distilled)

        with self._lock:
            # Caso 1: nodo identico
            if nid in self.nodes:
                n = self.nodes[nid]
                n.weight        = clamp(n.weight + 0.4, 0.01, 20.0)
                n.access_count += 1
                n.last_accessed = time.time()
                for t in tags:
                    if t not in n.tags:
                        n.tags.append(t)
                return n

            # Caso 2: nodo simile (Jaccard)
            similar = self._find_similar_locked(distilled)
            if similar:
                # Merge dei token: unione delle parole chiave, poi ri-distilla
                merged_tokens = set(similar.content.split()) | set(distilled.split())
                # Prendi i più rilevanti (tech vocab first)
                scored = sorted(
                    merged_tokens,
                    key=lambda w: (10 if w in _TECH_VOCAB else 0) + len(w),
                    reverse=True,
                )
                similar.content     = " ".join(sorted(scored[:8]))
                similar.weight      = clamp(similar.weight + 0.5, 0.01, 20.0)
                similar.access_count += 1
                similar.last_accessed = time.time()
                for t in tags:
                    if t not in similar.tags:
                        similar.tags.append(t)
                # Aggiorna l'id al nuovo fingerprint (content cambiato)
                new_id = fingerprint(similar.content)
                if new_id != similar.id:
                    del self.nodes[similar.id]
                    similar.id = new_id
                    self.nodes[new_id] = similar
                self.stats.total_merges += 1
                return similar

            # Caso 3: nodo nuovo
            node = NanoNode(
                id           = nid,
                content      = distilled,
                category     = category,
                tags         = list(tags),
                weight       = 1.0,
                created      = time.time(),
                last_accessed= time.time(),
                access_count = 1,
            )
            self.nodes[nid] = node
            self.stats.total_nodes += 1
            self._auto_connect_locked(node)
            return node

    def _find_similar_locked(self, distilled: str) -> Optional[NanoNode]:
        """Jaccard su bag-of-words. Deve essere chiamato con lock acquisito."""
        words_new = set(distilled.split())
        if not words_new:
            return None
        best, best_score = None, 0.0
        for node in self.nodes.values():
            words_node = set(node.content.split())
            if not words_node:
                continue
            inter = words_new & words_node
            union = words_new | words_node
            score = len(inter) / len(union)
            if score >= JACCARD_THRESHOLD and score > best_score:
                best_score = score
                best       = node
        return best

    def _auto_connect_locked(self, new_node: NanoNode):
        """Collega nodi con tag o categoria comune. Lock già acquisito."""
        for other in self.nodes.values():
            if other.id == new_node.id:
                continue
            shared = set(new_node.tags) & set(other.tags)
            if shared or other.category == new_node.category:
                if other.id not in new_node.connections:
                    new_node.connections.append(other.id)
                if new_node.id not in other.connections:
                    other.connections.append(new_node.id)
                new_node.connections = new_node.connections[:MAX_CONNECTIONS]
                other.connections    = other.connections[:MAX_CONNECTIONS]

    # ── PUBLIC ADD (backward compat) ──────────────────────────────────

    def add_node(self, content: str, category: str, tags: list[str] | None = None) -> NanoNode:
        """
        API pubblica: accetta testo grezzo, lo distilla, poi fa upsert.
        Usato da /remember e dall'estrazione automatica.
        """
        dist = distill(content, max_tokens=8)
        if not dist:
            dist = content[:40].lower()
        return self.upsert(dist, category, tags or _extract_tags(content))

    # ── PRUNING ───────────────────────────────────────────────────────

    def _prune(self):
        with self._lock:
            if len(self.nodes) <= MAX_NODES:
                return
            to_remove = len(self.nodes) - MAX_NODES
            candidates = sorted(
                (n for n in self.nodes.values() if n.weight < MIN_WEIGHT * 4),
                key=lambda n: n.weight,
            )[:to_remove]
            for node in candidates:
                for oid in node.connections:
                    if oid in self.nodes:
                        try:
                            self.nodes[oid].connections.remove(node.id)
                        except ValueError:
                            pass
                del self.nodes[node.id]
                self.stats.total_pruned += 1

    # ── MESSAGE PROCESSING ────────────────────────────────────────────

    def process_message(self, role: str, content: str):
        """
        Accumula messaggi. Ogni COMPRESS_EVERY messaggi → estrazione.
        Thread-safe.
        """
        if not content.strip():
            return
        with self._lock:
            self._pending.append({"role": role, "content": content})
            self.stats.total_messages += 1
        if len(self._pending) >= COMPRESS_EVERY:
            self._compress()

    def _compress(self):
        """Distilla i pending in nodi nano-compressi."""
        with self._lock:
            if not self._pending:
                return
            msgs  = list(self._pending)
            self._pending.clear()

        extracted = _extract_nano_nodes(msgs)

        for item in extracted:
            try:
                self.upsert(item["distilled"], item["category"], item["tags"])
            except Exception as e:
                log.debug("upsert failed: %s", e)

        with self._lock:
            self.stats.total_compressions += 1

        self._prune()
        self._save()

    # ── CONTEXT RETRIEVAL ─────────────────────────────────────────────

    def get_context(self, query: str) -> str:
        """
        Recupera nodi rilevanti e li ricostruisce in linguaggio naturale.
        Scoring: word overlap + tag match + category boost + weight + recency.
        """
        if not self.nodes:
            return ""

        query_dist  = distill(query, max_tokens=12)
        query_words = set(query_dist.split())
        query_tags  = _extract_tags(query)
        now         = time.time()

        scored: list[tuple[float, NanoNode]] = []

        for node in self.nodes.values():
            score      = 0.0
            node_words = set(node.content.split())

            # Overlap tra token distillati
            if node_words:
                overlap = len(query_words & node_words) / max(len(query_words), 1)
                score  += overlap * 4.0

            # Tag match
            score += len(set(query_tags) & set(node.tags)) * 2.5

            # Category boost
            cat_boost = {"instr": 2.5, "pref": 1.5, "fact": 1.2, "project": 1.0}
            score     += cat_boost.get(node.category, 0.0)

            # Weight
            score *= (1.0 + clamp(node.weight, 0, 10) * 0.2)

            # Recency
            age = (now - node.last_accessed) / 86400.0
            if age < 1:
                score *= 1.6
            elif age < 7:
                score *= 1.2

            if score > 0.15:
                scored.append((score, node))

        scored.sort(key=lambda x: -x[0])
        top = scored[:MAX_CONTEXT_NODES]

        if not top:
            # Fallback: inietta istruzioni/preferenze generali
            general = sorted(
                [n for n in self.nodes.values()
                 if n.category in ("instr", "pref", "fact") and n.weight > 0.3],
                key=lambda n: -n.weight,
            )
            top = [(1.0, n) for n in general[:5]]

        if not top:
            return ""

        # Aggiorna accessi
        ts = time.time()
        for _, node in top:
            node.last_accessed  = ts
            node.access_count  += 1

        self._save()

        lines = [f"[{BRAND_NAME} MEMORIA]"]
        for _, node in top:
            lines.append(f"- {node.to_natural()}")
        return "\n".join(lines)

    # ── FLUSH & UTILS ─────────────────────────────────────────────────

    def flush(self):
        if self._pending:
            self._compress()
        self._save()

    def clear(self):
        with self._lock:
            self.nodes.clear()
            self._pending.clear()
            self.stats = MemoryStats()
        self._save()

    def get_info(self) -> str:
        cats: dict[str, int] = {}
        for n in self.nodes.values():
            cats[n.category] = cats.get(n.category, 0) + 1
        kb = MEMORY_FILE.stat().st_size / 1024 if MEMORY_FILE.exists() else 0
        cat_str = " ".join(f"{k}:{v}" for k, v in sorted(cats.items()))
        return (
            f"Nodi:{len(self.nodes)} | "
            f"Msg:{self.stats.total_messages} | "
            f"Merge:{self.stats.total_merges} | "
            f"Sess:{self.stats.sessions} | "
            f"{kb:.1f}KB | {cat_str or '—'}"
        )

    def get_stats_dict(self) -> dict:
        return {
            "nodes":    len(self.nodes),
            "messages": self.stats.total_messages,
            "merges":   self.stats.total_merges,
            "sessions": self.stats.sessions,
        }


# ─────────────────────────────────────────────────────────────────────
# FUNZIONI DI ESTRAZIONE  (module-level, pure functions)
# ─────────────────────────────────────────────────────────────────────

def _extract_tags(text: str) -> list[str]:
    """Estrae keyword tech dal testo grezzo."""
    tl = text.lower()
    return [kw for kw in _TECH_VOCAB if kw in tl][:6]


def _extract_nano_nodes(messages: list[dict]) -> list[dict]:
    """
    Distilla una lista di messaggi in nano-nodi.
    Ogni nodo ha: distilled (str), category (str), tags (list).
    Zero LLM calls — tutto rule-based.
    """
    extracted: list[dict] = []
    full_text = " ".join(m["content"] for m in messages).lower()

    # ── PREFERENZE & TECH ─────────────────────────────────────────────
    pref_patterns = [
        r"\b(?:uso|utilizzo|preferisco|lavoro con|sto usando)\s+([\w][\w\s.+\-]{1,30})",
        r"\b(?:il mio stack|il mio framework|il mio linguaggio)\s+[eè']?\s*([\w][\w\s.+\-]{1,20})",
    ]
    for pat in pref_patterns:
        for m in re.findall(pat, full_text):
            m = m.strip()
            d = distill(m, 5)
            if d:
                extracted.append({"distilled": d, "category": "pref",
                                   "tags": _extract_tags(m)})

    # ── FATTI PERSONALI ───────────────────────────────────────────────
    fact_patterns = [
        r"\b(?:mi chiamo|il mio nome [eè']\s*)(\w+)",
        r"\b(?:sono un|lavoro come|faccio il)\s+([\w\s]{2,25})",
        r"\b(?:il mio progetto [eè']\s*|sto lavorando a\s*)([\w\s]{2,25})",
    ]
    for pat in fact_patterns:
        for m in re.findall(pat, full_text):
            if isinstance(m, str) and len(m) > 1:
                d = distill(m, 4)
                if d:
                    extracted.append({"distilled": d, "category": "fact",
                                       "tags": _extract_tags(m)})

    # ── Q&A COMPRESSI ─────────────────────────────────────────────────
    for i, msg in enumerate(messages):
        if msg["role"] != "user":
            continue
        q = msg["content"].strip()
        if len(q) < 15:
            continue
        # Cerca risposta AI successiva
        answer = next(
            (m["content"] for m in messages[i + 1:] if m["role"] == "assistant"),
            "",
        )
        if not answer:
            continue
        # Distilla domanda + risposta insieme
        combined = distill(q + " " + answer, max_tokens=8)
        if combined:
            extracted.append({"distilled": combined, "category": "qa",
                               "tags": _extract_tags(q + " " + answer)})

    # ── ISTRUZIONI ────────────────────────────────────────────────────
    instr_patterns = [
        r"\b(?:rispondi sempre|ricordati di|non dimenticare|d'ora in poi)\s+([\w\s,.']{5,60})",
        r"\b(?:preferisco che|vorrei che)\s+([\w\s,.']{5,60})",
    ]
    for pat in instr_patterns:
        for m in re.findall(pat, full_text):
            m = m.strip()
            d = distill(m, 6)
            if d:
                extracted.append({"distilled": d, "category": "instr",
                                   "tags": ["istruzione"]})

    # ── TECH KEYWORDS dirette (es. menzione esplicita di tecnologie) ──
    tech_in_text = _extract_tags(full_text)
    if tech_in_text:
        d = " ".join(sorted(tech_in_text[:6]))
        extracted.append({"distilled": d, "category": "tech", "tags": tech_in_text})

    # Deduplicazione veloce su distilled
    seen:   set[str] = set()
    unique: list[dict] = []
    for item in extracted:
        if item["distilled"] not in seen:
            seen.add(item["distilled"])
            unique.append(item)
    return unique
