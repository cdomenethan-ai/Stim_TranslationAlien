from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
import tkinter as tk
from tkinter import font as tkfont
from typing import Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RECOGNITION_FILE = DATA_DIR / "recognition_sets.json"
LEXICON_FILE = DATA_DIR / "lexicon.json"


# ----------------------------
# Data handling
# ----------------------------

def load_json(path: Path, fallback: dict) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(fallback, ensure_ascii=False, indent=2), encoding="utf-8")
        return fallback


def build_reverse_dictionary(dictionary: Dict[str, str]) -> Dict[str, str]:
    reverse = {}
    for french, glyphs in dictionary.items():
        reverse[glyphs] = french
    return reverse


# ----------------------------
# Styling
# ----------------------------

class Palette:
    bg = "#0b1021"
    panel = "#11162b"
    panel_border = "#1f2a4d"
    accent = "#00ffc6"
    accent_dim = "#00bfa6"
    text = "#e6f1ff"
    muted = "#7b89b6"


def apply_futuristic_theme(root: tk.Tk, base_font: tkfont.Font) -> None:
    root.configure(bg=Palette.bg)
    root.option_add("*Font", base_font)
    root.option_add("*Foreground", Palette.text)
    root.option_add("*Background", Palette.panel)
    root.option_add("*Button.ActiveBackground", Palette.accent_dim)
    root.option_add("*Button.ActiveForeground", Palette.bg)
    root.option_add("*HighlightThickness", 0)


# ----------------------------
# Data classes
# ----------------------------

@dataclass
class RecognitionChoice:
    round_index: int
    selection: str


@dataclass
class TranslationAttempt:
    french_word: str
    typed_glyphs: str


@dataclass
class GameState:
    font_label: str = "HoloGlyph"
    recognition_rounds: List[List[str]] = field(default_factory=list)
    practice_words: List[str] = field(default_factory=list)
    dictionary: Dict[str, str] = field(default_factory=dict)
    recognition_choices: List[RecognitionChoice] = field(default_factory=list)
    translation_attempts: List[TranslationAttempt] = field(default_factory=list)

    def reverse_dictionary(self) -> Dict[str, str]:
        return build_reverse_dictionary(self.dictionary)


# ----------------------------
# UI components
# ----------------------------

class BaseFrame(tk.Frame):
    def __init__(self, master: tk.Tk, controller: "TranslationAlienApp") -> None:
        super().__init__(master, bg=Palette.bg, highlightthickness=0)
        self.controller = controller
        self.columnconfigure(0, weight=1)

    def header(self, text: str) -> tk.Label:
        return tk.Label(self, text=text, fg=Palette.accent, bg=Palette.bg, font=self.controller.heading_font)

    def panel(self, **kwargs) -> tk.Frame:
        frame = tk.Frame(self, bg=Palette.panel, bd=2, relief=tk.SOLID, highlightbackground=Palette.panel_border)
        for key, value in kwargs.items():
            frame[key] = value
        return frame


class StartFrame(BaseFrame):
    def __init__(self, master: tk.Tk, controller: "TranslationAlienApp") -> None:
        super().__init__(master, controller)
        self.build()

    def build(self) -> None:
        self.header("Translation Alien").grid(row=0, pady=(40, 12))
        subtitle = tk.Label(
            self,
            text="Futuristic symbol trainer for your custom font",
            fg=Palette.muted,
            bg=Palette.bg,
        )
        subtitle.grid(row=1, pady=(0, 20))

        panel = self.panel()
        panel.grid(row=2, padx=40, pady=10, sticky="ew")
        panel.columnconfigure(0, weight=1)

        intro = (
            "In Step 1, select the symbol you recognize across seven rounds.\n"
            "In Step 2, translate French prompts using your glyphs.\n"
            "Then access the live translator between your font and French."
        )
        tk.Label(panel, text=intro, justify="left", bg=Palette.panel, fg=Palette.text, wraplength=520).grid(
            row=0, column=0, padx=20, pady=20
        )

        start = tk.Button(
            self,
            text="Commencer",
            command=lambda: self.controller.show_frame("recognition"),
            bg=Palette.accent,
            fg=Palette.bg,
            activebackground=Palette.accent_dim,
        )
        start.grid(row=3, pady=30, ipadx=16, ipady=8)


