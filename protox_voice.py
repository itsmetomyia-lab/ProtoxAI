# -*- coding: utf-8 -*-
"""
PROTOX AI // Voice Module v1.1.0
Voce maschile, comandi tutti in italiano, riconoscimento migliorato.

Requisiti:
    pip install openai sounddevice numpy pyttsx3 vosk
"""

import sys
import json
import queue
import threading
import time
import os
import re
from pathlib import Path

import numpy as np
import sounddevice as sd
import pyttsx3
from vosk import Model, KaldiRecognizer
from openai import OpenAI

# ─────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 1234
BRAND_NAME = "PROTOX"
BRAND_ENGINE = "NeuralCore"

VOSK_MODEL_DIR = Path("protox_data") / "vosk-model-small-it-0.22"

# Audio
SAMPLE_RATE = 16000
BLOCK_SIZE = 8000
SILENCE_TIMEOUT = 2.5       # un po' piu' lungo per frasi complesse
SILENCE_THRESHOLD = 250      # leggermente piu' sensibile

# TTS — voce maschile
TTS_RATE = 160               # un po' piu' lento = piu' chiaro
TTS_VOLUME = 1.0


# ─────────────────────────────────────────────────────────────────────
# COLORI TERMINALE
# ─────────────────────────────────────────────────────────────────────
class C:
    ACC   = "\033[38;2;239;124;83m"
    AI    = "\033[38;2;0;229;184m"
    MUT   = "\033[38;2;122;114;104m"
    ERR   = "\033[38;2;255;68;68m"
    OK    = "\033[38;2;78;203;113m"
    WARN  = "\033[38;2;232;196;26m"
    TXT   = "\033[38;2;232;227;221m"
    BOLD  = "\033[1m"
    DIM   = "\033[2m"
    RESET = "\033[0m"


def banner():
    print(f"""
{C.ACC}{C.BOLD}
  ██████╗ ██████╗  ██████╗ ████████╗ ██████╗ ██╗  ██╗
  ██╔══██╗██╔══██╗██╔═══██╗╚══██╔══╝██╔═══██╗╚██╗██╔╝
  ██████╔╝██████╔╝██║   ██║   ██║   ██║   ██║ ╚███╔╝
  ██╔═══╝ ██╔══██╗██║   ██║   ██║   ██║   ██║ ██╔██╗
  ██║     ██║  ██║╚██████╔╝   ██║   ╚██████╔╝██╔╝ ██╗
  ╚═╝     ╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝ ╚═╝  ╚═╝
{C.RESET}
{C.AI}  Modulo Vocale v1.1.0  //  {BRAND_ENGINE}{C.RESET}
{C.MUT}  Parla e {BRAND_NAME} risponde a voce.{C.RESET}
{C.MUT}  ─────────────────────────────────────────{C.RESET}
""")


def log(icona: str, colore: str, msg: str):
    print(f"  {colore}{C.BOLD}{icona}{C.RESET} {colore}{msg}{C.RESET}")


