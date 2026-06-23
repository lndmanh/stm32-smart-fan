"""Reusable CustomTkinter components built on the tokens in ``theme.py``.

These wrap the recurring UI primitives (cards, buttons, fields, labels, tiles)
so call sites compose named components instead of repeating colour/font/radius
styling. Fonts are read from :data:`theme.FONTS` at construction time, so
:func:`theme.init_theme` must run before any component is created.
"""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from theme import BUTTON_VARIANTS, COLORS, FONTS, RADIUS, SPACE


def _color(value: str) -> str:
    """Resolve a palette token name to its hex, or pass a literal colour through."""
    return COLORS.get(value, value)


def text_label(parent, text: str | None = None, *, font: str = "body", fg: str = "text", bg: str = "transparent", anchor: str = "w", **kw) -> ctk.CTkLabel:
    """A CTkLabel wired to the type/colour tokens. ``fg``/``bg`` accept token names or literal colours."""
    if text is not None:
        kw["text"] = text
    fg_color = "transparent" if bg in (None, "transparent") else _color(bg)
    return ctk.CTkLabel(parent, font=FONTS[font], text_color=_color(fg), fg_color=fg_color, anchor=anchor, **kw)


class Card(ctk.CTkFrame):
    """Rounded, bordered surface. Add children to ``.body`` (inset content frame)."""

    def __init__(self, parent, fill: str | None = None, radius: int | None = None, inset: int = SPACE["lg"], outline: str | None = None, shadow: bool = True, **kwargs):
        super().__init__(
            parent,
            corner_radius=radius if radius is not None else RADIUS["card"],
            fg_color=fill or COLORS["surface"],
            border_width=1,
            border_color=outline or COLORS["border"],
            **kwargs,
        )
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=inset, pady=inset)


class Button(ctk.CTkButton):
    """Themed button. ``variant`` is one of primary / secondary / danger."""

    def __init__(self, parent, text: str = "", command=None, *, variant: str = "primary", **kw):
        self._variant = variant
        fg, text_color, hover = BUTTON_VARIANTS[variant]
        kw.setdefault("corner_radius", RADIUS["control"])
        kw.setdefault("font", FONTS["button"])
        super().__init__(parent, text=text, command=command, fg_color=fg, hover_color=hover, text_color=text_color, **kw)

    def set_variant(self, variant: str) -> None:
        self._variant = variant
        fg, text_color, hover = BUTTON_VARIANTS[variant]
        self.configure(fg_color=fg, hover_color=hover, text_color=text_color)


class Field(ctk.CTkEntry):
    """Themed single-line text entry; shares the soft fill used by dropdowns."""

    def __init__(self, parent, textvariable: tk.StringVar, *, width: int | None = None, **kw):
        if width is not None:
            kw["width"] = width
        super().__init__(
            parent,
            textvariable=textvariable,
            corner_radius=RADIUS["control"],
            fg_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
            border_color=COLORS["border"],
            border_width=1,
            font=FONTS["mono"],
            **kw,
        )


class Dropdown(ctk.CTkOptionMenu):
    """Themed read-only selection menu."""

    def __init__(self, parent, variable: tk.StringVar, values, **kw):
        super().__init__(
            parent,
            variable=variable,
            values=list(values) or [""],
            corner_radius=RADIUS["control"],
            fg_color=COLORS["surface_alt"],
            button_color=COLORS["accent_soft"],
            button_hover_color=COLORS["accent_softer"],
            text_color=COLORS["text"],
            font=FONTS["body"],
            dropdown_fg_color=COLORS["surface"],
            dropdown_text_color=COLORS["text"],
            dropdown_hover_color=COLORS["accent_soft"],
            dropdown_font=FONTS["body"],
            **kw,
        )


class MicroLabel(ctk.CTkLabel):
    """Uppercase micro caption used above fields, tiles and chips."""

    def __init__(self, parent, text: str, *, bg: str = "transparent", **kw):
        super().__init__(parent, text=text.upper(), fg_color="transparent", text_color=COLORS["subtle"], font=FONTS["label"], anchor="w", **kw)


class GroupCard(ctk.CTkFrame):
    """Bordered soft-surface group with a title; controls grid into rows >= 1."""

    def __init__(self, parent, title: str, columns: int = 2):
        super().__init__(parent, corner_radius=RADIUS["tile"], fg_color=COLORS["surface_alt"], border_width=1, border_color=COLORS["border"])
        for column in range(columns):
            self.grid_columnconfigure(column, weight=1)
        text_label(self, title, font="group", bg="surface_alt").grid(
            row=0, column=0, columnspan=columns, sticky="w", padx=SPACE["md"], pady=(SPACE["sm"], SPACE["xs"] + 2)
        )


class MetricTile(ctk.CTkFrame):
    """Soft tile showing an uppercase caption above a value. Update via ``.value``."""

    def __init__(self, parent, title: str, value_font, *, value: str = "--"):
        super().__init__(parent, corner_radius=RADIUS["tile"], fg_color=COLORS["surface_alt"], border_width=1, border_color=COLORS["border"])
        MicroLabel(self, title).pack(anchor="w", padx=SPACE["md"], pady=(SPACE["sm"], 0))
        self.value = ctk.CTkLabel(self, text=value, fg_color="transparent", text_color=COLORS["text"], font=value_font, anchor="w")
        self.value.pack(anchor="w", padx=SPACE["md"], pady=(2, SPACE["sm"]))


class ConnectionDot(tk.Canvas):
    """Small status indicator: green ring when connected, slate when idle."""

    def __init__(self, parent, size: int = 26, bg: str = COLORS["surface"]):
        super().__init__(parent, width=size, height=size, bg=bg, highlightthickness=0, bd=0)
        self.set(False)

    def set(self, connected: bool) -> None:
        self.delete("all")
        self.create_oval(2, 2, 24, 24, fill=COLORS["success_ring" if connected else "idle_ring"], outline="")
        self.create_oval(8, 8, 18, 18, fill=COLORS["success" if connected else "subtle"], outline="")