class RecognitionFrame(BaseFrame):
    def __init__(self, master: tk.Tk, controller: "TranslationAlienApp") -> None:
        super().__init__(master, controller)
        self.selection_var = tk.StringVar(value="")
        self.build()

    def build(self) -> None:
        self.header("Étape 1 · Reconnaissance des glyphes").grid(row=0, pady=(30, 10))
        self.round_label = tk.Label(self, text="", fg=Palette.muted, bg=Palette.bg)
        self.round_label.grid(row=1, pady=(0, 20))

        self.buttons_frame = tk.Frame(self, bg=Palette.bg)
        self.buttons_frame.grid(row=2, padx=20, pady=10)

        self.none_button = tk.Button(
            self,
            text="Aucun symbole reconnu",
            command=lambda: self.record_choice("Aucun"),
            bg=Palette.panel,
            fg=Palette.muted,
        )
        self.none_button.grid(row=3, pady=(10, 0))

        self.next_button = tk.Button(
            self,
            text="Suivant",
            state=tk.DISABLED,
            command=self.next_round,
            bg=Palette.accent,
            fg=Palette.bg,
        )
        self.next_button.grid(row=4, pady=20, ipadx=10, ipady=6)

    def on_show(self) -> None:
        self.controller.state.recognition_choices.clear()
        self.selection_var.set("")
        self.current_round = 0
        self.render_round()

    def render_round(self) -> None:
        for widget in self.buttons_frame.winfo_children():
            widget.destroy()

        total_rounds = len(self.controller.state.recognition_rounds)
        self.round_label.configure(text=f"Série {self.current_round + 1} / {total_rounds}")
        symbols = self.controller.state.recognition_rounds[self.current_round]
        self.selection_var.set("")
        self.next_button.config(state=tk.DISABLED)

        for idx, symbol in enumerate(symbols):
            btn = tk.Radiobutton(
                self.buttons_frame,
                text=symbol,
                variable=self.selection_var,
                value=symbol,
                indicatoron=0,
                width=12,
                pady=10,
                command=lambda s=symbol: self.record_choice(s),
                selectcolor=Palette.accent_dim,
                bg=Palette.panel,
                fg=Palette.text,
            )
            btn.grid(row=idx // 3, column=idx % 3, padx=8, pady=6)

    def record_choice(self, selection: str) -> None:
        self.selection_var.set(selection)
        self.next_button.config(state=tk.NORMAL)

    def next_round(self) -> None:
        selection = self.selection_var.get() or "Aucun"
        self.controller.state.recognition_choices.append(
            RecognitionChoice(round_index=self.current_round + 1, selection=selection)
        )
        if self.current_round + 1 >= len(self.controller.state.recognition_rounds):
            self.controller.show_frame("translation")
        else:
            self.current_round += 1
            self.render_round()


class TranslationFrame(BaseFrame):
    def __init__(self, master: tk.Tk, controller: "TranslationAlienApp") -> None:
        super().__init__(master, controller)
        self.index = 0
        self.input_var = tk.StringVar()
        self.build()

    def build(self) -> None:
        self.header("Étape 2 · Taper en glyphes").grid(row=0, pady=(30, 8))
        self.prompt_label = tk.Label(self, text="", fg=Palette.muted, bg=Palette.bg)
        self.prompt_label.grid(row=1, pady=(0, 10))

        panel = self.panel()
        panel.grid(row=2, padx=30, pady=10, sticky="ew")
        panel.columnconfigure(0, weight=1)

        tk.Label(panel, text="Saisissez la traduction avec votre police futuriste", bg=Palette.panel).grid(
            row=0, column=0, padx=16, pady=(16, 8), sticky="w"
        )
        entry = tk.Entry(panel, textvariable=self.input_var, relief=tk.FLAT, bg=Palette.bg, fg=Palette.text)
        entry.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="ew")
        self.entry_widget = entry

        self.next_button = tk.Button(
            self,
            text="Valider",
            command=self.submit,
            bg=Palette.accent,
            fg=Palette.bg,
        )
        self.next_button.grid(row=3, pady=20, ipadx=12, ipady=6)

    def on_show(self) -> None:
        self.index = 0
        self.controller.state.translation_attempts.clear()
        self.load_prompt()
        self.input_var.set("")
        self.entry_widget.focus_set()

    def load_prompt(self) -> None:
        words = self.controller.state.practice_words
        if self.index >= len(words):
            self.controller.show_frame("translator")
            return
        word = words[self.index]
        self.prompt_label.configure(text=f"Mot {self.index + 1}/{len(words)} : {word}")
        self.input_var.set("")

    def submit(self) -> None:
        words = self.controller.state.practice_words
        if self.index >= len(words):
            self.controller.show_frame("translator")
            return

        self.controller.state.translation_attempts.append(
            TranslationAttempt(french_word=words[self.index], typed_glyphs=self.input_var.get().strip())
        )
        self.index += 1
        self.load_prompt()