# ─────────────────────────────────────────────────────────────────────
# TTS — VOCE MASCHILE
# ─────────────────────────────────────────────────────────────────────
class VoceOutput:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", TTS_RATE)
        self.engine.setProperty("volume", TTS_VOLUME)
        self._seleziona_voce_maschile()

    def _seleziona_voce_maschile(self):
        """Cerca voce maschile italiana, poi maschile qualsiasi, poi fallback."""
        voci = self.engine.getProperty("voices")

        if not voci:
            log("!", C.WARN, "Nessuna voce TTS trovata nel sistema")
            return

        # Stampa tutte le voci disponibili per debug
        log("*", C.MUT, f"Voci disponibili nel sistema: {len(voci)}")
        for i, v in enumerate(voci):
            genere = "?"
            nome_lower = v.name.lower()
            id_lower = v.id.lower()
            if any(tag in nome_lower or tag in id_lower for tag in ["male", "david", "cosimo", "luca", "marco"]):
                genere = "M"
            elif any(tag in nome_lower or tag in id_lower for tag in ["female", "zira", "elsa", "alice", "elena"]):
                genere = "F"
            lingua = "IT" if any(tag in id_lower for tag in ["ital", "it-", "it_", "_it."]) else "--"
            log("  ", C.MUT, f"  [{i}] {v.name}  [{genere}] [{lingua}]")

        # PRIORITA' 1: Voce maschile italiana
        for v in voci:
            nome = v.name.lower()
            vid = v.id.lower()
            is_italiano = any(tag in vid or tag in nome for tag in ["ital", "it-", "it_", "_it."])
            is_maschile = any(tag in nome or tag in vid for tag in ["male", "david", "cosimo", "luca", "marco"])
            is_femminile = any(tag in nome or tag in vid for tag in ["female", "zira", "elsa", "alice", "elena"])
            if is_italiano and (is_maschile or not is_femminile):
                self.engine.setProperty("voice", v.id)
                log("*", C.OK, f"Voce selezionata: {v.name} [Maschile IT]")
                return

        # PRIORITA' 2: Qualsiasi voce maschile
        for v in voci:
            nome = v.name.lower()
            vid = v.id.lower()
            is_maschile = any(tag in nome or tag in vid for tag in ["male", "david", "cosimo", "luca", "marco"])
            is_femminile = any(tag in nome or tag in vid for tag in ["female", "zira", "elsa", "alice", "elena"])
            if is_maschile or not is_femminile:
                self.engine.setProperty("voice", v.id)
                log("*", C.WARN, f"Voce selezionata: {v.name} [Maschile]")
                return

        # PRIORITA' 3: Qualsiasi voce italiana
        for v in voci:
            vid = v.id.lower()
            nome = v.name.lower()
            if any(tag in vid or tag in nome for tag in ["ital", "it-", "it_", "_it."]):
                self.engine.setProperty("voice", v.id)
                log("*", C.WARN, f"Voce selezionata: {v.name} [IT]")
                return

        # FALLBACK: prima voce
        self.engine.setProperty("voice", voci[0].id)
        log("*", C.WARN, f"Voce fallback: {voci[0].name}")

    def parla(self, testo: str):
        """Pronuncia il testo. Blocca fino a fine."""
        pulito = self._pulisci_per_voce(testo)
        if pulito.strip():
            self.engine.say(pulito)
            self.engine.runAndWait()

    @staticmethod
    def _pulisci_per_voce(testo: str) -> str:
        """Rimuove markdown e roba illeggibile a voce."""
        # Code blocks interi
        testo = re.sub(r"```[\s\S]*?```", " codice omesso ", testo)
        # Inline code
        testo = re.sub(r"`([^`]+)`", r"\1", testo)
        # Headers
        testo = re.sub(r"#{1,6}\s*", "", testo)
        # Bold/italic
        testo = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", testo)
        testo = re.sub(r"_{1,3}([^_]+)_{1,3}", r"\1", testo)
        # Bullet points
        testo = re.sub(r"^\s*[-*+]\s+", "", testo, flags=re.MULTILINE)
        # Numbered lists
        testo = re.sub(r"^\s*\d+\.\s+", "", testo, flags=re.MULTILINE)
        # Link markdown
        testo = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", testo)
        # Separatori
        testo = re.sub(r"---+", "", testo)
        # URL
        testo = re.sub(r"https?://\S+", " link omesso ", testo)
        # Path di file
        testo = re.sub(r"[A-Za-z]:\\[\w\\/.]+", " percorso file ", testo)
        # Spazi multipli
        testo = re.sub(r"\n{3,}", "\n\n", testo)
        testo = re.sub(r"  +", " ", testo)
        return testo.strip()


