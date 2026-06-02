# -*- coding: utf-8 -*-
"""
PROTOX AI — Multi-Agent Internal Debate v1.0
Lo stesso modello assume ruoli diversi e fa un dibattito interno
prima di dare la risposta finale.

Zero VRAM extra: usa lo stesso server LLM con prompt diversi.
"""

import re
from typing import Optional, Callable

from .config import BRAND_NAME

# ─────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────
DEBATE_TIMEOUT_PER_AGENT = 60  # secondi
MAX_AGENT_TOKENS = 350         # ogni agente e' breve
MAX_JUDGE_TOKENS = 1500        # il giudice puo' essere lungo

# ─────────────────────────────────────────────────────────────────────
# AGENTS
# ─────────────────────────────────────────────────────────────────────
AGENTS = {
    "optimist": {
        "icon": "+",
        "name": "Optimist",
        "prompt": (
            f"Sei un agente OTTIMISTA all'interno di un sistema multi-agent.\n"
            f"Il tuo ruolo: trovare il PERCHE' SI, le opportunita', le soluzioni positive, i vantaggi.\n"
            f"NON dare la risposta finale all'utente. Stai contribuendo a un dibattito interno.\n"
            f"Rispondi in MAX 4-5 frasi concise, focus solo sul lato positivo/soluzione.\n"
            f"Inizia con: 'Lato positivo:'\n"
        ),
    },
    "skeptic": {
        "icon": "-",
        "name": "Skeptic",
        "prompt": (
            f"Sei un agente SCETTICO all'interno di un sistema multi-agent.\n"
            f"Il tuo ruolo: trovare il PERCHE' NO, i problemi, i rischi, gli edge case, le contraddizioni.\n"
            f"NON dare la risposta finale all'utente. Stai contribuendo a un dibattito interno.\n"
            f"Rispondi in MAX 4-5 frasi concise, focus solo su problemi/rischi.\n"
            f"Inizia con: 'Lato critico:'\n"
        ),
    },
    "pragmatist": {
        "icon": "=",
        "name": "Pragmatist",
        "prompt": (
            f"Sei un agente PRAGMATICO all'interno di un sistema multi-agent.\n"
            f"Il tuo ruolo: bilanciare, valutare trade-off concreti, cosa funziona NELLA PRATICA, contesto reale.\n"
            f"NON dare la risposta finale all'utente. Stai contribuendo a un dibattito interno.\n"
            f"Rispondi in MAX 4-5 frasi concise, focus sul trade-off pratico.\n"
            f"Inizia con: 'Lato pratico:'\n"
        ),
    },
}


# ─────────────────────────────────────────────────────────────────────
# DEBATE DETECTION — quando attivare il debate
# ─────────────────────────────────────────────────────────────────────
DEBATE_TRIGGERS = [
    # Decisioni
    r"\bdovrei\b",
    r"\bmeglio\s+(?:\w+\s+)?(?:o|oppure)\b",
    r"\b(?:e'|è)\s+meglio\b",
    r"\bconvien[ea]\b",
    r"\bvale\s+la\s+pena\b",
    r"\bcosa\s+(?:mi\s+)?consigli\b",
    r"\bquale\s+(?:scegliere|usare|prendere)\b",

    # Confronti
    r"\b(\w+)\s+(?:vs|contro|or)\s+(\w+)\b",
    r"\bdifferenz[ae]\s+(?:tra|fra)\b",
    r"\bconfront(?:o|are)\b",

    # Architettura/design
    r"\barchitettura\b",
    r"\bdesign\s+pattern\b",
    r"\bcome\s+strutturare\b",
    r"\bcome\s+(?:dovrei|posso)\s+(?:progettare|impostare|organizzare)\b",

    # Migration/refactor
    r"\bmigrare\s+(?:a|verso|da)\b",
    r"\briscrivere\s+in\b",
    r"\brefactor\b",
    r"\bsostituire\s+\w+\s+con\b",

    # Domande aperte di valutazione
    r"\bperch(?:e'|è)\s+(?:dovrei|usare|scegliere)\b",
    r"\bha\s+senso\b",
    r"\bsensato\b",
]


def should_debate(text: str) -> bool:
    """Decide se attivare il debate mode."""
    text_lower = text.lower().strip()

    # Troppo corto = no debate
    if len(text) < 15:
        return False

    # Comandi codifica = no debate
    if re.match(r"^\s*(?:scrivi|crea|fai|genera|fammi|implementa|debug|fix)\b", text_lower):
        return False

    # Domande fattuali semplici = no debate
    if re.match(r"^\s*(?:cos'?(?:e'|è)|che\s+(?:cos'?)?(?:e'|è)|chi\s+(?:e'|è))\b", text_lower):
        return False

    # Match trigger
    for pattern in DEBATE_TRIGGERS:
        if re.search(pattern, text_lower):
            return True

    return False


