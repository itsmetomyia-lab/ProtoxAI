# -*- coding: utf-8 -*-
"""
PROTOX AI — Activation Steering v1.0
Controlla stile e comportamento del modello in tempo reale.

NOTA TECNICA:
Il vero activation steering modifica i tensori interni del modello.
Con llama-server non abbiamo accesso ai layer, quindi usiamo
"effective steering" via system prompt dinamico — risultato pratico
identico, zero overhead.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from .config import DATA_DIR

STEERING_FILE = DATA_DIR / "steering_state.json"


@dataclass
class SteeringConfig:
    """
    Configurazione steering. Ogni valore va da 0 a 100.
    50 = neutro, 0 = minimo, 100 = massimo.
    """
    formality:   int = 50   # 0=casual, 100=ultra-formale
    creativity:  int = 50   # 0=fattuale, 100=creativo
    conciseness: int = 50   # 0=prolisso, 100=telegrafico
    skepticism:  int = 50   # 0=accomodante, 100=critico
    technicality: int = 70  # 0=semplice, 100=tecnico avanzato
    confidence:  int = 50   # 0=dubbioso, 100=assertivo

    enabled: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SteeringConfig":
        valid_keys = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in d.items() if k in valid_keys})


class SteeringEngine:
    """Genera istruzioni dinamiche per il system prompt."""

    AXES = {
        "formality": {
            "name": "Formalità",
            "low":  "molto casual, usa slang tecnico, abbreviazioni, 'tipo', 'cmq', tono da amico developer",
            "mid":  "tono professionale ma rilassato, italiano corretto senza essere rigido",
            "high": "formale e rigoroso, sintassi precisa, niente colloquialismi, tono accademico",
        },
        "creativity": {
            "name": "Creatività",
            "low":  "STRETTAMENTE fattuale, solo informazioni verificate, nessuna speculazione, nessuna analogia, nessun esempio inventato",
            "mid":  "bilanciato tra fatti e spiegazioni con esempi pratici quando utili",
            "high": "esplora soluzioni alternative, usa analogie creative, proponi idee non convenzionali, pensa fuori dagli schemi",
        },
        "conciseness": {
            "name": "Concisione",
            "low":  "rispondi in modo esteso e dettagliato, espandi ogni concetto, includi contesto e sfumature",
            "mid":  "lunghezza bilanciata, dettagli quando servono, sintesi quando possibile",
            "high": "rispondi nel modo PIU' BREVE POSSIBILE. Una o due frasi. Nessun preambolo. Solo l'essenziale. Bullet point se proprio serve",
        },
        "skepticism": {
            "name": "Scetticismo",
            "low":  "assumi che l'utente abbia ragione, accomoda le sue idee, sii d'accordo quando possibile",
            "mid":  "valuta criticamente ma con rispetto, segnala problemi se evidenti",
            "high": "metti TUTTO in discussione, sfida le assunzioni dell'utente, identifica edge case, devil's advocate aggressivo, segnala anche piccoli problemi",
        },
        "technicality": {
            "name": "Tecnicismo",
            "low":  "spiega come a un principiante assoluto, evita gergo, usa analogie semplici",
            "mid":  "tecnico ma accessibile, spiega gli acronimi al primo uso",
            "high": "usa terminologia tecnica avanzata, assumi conoscenza approfondita, cita pattern/algoritmi/architetture per nome",
        },
        "confidence": {
            "name": "Confidenza",
            "low":  "usa hedging linguistico ('potrebbe', 'forse', 'in alcuni casi'), ammetti incertezza, suggerisci alternative",
            "mid":  "assertivo dove sai, prudente dove non sai",
            "high": "tono ASSERTIVO e DIRETTO, niente 'forse' o 'potrebbe', dai risposte definitive, comunica autorita'",
        },
    }

    def __init__(self):
        self.config = SteeringConfig()
        self._load()

    def _load(self):
        if STEERING_FILE.exists():
            try:
                data = json.loads(STEERING_FILE.read_text(encoding="utf-8"))
                self.config = SteeringConfig.from_dict(data)
            except Exception:
                self.config = SteeringConfig()

    def save(self):
        STEERING_FILE.write_text(
            json.dumps(self.config.to_dict(), indent=2),
            encoding="utf-8",
        )

    def set_axis(self, axis: str, value: int) -> bool:
        """Imposta un asse. Ritorna True se ok."""
        if axis not in self.AXES:
            return False
        value = max(0, min(100, value))
        setattr(self.config, axis, value)
        self.save()
        return True

    def reset(self):
        """Reset a valori neutri."""
        self.config = SteeringConfig()
        self.save()

    def toggle(self) -> bool:
        self.config.enabled = not self.config.enabled
        self.save()
        return self.config.enabled

    @staticmethod
    def _bucket(value: int) -> str:
        if value < 33:
            return "low"
        elif value > 66:
            return "high"
        return "mid"

    def build_instructions(self) -> str:
        """Genera istruzioni stilistiche da iniettare nel system prompt."""
        if not self.config.enabled:
            return ""

        # Identifica assi non neutri (significativamente diversi da 50)
        active = []
        for axis_key, axis_def in self.AXES.items():
            value = getattr(self.config, axis_key)
            # Solo se distante da neutro
            if abs(value - 50) >= 15:
                bucket = self._bucket(value)
                instruction = axis_def[bucket]
                active.append(f"- {axis_def['name']} ({value}/100): {instruction}")

        if not active:
            return ""

        return (
            "[STEERING ATTIVO — Modula la risposta secondo questi parametri:]\n"
            + "\n".join(active)
            + "\n[Fine steering]"
        )

    def get_state_summary(self) -> str:
        """Riassunto stato per UI."""
        if not self.config.enabled:
            return "Steering: OFF"

        lines = ["Steering: ON"]
        for axis_key, axis_def in self.AXES.items():
            value = getattr(self.config, axis_key)
            bar = self._bar(value)
            lines.append(f"  {axis_def['name']:14} {bar} {value:3}/100")
        return "\n".join(lines)

    @staticmethod
    def _bar(value: int, width: int = 10) -> str:
        """Barra di progresso ASCII."""
        filled = int((value / 100) * width)
        return "[" + "#" * filled + "-" * (width - filled) + "]"

    def parse_command(self, args: list[str]) -> str:
        """
        Parsa comando steering: /steer formality 80
        Ritorna messaggio di feedback.
        """
        if not args:
            return self.get_state_summary()

        first = args[0].lower()

        if first == "reset":
            self.reset()
            return "Steering resettato ai valori neutri (50/100)"

        if first in ("on", "enable"):
            self.config.enabled = True
            self.save()
            return "Steering: ON"

        if first in ("off", "disable"):
            self.config.enabled = False
            self.save()
            return "Steering: OFF"

        if first == "list":
            lines = ["Assi disponibili:"]
            for k, v in self.AXES.items():
                cur = getattr(self.config, k)
                lines.append(f"  {k:14} (attuale: {cur}/100) — {v['name']}")
            return "\n".join(lines)

        # /steer AXIS VALUE
        if len(args) < 2:
            return f"Uso: /steer {first} <0-100>  oppure  /steer list"

        # Match parziale dell'asse
        axis = None
        for key in self.AXES:
            if key.startswith(first):
                axis = key
                break
        if not axis:
            return f"Asse '{first}' non trovato. Usa /steer list"

        try:
            value = int(args[1])
        except ValueError:
            return f"Valore non valido: {args[1]} (serve numero 0-100)"

        self.set_axis(axis, value)
        return f"{self.AXES[axis]['name']} -> {value}/100\n{self.get_state_summary()}"