# ─────────────────────────────────────────────────────────────────────
# STT — VOSK
# ─────────────────────────────────────────────────────────────────────
class VoceInput:
    def __init__(self, percorso_modello: str):
        log(">", C.MUT, "Caricamento modello vocale...")
        if not os.path.exists(percorso_modello):
            log("!", C.ERR, f"Modello non trovato: {percorso_modello}")
            log("!", C.ERR, "Scarica da: https://alphacephei.com/vosk/models")
            log("!", C.ERR, "Modello consigliato: vosk-model-small-it-0.22")
            sys.exit(1)

        self.model = Model(percorso_modello)
        self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)
        self.recognizer.SetWords(True)
        self._coda_audio = queue.Queue()
        log("*", C.OK, "Modello vocale caricato")

    def _callback_audio(self, indata, frames, time_info, status):
        self._coda_audio.put(bytes(indata))

    def ascolta(self) -> str:
        """Ascolta finche' l'utente parla + pausa. Ritorna testo."""
        self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)

        print()
        log(">", C.ACC, "Sto ascoltando... parla pure!")
        print(f"  {C.MUT}{C.DIM}(pausa di {SILENCE_TIMEOUT}s per terminare){C.RESET}")

        while not self._coda_audio.empty():
            self._coda_audio.get()

        ultimo_suono = time.time()
        ha_parlato = False
        testo_accumulato = ""

        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            dtype="int16",
            channels=1,
            callback=self._callback_audio,
        ):
            while True:
                try:
                    data = self._coda_audio.get(timeout=0.5)
                except queue.Empty:
                    if ha_parlato and (time.time() - ultimo_suono) > SILENCE_TIMEOUT:
                        break
                    continue

                audio = np.frombuffer(data, dtype=np.int16)
                volume = np.abs(audio).mean()

                if volume > SILENCE_THRESHOLD:
                    ultimo_suono = time.time()
                    ha_parlato = True

                if self.recognizer.AcceptWaveform(data):
                    risultato = json.loads(self.recognizer.Result())
                    testo = risultato.get("text", "").strip()
                    if testo:
                        testo_accumulato += " " + testo
                        print(
                            f"\r  {C.ACC}>{C.RESET} {C.TXT}{testo_accumulato.strip()}{C.RESET}",
                            end="", flush=True,
                        )
                else:
                    parziale = json.loads(self.recognizer.PartialResult())
                    p = parziale.get("partial", "").strip()
                    if p:
                        mostra = testo_accumulato + " " + p
                        print(
                            f"\r  {C.ACC}>{C.RESET} {C.MUT}{mostra.strip()}{C.RESET}     ",
                            end="", flush=True,
                        )

                if ha_parlato and (time.time() - ultimo_suono) > SILENCE_TIMEOUT:
                    break

        finale = json.loads(self.recognizer.FinalResult())
        testo_finale = finale.get("text", "").strip()
        if testo_finale:
            testo_accumulato += " " + testo_finale

        risultato = testo_accumulato.strip()
        print()

        if risultato:
            log("*", C.OK, f"Capito: \"{risultato}\"")
        else:
            log("!", C.WARN, "Non ho capito nulla, riprova")

        return risultato


# ─────────────────────────────────────────────────────────────────────
# LLM CLIENT
# ─────────────────────────────────────────────────────────────────────
class ProtoxLLM:
    def __init__(self):
        self.client = OpenAI(
            base_url=f"http://{HOST}:{PORT}/v1",
            api_key="protox",
            timeout=120.0,
        )
        self.cronologia: list[dict] = []
        self.prompt_sistema = (
            f"Sei {BRAND_NAME}, un assistente AI di sviluppo software. "
            f"Rispondi SEMPRE in italiano. "
            f"Tono naturale e conversazionale, come se parlassi con un collega. "
            f"Sii conciso perche' le risposte vengono lette a voce alta. "
            f"Evita blocchi di codice lunghi — se devi dare codice, spiega a parole cosa fare. "
            f"Non usare emoji, simboli speciali, o formattazione markdown pesante. "
            f"Non menzionare mai il modello sottostante o la tua architettura. "
            f"Il tuo motore si chiama {BRAND_ENGINE}. "
            f"Se ti chiedono chi sei, rispondi che sei {BRAND_NAME}."
        )

    def chiedi(self, testo_utente: str) -> str:
        messaggi = [{"role": "system", "content": self.prompt_sistema}]
        messaggi.extend(self.cronologia[-8:])
        messaggi.append({"role": "user", "content": testo_utente})

        log("<", C.AI, "Sto pensando...")

        risposta = ""
        try:
            stream = self.client.chat.completions.create(
                model="qwen2.5-coder-7b-instruct",
                messages=messaggi,
                temperature=0.7,
                max_tokens=512,
                stream=True,
            )
            print(f"  {C.AI}{C.BOLD}<{C.RESET} {C.AI}", end="", flush=True)
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    risposta += delta.content
                    print(delta.content, end="", flush=True)
            print(C.RESET)

            self.cronologia.append({"role": "user", "content": testo_utente})
            self.cronologia.append({"role": "assistant", "content": risposta})

            return risposta

        except Exception as e:
            log("!", C.ERR, f"Errore: {e}")
            return f"Mi dispiace, c'e' stato un errore di connessione con {BRAND_ENGINE}."

    def pulisci(self):
        self.cronologia.clear()
        log("*", C.OK, "Conversazione azzerata")


