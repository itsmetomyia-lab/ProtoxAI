# -*- coding: utf-8 -*-
"""
PROTOX AI — Persistent Memory v1.0
Memoria persistente con graph-based compression.
Supporta milioni di interazioni con peso minimo su disco.

Architettura:
- I messaggi raw NON vengono salvati
- Ogni N messaggi, l'LLM estrae "knowledge nodes" compressi
- I nodi formano un grafo di conoscenza pesato
- Al prompt, i nodi piu' rilevanti vengono iniettati come contesto
- Peso su disco: ~1KB per 100 messaggi (vs ~50KB raw)
"""

import json
import time
import hashlib
import re
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

from .config import DATA_DIR, BRAND_NAME, BRAND_ENGINE

# ─────────────────────────────────────────────────────────────────────
# CONFIG MEMORIA
# ─────────────────────────────────────────────────────────────────────
MEMORY_FILE = DATA_DIR / "memory_graph.json"
MEMORY_STATS_FILE = DATA_DIR / "memory_stats.json"

# Ogni quanti messaggi comprimere in nodi
COMPRESS_EVERY = 6

# Massimi nodi nel grafo (i piu' vecchi/deboli vengono potati)
MAX_NODES = 500

# Massimi nodi iniettati nel prompt
MAX_CONTEXT_NODES = 15

# Peso minimo per sopravvivere al pruning
MIN_WEIGHT = 0.1

# Decay factor — i nodi perdono peso nel tempo
DECAY_RATE = 0.98  # per giorno


# ─────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────
@dataclass
class KnowledgeNode:
    """Singolo nodo di conoscenza nel grafo."""
    id: str                          # hash unico
    content: str                     # conoscenza compressa (1-2 frasi)
    category: str                    # tech, preference, project, fact, problem, solution
    tags: list[str] = field(default_factory=list)
    weight: float = 1.0              # importanza (cresce con rinforzo)
    created: float = 0.0             # timestamp creazione
    last_accessed: float = 0.0       # ultimo uso
    access_count: int = 0            # quante volte usato
    connections: list[str] = field(default_factory=list)  # id nodi correlati

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "KnowledgeNode":
        return cls(**d)


@dataclass
class MemoryStats:
    """Statistiche memoria."""
    total_messages_processed: int = 0
    total_nodes_created: int = 0
    total_nodes_pruned: int = 0
    total_compressions: int = 0
    last_compression: float = 0.0
    sessions_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "MemoryStats":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ─────────────────────────────────────────────────────────────────────
