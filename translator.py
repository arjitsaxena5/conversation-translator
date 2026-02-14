#!/usr/bin/env python3
"""
Live Conversation Translator: Spanish <-> Hindi
Real-time translation using Google Translate (free, no API key, no token limits)

Modes:
  - Text mode: type to translate, hear the audio output
  - Voice mode: speak to translate, hear the audio output
"""

import os
import sys
import time
import threading
import tempfile
from datetime import datetime
from typing import Optional

from deep_translator import GoogleTranslator
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

LANGUAGES = {
    "es": "Spanish",
    "hi": "Hindi",
}

LANG_COLOR = {
    "es": "cyan",
    "hi": "green",
}

# Google Speech Recognition language codes
SR_LANG_CODE = {
    "es": "es-ES",
    "hi": "hi-IN",
}


class ConversationEntry:
    def __init__(
        self,
        original: str,
        translated: str,
        source_lang: str,
        target_lang: str,
    ):
        self.original = original
        self.translated = translated
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.timestamp = datetime.now().strftime("%H:%M:%S")


class LiveTranslator:
    def __init__(self, source_lang: str, target_lang: str):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.history: list[ConversationEntry] = []

    # ------------------------------------------------------------------
    # Translation
    # ------------------------------------------------------------------

    def translate(self, text: str) -> str:
        try:
            result = GoogleTranslator(
                source=self.source_lang, target=self.target_lang
            ).translate(text)
            return result or ""
        except Exception as e:
            console.print(f"[red]Translation error: {e}[/red]")
            return ""

    # ------------------------------------------------------------------
    # Audio output (always on)
    # ------------------------------------------------------------------

    def speak(self, text: str, lang: str):
        """Convert text to speech and play it — blocks until done."""
        try:
            from gtts import gTTS
            import pygame

            tts = gTTS(text=text, lang=lang, slow=False)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                tts.save(f.name)
                tmp = f.name

            pygame.mixer.init()
            pygame.mixer.music.load(tmp)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
            os.unlink(tmp)
        except ImportError:
            console.print("[yellow]Audio output requires: pip install gtts pygame[/yellow]")
        except Exception as e:
            console.print(f"[yellow]Audio error: {e}[/yellow]")

    # ------------------------------------------------------------------
    # Core processing
    # ------------------------------------------------------------------

    def _looks_like_speech(self, text: str) -> bool:
        if len(text) < 2:
            return False
        vowels = set("aeiouAEIOUअआइईउऊएऐओऔ")
        return any(ch in vowels for ch in text)

    def process(self, text: str) -> Optional[ConversationEntry]:
        text = text.strip()
        if not text:
            return None

        if not self._looks_like_speech(text):
            console.print(f"[dim]Skipping noise: '{text}'[/dim]")
            return None

        src_color = LANG_COLOR[self.source_lang]
        tgt_color = LANG_COLOR[self.target_lang]

        console.print(
            f"\n  [{src_color}]{LANGUAGES[self.source_lang]}:[/{src_color}]  {text}"
        )

        translated = self.translate(text)
        if not translated:
            return None

        console.print(
            f"  [{tgt_color}]{LANGUAGES[self.target_lang]}:[/{tgt_color}]  {translated}"
        )
        console.print("[dim]  Speaking…[/dim]")

        # Speak in a thread so the UI doesn't freeze
        threading.Thread(
            target=self.speak, args=(translated, self.target_lang), daemon=True
        ).start()

        entry = ConversationEntry(text, translated, self.source_lang, self.target_lang)
        self.history.append(entry)
        return entry

    # ------------------------------------------------------------------
    # Text mode
    # ------------------------------------------------------------------

    def run_text_mode(self):
        src_color = LANG_COLOR[self.source_lang]
        tgt_color = LANG_COLOR[self.target_lang]
        console.print(
            Panel(
                f"[bold]Text Mode[/bold]\n"
                f"• Type in [{src_color}]{LANGUAGES[self.source_lang]}[/{src_color}]"
                f" → spoken in [{tgt_color}]{LANGUAGES[self.target_lang]}[/{tgt_color}]\n"
                f"• Commands: [bold]history[/bold] · [bold]quit[/bold]",
                title="[bold blue]Live Conversation Translator[/bold blue]",
                border_style="blue",
            )
        )

        while True:
            try:
                text = console.input("\n[bold blue]>[/bold blue] ").strip()
                if not text:
                    continue
                elif text.lower() in ("quit", "exit", "q"):
                    break
                elif text.lower() == "history":
                    self._show_history()
                else:
                    self.process(text)
            except KeyboardInterrupt:
                break

    # ------------------------------------------------------------------
    # Voice mode
    # ------------------------------------------------------------------

    def run_voice_mode(self):
        try:
            import speech_recognition as sr
        except ImportError:
            console.print(
                "[red]Voice mode requires: pip install SpeechRecognition pyaudio[/red]"
            )
            sys.exit(1)

        recognizer = sr.Recognizer()
        src_lang_code = SR_LANG_CODE[self.source_lang]
        src_color = LANG_COLOR[self.source_lang]
        tgt_color = LANG_COLOR[self.target_lang]

        console.print(
            Panel(
                f"[bold]Voice Mode[/bold]\n"
                f"• Speak in [{src_color}]{LANGUAGES[self.source_lang]}[/{src_color}]"
                f" → spoken back in [{tgt_color}]{LANGUAGES[self.target_lang]}[/{tgt_color}]\n"
                f"• Press [bold]Ctrl+C[/bold] to stop",
                title="[bold blue]Live Conversation Translator[/bold blue]",
                border_style="blue",
            )
        )

        while True:
            try:
                with sr.Microphone() as source:
                    console.print(
                        f"\n[bold green]Listening…[/bold green] "
                        f"[dim](speak in {LANGUAGES[self.source_lang]})[/dim]"
                    )
                    recognizer.adjust_for_ambient_noise(source, duration=0.4)
                    try:
                        audio = recognizer.listen(source, timeout=8, phrase_time_limit=15)
                    except sr.WaitTimeoutError:
                        console.print("[dim]No speech detected — try again.[/dim]")
                        continue

                console.print("[dim]Recognising…[/dim]")

                try:
                    text = recognizer.recognize_google(audio, language=src_lang_code)
                except sr.UnknownValueError:
                    console.print("[yellow]Could not understand — please try again.[/yellow]")
                    continue
                except sr.RequestError as e:
                    console.print(f"[red]Speech API error: {e}[/red]")
                    continue

                self.process(text)

            except KeyboardInterrupt:
                break

    # ------------------------------------------------------------------
    # History display
    # ------------------------------------------------------------------

    def _show_history(self):
        if not self.history:
            console.print("[dim]No conversation history yet.[/dim]")
            return

        table = Table(title="Conversation History", box=box.ROUNDED, show_lines=True)
        table.add_column("Time", style="dim", width=8)
        table.add_column("Original", width=35)
        table.add_column("Translation", width=35)

        for entry in self.history:
            src_color = LANG_COLOR[entry.source_lang]
            tgt_color = LANG_COLOR[entry.target_lang]
            table.add_row(
                entry.timestamp,
                f"[{src_color}]{entry.original}[/{src_color}]",
                f"[{tgt_color}]{entry.translated}[/{tgt_color}]",
            )

        console.print(table)

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def run(self, mode: str = "text"):
        if mode == "voice":
            self.run_voice_mode()
        else:
            self.run_text_mode()

        console.print(
            f"\n[dim]Session ended — {len(self.history)} translation(s) made.[/dim]"
        )
        console.print("\n[bold blue]Goodbye![/bold blue]")


