"""Polished CustomTkinter dashboard for the STM32 smart-fan telemetry stream."""

from __future__ import annotations

import math
from queue import Empty, Queue
from pathlib import Path
from time import strftime
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox

import customtkinter as ctk
import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from auto_curve import (
    AUTO_TEMP_FULL_C,
    AUTO_TEMP_START_C,
    temperature_to_duty_percent,
)
from command_protocol import (
    build_auto_mode_command,
    build_help_command,
    build_manual_mode_command,
    build_pid_command,
    build_reset_faults_command,
    build_set_speed_command,
    build_stop_command,
)
from components import (
    Button,
    Card,
    ConnectionDot,
    Dropdown,
    Field,
    GroupCard,
    MetricTile,
    MicroLabel,
    TemperatureHighlightCard,
    text_label,
)
from app_settings import SettingsStore, default_settings_path
from connection_directory import PortChoice, build_port_choices
from dashboard_state import DashboardState
from serial_client import SerialClient
from telemetry import (
    is_legacy_odometry_line,
    parse_fan_telemetry_line,
    temperature_is_valid,
)
from telemetry_recorder import TelemetryRecorder
from theme import COLORS, RADIUS, SPACE, init_theme


BAUD_RATE = 115200
POLL_MS = 80
MAX_LOG_LINES = 120
SIDEBAR_WIDTH = 300
RAIL_WIDTH = 58

# Fixed chart y-ranges. The traces are pinned to a constant vertical scale
# instead of auto-rescaling per sample, so small jitter reads as small jitter
# rather than being zoomed to fill the panel. Firmware caps RPM at ~190
# (FAN_MAX_RPM 180) and the temperature curve spans 10–60 °C.
SPEED_CHART_YLIM = (0.0, 200.0)
TEMP_CHART_YLIM = (10.0, 60.0)

# Fan animation: the hero fan spins at a rate proportional to live RPM and tints
# red on a fault, so the illustration actually reports state instead of decorating.
FAN_ANIM_MS = 50          # ~20 fps redraw of the rotating blades
FAN_SPIN_GAIN = 0.22      # degrees advanced per frame, per RPM
FAN_MAX_STEP_DEG = 42     # cap per-frame rotation to avoid strobing at high RPM

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

# Two operating modes, surfaced as sidebar tabs. "auto" hands speed to the
# firmware's temperature curve (an indicator-only view); "manual" lets the user
# drive target RPM and PID tuning. The board powers up in temperature control,
# so the dashboard defaults to Auto to stay in sync with the firmware.
FAN_MODES = (("auto", "Auto"), ("manual", "Manual"))
DEFAULT_MODE = "auto"
MODE_COMMAND_BUILDERS = {
    "auto": build_auto_mode_command,
    "manual": build_manual_mode_command,
}
MODE_TAB_LABELS = {label: mode_id for mode_id, label in FAN_MODES}
MODE_STATUS_LABELS = {"auto": "Auto · temperature curve", "manual": "Manual control"}
# Single-glyph labels for the collapsed rail's icon-only mode switch.
MODE_RAIL_GLYPHS = {"auto": "A", "manual": "M"}
EVENT_LOG_TAB_LABEL = "Event log"