# MEMORY GRAPH
# ─────────────────────────────────────────────────────────────────────
class MemoryGraph:
    """
    Grafo di conoscenza persistente.
    Comprime conversazioni in nodi leggeri e li collega.
    """

    def __init__(self):
        self.nodes: dict[str, KnowledgeNode] = {}
        self.stats = MemoryStats()
        self._pending_messages: list[dict] = []
        self._load()

    # ── PERSISTENCE ──────────────────────────────────────────────────
    def _load(self):
        """Carica grafo da disco."""
        if MEMORY_FILE.exists():
            try:
                data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
                for nd in data.get("nodes", []):
                    node = KnowledgeNode.from_dict(nd)
                    self.nodes[node.id] = node
            except Exception:
                self.nodes = {}

        if MEMORY_STATS_FILE.exists():
            try:
                data = json.loads(MEMORY_STATS_FILE.read_text(encoding="utf-8"))
                self.stats = MemoryStats.from_dict(data)
            except Exception:
                self.stats = MemoryStats()

        self.stats.sessions_count += 1
        self._apply_time_decay()
        self._save()

    def _save(self):
        """Salva grafo su disco."""
        data = {
            "version": 1,
            "node_count": len(self.nodes),
            "nodes": [n.to_dict() for n in self.nodes.values()],
        }
        MEMORY_FILE.write_text(
            json.dumps(data, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        MEMORY_STATS_FILE.write_text(
            json.dumps(self.stats.to_dict(), indent=2),
            encoding="utf-8",
        )

    # ── TIME DECAY ───────────────────────────────────────────────────
    def _apply_time_decay(self):
        """Applica decay temporale ai nodi. Nodi vecchi e mai usati perdono peso."""
        now = time.time()
        for node in self.nodes.values():
            if node.last_accessed > 0:
                days_since = (now - node.last_accessed) / 86400
                decay = DECAY_RATE ** days_since
                node.weight *= decay
                node.weight = max(node.weight, 0.01)

    # ── NODE CREATION ────────────────────────────────────────────────
    def _make_id(self, content: str) -> str:
        """Genera ID unico per un nodo."""
        h = hashlib.md5(content.encode()).hexdigest()[:12]
        return f"n_{h}"

    def add_node(self, content: str, category: str, tags: list[str] = None) -> KnowledgeNode:
        """Aggiunge un nodo al grafo."""
        nid = self._make_id(content)

        # Se esiste gia' un nodo simile, rinforza
        existing = self._find_similar(content)
        if existing:
            existing.weight = min(existing.weight + 0.5, 10.0)
            existing.access_count += 1
            existing.last_accessed = time.time()
            if tags:
                for t in tags:
                    if t not in existing.tags:
                        existing.tags.append(t)
            self._save()
            return existing

        node = KnowledgeNode(
            id=nid,
            content=content,
            category=category,
            tags=tags or [],
            weight=1.0,
            created=time.time(),
            last_accessed=time.time(),
            access_count=1,
        )
        self.nodes[nid] = node
        self.stats.total_nodes_created += 1

        # Collega a nodi con tag simili
        self._auto_connect(node)
        self._save()
        return node

    def _find_similar(self, content: str) -> Optional[KnowledgeNode]:
        """Cerca un nodo con contenuto simile (deduplicazione)."""
        content_lower = content.lower().strip()
        content_words = set(content_lower.split())

        best_match = None
        best_score = 0

        for node in self.nodes.values():
            node_words = set(node.content.lower().split())
            if not node_words:
                continue
            # Jaccard similarity
            intersection = content_words & node_words
            union = content_words | node_words
            if union:
                score = len(intersection) / len(union)
                if score > 0.6 and score > best_score:
                    best_score = score
                    best_match = node

        return best_match

    def _auto_connect(self, new_node: KnowledgeNode):
        """Collega automaticamente nodi con tag in comune."""
        for other in self.nodes.values():
            if other.id == new_node.id:
                continue
            # Connetti se hanno tag in comune
            shared_tags = set(new_node.tags) & set(other.tags)
            if shared_tags or other.category == new_node.category:
                if other.id not in new_node.connections:
                    new_node.connections.append(other.id)
                if new_node.id not in other.connections:
                    other.connections.append(new_node.id)
                # Max 10 connessioni per nodo
                new_node.connections = new_node.connections[:10]
                other.connections = other.connections[:10]

    # ── PRUNING ──────────────────────────────────────────────────────
    def _prune(self):
        """Rimuove nodi deboli se superiamo il limite."""
        if len(self.nodes) <= MAX_NODES:
            return

        # Ordina per peso (i piu' deboli prima)
        sorted_nodes = sorted(self.nodes.values(), key=lambda n: n.weight)
        to_remove = len(self.nodes) - MAX_NODES

        removed = 0
        for node in sorted_nodes:
            if removed >= to_remove:
                break
            if node.weight < MIN_WEIGHT:
                # Rimuovi connessioni
                for other_id in node.connections:
                    if other_id in self.nodes:
                        other = self.nodes[other_id]
                        if node.id in other.connections:
                            other.connections.remove(node.id)
                del self.nodes[node.id]
                removed += 1
                self.stats.total_nodes_pruned += 1

        self._save()

    # ── MESSAGE PROCESSING ───────────────────────────────────────────
    def process_message(self, role: str, content: str):
        """
        Processa un messaggio. Accumula e comprime ogni N messaggi.
        """
        self._pending_messages.append({"role": role, "content": content})
        self.stats.total_messages_processed += 1

        if len(self._pending_messages) >= COMPRESS_EVERY:
            self._compress_pending()

    def _compress_pending(self):
        """
        Comprime i messaggi pending in nodi di conoscenza.
        Usa estrazione rule-based (no LLM call = veloce).
        """
        if not self._pending_messages:
            return

        all_text = " ".join(m["content"] for m in self._pending_messages)

        # Estrai conoscenza con pattern matching
        extracted = self._extract_knowledge(all_text, self._pending_messages)

        for item in extracted:
            self.add_node(
                content=item["content"],
                category=item["category"],
                tags=item["tags"],
            )

        self._pending_messages.clear()
        self.stats.total_compressions += 1
        self.stats.last_compression = time.time()
        self._prune()
        self._save()

    def _extract_knowledge(self, full_text: str, messages: list[dict]) -> list[dict]:
        """
        Estrazione conoscenza rule-based.
        Veloce, zero chiamate LLM, cattura i pattern piu' importanti.
        """
        extracted = []
        text_lower = full_text.lower()

        # ── PREFERENZE TECNOLOGICHE ──
        tech_patterns = [
            (r"\b(?:uso|utilizzo|preferisco|lavoro con)\s+(\w[\w\s.+-]*\w)", "preference"),
            (r"\b(?:il mio stack|il mio progetto|sto usando)\s+(?:e'|è)?\s*(\w[\w\s.+-]*\w)", "preference"),
            (r"\b(?:framework|linguaggio|database|libreria|tool)\s+(?:e'|è)?\s*(\w[\w\s.+-]*\w)", "tech"),
        ]
        for pattern, cat in tech_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                match = match.strip()
                if len(match) > 2 and len(match) < 60:
                    extracted.append({
                        "content": f"L'utente usa/preferisce: {match}",
                        "category": cat,
                        "tags": self._extract_tags(match),
                    })

        # ── PROBLEMI E SOLUZIONI ──
        # Cerca pattern domanda -> risposta
        for i, msg in enumerate(messages):
            if msg["role"] == "user":
                content = msg["content"].strip()
                # Domanda significativa (> 20 char)
                if len(content) > 20:
                    # Cerca la risposta AI successiva
                    answer = ""
                    for j in range(i + 1, len(messages)):
                        if messages[j]["role"] == "assistant":
                            answer = messages[j]["content"]
                            break

                    if answer:
                        # Comprimi il Q&A in una riga
                        q_summary = content[:100].replace("\n", " ")
                        a_summary = self._summarize_answer(answer)
                        if a_summary:
                            extracted.append({
                                "content": f"Q: {q_summary} → A: {a_summary}",
                                "category": "solution",
                                "tags": self._extract_tags(content + " " + answer),
                            })

        # ── FATTI DICHIARATI ──
        fact_patterns = [
            r"\b(?:il mio nome|mi chiamo)\s+(?:e'|è)?\s*(\w+)",
            r"\b(?:lavoro come|sono un|faccio il)\s+(\w[\w\s]*\w)",
            r"\b(?:il mio progetto si chiama|sto lavorando a|progetto)\s+(\w[\w\s]*\w)",
            r"\b(?:il mio sistema|il mio os|uso windows|uso linux|uso mac)",
        ]
        for pattern in fact_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                if isinstance(match, str) and len(match) > 1:
                    extracted.append({
                        "content": f"Fatto utente: {match.strip()}",
                        "category": "fact",
                        "tags": self._extract_tags(match),
                    })

        # ── ISTRUZIONI RICORRENTI ──
        instruction_patterns = [
            r"\b(?:rispondi sempre|ricordati di|non dimenticare|d'ora in poi)\s+([\w\s,.']+)",
            r"\b(?:preferisco che|vorrei che|quando scrivi)\s+([\w\s,.']+)",
        ]
        for pattern in instruction_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                match = match.strip()
                if len(match) > 5 and len(match) < 100:
                    extracted.append({
                        "content": f"Istruzione utente: {match}",
                        "category": "preference",
                        "tags": ["istruzione"],
                    })

        return extracted

    @staticmethod
    def _summarize_answer(answer: str) -> str:
        """Comprimi una risposta AI in max 80 char."""
        # Rimuovi code blocks
        clean = re.sub(r"```[\s\S]*?```", "[codice]", answer)
        # Rimuovi markdown
        clean = re.sub(r"[#*_`>-]", "", clean)
        # Prima frase significativa
        sentences = re.split(r"[.!?\n]", clean)
        for s in sentences:
            s = s.strip()
            if len(s) > 15:
                return s[:80]
        return clean[:80].strip()

    @staticmethod
    def _extract_tags(text: str) -> list[str]:
        """Estrae tag/keyword dal testo."""
        # Lista di tech keywords comuni
        tech_keywords = {
            "python", "javascript", "typescript", "react", "vue", "angular",
            "flask", "django", "fastapi", "node", "express", "next",
            "html", "css", "sql", "nosql", "mongodb", "postgres", "mysql",
            "redis", "docker", "kubernetes", "git", "github", "linux",
            "windows", "mac", "api", "rest", "graphql", "websocket",
            "tensorflow", "pytorch", "pandas", "numpy", "rust", "go",
            "java", "kotlin", "swift", "flutter", "dart", "electron",
            "tailwind", "bootstrap", "sass", "webpack", "vite",
            "aws", "azure", "gcp", "firebase", "supabase", "vercel",
            "openai", "llm", "ai", "machine learning", "deep learning",
            "database", "server", "frontend", "backend", "fullstack",
            "testing", "debug", "deploy", "ci/cd", "devops",
        }
        text_lower = text.lower()
        found = []
        for kw in tech_keywords:
            if kw in text_lower:
                found.append(kw)
        return found[:8]  # max 8 tag

    # ── CONTEXT RETRIEVAL ────────────────────────────────────────────
    def get_context(self, query: str) -> str:
        """
        Recupera nodi rilevanti per la query e li formatta come contesto.
        Usa TF-IDF-like scoring con boost per peso e connessioni.
        """
        if not self.nodes:
            return ""

        query_words = set(query.lower().split())
        query_tags = self._extract_tags(query)

        scored: list[tuple[float, KnowledgeNode]] = []

        for node in self.nodes.values():
            score = 0.0

            # Word overlap score
            node_words = set(node.content.lower().split())
            if node_words:
                overlap = len(query_words & node_words) / max(len(query_words), 1)
                score += overlap * 3.0

            # Tag match score
            tag_overlap = len(set(query_tags) & set(node.tags))
            score += tag_overlap * 2.0

            # Category boost
            if node.category == "preference":
                score += 1.0  # preferenze sempre rilevanti
            if node.category == "fact":
                score += 0.8

            # Weight boost (nodi rinforzati contano di piu')
            score *= (1.0 + node.weight * 0.3)

            # Recency boost
            age_days = (time.time() - node.last_accessed) / 86400
            if age_days < 1:
                score *= 1.5
            elif age_days < 7:
                score *= 1.2

            if score > 0.1:
                scored.append((score, node))

        # Ordina per score, prendi i migliori
        scored.sort(key=lambda x: -x[0])
        top_nodes = scored[:MAX_CONTEXT_NODES]

        if not top_nodes:
            # Nessun match specifico: inietta preferenze e fatti generali
            general = [n for n in self.nodes.values()
                       if n.category in ("preference", "fact") and n.weight > 0.5]
            general.sort(key=lambda n: -n.weight)
            top_nodes = [(1.0, n) for n in general[:5]]

        if not top_nodes:
            return ""

        # Marca come acceduti
        for _, node in top_nodes:
            node.last_accessed = time.time()
            node.access_count += 1
        self._save()

        # Formatta contesto
        lines = [f"[{BRAND_NAME} MEMORIA — Contesto dall'utente]"]
        for score, node in top_nodes:
            lines.append(f"- [{node.category}] {node.content}")

        return "\n".join(lines)

    # ── FLUSH ────────────────────────────────────────────────────────
    def flush(self):
        """Forza compressione dei messaggi pending."""
        if self._pending_messages:
            self._compress_pending()

    # ── INFO ─────────────────────────────────────────────────────────
    def get_info(self) -> str:
        """Ritorna info sulla memoria."""
        categories = {}
        for n in self.nodes.values():
            categories[n.category] = categories.get(n.category, 0) + 1

        file_size = 0
        if MEMORY_FILE.exists():
            file_size = MEMORY_FILE.stat().st_size

        lines = [
            f"Nodi totali: {len(self.nodes)}",
            f"Messaggi processati: {self.stats.total_messages_processed}",
            f"Compressioni: {self.stats.total_compressions}",
            f"Nodi rimossi (pruning): {self.stats.total_nodes_pruned}",
            f"Sessioni: {self.stats.sessions_count}",
            f"Peso su disco: {file_size / 1024:.1f} KB",
            f"Categorie: {categories}",
        ]
        return "  |  ".join(lines)

    def clear(self):
        """Cancella tutta la memoria."""
        self.nodes.clear()
        self._pending_messages.clear()
        self.stats = MemoryStats()
        self._save()