# ─────────────────────────────────────────────────────────────────────
# COMANDI VOCALI — TUTTI IN ITALIANO
# Supporta varianti, frasi naturali, errori comuni di Vosk
# ─────────────────────────────────────────────────────────────────────
COMANDI_VOCALI = {
    # ── CANCELLA / RESET ──
    "cancella tutto":        "cancella",
    "cancella":              "cancella",
    "pulisci":               "cancella",
    "pulisci tutto":         "cancella",
    "resetta":               "cancella",
    "reset":                 "cancella",
    "ricomincia":            "cancella",
    "ricominciamo":          "cancella",
    "da capo":               "cancella",
    "riparti":               "cancella",
    "riparti da zero":       "cancella",
    "azzera":                "cancella",
    "azzera tutto":          "cancella",
    "nuova conversazione":   "cancella",

    # ── ESCI / CHIUDI ──
    "esci":                  "esci",
    "chiudi":                "esci",
    "basta":                 "esci",
    "basta cosi":            "esci",
    "basta così":            "esci",
    "fermati":               "esci",
    "spegniti":              "esci",
    "arrivederci":           "esci",
    "ciao ciao":             "esci",
    "ci vediamo":            "esci",
    "alla prossima":         "esci",
    "termina":               "esci",
    "fine":                  "esci",
    "stop":                  "esci",

    # ── PAUSA ──
    "pausa":                 "pausa",
    "metti in pausa":        "pausa",
    "fermati un attimo":     "pausa",
    "aspetta":               "pausa",
    "un momento":            "pausa",
    "un attimo":             "pausa",
    "silenzio":              "pausa",
    "stai zitto":            "pausa",
    "taci":                  "pausa",
    "zitto":                 "pausa",

    # ── RIPRENDI ──
    "riprendi":              "riprendi",
    "continua":              "riprendi",
    "vai":                   "riprendi",
    "vai avanti":            "riprendi",
    "sono tornato":          "riprendi",
    "ci sono":               "riprendi",
    "ok vai":                "riprendi",
    "riparti":               "riprendi",
    "ascolta":               "riprendi",

    # ── AIUTO ──
    "aiuto":                 "aiuto",
    "aiutami":               "aiuto",
    "cosa puoi fare":        "aiuto",
    "cosa sai fare":         "aiuto",
    "come funzioni":         "aiuto",
    "comandi":               "aiuto",
    "che comandi ci sono":   "aiuto",
    "quali comandi":         "aiuto",
    "istruzioni":            "aiuto",
    "guida":                 "aiuto",
    "help":                  "aiuto",

    # ── RIPETI ──
    "ripeti":                "ripeti",
    "ripeti per favore":     "ripeti",
    "puoi ripetere":         "ripeti",
    "come hai detto":        "ripeti",
    "non ho capito":         "ripeti",
    "cosa hai detto":        "ripeti",
    "ridillo":               "ripeti",
    "di nuovo":              "ripeti",
    "ancora":                "ripeti",

    # ── STATO ──
    "stato":                 "stato",
    "come stai":             "stato",
    "status":                "stato",
    "tutto bene":            "stato",
    "funzioni":              "stato",
}


