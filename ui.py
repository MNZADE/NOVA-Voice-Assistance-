import math
import random
import tkinter as tk


BG = "#080D19"
PANEL = "#10192A"
PANEL_EDGE = "#1B2940"
TEXT = "#F1F6FF"
MUTED = "#8695AD"
CYAN = "#48E5D2"
BLUE = "#5BA8FF"
PURPLE = "#A78BFA"
AMBER = "#F7BC65"


class NovaStatusLabel(tk.Label):
    def __init__(self, master, mood_callback, **kwargs):
        self._mood_callback = mood_callback
        super().__init__(master, **kwargs)

    def configure(self, cnf=None, **kwargs):
        result = super().configure(cnf, **kwargs)
        if "text" in kwargs:
            self._mood_callback(kwargs["text"])
        elif isinstance(cnf, dict) and "text" in cnf:
            self._mood_callback(cnf["text"])
        return result

    config = configure


class NovaOrb(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            height=340,
            highlightthickness=0,
            bd=0,
            bg=BG,
            **kwargs,
        )
        self.mood = "ready"
        self.phase = 0.0
        self._after_id = None
        randomizer = random.Random(13)
        self.stars = [
            (
                randomizer.uniform(0.04, 0.96),
                randomizer.uniform(0.08, 0.92),
                randomizer.choice((1, 1.5, 2)),
                randomizer.uniform(0, math.tau),
            )
            for _ in range(48)
        ]
        self.bind(
            "<Configure>",
            lambda event: self._draw(event.width, event.height),
        )
        self._animate()

    def set_mood(self, text):
        text = str(text).lower()
        if any(word in text for word in ("listening", "waiting for command")):
            self.mood = "listening"
        elif any(word in text for word in ("processing", "thinking", "searching")):
            self.mood = "thinking"
        elif any(
            word in text
            for word in (
                "error", "couldn't", "could not", "sorry", "busy",
                "quota", "limit",
            )
        ):
            self.mood = "attention"
        elif text.startswith("nova:"):
            self.mood = "speaking"
        else:
            self.mood = "ready"
        self._draw()

    def _animate(self):
        self.phase = (self.phase + 0.045) % math.tau
        self._draw()
        self._after_id = self.after(50, self._animate)

    def _draw(self, width=None, height=None):
        width = width or self.winfo_width()
        height = height or self.winfo_height()
        if width < 20 or height < 20:
            return

        self.delete("all")
        colors = {
            "ready": (CYAN, BLUE),
            "listening": (CYAN, "#37B9FF"),
            "thinking": (PURPLE, BLUE),
            "speaking": (CYAN, "#74F0BC"),
            "attention": (AMBER, "#FF8A79"),
        }
        primary, secondary = colors[self.mood]
        for x_ratio, y_ratio, radius, offset in self.stars:
            twinkle = 0.45 + (math.sin(self.phase * 1.5 + offset) + 1) * 0.25
            color = primary if twinkle > 0.85 else "#31415B"
            x, y = width * x_ratio, height * y_ratio
            self.create_oval(x, y, x + radius, y + radius, fill=color, outline="")

        cx, cy = width / 2, height / 2 - 2
        pulse = (math.sin(self.phase * (1.8 if self.mood == "listening" else 1.0)) + 1) / 2
        outer = 112 + pulse * (15 if self.mood in ("listening", "speaking") else 7)

        self.create_oval(
            cx - outer - 28, cy - outer - 28, cx + outer + 28, cy + outer + 28,
            outline="#14253A", width=1,
        )
        self.create_oval(
            cx - outer, cy - outer, cx + outer, cy + outer,
            outline=primary, width=2,
            dash=(3, 8),
        )
        orbit_angle = self.phase * 0.7
        orbit_x = cx + math.cos(orbit_angle) * (outer + 7)
        orbit_y = cy + math.sin(orbit_angle) * (outer + 7)
        self.create_oval(
            orbit_x - 4, orbit_y - 4, orbit_x + 4, orbit_y + 4,
            fill=secondary, outline="",
        )

        for ring in range(5, 0, -1):
            radius = 44 + ring * 8 + pulse * 3
            self.create_oval(
                cx - radius, cy - radius, cx + radius, cy + radius,
                fill="",
                outline="#14243A" if ring > 2 else "#1C3A4D",
                width=1,
            )
        self.create_oval(
            cx - 50, cy - 50, cx + 50, cy + 50,
            fill="#0E2234", outline=primary, width=2,
        )
        self.create_oval(
            cx - 38, cy - 38, cx + 38, cy + 38,
            fill="#122D43", outline=secondary, width=1,
        )
        self.create_text(
            cx, cy - 2, text="N", fill=TEXT,
            font=("Segoe UI", 33, "bold"),
        )
        self.create_text(
            cx, cy + outer + 33,
            text={
                "ready": "YOUR VOICE ASSISTANT",
                "listening": "I'M LISTENING",
                "thinking": "THINKING",
                "speaking": "SPEAKING",
                "attention": "LET'S TRY AGAIN",
            }[self.mood],
            fill=primary, font=("Segoe UI", 9, "bold"),
        )

        bar_y = height - 29
        bar_count = 43
        spacing = min(13, (width - 48) / bar_count)
        start_x = (width - spacing * (bar_count - 1)) / 2
        amplitude = 12 if self.mood in ("listening", "speaking") else 5
        for index in range(bar_count):
            wave = (
                math.sin(index * 0.62 + self.phase * 2.8)
                + 0.42 * math.sin(index * 1.31 - self.phase * 1.7)
            )
            bar_height = 3 + abs(wave) * amplitude
            x = start_x + index * spacing
            self.create_line(
                x, bar_y - bar_height / 2, x, bar_y + bar_height / 2,
                fill=primary if abs(wave) > 0.7 else "#25364E",
                width=3,
                capstyle=tk.ROUND,
            )

    def destroy(self):
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
        super().destroy()