class TranslatorFrame(BaseFrame):
    def __init__(self, master: tk.Tk, controller: "TranslationAlienApp") -> None:
        super().__init__(master, controller)
        self.custom_var = tk.StringVar()
        self.french_var = tk.StringVar()
        self.feedback_var = tk.StringVar()
        self.build()

    def build(self) -> None:
        self.header("Traducteur interactif").grid(row=0, pady=(30, 10))

        summary_panel = self.panel()
        summary_panel.grid(row=1, padx=30, pady=10, sticky="ew")
        summary_panel.columnconfigure(0, weight=1)
        tk.Label(summary_panel, text="Vos sélections", bg=Palette.panel, fg=Palette.muted).grid(
            row=0, column=0, padx=16, pady=(14, 6), sticky="w"
        )
        self.summary_text = tk.Text(
            summary_panel,
            height=8,
            relief=tk.FLAT,
            bg=Palette.bg,
            fg=Palette.text,
            insertbackground=Palette.accent,
            state=tk.DISABLED,
            wrap="word",
        )
        self.summary_text.grid(row=1, column=0, padx=16, pady=(0, 14), sticky="ew")

        translator_panel = self.panel()
        translator_panel.grid(row=2, padx=30, pady=10, sticky="ew")
        translator_panel.columnconfigure(0, weight=1)
        translator_panel.columnconfigure(1, weight=0)

        tk.Label(
            translator_panel,
            text="Entrer un mot en glyphes (votre police)",
            bg=Palette.panel,
            fg=Palette.text,
        ).grid(row=0, column=0, padx=16, pady=(16, 4), sticky="w")
        glyph_entry = tk.Entry(
            translator_panel,
            textvariable=self.custom_var,
            relief=tk.FLAT,
            bg=Palette.bg,
            fg=Palette.text,
        )
        glyph_entry.grid(row=1, column=0, padx=16, pady=(0, 12), sticky="ew")

        tk.Button(
            translator_panel,
            text="Traduire → Français",
            command=self.translate_custom,
            bg=Palette.accent,
            fg=Palette.bg,
        ).grid(row=1, column=1, padx=(0, 16), pady=(0, 12), ipadx=8, ipady=4)

        tk.Label(
            translator_panel,
            text="Entrer un mot en français",
            bg=Palette.panel,
            fg=Palette.text,
        ).grid(row=2, column=0, padx=16, pady=(10, 4), sticky="w")
        french_entry = tk.Entry(
            translator_panel,
            textvariable=self.french_var,
            relief=tk.FLAT,
            bg=Palette.bg,
            fg=Palette.text,
        )
        french_entry.grid(row=3, column=0, padx=16, pady=(0, 16), sticky="ew")

        tk.Button(
            translator_panel,
            text="Traduire → Glyphes",
            command=self.translate_french,
            bg=Palette.accent,
            fg=Palette.bg,
        ).grid(row=3, column=1, padx=(0, 16), pady=(0, 16), ipadx=8, ipady=4)

        self.feedback = tk.Label(translator_panel, textvariable=self.feedback_var, bg=Palette.panel, fg=Palette.accent)
        self.feedback.grid(row=4, column=0, columnspan=2, padx=16, pady=(0, 16), sticky="w")

    def on_show(self) -> None:
        self.populate_summary()
        self.custom_var.set("")
        self.french_var.set("")
        self.feedback_var.set("")

    def populate_summary(self) -> None:
        text_lines = ["Reconnaissance :"]
        for choice in self.controller.state.recognition_choices:
            text_lines.append(f"• Série {choice.round_index}: {choice.selection}")

        text_lines.append("\nSaisie en glyphes :")
        for attempt in self.controller.state.translation_attempts:
            text_lines.append(f"• {attempt.french_word} → {attempt.typed_glyphs or '<vide>'}")

        summary_text = "\n".join(text_lines)
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, summary_text)
        self.summary_text.config(state=tk.DISABLED)

    def translate_custom(self) -> None:
        glyphs = self.custom_var.get().strip()
        if not glyphs:
            self.feedback_var.set("Saisissez un mot en glyphes.")
            return
        french = self.controller.state.reverse_dictionary().get(glyphs)
        if french:
            self.feedback_var.set(f"→ {french}")
        else:
            self.feedback_var.set("Aucune correspondance trouvée dans la liste fournie.")

    def translate_french(self) -> None:
        french = self.french_var.get().strip().lower()
        if not french:
            self.feedback_var.set("Saisissez un mot français.")
            return
        glyphs = self.controller.state.dictionary.get(french)
        if glyphs:
            self.feedback_var.set(f"→ {glyphs}")
        else:
            self.feedback_var.set("Ce mot n'est pas dans la liste fournie.")