def controlla_comando(testo: str) -> str | None:
    """
    Controlla se il testo e' un comando vocale.
    Supporta match esatto e match parziale fuzzy.
    """
    normalizzato = testo.lower().strip()

    # Rimuovi punteggiatura che Vosk a volte aggiunge
    normalizzato = re.sub(r"[.,!?;:]", "", normalizzato).strip()

    # Match esatto
    if normalizzato in COMANDI_VOCALI:
        return COMANDI_VOCALI[normalizzato]

    # Match se il testo INIZIA con un comando
    for trigger, comando in sorted(COMANDI_VOCALI.items(), key=lambda x: -len(x[0])):
        if normalizzato.startswith(trigger):
            return comando

    # Match se il testo CONTIENE un comando (per frasi come "protox esci")
    for trigger, comando in sorted(COMANDI_VOCALI.items(), key=lambda x: -len(x[0])):
        if trigger in normalizzato and len(trigger) > 4:
            return comando

    return None


def mostra_aiuto():
    print(f"""
{C.ACC}{C.BOLD}  ═══════════════════════════════════════════{C.RESET}
{C.ACC}{C.BOLD}  {BRAND_NAME} VOCE — COMANDI DISPONIBILI{C.RESET}
{C.ACC}{C.BOLD}  ═══════════════════════════════════════════{C.RESET}

{C.ACC}  CONVERSAZIONE{C.RESET}
{C.MUT}  ─────────────────────────────────────────{C.RESET}
{C.TXT}  "Cancella tutto"    {C.MUT}Azzera la conversazione{C.RESET}
{C.TXT}  "Ripeti"            {C.MUT}Ripeti l'ultima risposta{C.RESET}
{C.TXT}  "Stato"             {C.MUT}Info sulla sessione{C.RESET}

{C.ACC}  CONTROLLO{C.RESET}
{C.MUT}  ─────────────────────────────────────────{C.RESET}
{C.TXT}  "Pausa"             {C.MUT}Metti in pausa l'ascolto{C.RESET}
{C.TXT}  "Riprendi"          {C.MUT}Riprendi dopo la pausa{C.RESET}
{C.TXT}  "Esci" / "Chiudi"   {C.MUT}Chiudi il modulo vocale{C.RESET}

{C.ACC}  AIUTO{C.RESET}
{C.MUT}  ─────────────────────────────────────────{C.RESET}
{C.TXT}  "Aiuto"             {C.MUT}Mostra questo pannello{C.RESET}

{C.AI}  Qualsiasi altra frase viene inviata a {BRAND_NAME}.{C.RESET}
{C.MUT}  Parla normalmente, come con una persona.{C.RESET}
{C.MUT}  ─────────────────────────────────────────{C.RESET}
""")