def create_ui(on_question=None):
    root = tk.Tk()
    root.title("NOVA | Voice Assistant")
    root.geometry("760x780")
    root.minsize(620, 680)
    root.configure(bg=BG)

    container = tk.Frame(root, bg=BG)
    container.pack(fill="both", expand=True, padx=34, pady=(24, 20))

    header = tk.Frame(container, bg=BG)
    header.pack(fill="x", pady=(0, 24))

    brand_icon = tk.Canvas(
        header, width=42, height=42, bg=BG, highlightthickness=0,
    )
    brand_icon.pack(side="left")
    brand_icon.create_oval(3, 3, 39, 39, fill="#102A39", outline=CYAN, width=2)
    brand_icon.create_text(
        21, 21, text="N", fill=TEXT, font=("Segoe UI", 18, "bold"),
    )

    brand_text = tk.Frame(header, bg=BG)
    brand_text.pack(side="left", padx=(12, 0))
    tk.Label(
        brand_text, text="NOVA", bg=BG, fg=TEXT,
        font=("Segoe UI", 17, "bold"),
    ).pack(anchor="w")
    tk.Label(
        brand_text, text="PERSONAL VOICE ASSISTANT", bg=BG, fg=MUTED,
        font=("Segoe UI", 8, "bold"),
    ).pack(anchor="w", pady=(1, 0))

    online = tk.Frame(
        header, bg="#10251F", highlightbackground="#1E4838", highlightthickness=1,
    )
    online.pack(side="right", pady=5)
    tk.Label(
        online, text="  ", bg="#48D597", width=1, height=1,
    ).pack(side="left", padx=(10, 1), pady=9)
    tk.Label(
        online, text="READY  ", bg="#10251F", fg="#9BE6C4",
        font=("Segoe UI", 9, "bold"),
    ).pack(side="left", padx=(5, 0), pady=7)

    hero = tk.Frame(
        container, bg=BG, highlightbackground=PANEL_EDGE, highlightthickness=1,
    )
    hero.pack(fill="both", expand=True)
    hero_top = tk.Frame(hero, bg=BG)
    hero_top.pack(fill="x", padx=22, pady=(17, 0))
    tk.Label(
        hero_top, text="VOICE INTERFACE", bg=BG, fg=MUTED,
        font=("Segoe UI", 9, "bold"),
    ).pack(side="left")
    tk.Label(
        hero_top, text="●  LIVE", bg=BG, fg=CYAN,
        font=("Segoe UI", 8, "bold"),
    ).pack(side="right")

    orb = NovaOrb(hero)
    orb.pack(fill="both", expand=True, padx=10, pady=(0, 0))

    card = tk.Frame(
        container, bg=PANEL, highlightbackground=PANEL_EDGE, highlightthickness=1,
    )
    card.pack(fill="x", pady=(18, 0))
    tk.Label(
        card, text="NOVA STATUS", bg=PANEL, fg=MUTED,
        font=("Segoe UI", 8, "bold"),
    ).pack(anchor="w", padx=18, pady=(13, 3))
    status_label = NovaStatusLabel(
        card,
        orb.set_mood,
        text="Nova is ready. Say “Hey Nova” to begin.",
        bg=PANEL,
        fg=TEXT,
        justify="left",
        anchor="w",
        wraplength=660,
        font=("Segoe UI", 11),
    )
    status_label.pack(fill="x", padx=18, pady=(0, 14))

    ask_card = tk.Frame(
        container,
        bg=PANEL,
        highlightbackground=PANEL_EDGE,
        highlightthickness=1,
    )
    ask_card.pack(fill="x", pady=(12, 0))
    tk.Label(
        ask_card,
        text="TYPE A QUESTION — NOVA WILL ANSWER OUT LOUD",
        bg=PANEL,
        fg=CYAN,
        font=("Segoe UI", 8, "bold"),
    ).pack(anchor="w", padx=18, pady=(12, 7))

    ask_row = tk.Frame(ask_card, bg=PANEL)
    ask_row.pack(fill="x", padx=14, pady=(0, 13))
    question_entry = tk.Entry(
        ask_row,
        bg="#0B1322",
        fg=TEXT,
        insertbackground=CYAN,
        selectbackground="#234A68",
        relief="flat",
        bd=0,
        font=("Segoe UI", 11),
    )
    question_entry.pack(side="left", fill="x", expand=True, ipady=11, padx=(0, 10))

    def submit_question(event=None):
        input_widget = event.widget if event is not None else question_entry
        question = input_widget.get().strip()
        if question and on_question is not None:
            on_question(question)
            input_widget.delete(0, tk.END)
        return "break"

    question_entry.bind("<Return>", submit_question)
    tk.Button(
        ask_row,
        text="ASK & SPEAK",
        command=submit_question,
        bg="#13BFAF",
        fg="#04131B",
        activebackground="#47E6D2",
        activeforeground="#04131B",
        relief="flat",
        bd=0,
        padx=16,
        pady=10,
        cursor="hand2",
        font=("Segoe UI", 8, "bold"),
    ).pack(side="right")

    footer = tk.Frame(container, bg=BG)
    footer.pack(fill="x", pady=(16, 0))
    tk.Label(
        footer,
        text="TRY  “HEY NOVA, WHAT IS PYTHON?”",
        bg=BG,
        fg="#AAB8CC",
        font=("Segoe UI", 9, "bold"),
    ).pack(side="left")
    tk.Button(
        footer,
        text="EXIT",
        command=root.destroy,
        bg="#162237",
        fg=MUTED,
        activebackground="#22334D",
        activeforeground=TEXT,
        relief="flat",
        bd=0,
        padx=16,
        pady=7,
        cursor="hand2",
        font=("Segoe UI", 8, "bold"),
    ).pack(side="right")

    splash = tk.Canvas(root, bg="#070B18", highlightthickness=0)
    splash.place(relx=0, rely=0, relwidth=1, relheight=1)
    splash_stars = [
        (
            random.random(),
            random.random(),
            random.choice((1, 1.5, 2)),
            random.random() * math.tau,
        )
        for _ in range(75)
    ]
    splash_frame = {"value": 0}

    def animate_splash():
        if not splash.winfo_exists():
            return
        width = max(splash.winfo_width(), 1)
        height = max(splash.winfo_height(), 1)
        frame = splash_frame["value"]
        splash.delete("all")

        for x_ratio, y_ratio, radius, offset in splash_stars:
            alpha = math.sin(frame * 0.12 + offset)
            color = "#57F7E2" if alpha > 0.68 else "#304A69"
            x, y = width * x_ratio, height * y_ratio
            splash.create_oval(x, y, x + radius, y + radius, fill=color, outline="")

        cx, cy = width / 2, height / 2 - 18
        pulse = (math.sin(frame * 0.16) + 1) / 2
        radius = 72 + pulse * 12
        splash.create_oval(
            cx - radius - 17, cy - radius - 17,
            cx + radius + 17, cy + radius + 17,
            outline="#1D4160", width=1,
        )
        splash.create_oval(
            cx - radius, cy - radius, cx + radius, cy + radius,
            outline=CYAN, width=2, dash=(4, 7),
        )
        splash.create_oval(
            cx - 49, cy - 49, cx + 49, cy + 49,
            fill="#10283D", outline=BLUE, width=2,
        )
        splash.create_oval(
            cx - 39, cy - 39, cx + 39, cy + 39,
            fill="#142F48", outline=PURPLE, width=1,
        )
        splash.create_text(
            cx, cy, text="N", fill=TEXT,
            font=("Segoe UI", 37, "bold"),
        )
        splash.create_text(
            cx, cy + 114, text="WELCOME BACK, MOHANISH",
            fill=TEXT, font=("Segoe UI", 20, "bold"),
        )
        splash.create_text(
            cx, cy + 146, text="YOUR PERSONAL AI IS COMING ONLINE",
            fill=CYAN, font=("Segoe UI", 9, "bold"),
        )

        progress_width = min(220, width * 0.45)
        progress_left = cx - progress_width / 2
        progress_top = cy + 175
        splash.create_rectangle(
            progress_left, progress_top, progress_left + progress_width,
            progress_top + 3, fill="#20314A", outline="",
        )
        progress = (frame % 40) / 40
        splash.create_rectangle(
            progress_left, progress_top,
            progress_left + progress_width * progress, progress_top + 3,
            fill=CYAN, outline="",
        )

        splash_frame["value"] += 1
        if splash_frame["value"] < 42:
            root.after(45, animate_splash)
        else:
            splash.place_forget()
            splash.destroy()

    root.after(100, animate_splash)

    return root, status_label, question_entry