# Lookup over the control-group registry so a mode can pull a group by id.
FOOTER_CONTROL_GROUP_MAP = {
    group_id: (title, actions) for group_id, title, actions in FOOTER_CONTROL_GROUPS
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


def rounded_rect_points(x1: float, y1: float, x2: float, y2: float, radius: float) -> list[float]:
    """Control points for a smooth-spline rounded rectangle on a tk.Canvas."""
    r = max(0.0, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
    return [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]


class _FanChipHandle:
    """Label-like handle so the fan-stage HUD chips update via ``.configure()``.

    The chips are painted natively on the fan canvas rather than embedded as CTk
    widgets — an embedded widget always paints an opaque rectangle behind its
    rounded corners, which showed as a weird square box over the fan artwork.
    This handle only records the latest value/colour into chip state; the canvas
    is repainted from that state.
    """

    def __init__(self, app: "FanDashboardApp", key: str):
        self._app = app
        self._key = key

    def configure(self, *, text: str | None = None, text_color: str | None = None, **_ignored) -> None:
        state = self._app._chip_state[self._key]
        if text is not None:
            state["value"] = text
        if text_color is not None:
            state["color"] = text_color


class FanDashboardApp(ctk.CTk):
    NO_PORTS_LABEL = "No devices found"

    def __init__(self) -> None:
        super().__init__()
        self.fonts = init_theme(self)
        self.title("STM32 Smart Fan Monitor")
        self.geometry("1480x880")
        self.minsize(1160, 850)
        self.configure(fg_color=COLORS["bg"])

        self.state_model = DashboardState()
        self.events: Queue[tuple[str, object]] = Queue()
        self.serial_client = SerialClient(
            baud_rate=BAUD_RATE,
            on_line=lambda line: self.events.put(("line", line)),
            on_status=lambda status: self.events.put(("status", status)),
            on_error=lambda exc: self.events.put(("error", exc)),
        )

        self.settings_store = SettingsStore(default_settings_path())
        self.settings = self.settings_store.load()

        self.metric_labels: dict[str, ctk.CTkLabel | _FanChipHandle] = {}
        self.status_var = tk.StringVar(value="Disconnected")
        self.port_var = tk.StringVar()
        self.port_detail_var = tk.StringVar(value="Scanning for devices…")
        self.autoreconnect_var = tk.BooleanVar(value=self.settings.auto_reconnect)
        self._port_choices: list[PortChoice] = []
        self._choice_by_label: dict[str, PortChoice] = {}
        self._pending_select_key: str | None = None
        self.speed_var = tk.StringVar(value="120")
        self.pid_gain_var = tk.StringVar(value="Kp")
        self.pid_value_var = tk.StringVar(value="35")
        self.fan_image_ref: tk.PhotoImage | None = None
        self._fan_asset_attempted = False
        self._fan_uses_asset = False
        self._fan_angle = 0.0
        self._fan_geom: tuple[float, float, float] | None = None
        self._recorder: TelemetryRecorder | None = None
        self._rendered_log_count = 0
        self._sidebar_collapsed = False
        self.mode = DEFAULT_MODE
        self.mode_status_var = tk.StringVar(value=MODE_STATUS_LABELS[DEFAULT_MODE])

        self._build_layout()
        self.refresh_ports()
        self._log("Dashboard ready. Pick your fan's device and connect.")
        self.after(POLL_MS, self._drain_events)
        self.after(FAN_ANIM_MS, self._animate_fan)
        self.after(600, self._maybe_auto_reconnect)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ layout
    def _build_layout(self) -> None:
        self.shell = ctk.CTkFrame(self, fg_color="transparent")
        self.shell.pack(fill="both", expand=True, padx=SPACE["xxl"], pady=SPACE["xxl"])
        self.shell.grid_columnconfigure(0, weight=1)   # main content stretches
        self.shell.grid_columnconfigure(1, weight=0, minsize=SIDEBAR_WIDTH)  # sidebar / rail
        self.shell.grid_rowconfigure(0, weight=1)

        cockpit = ctk.CTkFrame(self.shell, fg_color="transparent")
        cockpit.grid(row=0, column=0, sticky="nsew", padx=(0, SPACE["lg"]))
        cockpit.grid_columnconfigure(0, weight=3)
        cockpit.grid_columnconfigure(1, weight=2)
        cockpit.grid_rowconfigure(0, weight=1)

        self._build_fan_stage(cockpit)
        self._build_analytics_panel(cockpit)
        self._build_control_sidebar(self.shell)

    def _build_fan_stage(self, parent) -> None:
        stage = Card(parent, fill=COLORS["surface"], radius=RADIUS["panel"], inset=SPACE["xl"], outline=COLORS["border_strong"])
        stage.grid(row=0, column=0, sticky="nsew", padx=(0, SPACE["lg"]))
        body = stage.body
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(body, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        text_label(header, "Smart Fan", font="heading").grid(row=1, column=0, sticky="w", pady=(2, 0))
        text_label(header, font="body", fg="muted", textvariable=self.status_var).grid(row=2, column=0, sticky="w", pady=(3, 0))
        self.connection_dot = ConnectionDot(header)
        self.connection_dot.grid(row=0, column=1, rowspan=3, sticky="e", padx=(SPACE["md"], 0))

        self.fan_canvas = tk.Canvas(body, bg=COLORS["surface"], highlightthickness=0, bd=0)
        self.fan_canvas.grid(row=1, column=0, sticky="nsew", pady=(SPACE["md"], 0))
        self._ensure_fan_stage_labels()
        self.fan_canvas.bind("<Configure>", self._draw_fan_stage)

    def _build_analytics_panel(self, parent) -> None:
        panel = Card(parent, fill=COLORS["surface"], radius=RADIUS["panel"], inset=SPACE["lg"])
        panel.grid(row=0, column=1, sticky="nsew")
        body = panel.body
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=0)   # metric tiles keep their natural height
        body.grid_rowconfigure(2, weight=1)   # charts absorb the freed vertical space

        header = ctk.CTkFrame(body, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, SPACE["sm"]))
        header.grid_columnconfigure(0, weight=1)
        text_label(header, "Live analytics", font="title").grid(row=0, column=0, sticky="w")
        self.record_button = Button(header, command=self._toggle_recording, variant="secondary")
        self.record_button.grid(row=0, column=1, sticky="e")
        self._update_record_button(False)

        summary = ctk.CTkFrame(body, fg_color="transparent")
        summary.grid(row=1, column=0, sticky="ew", pady=(0, SPACE["sm"]))
        for column in range(3):
            summary.grid_columnconfigure(column, weight=1)
        for index, key in enumerate(("rps", "target", "pwm", "temperature", "fault", "state")):
            tile = MetricTile(summary, METRIC_CARD_TITLES[key], self.fonts["mono"])
            tile.grid(row=index // 3, column=index % 3, sticky="ew", padx=(0 if index % 3 == 0 else SPACE["sm"], 0), pady=(0 if index < 3 else SPACE["sm"], 0))
            self.metric_labels[key] = tile.value

        charts = ctk.CTkFrame(body, fg_color="transparent")
        charts.grid(row=2, column=0, sticky="nsew")
        charts.grid_columnconfigure(0, weight=1)
        charts.grid_rowconfigure(0, weight=1)
        charts.grid_rowconfigure(1, weight=1)
        speed_card = Card(charts, fill=COLORS["chart"], radius=RADIUS["tile"], inset=SPACE["md"])
        speed_card.grid(row=0, column=0, sticky="nsew", pady=(0, SPACE["sm"]))
        temp_card = Card(charts, fill=COLORS["chart"], radius=RADIUS["tile"], inset=SPACE["md"])
        temp_card.grid(row=1, column=0, sticky="nsew")
        self.speed_ax, self.speed_canvas = self._chart(speed_card.body, "Speed vs target", "RPM", surface=COLORS["chart"], ylim=SPEED_CHART_YLIM)
        self.temp_ax, self.temp_canvas = self._chart(temp_card.body, "Temperature", "°C", surface=COLORS["chart"], ylim=TEMP_CHART_YLIM)
        # Persistent line artists: refreshes call set_data() instead of clearing
        # and re-plotting the whole axes on every telemetry sample. The soft area
        # fills under each trace are re-drawn per refresh in _fill_under().
        (self._speed_line,) = self.speed_ax.plot([], [], color=COLORS["accent"], linewidth=2.4, solid_capstyle="round", solid_joinstyle="round", label="Speed")
        (self._target_line,) = self.speed_ax.plot([], [], color=COLORS["warning"], linewidth=1.6, linestyle=(0, (4, 3)), label="Target")
        self.speed_ax.legend(loc="lower right", frameon=False, fontsize=8, labelcolor=COLORS["muted"])
        (self._temp_line,) = self.temp_ax.plot([], [], color=COLORS["error"], linewidth=2.4, solid_capstyle="round", solid_joinstyle="round")
        self._speed_fill = None
        self._temp_fill = None

    def _build_control_sidebar(self, parent) -> None:
        # Expanded sidebar (top → bottom): mode badge, the Auto / Manual / Event
        # log tabview, the connection (Bluetooth) group, then a full-width
        # collapse button. The Auto and Manual tabs are the two operating modes;
        # switching tabs re-commands the firmware. Collapses to a slim rail.
        self.sidebar = Card(parent, fill=COLORS["surface"], radius=RADIUS["card"], inset=SPACE["md"])
        self.sidebar.grid(row=0, column=1, sticky="nsew")
        body = self.sidebar.body
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)  # tabview absorbs the height

        header = ctk.CTkFrame(body, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, SPACE["sm"]))
        header.grid_columnconfigure(0, weight=1)
        MicroLabel(header, "Mode").grid(row=0, column=0, sticky="w")
        text_label(header, font="group", fg="accent_dark", textvariable=self.mode_status_var).grid(row=1, column=0, sticky="w")

        tabs = ctk.CTkTabview(
            body,
            corner_radius=RADIUS["tile"],
            border_width=0,
            fg_color=COLORS["surface"],
            segmented_button_fg_color=COLORS["surface_alt"],
            segmented_button_selected_color=COLORS["accent_soft"],
            segmented_button_selected_hover_color=COLORS["accent_softer"],
            segmented_button_unselected_color=COLORS["surface_alt"],
            segmented_button_unselected_hover_color=COLORS["accent_soft"],
            text_color=COLORS["accent_dark"],
            command=self._on_tab_change,
        )
        tabs.grid(row=1, column=0, sticky="nsew")
        self.mode_tabs = tabs
        self._populate_auto_tab(tabs.add(dict(FAN_MODES)["auto"]))
        self._populate_manual_tab(tabs.add(dict(FAN_MODES)["manual"]))
        self._populate_event_log_tab(tabs.add(EVENT_LOG_TAB_LABEL))
        tabs.set(dict(FAN_MODES)[DEFAULT_MODE])

        connection = self._make_group(body, "connection")
        connection.grid(row=2, column=0, sticky="ew", pady=(SPACE["sm"], SPACE["sm"]))

        collapse = Button(body, text="Collapse  ❯", command=self._toggle_sidebar, variant="secondary")
        collapse.grid(row=3, column=0, sticky="ew")

        # Collapsed rail: icon-only mode switch on top, expand button pinned below.
        self.sidebar_rail = Card(parent, fill=COLORS["surface"], radius=RADIUS["pill"], inset=SPACE["xs"])
        rail_body = self.sidebar_rail.body
        rail_body.grid_columnconfigure(0, weight=1)
        rail_body.grid_rowconfigure(len(FAN_MODES), weight=1)  # spacer pushes expand to the bottom
        self.rail_mode_buttons: dict[str, Button] = {}
        for index, (mode_id, _label) in enumerate(FAN_MODES):
            button = Button(rail_body, text=MODE_RAIL_GLYPHS[mode_id], command=lambda m=mode_id: self._set_mode(m), variant="secondary", width=36)
            button.grid(row=index, column=0, sticky="ew", pady=(0, SPACE["xs"]))
            self.rail_mode_buttons[mode_id] = button
        self._sidebar_toggle_button(rail_body, "❮").grid(row=len(FAN_MODES) + 1, column=0, sticky="ew")
        self.sidebar_rail.grid(row=0, column=1, sticky="nsew")
        self.sidebar_rail.grid_remove()
        self._refresh_rail_mode_buttons()

    def _make_group(self, parent, group_id: str) -> GroupCard:
        title, actions = FOOTER_CONTROL_GROUP_MAP[group_id]
        group = GroupCard(parent, title)
        self._build_control_group(group_id, group, actions)
        return group

    def _populate_auto_tab(self, tab) -> None:
        # Speed is owned by the firmware's temperature curve, and the live charts
        # / metric tiles already live in the main panel — so this tab is just one
        # big hero card: the current temperature on a gradient that shifts colour
        # with the reading. The card flexes to fill whatever height is available.
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        self.auto_card = TemperatureHighlightCard(tab, self.fonts["hero"])
        self.auto_card.grid(row=0, column=0, sticky="nsew", pady=(SPACE["sm"], 0))

        service = GroupCard(tab, "Service")
        service.grid(row=1, column=0, sticky="ew", pady=(SPACE["md"], 0))
        self._build_service_buttons(service)

    def _populate_manual_tab(self, tab) -> None:
        tab.grid_columnconfigure(0, weight=1)
        for index, group_id in enumerate(("speed", "tuning")):
            group = self._make_group(tab, group_id)
            group.grid(row=index, column=0, sticky="ew", pady=(SPACE["sm"], 0))
        tab.grid_rowconfigure(2, weight=1)  # keep groups top-aligned

    def _populate_event_log_tab(self, tab) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        self.log_text = tk.Text(
            tab,
            bg=COLORS["surface_alt"],
            fg=COLORS["text"],
            relief="flat",
            font=self.fonts["mono"],
            padx=SPACE["sm"],
            pady=SPACE["xs"] + 2,
            wrap="word",
            borderwidth=0,
            highlightthickness=0,
        )
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=SPACE["xs"], pady=SPACE["xs"])
        self.log_text.tag_configure("info", foreground=COLORS["muted"])
        self.log_text.tag_configure("success", foreground=COLORS["success"])
        self.log_text.tag_configure("warning", foreground=COLORS["warning"])
        self.log_text.tag_configure("error", foreground=COLORS["error"])
        self.log_text.configure(state="disabled")

    def _toggle_sidebar(self) -> None:
        if self._sidebar_collapsed:
            self.sidebar_rail.grid_remove()
            self.shell.grid_columnconfigure(1, minsize=SIDEBAR_WIDTH)
            self.sidebar.grid()
        else:
            self.sidebar.grid_remove()
            self.shell.grid_columnconfigure(1, minsize=RAIL_WIDTH)
            self.sidebar_rail.grid()
        self._sidebar_collapsed = not self._sidebar_collapsed

    def _sidebar_toggle_button(self, parent, glyph: str) -> Button:
        return Button(parent, text=glyph, command=self._toggle_sidebar, variant="secondary", width=36)

    def _action_button(self, parent, action: str, command) -> Button:
        return Button(parent, text=FOOTER_ACTION_LABEL_MAP[action], command=command, variant=FOOTER_ACTION_ROLES[action])

    def _build_control_group(self, group_id: str, group, actions: tuple[str, ...]) -> None:
        pad = SPACE["md"]
        gap = SPACE["xs"]
        label_grid = dict(row=1, column=0, sticky="w", padx=pad, pady=(0, gap + 2))
        left_btn = dict(sticky="ew", padx=(pad, gap), pady=(0, pad))
        right_btn = dict(sticky="ew", padx=(gap, pad), pady=(0, pad))
        if group_id == "connection":
            refresh_action, connect_action = actions
            MicroLabel(group, "Device").grid(**label_grid)
            device_row = ctk.CTkFrame(group, fg_color="transparent")
            device_row.grid(row=2, column=0, columnspan=2, sticky="ew", padx=pad, pady=(0, gap))
            device_row.grid_columnconfigure(0, weight=1)
            self.port_combo = Dropdown(device_row, self.port_var, [self.NO_PORTS_LABEL], command=lambda _value=None: self._on_port_selected())
            self.port_combo.grid(row=0, column=0, sticky="ew", padx=(0, gap))
            self.rename_button = Button(device_row, text="✎", command=self._rename_selected_device, variant="secondary", width=42)
            self.rename_button.grid(row=0, column=1, sticky="e")
            text_label(group, font="small", fg="subtle", bg="surface_alt", textvariable=self.port_detail_var, wraplength=230, justify="left").grid(
                row=3, column=0, columnspan=2, sticky="w", padx=pad, pady=(0, SPACE["sm"])
            )
            self._action_button(group, refresh_action, self.refresh_ports).grid(row=4, column=0, **left_btn)
            self.connect_button = self._action_button(group, connect_action, self.toggle_connection)
            self.connect_button.grid(row=4, column=1, **right_btn)
            self.autoreconnect_check = ctk.CTkCheckBox(
                group,
                text="Reconnect on launch",
                variable=self.autoreconnect_var,
                command=self._toggle_auto_reconnect,
                font=self.fonts["body"],
                text_color=COLORS["muted"],
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_dark"],
                checkmark_color="white",
                border_color=COLORS["border"],
                checkbox_width=18,
                checkbox_height=18,
                corner_radius=RADIUS["control"],
            )
            self.autoreconnect_check.grid(row=5, column=0, columnspan=2, sticky="w", padx=pad, pady=(0, pad))
            return

        if group_id == "speed":
            set_speed_action, stop_action = actions
            MicroLabel(group, "Target RPM").grid(**label_grid)
            Field(group, self.speed_var).grid(row=2, column=0, columnspan=2, sticky="ew", padx=pad, pady=(0, SPACE["sm"]))
            self._action_button(group, set_speed_action, self.send_speed_command).grid(row=3, column=0, **left_btn)
            self._action_button(group, stop_action, lambda: self.send_command(build_stop_command(), "Stop command sent")).grid(row=3, column=1, **right_btn)
            return

        if group_id != "tuning":
            raise ValueError(f"Unknown control group: {group_id}")

        pid_action, reset_action, help_action = actions
        MicroLabel(group, "PID").grid(**label_grid)
        Dropdown(group, self.pid_gain_var, ("Kp", "Ki", "Kd")).grid(row=2, column=0, sticky="ew", padx=(pad, gap), pady=(0, SPACE["sm"]))
        Field(group, self.pid_value_var).grid(row=2, column=1, sticky="ew", padx=(gap, pad), pady=(0, SPACE["sm"]))
        self._action_button(group, pid_action, self.send_pid_command).grid(row=3, column=0, **left_btn)
        self._action_button(group, reset_action, lambda: self.send_command(build_reset_faults_command(), "Reset command sent")).grid(row=3, column=1, **right_btn)
        self._action_button(group, help_action, lambda: self.send_command(build_help_command(), "Help command sent")).grid(row=4, column=0, columnspan=2, sticky="ew", padx=pad, pady=(0, pad))

    def _build_service_buttons(self, group) -> None:
        # Reset / Help, shared by the Auto tab where there is no tuning group.
        pad, gap = SPACE["md"], SPACE["xs"]
        self._action_button(group, "reset", lambda: self.send_command(build_reset_faults_command(), "Reset command sent")).grid(
            row=1, column=0, sticky="ew", padx=(pad, gap), pady=(0, pad)
        )
        self._action_button(group, "help", lambda: self.send_command(build_help_command(), "Help command sent")).grid(
            row=1, column=1, sticky="ew", padx=(gap, pad), pady=(0, pad)
        )

    # --------------------------------------------------------------- mode switch
    def _on_tab_change(self) -> None:
        mode = MODE_TAB_LABELS.get(self.mode_tabs.get())
        if mode is None:  # Event log tab — leave the active control mode alone
            return
        self._set_mode(mode)

    def _set_mode(self, mode: str) -> None:
        # Single entry point for a mode change from either surface (tab or rail):
        # command the firmware, then keep the tabview and rail buttons in sync.
        self._apply_mode(mode)
        self.mode_tabs.set(dict(FAN_MODES)[mode])  # no-op if already selected; never re-fires the callback
        self._refresh_rail_mode_buttons()

    def _apply_mode(self, mode: str, *, announce: bool = True) -> None:
        self.mode = mode
        self.mode_status_var.set(MODE_STATUS_LABELS[mode])
        label = dict(FAN_MODES)[mode]
        if self.serial_client.is_connected:
            self.send_command(MODE_COMMAND_BUILDERS[mode](), f"{label} mode enabled")
        elif announce:
            self._log(f"{label} mode selected — applies on connect.", "info")

    def _refresh_rail_mode_buttons(self) -> None:
        if not hasattr(self, "rail_mode_buttons"):
            return
        for mode_id, button in self.rail_mode_buttons.items():
            button.set_variant("primary" if mode_id == self.mode else "secondary")

    def _ensure_fan_stage_labels(self) -> dict[str, _FanChipHandle]:
        if hasattr(self, "fan_stage_labels"):
            return self.fan_stage_labels
        self.fan_stage_labels = {}
        self.fan_stage_metric_labels = {}
        self._chip_state: dict[str, dict[str, str]] = {}
        self._chip_font_cache: dict[tuple, tkfont.Font] = {}
        self._fan_chip_specs = (
            ("rpm", "RPM", self.fonts["display"]),
            ("pwm", "LOAD", self.fonts["mono_big"]),
            ("temperature", "TEMP", self.fonts["mono_big"]),
            ("state", "STATE", self.fonts["mono"]),
            ("fault", "FAULT", self.fonts["mono"]),
        )
        for key, _title, _font in self._fan_chip_specs:
            self._chip_state[key] = {"value": "--", "color": COLORS["text"]}
            handle = _FanChipHandle(self, key)
            self.fan_stage_labels[key] = handle
            self.fan_stage_metric_labels[key] = handle
            if key not in self.metric_labels:
                self.metric_labels[key] = handle
        return self.fan_stage_labels

    # -------------------------------------------------------------- fan canvas
    def _draw_fan_stage(self, _event=None) -> None:
        canvas = self.fan_canvas
        canvas.delete("fan_static")
        width = max(320, canvas.winfo_width())
        height = max(320, canvas.winfo_height())
        cx, cy = width * 0.48, height * 0.52

        if not self._fan_asset_attempted:
            self._fan_asset_attempted = True
            if fan_asset_is_available():
                try:
                    self.fan_image_ref = tk.PhotoImage(file=str(FAN_ASSET_PATH))
                except tk.TclError:
                    self.fan_image_ref = None
        self._fan_uses_asset = False
        if self.fan_image_ref is not None:
            try:
                canvas.delete("fan_image")
                canvas.create_image(cx, cy, image=self.fan_image_ref, tags=("fan_art", "fan_static", "fan_image"))
                self._fan_uses_asset = True
            except tk.TclError:
                self.fan_image_ref = None
        if not self._fan_uses_asset:
            radius = min(width, height) * 0.32
            self._fan_geom = (cx, cy, radius)
            self._draw_fan_decor(canvas, cx, cy, radius)
        canvas.tag_lower("fan_art")

        self._ensure_fan_stage_labels()
        self._fan_chip_geom = (width, height)
        self._draw_fan_chips(width, height)
        self._draw_fan_blades()

    def _measure_font(self, spec: tuple) -> tkfont.Font:
        font = self._chip_font_cache.get(spec)
        if font is None:
            font = tkfont.Font(family=spec[0], size=spec[1], weight=spec[2] if len(spec) > 2 else "normal")
            self._chip_font_cache[spec] = font
        return font

    def _draw_fan_chips(self, width: int, height: int) -> None:
        # HUD chips drawn natively on the canvas so their rounded corners sit
        # cleanly over the fan art (no opaque square background from an embedded
        # widget). Repainted from chip state on every resize and telemetry tick.
        canvas = self.fan_canvas
        canvas.delete("stage_chip")
        positions = fan_stage_chip_layout(width, height)
        for key, title, value_font in self._fan_chip_specs:
            x, y, _anchor = positions[key]
            state = self._chip_state[key]
            self._draw_one_chip(canvas, x, y, title, value_font, state["value"], state["color"])
        canvas.tag_raise("stage_chip")

    def _draw_one_chip(self, canvas, x, y, title, value_font, value, value_color) -> None:
        label_font = self.fonts["label"]
        cap_h = self._measure_font(label_font).metrics("linespace")
        value_metrics = self._measure_font(value_font)
        pad_x, pad_y, gap = SPACE["md"], SPACE["sm"], 2
        inner_w = max(self._measure_font(label_font).measure(title), value_metrics.measure(value))
        x2 = x + inner_w + pad_x * 2
        y2 = y + pad_y * 2 + cap_h + gap + value_metrics.metrics("linespace")
        canvas.create_polygon(
            rounded_rect_points(x, y, x2, y2, RADIUS["tile"]),
            smooth=True, fill=COLORS["surface_alt"], outline=COLORS["border"], width=1, tags="stage_chip",
        )
        text_x = x + pad_x
        canvas.create_text(text_x, y + pad_y, text=title, anchor="nw", fill=COLORS["subtle"], font=label_font, tags="stage_chip")
        canvas.create_text(text_x, y + pad_y + cap_h + gap, text=value, anchor="nw", fill=value_color, font=value_font, tags="stage_chip")

    def _draw_fan_decor(self, canvas: tk.Canvas, cx: float, cy: float, radius: float) -> None:
        # Static halo, rings and arcs. Soft sky so the fan reads as the hero.
        glow = radius * 1.55
        canvas.create_oval(cx - glow, cy - glow, cx + glow, cy + glow, fill=COLORS["accent_tint"], outline="", tags=("fan_art", "fan_static"))
        for scale, color, width in ((1.34, "#DBE7F8", 2), (1.06, "#C3D6F0", 2), (0.74, "#E6EEFA", 1)):
            r = radius * scale
            canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=width, tags=("fan_art", "fan_static"))
        for start in (18, 138, 258):
            canvas.create_arc(cx - radius * 1.62, cy - radius * 1.62, cx + radius * 1.62, cy + radius * 1.62, start=start, extent=44, style="arc", outline="#AFC9F0", width=3, tags=("fan_art", "fan_static"))

    def _draw_fan_blades(self) -> None:
        # Rotating blades + hub, redrawn each animation frame at the current angle.
        canvas = self.fan_canvas
        canvas.delete("fan_blades")
        geom = self._fan_geom
        if geom is None or self._fan_uses_asset:
            return
        cx, cy, radius = geom
        fault = bool(self.state_model.latest and self.state_model.latest.fault_code)
        blade_fill = COLORS["error_soft"] if fault else "#FFFFFF"
        blade_outline = COLORS["error"] if fault else "#B7CDF0"
        for base_angle in (20, 140, 260):
            angle = base_angle + self._fan_angle
            blade = []
            for dist, offset in ((0.18, -22), (1.02, -10), (1.15, 24), (0.22, 26)):
                radians = math.radians(angle + offset)
                blade.extend((cx + radius * dist * math.cos(radians), cy + radius * dist * math.sin(radians)))
            canvas.create_polygon(blade, smooth=True, fill=blade_fill, outline=blade_outline, width=2, tags=("fan_art", "fan_blades"))
        hub = radius * 0.24
        canvas.create_oval(cx - hub, cy - hub, cx + hub, cy + hub, fill="#FFFFFF", outline=(COLORS["error_softer"] if fault else "#A6C0EC"), width=2, tags=("fan_art", "fan_blades"))
        accent = COLORS["error"] if fault else COLORS["accent"]
        canvas.create_oval(cx - hub * 0.46, cy - hub * 0.46, cx + hub * 0.46, cy + hub * 0.46, fill=accent, outline="", tags=("fan_art", "fan_blades"))
        canvas.tag_raise("stage_chip")

    def _animate_fan(self) -> None:
        rpm = 0.0
        if self.serial_client.is_connected and self.state_model.latest is not None:
            rpm = max(0.0, self.state_model.latest.rpm)
        self._fan_angle = (self._fan_angle + min(rpm * FAN_SPIN_GAIN, FAN_MAX_STEP_DEG)) % 360
        self._draw_fan_blades()
        self.after(FAN_ANIM_MS, self._animate_fan)

    def _chart(self, parent, title: str, ylabel: str, surface: str = COLORS["surface"], ylim: tuple[float, float] | None = None) -> tuple[object, FigureCanvasTkAgg]:
        text_label(parent, title, font="section", bg=surface).pack(anchor="w")
        fig = Figure(figsize=(6, 2.1), dpi=100, facecolor=surface)
        ax = fig.add_subplot(111)
        ax.set_facecolor(surface)
        ax.margins(x=0.015, y=0.2)
        if ylim is not None:
            # Pin the vertical scale so the trace keeps a stable baseline; only
            # the time axis scrolls. Without this the per-sample autoscale below
            # makes flat data look like it is swinging wildly.
            ax.set_ylim(*ylim)
        # Spineless, ticks without marks, a faint dotted baseline grid: minimal
        # chrome so the line itself is the focus.
        ax.tick_params(colors=COLORS["subtle"], labelsize=8, length=0, pad=4)
        ax.set_ylabel(ylabel, color=COLORS["subtle"], fontsize=8)
        ax.grid(True, axis="y", color=COLORS["grid"], linewidth=1.0, linestyle=(0, (1, 3)))
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_visible(False)
        fig.subplots_adjust(left=0.11, right=0.975, top=0.94, bottom=0.17)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.get_tk_widget().pack(fill="both", expand=True, pady=(SPACE["sm"], 0))
        return ax, canvas

    # ----------------------------------------------------------- serial / cmds
    def refresh_ports(self) -> None:
        try:
            infos = self.serial_client.list_port_infos()
        except Exception as exc:
            self._log(f"Device scan failed: {exc}", "error")
            infos = []
        choices = build_port_choices(infos, last_key=self.settings.last_port_key, custom_names=self.settings.custom_names)
        self._port_choices = choices
        self._choice_by_label = {choice.name: choice for choice in choices}
        self.port_combo.configure(values=[choice.name for choice in choices] if choices else [self.NO_PORTS_LABEL])
        self.port_var.set(self._default_port_label(choices))
        self._on_port_selected()
        self._log(f"Found {len(choices)} device(s).", "info")

    def _default_port_label(self, choices) -> str:
        if not choices:
            return self.NO_PORTS_LABEL
        # A device just renamed jumps back to the top of the selection priority.
        pending = getattr(self, "_pending_select_key", None)
        self._pending_select_key = None
        for key in (pending, self.settings.last_port_key):
            if key is not None:
                match = next((choice for choice in choices if choice.key == key), None)
                if match is not None:
                    return match.name
        if self.port_var.get() in self._choice_by_label:
            return self.port_var.get()
        return choices[0].name

    def _selected_choice(self):
        return self._choice_by_label.get(self.port_var.get())

    def _on_port_selected(self) -> None:
        choice = self._selected_choice()
        if choice is not None:
            self.port_detail_var.set(choice.detail)
        elif self._port_choices:
            self.port_detail_var.set("Select a device to connect.")
        else:
            self.port_detail_var.set("No devices found. Pair your fan over Bluetooth, then Refresh.")
        has_device = choice is not None
        if hasattr(self, "rename_button"):
            self.rename_button.configure(state="normal" if has_device else "disabled")
        if hasattr(self, "connect_button") and not self.serial_client.is_connected:
            self.connect_button.configure(state="normal" if has_device else "disabled")

    def _rename_selected_device(self) -> None:
        choice = self._selected_choice()
        if choice is None:
            return
        dialog = ctk.CTkInputDialog(title="Rename device", text=f"Friendly name for:\n{choice.device}\n\n(leave blank to reset)")
        response = dialog.get_input()  # blocks until the dialog closes; None on cancel
        if response is None:
            return
        name = response.strip()
        if name:
            self.settings.custom_names[choice.key] = name
            self._log(f"Renamed device to “{name}”.", "success")
        else:
            self.settings.custom_names.pop(choice.key, None)
            self._log("Reset device to its default name.", "info")
        self.settings_store.save(self.settings)
        self._pending_select_key = choice.key
        self.refresh_ports()

    def _toggle_auto_reconnect(self) -> None:
        self.settings.auto_reconnect = bool(self.autoreconnect_var.get())
        self.settings_store.save(self.settings)
        state = "on" if self.settings.auto_reconnect else "off"
        self._log(f"Reconnect on launch turned {state}.", "info")

    def _maybe_auto_reconnect(self) -> None:
        if not self.settings.auto_reconnect or self.serial_client.is_connected:
            return
        choice = self._selected_choice()
        if choice is not None and choice.is_last_used:
            self._log(f"Auto-reconnecting to {choice.name}…", "info")
            self.toggle_connection()

    def toggle_connection(self) -> None:
        if self.serial_client.is_connected:
            self.serial_client.disconnect()
            self._set_connected(False)
            return
        choice = self._selected_choice()
        if choice is None:
            messagebox.showwarning("No device", "Select a Bluetooth or serial device before connecting.")
            return
        try:
            self.serial_client.connect(choice.device)
            self._set_connected(True)
            self._apply_mode(self.mode, announce=False)
            self.status_var.set(f"Connected · {choice.name}")
            self._remember_device(choice)
        except Exception as exc:
            self._set_connected(False)
            self._log(f"Connection to {choice.name} failed: {exc}", "error")
            messagebox.showerror("Connection failed", str(exc))

    def _remember_device(self, choice) -> None:
        if self.settings.last_port_key != choice.key:
            self.settings.last_port_key = choice.key
            self.settings_store.save(self.settings)

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

    # ------------------------------------------------------------- recording
    def _toggle_recording(self) -> None:
        if self._recorder is not None and self._recorder.is_recording:
            path = self._recorder.path
            rows = self._recorder.rows_written
            self._recorder.stop()
            self._recorder = None
            self._update_record_button(False)
            self._log(f"Recording saved: {path} ({rows} rows)", "success")
            return

        default_name = strftime("fan_telemetry_%Y%m%d_%H%M%S.csv")
        path = filedialog.asksaveasfilename(
            title="Save telemetry recording",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        recorder = TelemetryRecorder(path)
        try:
            recorder.start()
        except OSError as exc:
            self._log(f"Could not start recording: {exc}", "error")
            return
        self._recorder = recorder
        self._update_record_button(True)
        self._log(f"Recording telemetry to {path}", "success")

    def _record_sample(self, sample) -> None:
        if self._recorder is None or not self._recorder.is_recording:
            return
        try:
            self._recorder.write_sample(sample)
        except OSError as exc:
            self._recorder.stop()
            self._recorder = None
            self._update_record_button(False)
            self._log(f"Recording stopped (write failed): {exc}", "error")

    def _update_record_button(self, recording: bool) -> None:
        if recording:
            self.record_button.configure(text="■ Stop recording")
            self.record_button.set_variant("danger")
        else:
            self.record_button.configure(text="● Record CSV")
            self.record_button.set_variant("secondary")

    # ----------------------------------------------------------- event pump
    def _drain_events(self) -> None:
        # Drain the whole queue, then render once: a burst of telemetry lines
        # triggers a single dashboard refresh instead of one per line.
        dashboard_dirty = False
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "line":
                    if self._handle_line(str(payload)):
                        dashboard_dirty = True
                elif kind == "status":
                    self._handle_status(str(payload))
                elif kind == "error":
                    self._log(f"Serial error: {payload}", "error")
        except Empty:
            pass
        if dashboard_dirty:
            self._refresh_dashboard()
        self.after(POLL_MS, self._drain_events)

    def _handle_status(self, message: str) -> None:
        connected = self.serial_client.is_connected
        self._log(message, "success" if connected else "info")
        # An unexpected drop (device unplugged) arrives as a status while the
        # button still reads "Disconnect" — flip the UI back to a clean state.
        if not connected and self.connect_button.cget("text") == "Disconnect":
            self._set_connected(False)
        self.status_var.set(message)

    def _handle_line(self, line: str) -> bool:
        sample = parse_fan_telemetry_line(line)
        if sample is not None:
            self.state_model.apply_sample(sample)
            self._record_sample(sample)
            return True
        level = "warning" if is_legacy_odometry_line(line) else "info"
        self._log(line, level)
        return False

    def _refresh_dashboard(self) -> None:
        snapshot = self.state_model.metric_snapshot()
        for key, value in snapshot.items():
            if key in self.metric_labels:
                self.metric_labels[key].configure(text=value)
            if hasattr(self, "fan_stage_metric_labels") and key in self.fan_stage_metric_labels:
                self.fan_stage_metric_labels[key].configure(text=value)
        fault = self.state_model.latest.fault_code if self.state_model.latest else 0
        fault_color = COLORS["error"] if fault else COLORS["success"]
        self.metric_labels["fault"].configure(text_color=fault_color)
        if hasattr(self, "fan_stage_metric_labels"):
            self.fan_stage_metric_labels["fault"].configure(text_color=fault_color)
        if getattr(self, "_fan_chip_geom", None) is not None:
            self._draw_fan_chips(*self._fan_chip_geom)
        self.status_var.set(self.state_model.connection_label)
        self.connection_dot.set(True)
        self._refresh_auto_card()
        self._refresh_charts()
        self._sync_logs()

    def _refresh_auto_card(self) -> None:
        if not hasattr(self, "auto_card"):
            return
        latest = self.state_model.latest
        if latest is not None and temperature_is_valid(latest.temperature_c):
            self.auto_card.set_temperature(latest.temperature_c, self._auto_status_text(latest.temperature_c), valid=True)
        else:
            self.auto_card.set_temperature(None, "No temperature reading", valid=False)

    @staticmethod
    def _auto_status_text(temp_c: float) -> str:
        # Auto-mode-specific read of the firmware curve — not a duplicate metric.
        if temp_c <= AUTO_TEMP_START_C:
            return f"Idle · below {AUTO_TEMP_START_C:g}°C threshold"
        if temp_c >= AUTO_TEMP_FULL_C:
            return "Full power"
        return f"Ramping · {temperature_to_duty_percent(temp_c):.0f}% power"

    def _refresh_charts(self) -> None:
        speed_points = self.state_model.speed_points
        temp_points = self.state_model.temperature_points
        if speed_points:
            base = speed_points[0][0]
            xs = [(point[0] - base) / 1000 for point in speed_points]
            speed_ys = [point[1] for point in speed_points]
            self._speed_line.set_data(xs, speed_ys)
            self._target_line.set_data(xs, [point[2] for point in speed_points])
            self.speed_ax.relim()
            # Only the time axis follows the data; the RPM scale stays fixed.
            self.speed_ax.autoscale_view(scalex=True, scaley=False)
            self._speed_fill = self._fill_under(self.speed_ax, self._speed_fill, xs, speed_ys, COLORS["accent"])
        if temp_points:
            base = temp_points[0][0]
            xs = [(point[0] - base) / 1000 for point in temp_points]
            temp_ys = [point[1] for point in temp_points]
            self._temp_line.set_data(xs, temp_ys)
            self.temp_ax.relim()
            # Only the time axis follows the data; the °C scale stays fixed.
            self.temp_ax.autoscale_view(scalex=True, scaley=False)
            self._temp_fill = self._fill_under(self.temp_ax, self._temp_fill, xs, temp_ys, COLORS["error"])
        self.speed_canvas.draw_idle()
        self.temp_canvas.draw_idle()

    @staticmethod
    def _fill_under(ax, previous, xs, ys, color):
        # Soft gradient-like wash under a trace. The previous PolyCollection is
        # removed first so fills don't stack as telemetry streams in.
        if previous is not None:
            previous.remove()
        baseline = ax.get_ylim()[0]
        return ax.fill_between(xs, ys, baseline, color=color, alpha=0.10, linewidth=0)

    # ----------------------------------------------------------------- logging
    def _log(self, message: str, level: str = "info") -> None:
        self.state_model.add_log(message, level)
        if hasattr(self, "log_text"):
            self._sync_logs()

    def _sync_logs(self) -> None:
        total = self.state_model.log_count
        new = total - self._rendered_log_count
        if new <= 0:
            return
        logs = self.state_model.logs
        new = min(new, len(logs))
        at_bottom = self._log_at_bottom()
        self.log_text.configure(state="normal")
        for entry in logs[-new:]:
            self.log_text.insert("end", f"{entry.timestamp}  {entry.message}\n", entry.level)
        line_count = int(self.log_text.index("end-1c").split(".")[0])
        if line_count > MAX_LOG_LINES:
            self.log_text.delete("1.0", f"{line_count - MAX_LOG_LINES + 1}.0")
        self.log_text.configure(state="disabled")
        self._rendered_log_count = total
        if at_bottom:
            self.log_text.see("end")

    def _log_at_bottom(self) -> bool:
        # Only autoscroll when the user is already at the tail; don't yank them
        # back down while they're scrolled up reading an earlier entry.
        try:
            return self.log_text.yview()[1] >= 0.999
        except tk.TclError:
            return True

    def _set_connected(self, connected: bool) -> None:
        self.connect_button.configure(text="Disconnect" if connected else FOOTER_ACTION_LABEL_MAP["connect"])
        self.connect_button.set_variant("danger" if connected else "primary")
        self.status_var.set("Connected" if connected else "Disconnected")
        self.connection_dot.set(connected)

    def _on_close(self) -> None:
        if self._recorder is not None and self._recorder.is_recording:
            self._recorder.stop()
        try:
            self.serial_client.disconnect()
        finally:
            self.destroy()