# ─────────────────────────────────────────────────────────────────────
# DEBATE ENGINE
# ─────────────────────────────────────────────────────────────────────
class DebateEngine:
    """
    Orchestra un dibattito multi-agent usando lo stesso LLM.
    Stesso modello in VRAM, solo prompt diversi -> ZERO overhead di memoria.

    Modalità:
    - "off":   mai attivo
    - "auto":  attivo solo su domande di decisione (trigger pattern)
    - "force": SEMPRE attivo per ogni messaggio
    """

    def __init__(self, client, model_name: str):
        self.client = client
        self.model_name = model_name
        self.mode: str = "auto"   # off | auto | force

    @property
    def enabled(self) -> bool:
        """Compatibilita' con vecchio codice."""
        return self.mode != "off"

    @enabled.setter
    def enabled(self, value: bool):
        """Compatibilita' con vecchio codice."""
        self.mode = "auto" if value else "off"

    def set_mode(self, mode: str) -> str:
        """Imposta la modalita'. Ritorna messaggio di feedback."""
        mode = mode.lower().strip()
        if mode in ("off", "no", "disable"):
            self.mode = "off"
            return "Debate Mode: OFF (mai attivo)"
        elif mode in ("auto", "smart"):
            self.mode = "auto"
            return "Debate Mode: AUTO (attivo solo su domande di decisione)"
        elif mode in ("on", "force", "always", "all"):
            self.mode = "force"
            return "Debate Mode: FORCE (attivo SEMPRE, per ogni messaggio)"
        else:
            return f"Modalita' sconosciuta: {mode}. Usa: off | auto | force"

    def toggle(self) -> str:
        """Cicla tra off -> auto -> force -> off."""
        cycle = {"off": "auto", "auto": "force", "force": "off"}
        self.mode = cycle.get(self.mode, "auto")
        return self.get_status()

    def get_status(self) -> str:
        """Stato attuale formattato."""
        descriptions = {
            "off":   "OFF (mai attivo)",
            "auto":  "AUTO (solo su domande di decisione)",
            "force": "FORCE (SEMPRE attivo)",
        }
        return f"Debate Mode: {descriptions.get(self.mode, self.mode.upper())}"

    def should_run(self, user_msg: str) -> bool:
        """
        Decide se attivare il debate per questo messaggio.
        - off: mai
        - force: sempre
        - auto: solo se matcha i trigger
        """
        if self.mode == "off":
            return False
        if self.mode == "force":
            return True
        # auto
        return should_debate(user_msg)

    def _call_agent(self, agent_key: str, user_question: str,
                    extra_context: str = "") -> str:
        """Chiama un singolo agente (non-streaming, veloce)."""
        agent = AGENTS[agent_key]

        messages = [
            {"role": "system", "content": agent["prompt"]},
        ]
        if extra_context:
            messages.append({"role": "system", "content": extra_context})
        messages.append({
            "role": "user",
            "content": f"Domanda da analizzare dal tuo punto di vista:\n\n{user_question}"
        })

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.8,
                max_tokens=MAX_AGENT_TOKENS,
                stream=False,
                timeout=DEBATE_TIMEOUT_PER_AGENT,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[{agent['name']} non ha risposto: {e}]"

    def run_debate(self, user_question: str,
                   extra_context: str = "",
                   on_progress: Optional[Callable] = None) -> dict:
        """Esegue il dibattito completo."""
        agent_responses = {}

        for i, agent_key in enumerate(("optimist", "skeptic", "pragmatist"), 1):
            agent = AGENTS[agent_key]
            if on_progress:
                on_progress(
                    "agent",
                    f"[{i}/3] {agent['name']} sta ragionando..."
                )

            response = self._call_agent(agent_key, user_question, extra_context)
            agent_responses[agent_key] = response

        if on_progress:
            on_progress("synth", "Sintesi finale in corso...")

        judge_context = self._build_judge_context(agent_responses)

        return {
            "agents": agent_responses,
            "judge_context": judge_context,
        }

    def _build_judge_context(self, responses: dict) -> str:
        """Formatta le risposte degli agenti come contesto per il giudice finale."""
        parts = [
            "[DIBATTITO INTERNO MULTI-AGENT — Hai gia' analizzato la domanda da 3 prospettive:]",
            "",
        ]
        for agent_key in ("optimist", "skeptic", "pragmatist"):
            agent = AGENTS[agent_key]
            response = responses.get(agent_key, "[nessuna risposta]")
            parts.append(f"### {agent['name'].upper()}")
            parts.append(response)
            parts.append("")

        parts.append("[ISTRUZIONI PER LA RISPOSTA FINALE:]")
        parts.append(
            "Ora sei il GIUDICE SINTETIZZATORE. Usa le 3 prospettive sopra "
            "per dare una risposta finale BILANCIATA, COMPLETA e DECISIONALE all'utente. "
            "NON menzionare il dibattito interno o gli agenti. "
            "Integra le considerazioni in un'unica risposta coerente. "
            "Se i punti di vista sono in conflitto, prendi una posizione chiara e motivala. "
            "Usa markdown ben strutturato (titoli, bullet, esempi quando utili)."
        )
        parts.append("[Fine istruzioni dibattito]")
        return "\n".join(parts)