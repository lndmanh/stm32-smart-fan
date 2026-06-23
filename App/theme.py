"""Design tokens and CustomTkinter appearance setup for the smart-fan dashboard.

Refined-light design system layered on CustomTkinter: a cool, airy surface
palette with a crisp blue accent and a tight spacing scale. The colour / type /
radius / spacing / button-variant tokens here feed both the CustomTkinter
widgets in ``components.py`` and the matplotlib charts / canvas art in the
dashboard. Call :func:`init_theme` once after the CTk root exists.
"""

from __future__ import annotations

from tkinter import font as tkfont

import customtkinter as ctk


COLORS = {
    # Cool, airy page + card system. Backdrop sits a touch deeper than the cards
    # so white surfaces lift off the page; hairlines are barely-there for a soft,
    # modern (rather than boxy) feel.
    "bg": "#E8EDF6",          # cool light gray-blue backdrop
    "surface": "#FFFFFF",      # crisp white cards
    "surface_alt": "#F4F7FC",  # nested tiles / soft inner surface
    "border": "#ECF0F7",       # faint hairline border
    "border_strong": "#DBE2EE",  # emphasised border for the hero card
    # Slate ink (slate-900 / 600 / 400)
    "text": "#0F172A",
    "muted": "#475569",
    "subtle": "#94A3B8",
    # Blue primary (blue-600 family)
    "accent": "#2563EB",
    "accent_dark": "#1D4ED8",  # hover / pressed
    "accent_soft": "#E4ECFE",  # tinted fill for soft buttons & chips
    "accent_softer": "#CEDDFD",  # pressed state for soft buttons
    "accent_tint": "#EFF4FE",  # faint wash (halo, highlights)
    # Semantic
    "success": "#16A34A",
    "success_ring": "#DCFCE7",
    "warning": "#D97706",
    "error": "#DC2626",
    "error_soft": "#FEE2E2",
    "error_softer": "#FECACA",  # pressed state for danger buttons
    "idle_ring": "#E2E8F0",
    # Charts
    "chart": "#FBFCFE",
    "grid": "#EAEFF7",
}

# Corner radii (px) for the card system, named by role. Generous rounding reads
# softer and more contemporary than tight corners.
RADIUS = {"panel": 22, "card": 18, "pill": 14, "tile": 14, "control": 10}

# Spacing scale (px). Use these for padding/gaps so rhythm stays consistent.
SPACE = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 20, "xxl": 24, "xxxl": 30}

# Button variants: variant -> (fg_color, text_color, hover_color).
# Roles in FOOTER_ACTION_ROLES map directly onto these variant names.
BUTTON_VARIANTS = {
    "primary": (COLORS["accent"], "white", COLORS["accent_dark"]),
    "secondary": (COLORS["accent_soft"], COLORS["accent_dark"], COLORS["accent_softer"]),
    "danger": (COLORS["error_soft"], COLORS["error"], COLORS["error_softer"]),
}

# Heat palette for the auto-mode temperature hero: cool blue → hot red. Every
# stop is deep enough that white text stays legible across the whole range.
TEMP_GRADIENT_STOPS = (
    (10.0, "#1E40AF"),  # blue-800   cold
    (20.0, "#0369A1"),  # sky-700
    (30.0, "#047857"),  # emerald-700
    (40.0, "#B45309"),  # amber-700
    (50.0, "#C2410C"),  # orange-700
    (60.0, "#991B1B"),  # red-800     hot
)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(channel))) for channel in rgb)


def mix_color(start: str, end: str, t: float) -> str:
    """Linearly blend two hex colours; ``t`` in [0, 1] runs start → end."""
    a, b = _hex_to_rgb(start), _hex_to_rgb(end)
    return _rgb_to_hex((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t))


def lighten(value: str, t: float) -> str:
    return mix_color(value, "#FFFFFF", t)


def darken(value: str, t: float) -> str:
    return mix_color(value, "#000000", t)


def temperature_to_color(temp_c: float) -> str:
    """Map a temperature onto the heat palette, clamped to its end stops."""
    stops = TEMP_GRADIENT_STOPS
    if temp_c <= stops[0][0]:
        return stops[0][1]
    if temp_c >= stops[-1][0]:
        return stops[-1][1]
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t0 <= temp_c <= t1:
            return mix_color(c0, c1, (temp_c - t0) / (t1 - t0))
    return stops[-1][1]

# UI fonts are resolved at runtime against the families actually installed, so
# the dashboard prefers a modern grotesque and gracefully falls back otherwise.
UI_FONT_CANDIDATES = ("Inter", "SF Pro Display", "Helvetica Neue", "Avenir Next")
MONO_FONT_CANDIDATES = ("SF Mono", "Menlo", "Monaco", "Courier New")

# Populated by init_theme(); imported by components and read at widget creation.
FONTS: dict[str, tuple] = {}


def resolve_font_family(candidates: tuple[str, ...], available: set[str]) -> str:
    for name in candidates:
        if name in available:
            return name
    return candidates[-1]


def build_font_palette(ui_family: str, mono_family: str) -> dict[str, tuple]:
    return {
        "display": (ui_family, 38, "bold"),   # hero RPM readout
        "hero": (ui_family, 54, "bold"),      # auto-mode temperature card
        "heading": (ui_family, 24, "bold"),   # "Smart Fan" title
        "title": (ui_family, 16, "bold"),     # panel titles
        "section": (ui_family, 13, "bold"),   # chart / log headings
        "group": (ui_family, 12, "bold"),     # group / tab titles
        "button": (ui_family, 12, "bold"),
        "body": (ui_family, 12),
        "small": (ui_family, 10),
        "label": (ui_family, 11, "bold"),     # uppercase micro labels
        "mono": (mono_family, 12),
        "mono_big": (mono_family, 22, "bold"),
    }


def init_theme(root) -> dict[str, tuple]:
    """Set CustomTkinter appearance, resolve fonts, return the font palette."""
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    available = set(tkfont.families(root))
    FONTS.clear()
    FONTS.update(
        build_font_palette(
            resolve_font_family(UI_FONT_CANDIDATES, available),
            resolve_font_family(MONO_FONT_CANDIDATES, available),
        )
    )
    return FONTS