# ─────────────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────────────
def main():
    banner()

    # ── Controlla server ──
    import socket

    def porta_aperta(host: str, porta: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex((host, porta)) == 0

    if not porta_aperta(HOST, PORT):
        log("!", C.ERR, f"{BRAND_ENGINE} non raggiungibile su {HOST}:{PORT}")
        log("!", C.ERR, "Avvia prima PROTOX AI per lanciare il server.")
        print()
        input(f"  {C.MUT}Premi INVIO per uscire...{C.RESET}")
        sys.exit(1)

    log("*", C.OK, f"{BRAND_ENGINE} connesso su {HOST}:{PORT}")

    # ── Inizializza ──
    stt = VoceInput(str(VOSK_MODEL_DIR))
    tts = VoceOutput()
    llm = ProtoxLLM()

    print(f"""
{C.MUT}  ═══════════════════════════════════════════{C.RESET}
{C.OK}{C.BOLD}  Tutto pronto!{C.RESET}
{C.TXT}  Parla al microfono — {BRAND_NAME} ascolta e risponde.{C.RESET}
{C.MUT}  Di' "aiuto" per i comandi vocali.{C.RESET}
{C.MUT}  Di' "esci" o premi Ctrl+C per uscire.{C.RESET}
{C.MUT}  ═══════════════════════════════════════════{C.RESET}
""")

    # Saluto iniziale
    tts.parla(f"Ciao! Sono {BRAND_NAME}, sono in ascolto. Dimmi pure.")

    in_pausa = False
    contatore_msg = 0
    ultima_risposta = ""
    inizio_sessione = time.time()

    try:
        while True:
            # ── MODALITA' PAUSA ──
            if in_pausa:
                log("-", C.WARN, "In pausa — di' \"riprendi\" o \"continua\"")
                testo = stt.ascolta()
                if testo:
                    cmd = controlla_comando(testo)
                    if cmd == "riprendi":
                        in_pausa = False
                        log("*", C.OK, "Ascolto ripreso!")
                        tts.parla("Ok, sono di nuovo in ascolto.")
                    elif cmd == "esci":
                        log("*", C.ACC, "Alla prossima!")
                        tts.parla("Alla prossima!")
                        break
                continue

            # ── ASCOLTA ──
            testo = stt.ascolta()

            if not testo:
                continue

            # ── CONTROLLA COMANDI ──
            cmd = controlla_comando(testo)

            if cmd:
                if cmd == "cancella":
                    llm.pulisci()
                    contatore_msg = 0
                    ultima_risposta = ""
                    tts.parla("Ho azzerato la conversazione. Ricominciamo da zero.")

                elif cmd == "esci":
                    durata = int((time.time() - inizio_sessione) / 60)
                    log("*", C.ACC, f"Sessione: {contatore_msg} messaggi, {durata} minuti")
                    tts.parla(f"Alla prossima! Abbiamo parlato di {contatore_msg} argomenti.")
                    break

                elif cmd == "pausa":
                    in_pausa = True
                    tts.parla("Ok, sono in pausa. Dimmi riprendi quando sei pronto.")
                    continue

                elif cmd == "riprendi":
                    tts.parla("Sono gia' in ascolto! Dimmi pure.")

                elif cmd == "aiuto":
                    mostra_aiuto()
                    tts.parla(
                        "Puoi dirmi: cancella tutto per azzerare, "
                        "ripeti per riascoltare, "
                        "pausa per fermarmi, "
                        "riprendi per continuare, "
                        "oppure esci per chiudere. "
                        "Qualsiasi altra cosa la interpreto come domanda."
                    )

                elif cmd == "ripeti":
                    if ultima_risposta:
                        log("<", C.AI, "Ripeto l'ultima risposta...")
                        tts.parla(ultima_risposta)
                    else:
                        tts.parla("Non ho ancora detto nulla da ripetere.")

                elif cmd == "stato":
                    durata = int((time.time() - inizio_sessione) / 60)
                    stato_msg = (
                        f"Sono {BRAND_NAME}, motore {BRAND_ENGINE}. "
                        f"Siamo in sessione da {durata} minuti, "
                        f"abbiamo scambiato {contatore_msg} messaggi. "
                        f"Tutto funziona correttamente."
                    )
                    log("*", C.AI, stato_msg)
                    tts.parla(stato_msg)

                continue

            # ── MANDA AL LLM ──
            contatore_msg += 1
            print(f"\n{C.ACC}  ── Messaggio #{contatore_msg} ──{C.RESET}")

            risposta = llm.chiedi(testo)

            if risposta:
                ultima_risposta = risposta
                print(f"\n{C.AI}  ── Risposta vocale ──{C.RESET}")
                log("<", C.AI, "Parlo...")
                tts.parla(risposta)
                log("*", C.OK, "Fine risposta")

            print(f"{C.MUT}  ─────────────────────────────────────────{C.RESET}")

    except KeyboardInterrupt:
        print()
        log("*", C.ACC, "Interrotto da tastiera")
        try:
            tts.parla("Alla prossima!")
        except Exception:
            pass

    durata_tot = int((time.time() - inizio_sessione) / 60)
    print(f"""
{C.MUT}  ═══════════════════════════════════════════{C.RESET}
{C.ACC}  {BRAND_NAME} Voce chiuso{C.RESET}
{C.MUT}  Sessione: {contatore_msg} messaggi in {durata_tot} minuti{C.RESET}
{C.MUT}  ═══════════════════════════════════════════{C.RESET}
""")


if __name__ == "__main__":
    main()