# ----------------------------------------------------------------------
# CLI entry point
# ----------------------------------------------------------------------


def main():
    console.print(
        Panel.fit(
            "[bold blue]Live Conversation Translator[/bold blue]\n"
            "[cyan]Spanish[/cyan] [bold]↔[/bold] [green]Hindi[/green]\n"
            "[dim]Powered by Google Translate (free)[/dim]",
            border_style="blue",
        )
    )

    # Step 1: translation direction
    console.print("\nSelect translation direction:")
    console.print(
        f"  [bold]1.[/bold] [cyan]Spanish[/cyan] → [green]Hindi[/green]"
    )
    console.print(
        f"  [bold]2.[/bold] [green]Hindi[/green] → [cyan]Spanish[/cyan]"
    )
    direction = console.input("\nEnter choice [1/2]: ").strip()
    if direction == "2":
        source_lang, target_lang = "hi", "es"
    else:
        source_lang, target_lang = "es", "hi"

    # Step 2: input mode
    console.print("\nSelect input mode:")
    console.print("  [bold]1.[/bold] Text mode  — type to translate")
    console.print("  [bold]2.[/bold] Voice mode — speak to translate")
    mode_choice = console.input("\nEnter choice [1/2]: ").strip()

    translator = LiveTranslator(source_lang, target_lang)
    translator.run("voice" if mode_choice == "2" else "text")


if __name__ == "__main__":
    main()