# ----------------------------
# Application
# ----------------------------

class TranslationAlienApp(tk.Tk):
    def __init__(self, state: GameState):
        super().__init__()
        self.state = state
        self.title("Translation Alien")
        self.geometry("720x780")
        self.resizable(False, False)

        base_font = tkfont.Font(family="Segoe UI", size=12)
        self.heading_font = tkfont.Font(family=base_font.actual("family"), size=18, weight="bold")
        apply_futuristic_theme(self, base_font)

        container = tk.Frame(self, bg=Palette.bg)
        container.pack(fill="both", expand=True)

        self.frames: Dict[str, BaseFrame] = {}
        for key, frame_cls in {
            "start": StartFrame,
            "recognition": RecognitionFrame,
            "translation": TranslationFrame,
            "translator": TranslatorFrame,
        }.items():
            frame = frame_cls(container, self)
            self.frames[key] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("start")

    def show_frame(self, name: str) -> None:
        frame = self.frames[name]
        if hasattr(frame, "on_show"):
            frame.on_show()  # type: ignore[attr-defined]
        frame.tkraise()


# ----------------------------
# Bootstrap helpers
# ----------------------------

def load_state() -> GameState:
    recognition_data = load_json(
        RECOGNITION_FILE,
        fallback={
            "font_label": "HoloGlyph",
            "rounds": [
                ["Δ", "Λ", "Ω", "Ψ", "Φ", "Σ"],
                ["Ϟ", "ϟ", "𐄣", "𐄢", "✶", "✧"],
                ["₪", "⌬", "⎈", "⧫", "◈", "⬣"],
                ["₪Δ", "ΛΩ", "ΨΣ", "ΦΘ", "ΘΨ", "ΩΛ"],
                ["⟁", "⋇", "⎊", "⍾", "⟡", "⟠"],
                ["⊶", "⊷", "⊸", "⋔", "⋇", "⋉"],
                ["⌖", "⌖Δ", "Λ⌖", "Ω⌖", "Ψ⌖", "Φ⌖"],
            ],
        },
    )

    lexicon_data = load_json(
        LEXICON_FILE,
        fallback={
            "practice_words": ["soleil", "lune", "étoile", "terre", "eau"],
            "dictionary": {
                "soleil": "◉sol",
                "lune": "☾une",
                "étoile": "✦toile",
                "terre": "⟁terre",
                "eau": "≈eau",
                "vent": "〄vent",
                "feu": "🔥feu",
            },
        },
    )

    return GameState(
        font_label=recognition_data.get("font_label", "HoloGlyph"),
        recognition_rounds=recognition_data.get("rounds", []),
        practice_words=lexicon_data.get("practice_words", []),
        dictionary=lexicon_data.get("dictionary", {}),
    )


def main() -> None:
    state = load_state()
    app = TranslationAlienApp(state)
    app.mainloop()


if __name__ == "__main__":
    main()
