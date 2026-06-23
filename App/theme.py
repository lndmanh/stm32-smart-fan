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
    # Cool, airy page + card system
    "bg": "#EEF2F8",          # cool light gray-blue backdrop
    "surface": "#FFFFFF",      # crisp white cards
    "surface_alt": "#F4F7FB",  # nested tiles / soft inner surface
    "border": "#E2E8F0",       # crisp slate hairline border
    "border_strong": "#CBD5E1",  # emphasised border for the hero card
    # Slate ink (slate-900 / 600 / 400)
    "text": "#0F172A",
    "muted": "#475569",
    "subtle": "#94A3B8",
    # Blue primary (blue-600 family)
    "accent": "#2563EB",
    "accent_dark": "#1D4ED8",  # hover / pressed
    "accent_soft": "#DBEAFE",  # tinted fill for soft buttons & chips
    "accent_softer": "#BFDBFE",  # pressed state for soft buttons
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
    "chart": "#F8FAFC",
    "grid": "#E9EEF6",
}

# Corner radii (px) for the card system, named by role.
RADIUS = {"panel": 18, "card": 16, "pill": 12, "tile": 12, "control": 8}

# Spacing scale (px). Use these for padding/gaps so rhythm stays consistent.
SPACE = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 20, "xxl": 24}

# Button variants: variant -> (fg_color, text_color, hover_color).
# Roles in FOOTER_ACTION_ROLES map directly onto these variant names.
BUTTON_VARIANTS = {
    "primary": (COLORS["accent"], "white", COLORS["accent_dark"]),
    "secondary": (COLORS["accent_soft"], COLORS["accent_dark"], COLORS["accent_softer"]),
    "danger": (COLORS["error_soft"], COLORS["error"], COLORS["error_softer"]),
}

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
