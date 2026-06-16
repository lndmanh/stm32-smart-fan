"""Polished Tkinter dashboard for the STM32 smart-fan telemetry stream."""

from __future__ import annotations

import math
from queue import Empty, Queue
from pathlib import Path
import tkinter as tk
from tkinter import font as tkfont, messagebox, ttk

import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from command_protocol import (
    build_help_command,
    build_pid_command,
    build_reset_faults_command,
    build_set_speed_command,
    build_stop_command,
)
from dashboard_state import DashboardState
from serial_client import SerialClient
from telemetry import is_legacy_odometry_line, parse_fan_telemetry_line


BAUD_RATE = 115200
POLL_MS = 80
MAX_LOG_LINES = 120

COLORS = {
    # Cool, airy page + card system
    "bg": "#E8F1FB",          # soft sky-tinted backdrop
    "surface": "#FFFFFF",      # crisp white cards
    "surface_alt": "#F1F6FD",  # nested tiles / soft inner surface
    "border": "#DBE7F5",       # soft cool hairline border
    "border_strong": "#C4D7EE",  # emphasised border for the hero card
    # Cool slate ink
    "text": "#15263D",         # deep navy-slate
    "muted": "#566782",        # slate
    "subtle": "#93A2B8",       # light slate
    # Sky-blue primary
    "accent": "#1E8FE6",       # vivid sky blue (primary)
    "accent_dark": "#1573C0",  # hover / pressed
    "accent_soft": "#DEEEFB",  # tinted fill for soft buttons & chips
    "accent_tint": "#EFF6FE",  # faint sky wash (halo, highlights)
    # Semantic
    "success": "#15A06B",
    "warning": "#E08A1E",
    "error": "#E0524E",
    "error_soft": "#FBE7E6",
    # Charts
    "chart": "#F6FAFE",
    "grid": "#E2ECF8",
}

# UI fonts are resolved at runtime against the families actually installed, so
# the dashboard prefers a modern grotesque and gracefully falls back otherwise.
UI_FONT_CANDIDATES = ("Inter", "SF Pro Display", "Helvetica Neue", "Avenir Next")
MONO_FONT_CANDIDATES = ("SF Mono", "Menlo", "Monaco", "Courier New")


def resolve_font_family(candidates: tuple[str, ...], available: set[str]) -> str:
    for name in candidates:
        if name in available:
            return name
    return candidates[-1]


def build_font_palette(ui_family: str, mono_family: str) -> dict[str, tuple]:
    return {
        "display": (ui_family, 40, "bold"),   # hero RPM readout
        "heading": (ui_family, 26, "bold"),   # "Smart Fan" title
        "title": (ui_family, 17, "bold"),     # panel titles
        "section": (ui_family, 13, "bold"),   # chart / log headings
        "group": (ui_family, 12, "bold"),     # footer group titles
        "button": (ui_family, 11, "bold"),
        "body": (ui_family, 12),
        "small": (ui_family, 10),
        "label": (ui_family, 9, "bold"),      # uppercase micro labels
        "mono": (mono_family, 12),
        "mono_big": (mono_family, 22, "bold"),
    }

FAN_ASSET_PATH = Path(__file__).resolve().parent / "assets" / "fan_model.png"
DASHBOARD_METRIC_KEYS = ("rpm", "rps", "target", "pwm", "temperature", "fault", "state")
FOOTER_CONTROL_GROUPS = (
    ("connection", "Connection", ("refresh", "connect")),
    ("speed", "Speed control", ("set_speed", "stop")),
    ("tuning", "Tune & service", ("pid", "reset", "help")),
)
FOOTER_ACTION_LABEL_ITEMS = (
    ("refresh", "Refresh"),
    ("connect", "Connect"),
    ("set_speed", "Set speed"),
    ("stop", "Stop"),
    ("pid", "PID"),
    ("reset", "Reset"),
    ("help", "Help"),
)
FOOTER_ACTION_LABEL_MAP = dict(FOOTER_ACTION_LABEL_ITEMS)
FOOTER_ACTION_LABELS = tuple(label for _, label in FOOTER_ACTION_LABEL_ITEMS)
FOOTER_ACTION_ROLES = {
    "refresh": "secondary",
    "connect": "primary",
    "set_speed": "primary",
    "stop": "danger",
    "reset": "secondary",
    "pid": "primary",
    "help": "secondary",
}
METRIC_CARD_TITLES = {
    "rps": "RPS",
    "target": "Target RPM",
    "pwm": "PWM",
    "temperature": "Temperature",
    "fault": "Fault",
    "state": "State",
}


def fan_asset_is_available(asset_path: Path = FAN_ASSET_PATH) -> bool:
    return asset_path.is_file()


def fan_stage_chip_layout(width: float, height: float) -> dict[str, tuple[float, float, str]]:
    return {
        "rpm": (width * 0.05, height * 0.06, "nw"),
        "pwm": (width * 0.74, height * 0.12, "nw"),
        "temperature": (width * 0.74, height * 0.34, "nw"),
        "state": (width * 0.08, height * 0.76, "nw"),
        "fault": (width * 0.68, height * 0.76, "nw"),
    }


def footer_action_sequence() -> tuple[str, ...]:
    return tuple(action for _, _, actions in FOOTER_CONTROL_GROUPS for action in actions)


def _rounded_rect(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs) -> int:
    radius = min(radius, max(1, (x2 - x1) // 2), max(1, (y2 - y1) // 2))
    points = [
        x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
        x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class RoundedSurface(tk.Canvas):
    """Canvas-backed surface that gives Tk widgets a rounded, softly elevated card shell."""

    # Stepped offset layers (dx, dy, fill) approximate a soft drop shadow.
    SHADOW = ((3, 7, "#CDDBEE"), (2, 4, "#D9E4F3"), (1, 2, "#E6EEF8"))
    MARGIN = 8  # reserved canvas border so the shadow has room to fall

    def __init__(self, parent, fill=COLORS["surface"], radius=24, inset=18, outline=None, shadow=True, **kwargs):
        super().__init__(parent, bg=parent.cget("bg"), highlightthickness=0, bd=0, **kwargs)
        self.fill = fill
        self.radius = radius
        self.inset = inset
        self.outline = outline or COLORS["border"]
        self.shadow = shadow
        self.body = tk.Frame(self, bg=fill)
        self._window = self.create_window(inset, inset, anchor="nw", window=self.body)
        self.bind("<Configure>", self._draw)

    def _draw(self, _event=None) -> None:
        self.delete("surface")
        width = max(2, self.winfo_width())
        height = max(2, self.winfo_height())
        m = self.MARGIN if self.shadow else 3
        if self.shadow and width > 2 * m + 12 and height > 2 * m + 12:
            for dx, dy, color in self.SHADOW:
                _rounded_rect(self, m + dx, m + dy, width - m + dx, height - m + dy, self.radius, fill=color, outline="", tags="surface")
        _rounded_rect(
            self,
            m,
            m,
            width - m,
            height - m,
            self.radius,
            fill=self.fill,
            outline=self.outline,
            width=1,
            tags="surface",
        )
        self.tag_lower("surface")
        self.coords(self._window, self.inset, self.inset)
        self.itemconfigure(self._window, width=max(1, width - self.inset * 2), height=max(1, height - self.inset * 2))


class FanDashboardApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("STM32 Smart Fan Monitor")
        self.geometry("1320x860")
        self.minsize(1160, 760)
        self.configure(bg=COLORS["bg"])

        available = set(tkfont.families(self))
        self.ui_font = resolve_font_family(UI_FONT_CANDIDATES, available)
        self.mono_font = resolve_font_family(MONO_FONT_CANDIDATES, available)
        self.fonts = build_font_palette(self.ui_font, self.mono_font)

        self.state_model = DashboardState()
        self.events: Queue[tuple[str, object]] = Queue()
        self.serial_client = SerialClient(
            baud_rate=BAUD_RATE,
            on_line=lambda line: self.events.put(("line", line)),
            on_status=lambda status: self.events.put(("status", status)),
            on_error=lambda exc: self.events.put(("error", exc)),
        )

        self.metric_labels: dict[str, tk.Label] = {}
        self.status_var = tk.StringVar(value="Disconnected")
        self.port_var = tk.StringVar()
        self.speed_var = tk.StringVar(value="120")
        self.pid_gain_var = tk.StringVar(value="Kp")
        self.pid_value_var = tk.StringVar(value="35")
        self.fan_image_ref: tk.PhotoImage | None = None
        self._fan_asset_attempted = False

        self._build_styles()
        self._build_layout()
        self.refresh_ports()
        self._log("Dashboard ready. Connect to a serial port to begin.")
        self.after(POLL_MS, self._drain_events)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "TCombobox",
            fieldbackground=COLORS["accent_tint"],
            background=COLORS["accent_tint"],
            foreground=COLORS["text"],
            bordercolor=COLORS["border"],
            lightcolor=COLORS["border"],
            darkcolor=COLORS["border"],
            arrowcolor=COLORS["accent"],
            arrowsize=14,
            padding=4,
            relief="flat",
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", COLORS["accent_tint"]), ("focus", COLORS["accent_tint"])],
            foreground=[("readonly", COLORS["text"])],
            bordercolor=[("focus", COLORS["accent"])],
            arrowcolor=[("active", COLORS["accent_dark"])],
        )
        # Match the drop-down list to the sky palette.
        self.option_add("*TCombobox*Listbox.background", COLORS["surface"])
        self.option_add("*TCombobox*Listbox.foreground", COLORS["text"])
        self.option_add("*TCombobox*Listbox.selectBackground", COLORS["accent"])
        self.option_add("*TCombobox*Listbox.selectForeground", "white")
        self.option_add("*TCombobox*Listbox.font", self.fonts["body"])

    def _build_layout(self) -> None:
        shell = tk.Frame(self, bg=COLORS["bg"])
        shell.pack(fill="both", expand=True, padx=24, pady=24)
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_rowconfigure(0, weight=1)

        cockpit = tk.Frame(shell, bg=COLORS["bg"])
        cockpit.grid(row=0, column=0, sticky="nsew", pady=(0, 18))
        cockpit.grid_columnconfigure(0, weight=3)
        cockpit.grid_columnconfigure(1, weight=2)
        cockpit.grid_rowconfigure(0, weight=1)

        self._build_fan_stage(cockpit)
        self._build_analytics_panel(cockpit)
        self._build_command_dock(shell)

    def _build_fan_stage(self, parent: tk.Frame) -> None:
        stage = RoundedSurface(parent, fill=COLORS["surface"], radius=34, inset=28, outline=COLORS["border_strong"])
        stage.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        body = stage.body
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        header = tk.Frame(body, bg=COLORS["surface"])
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        tk.Label(header, text="Smart Fan", bg=COLORS["surface"], fg=COLORS["text"], font=self.fonts["heading"]).grid(row=1, column=0, sticky="w", pady=(2, 0))
        tk.Label(header, textvariable=self.status_var, bg=COLORS["surface"], fg=COLORS["muted"], font=self.fonts["body"]).grid(row=2, column=0, sticky="w", pady=(3, 0))
        self.connection_dot = tk.Canvas(header, width=26, height=26, bg=COLORS["surface"], highlightthickness=0)
        self.connection_dot.grid(row=0, column=1, rowspan=3, sticky="e", padx=(14, 0))
        self._draw_connection_dot(False)

        self.fan_canvas = tk.Canvas(body, bg=COLORS["surface"], highlightthickness=0, bd=0)
        self.fan_canvas.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
        self._ensure_fan_stage_labels()
        self.fan_canvas.bind("<Configure>", self._draw_fan_stage)

    def _build_analytics_panel(self, parent: tk.Frame) -> None:
        panel = RoundedSurface(parent, fill=COLORS["surface"], radius=34, inset=20)
        panel.grid(row=0, column=1, sticky="nsew")
        body = panel.body
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=0)   # metric tiles keep their natural height
        body.grid_rowconfigure(2, weight=1)   # charts absorb the extra vertical space
        body.grid_rowconfigure(3, weight=0)   # event log keeps its fixed height

        tk.Label(body, text="Live analytics", bg=COLORS["surface"], fg=COLORS["text"], font=self.fonts["title"]).grid(row=0, column=0, sticky="w", pady=(0, 10))

        summary = tk.Frame(body, bg=COLORS["surface"])
        summary.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        for column in range(3):
            summary.grid_columnconfigure(column, weight=1)
        for index, key in enumerate(("rps", "target", "pwm", "temperature", "fault", "state")):
            self._metric_tile(summary, key, METRIC_CARD_TITLES[key], index)

        charts = tk.Frame(body, bg=COLORS["surface"])
        charts.grid(row=2, column=0, sticky="nsew")
        charts.grid_columnconfigure(0, weight=1)
        charts.grid_rowconfigure(0, weight=1)
        charts.grid_rowconfigure(1, weight=1)
        speed_card = RoundedSurface(charts, fill=COLORS["chart"], radius=20, inset=14, shadow=False)
        speed_card.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        temp_card = RoundedSurface(charts, fill=COLORS["chart"], radius=20, inset=14, shadow=False)
        temp_card.grid(row=1, column=0, sticky="nsew")
        self.speed_ax, self.speed_canvas = self._chart(speed_card.body, "Speed vs target", "RPM", surface=COLORS["chart"])
        self.temp_ax, self.temp_canvas = self._chart(temp_card.body, "Temperature", "°C", surface=COLORS["chart"])

        log_card = RoundedSurface(body, fill=COLORS["surface_alt"], radius=20, inset=14, height=122, shadow=False)
        log_card.grid(row=3, column=0, sticky="nsew", pady=(10, 0))
        tk.Label(log_card.body, text="Live event log", bg=COLORS["surface_alt"], fg=COLORS["text"], font=self.fonts["section"]).pack(anchor="w", pady=(0, 8))
        self.log_text = tk.Text(log_card.body, bg=COLORS["surface_alt"], fg=COLORS["text"], relief="flat", font=self.fonts["mono"], padx=8, pady=6, wrap="word", height=5)
        self.log_text.pack(fill="both", expand=True)
        self.log_text.tag_configure("info", foreground=COLORS["muted"])
        self.log_text.tag_configure("success", foreground=COLORS["success"])
        self.log_text.tag_configure("warning", foreground=COLORS["warning"])
        self.log_text.tag_configure("error", foreground=COLORS["error"])
        self.log_text.configure(state="disabled")

    def _build_command_dock(self, parent: tk.Frame) -> None:
        dock = RoundedSurface(parent, fill=COLORS["surface"], radius=30, inset=18, height=154)
        dock.grid(row=1, column=0, sticky="ew")
        dock.grid_propagate(False)
        body = dock.body
        for column, (group_id, title, actions) in enumerate(FOOTER_CONTROL_GROUPS):
            body.grid_columnconfigure(column, weight=1)
            group = self._footer_group(body, title, self._footer_group_column_count(group_id))
            group.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 10, 0))
            self._build_footer_group_controls(group_id, group, actions)

    def _footer_group_column_count(self, group_id: str) -> int:
        if group_id in ("connection", "speed"):
            return 3
        if group_id == "tuning":
            return 5
        raise ValueError(f"Unknown footer control group: {group_id}")

    def _build_footer_group_controls(self, group_id: str, group: tk.Frame, actions: tuple[str, ...]) -> None:
        if group_id == "connection":
            refresh_action, connect_action = actions
            self._footer_label(group, "Port", 1, 0)
            self.port_combo = ttk.Combobox(group, textvariable=self.port_var, state="readonly", height=8, width=18)
            self.port_combo.grid(row=2, column=0, sticky="ew", padx=(14, 8), pady=(0, 12), ipady=4)
            self._footer_button(group, refresh_action, self.refresh_ports).grid(row=2, column=1, sticky="ew", padx=(0, 8), pady=(0, 12))
            self.connect_button = self._footer_button(group, connect_action, self.toggle_connection)
            self.connect_button.grid(row=2, column=2, sticky="ew", padx=(0, 14), pady=(0, 12))
            return

        if group_id == "speed":
            set_speed_action, stop_action = actions
            self._footer_label(group, "Target RPM", 1, 0)
            self._footer_input(group, self.speed_var).grid(row=2, column=0, sticky="ew", padx=(14, 8), pady=(0, 12), ipady=7)
            self._footer_button(group, set_speed_action, self.send_speed_command).grid(row=2, column=1, sticky="ew", padx=(0, 8), pady=(0, 12))
            self._footer_button(group, stop_action, lambda: self.send_command(build_stop_command(), "Stop command sent")).grid(row=2, column=2, sticky="ew", padx=(0, 14), pady=(0, 12))
            return

        if group_id != "tuning":
            raise ValueError(f"Unknown footer control group: {group_id}")

        pid_action, reset_action, help_action = actions
        self._footer_label(group, "PID", 1, 0)
        ttk.Combobox(group, textvariable=self.pid_gain_var, values=("Kp", "Ki", "Kd"), state="readonly", width=5).grid(row=2, column=0, sticky="ew", padx=(14, 6), pady=(0, 12), ipady=4)
        self._footer_input(group, self.pid_value_var, width=8).grid(row=2, column=1, sticky="ew", padx=(0, 8), pady=(0, 12), ipady=7)
        self._footer_button(group, pid_action, self.send_pid_command).grid(row=2, column=2, sticky="ew", padx=(0, 8), pady=(0, 12))
        self._footer_button(group, reset_action, lambda: self.send_command(build_reset_faults_command(), "Reset command sent")).grid(row=2, column=3, sticky="ew", padx=(0, 8), pady=(0, 12))
        self._footer_button(group, help_action, lambda: self.send_command(build_help_command(), "Help command sent")).grid(row=2, column=4, sticky="ew", padx=(0, 14), pady=(0, 12))

    def _footer_group(self, parent: tk.Frame, title: str, column_count: int) -> tk.Frame:
        group = tk.Frame(parent, bg=COLORS["surface_alt"], highlightthickness=1, highlightbackground=COLORS["border"])
        for column in range(column_count):
            group.grid_columnconfigure(column, weight=1)
        tk.Label(group, text=title, bg=COLORS["surface_alt"], fg=COLORS["text"], font=self.fonts["group"]).grid(row=0, column=0, columnspan=column_count, sticky="w", padx=14, pady=(10, 6))
        return group

    def _footer_button(self, parent: tk.Frame, action: str, command) -> tk.Button:
        palette = self._footer_button_palette(action)
        return tk.Button(
            parent,
            text=FOOTER_ACTION_LABEL_MAP[action],
            command=command,
            bg=palette[0],
            fg=palette[1],
            activebackground=palette[2],
            activeforeground=palette[1],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=palette[2],
            font=self.fonts["button"],
            padx=12,
            pady=8,
            cursor="hand2",
        )

    def _footer_button_palette(self, action: str) -> tuple[str, str, str]:
        role = FOOTER_ACTION_ROLES[action]
        return {
            "primary": (COLORS["accent"], "white", COLORS["accent_dark"]),
            "secondary": (COLORS["accent_soft"], COLORS["accent_dark"], "#CADFF6"),
            "danger": (COLORS["error_soft"], COLORS["error"], "#F4CFCD"),
        }[role]

    def _footer_input(self, parent: tk.Frame, textvariable: tk.StringVar, width: int = 10) -> tk.Entry:
        return tk.Entry(
            parent,
            textvariable=textvariable,
            width=width,
            bg=COLORS["accent_tint"],
            fg=COLORS["text"],
            relief="flat",
            font=self.fonts["mono"],
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
            insertbackground=COLORS["accent"],
        )

    def _footer_label(self, parent: tk.Frame, text: str, row: int, column: int) -> None:
        tk.Label(parent, text=text.upper(), bg=COLORS["surface_alt"], fg=COLORS["subtle"], font=self.fonts["label"]).grid(row=row, column=column, sticky="w", padx=14 if column == 0 else 0, pady=(0, 6))

    def _metric_tile(self, parent: tk.Frame, key: str, title: str, index: int) -> None:
        tile = tk.Frame(parent, bg=COLORS["surface_alt"], highlightthickness=1, highlightbackground=COLORS["border"])
        tile.grid(row=index // 3, column=index % 3, sticky="ew", padx=(0 if index % 3 == 0 else 8, 0), pady=(0 if index < 3 else 8, 0))
        tk.Label(tile, text=title.upper(), bg=COLORS["surface_alt"], fg=COLORS["subtle"], font=self.fonts["label"]).pack(anchor="w", padx=10, pady=(6, 0))
        self.metric_labels[key] = tk.Label(tile, text="--", bg=COLORS["surface_alt"], fg=COLORS["text"], font=self.fonts["mono"])
        self.metric_labels[key].pack(anchor="w", padx=10, pady=(1, 6))

    def _ensure_fan_stage_labels(self) -> dict[str, tk.Label]:
        if hasattr(self, "fan_stage_labels"):
            return self.fan_stage_labels
        self.fan_stage_labels = {}
        self.fan_stage_metric_labels = {}
        specs = (
            ("rpm", "RPM", self.fonts["display"]),
            ("pwm", "LOAD", self.fonts["mono_big"]),
            ("temperature", "TEMP", self.fonts["mono_big"]),
            ("state", "STATE", self.fonts["mono"]),
            ("fault", "FAULT", self.fonts["mono"]),
        )
        for key, title, font in specs:
            chip = tk.Frame(self.fan_canvas, bg=COLORS["surface_alt"], highlightthickness=1, highlightbackground=COLORS["border"])
            tk.Label(chip, text=title, bg=COLORS["surface_alt"], fg=COLORS["subtle"], font=self.fonts["label"]).pack(anchor="w", padx=12, pady=(8, 0))
            label = tk.Label(chip, text="--", bg=COLORS["surface_alt"], fg=COLORS["text"], font=font)
            label.pack(anchor="w", padx=12, pady=(0, 8))
            self.fan_stage_labels[key] = chip
            self.fan_stage_metric_labels[key] = label
            if key not in self.metric_labels:
                self.metric_labels[key] = label
        return self.fan_stage_labels

    def _draw_fan_stage(self, _event=None) -> None:
        canvas = self.fan_canvas
        canvas.delete("fan_art")
        width = max(320, canvas.winfo_width())
        height = max(320, canvas.winfo_height())
        cx, cy = width * 0.48, height * 0.52

        loaded_asset = False
        if not self._fan_asset_attempted:
            self._fan_asset_attempted = True
            if fan_asset_is_available():
                try:
                    self.fan_image_ref = tk.PhotoImage(file=str(FAN_ASSET_PATH))
                except tk.TclError:
                    self.fan_image_ref = None
        if self.fan_image_ref is not None:
            try:
                canvas.create_image(cx, cy, image=self.fan_image_ref, tags="fan_art")
                loaded_asset = True
            except tk.TclError:
                self.fan_image_ref = None
        if not loaded_asset:
            self._draw_fallback_fan(canvas, cx, cy, min(width, height) * 0.32)
        canvas.tag_lower("fan_art")

        chips = self._ensure_fan_stage_labels()
        positions = fan_stage_chip_layout(width, height)
        for key, (x, y, anchor) in positions.items():
            window = getattr(self, f"_{key}_stage_window", None)
            if window is None:
                window = canvas.create_window(x, y, window=chips[key], anchor=anchor, tags="stage_chip")
                setattr(self, f"_{key}_stage_window", window)
            else:
                canvas.coords(window, x, y)
        canvas.tag_raise("stage_chip")

    def _draw_fallback_fan(self, canvas: tk.Canvas, cx: float, cy: float, radius: float) -> None:
        # Soft sky halo so the fan reads as the hero element on the white stage.
        glow = radius * 1.55
        canvas.create_oval(cx - glow, cy - glow, cx + glow, cy + glow, fill=COLORS["accent_tint"], outline="", tags="fan_art")
        for scale, color, width in ((1.34, "#CFE0F4", 2), (1.06, "#BBD3EE", 2), (0.74, "#DEEAF8", 1)):
            r = radius * scale
            canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=width, tags="fan_art")
        for start in (18, 138, 258):
            canvas.create_arc(cx - radius * 1.62, cy - radius * 1.62, cx + radius * 1.62, cy + radius * 1.62, start=start, extent=44, style="arc", outline="#A6CDF0", width=3, tags="fan_art")
        for angle in (20, 140, 260):
            blade = []
            for dist, offset in ((0.18, -22), (1.02, -10), (1.15, 24), (0.22, 26)):
                radians = math.radians(angle + offset)
                blade.extend((cx + radius * dist * math.cos(radians), cy + radius * dist * math.sin(radians)))
            canvas.create_polygon(blade, smooth=True, fill="#FFFFFF", outline="#AFCDEE", width=2, tags="fan_art")
        hub = radius * 0.24
        canvas.create_oval(cx - hub, cy - hub, cx + hub, cy + hub, fill="#FFFFFF", outline="#9CC2EA", width=2, tags="fan_art")
        canvas.create_oval(cx - hub * 0.46, cy - hub * 0.46, cx + hub * 0.46, cy + hub * 0.46, fill=COLORS["accent"], outline="", tags="fan_art")

    def _chart(self, parent: tk.Frame, title: str, ylabel: str, surface: str = COLORS["surface"]) -> tuple[object, FigureCanvasTkAgg]:
        tk.Label(parent, text=title, bg=surface, fg=COLORS["text"], font=self.fonts["section"]).pack(anchor="w")
        fig = Figure(figsize=(6, 2.1), dpi=100, facecolor=surface)
        ax = fig.add_subplot(111)
        ax.set_facecolor(COLORS["chart"])
        ax.tick_params(colors=COLORS["muted"], labelsize=9)
        ax.set_ylabel(ylabel, color=COLORS["muted"], fontsize=9)
        ax.grid(True, color=COLORS["grid"], linewidth=0.8)
        for spine in ax.spines.values():
            spine.set_color(COLORS["border"])
        fig.tight_layout(pad=1.5)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.get_tk_widget().pack(fill="both", expand=True, pady=(8, 0))
        return ax, canvas

    def refresh_ports(self) -> None:
        try:
            ports = SerialClient.list_ports()
        except Exception as exc:
            self._log(f"Port scan failed: {exc}", "error")
            ports = []
        self.port_combo["values"] = ports
        if ports and self.port_var.get() not in ports:
            self.port_var.set(ports[0])
        elif not ports:
            self.port_var.set("")
        self._log(f"Found {len(ports)} serial port(s).", "info")

    def toggle_connection(self) -> None:
        if self.serial_client.is_connected:
            self.serial_client.disconnect()
            self._set_connected(False)
            return
        port = self.port_var.get().strip()
        if not port:
            messagebox.showwarning("No serial port", "Select a serial port before connecting.")
            return
        try:
            self.serial_client.connect(port)
            self._set_connected(True)
        except Exception as exc:
            self._set_connected(False)
            self._log(f"Connection failed: {exc}", "error")
            messagebox.showerror("Connection failed", str(exc))

    def send_speed_command(self) -> None:
        try:
            command = build_set_speed_command(float(self.speed_var.get()))
            self.send_command(command, f"Target speed command sent: {command.strip()}")
        except ValueError as exc:
            self._log(f"Invalid speed value: {exc}", "error")

    def send_pid_command(self) -> None:
        try:
            command = build_pid_command(self.pid_gain_var.get(), float(self.pid_value_var.get()))
            self.send_command(command, f"PID command sent: {command.strip()}")
        except ValueError as exc:
            self._log(f"Invalid PID command: {exc}", "error")

    def send_command(self, command: str, success_message: str) -> None:
        try:
            self.serial_client.send(command)
            self._log(success_message, "success")
        except Exception as exc:
            self._log(f"Command send failed: {exc}", "error")

    def _drain_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "line":
                    self._handle_line(str(payload))
                elif kind == "status":
                    self._log(str(payload), "success" if self.serial_client.is_connected else "info")
                    self.status_var.set(str(payload))
                elif kind == "error":
                    self._log(f"Serial error: {payload}", "error")
        except Empty:
            pass
        self.after(POLL_MS, self._drain_events)

    def _handle_line(self, line: str) -> None:
        sample = parse_fan_telemetry_line(line)
        if sample is not None:
            self.state_model.apply_sample(sample)
            self._refresh_dashboard()
            return
        level = "warning" if is_legacy_odometry_line(line) else "info"
        self._log(line, level)

    def _refresh_dashboard(self) -> None:
        snapshot = self.state_model.metric_snapshot()
        for key, value in snapshot.items():
            if key in self.metric_labels:
                self.metric_labels[key].configure(text=value)
            if hasattr(self, "fan_stage_metric_labels") and key in self.fan_stage_metric_labels:
                self.fan_stage_metric_labels[key].configure(text=value)
        fault = self.state_model.latest.fault_code if self.state_model.latest else 0
        self.metric_labels["fault"].configure(fg=COLORS["error"] if fault else COLORS["success"])
        if hasattr(self, "fan_stage_metric_labels"):
            self.fan_stage_metric_labels["fault"].configure(fg=COLORS["error"] if fault else COLORS["success"])
        self.status_var.set(self.state_model.connection_label)
        self._draw_connection_dot(True)
        self._refresh_charts()
        self._sync_logs()

    def _refresh_charts(self) -> None:
        speed_points = self.state_model.speed_points
        temp_points = self.state_model.temperature_points
        self.speed_ax.clear()
        self.temp_ax.clear()
        self._style_axes(self.speed_ax, "RPM")
        self._style_axes(self.temp_ax, "°C")
        if speed_points:
            base = speed_points[0][0]
            xs = [(point[0] - base) / 1000 for point in speed_points]
            rpm = [point[1] for point in speed_points]
            target = [point[2] for point in speed_points]
            self.speed_ax.plot(xs, rpm, color=COLORS["accent"], linewidth=2.2, label="Speed")
            self.speed_ax.plot(xs, target, color=COLORS["warning"], linewidth=1.8, linestyle="--", label="Target")
            self.speed_ax.legend(loc="lower right", frameon=False, fontsize=8, labelcolor=COLORS["muted"])
        if temp_points:
            base = temp_points[0][0]
            xs = [(point[0] - base) / 1000 for point in temp_points]
            temps = [point[1] for point in temp_points]
            self.temp_ax.plot(xs, temps, color=COLORS["error"], linewidth=2.0)
        self.speed_canvas.draw_idle()
        self.temp_canvas.draw_idle()

    def _style_axes(self, ax, ylabel: str) -> None:
        ax.set_facecolor(COLORS["chart"])
        ax.set_xlabel("seconds", color=COLORS["muted"], fontsize=9)
        ax.set_ylabel(ylabel, color=COLORS["muted"], fontsize=9)
        ax.tick_params(colors=COLORS["muted"], labelsize=9)
        ax.grid(True, color=COLORS["grid"], linewidth=0.8)
        for spine in ax.spines.values():
            spine.set_color(COLORS["border"])

    def _log(self, message: str, level: str = "info") -> None:
        self.state_model.add_log(message, level)
        if hasattr(self, "log_text"):
            self._sync_logs()

    def _sync_logs(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        for entry in self.state_model.logs[-MAX_LOG_LINES:]:
            self.log_text.insert("end", f"{entry.timestamp}  {entry.message}\n", entry.level)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _set_connected(self, connected: bool) -> None:
        palette = self._footer_button_palette("stop" if connected else "connect")
        self.connect_button.configure(
            text="Disconnect" if connected else FOOTER_ACTION_LABEL_MAP["connect"],
            bg=palette[0],
            fg=palette[1],
            activebackground=palette[2],
            activeforeground=palette[1],
            highlightbackground=palette[2],
        )
        self.status_var.set("Connected" if connected else "Disconnected")
        self._draw_connection_dot(connected)

    def _draw_connection_dot(self, connected: bool) -> None:
        canvas = self.connection_dot
        canvas.delete("all")
        ring = "#D7F0E5" if connected else "#E4EAF2"
        dot = COLORS["success"] if connected else COLORS["subtle"]
        canvas.create_oval(2, 2, 24, 24, fill=ring, outline="")
        canvas.create_oval(8, 8, 18, 18, fill=dot, outline="")

    def _on_close(self) -> None:
        try:
            self.serial_client.disconnect()
        finally:
            self.destroy()
