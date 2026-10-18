"""Темы оформления приложения: светлая и тёмная.

Единый источник палитры для customtkinter-виджетов и ttk-таблицы.
Состояние (выбранный режим) сохраняется в simplecache customtkinter,
следующий запуск стартует с той же темой.
"""
from __future__ import annotations

import tkinter as tk
import tkinter.ttk as ttk
from dataclasses import dataclass

import customtkinter as ctk


@dataclass(frozen=True)
class ThemePalette:
    """Набор цветов, используемых UI вне стандартных ролей customtkinter."""
    window_bg: str        # фон корневого окна (заодно фон ttk-виджетов)
    panel_bg: str         # фон панелей и области таблицы
    header_bg: str        # фон шапки таблицы
    text: str             # основной текст
    muted_text: str       # второстепенный текст (переключатели дерева, статус)
    border: str           # тонкие линии-разделители
    selected: str         # выделение узла/строки
    selected_text: str    # текст на выделении
    row_alt: str          # альтернативная (чётная) строка таблицы
    hover: str            # подсветка строк дерева при наведении


LIGHT = ThemePalette(
    window_bg='#f4f5f7',
    panel_bg='#ffffff',
    header_bg='#e8eaed',
    text='#1d1d1f',
    muted_text='#6b7280',
    border='#d5d9de',
    selected='#2f6fb2',
    selected_text='#ffffff',
    row_alt='#f2f5f9',
    hover='#e3e7ec',
)

DARK = ThemePalette(
    window_bg='#1a1b1e',
    panel_bg='#242526',
    header_bg='#3a3d40',
    text='#e6e6e6',
    muted_text='#9aa0a6',
    border='#4a4d50',
    selected='#1f538d',
    selected_text='#ffffff',
    row_alt='#2c2d30',
    hover='#3a3d41',
)

PALETTES = {'light': LIGHT, 'dark': DARK}

#: Значение по умолчанию, если тема ещё не выбиралась.
DEFAULT_MODE = 'dark'


def current_mode() -> str:
    """Сохранённый режим темы: 'light' или 'dark'.

    ``get_appearance_mode()`` возвращает строку с заглавной буквы
    ('Light'/'Dark') и 'System', если режим не задавался явно, —
    нормализуем к ключам палитры.
    """
    saved = ctk.get_appearance_mode().lower()
    return saved if saved in PALETTES else DEFAULT_MODE


def palette(mode: str | None = None) -> ThemePalette:
    return PALETTES[mode or current_mode()]


def apply_theme(mode: str) -> None:
    """Переключить тему приложения целиком.

    * customtkinter меняет ``set_appearance_mode``;
    * ttk-стили перестраиваются под новую палитру;
    * корневое окно перекрашивается (ttk-виджеты наследуют его фон);
    * все слушатели события ``<<ThemeChanged>>`` обновляют свои цвета
      (например, дерево контейнеров).
    """
    if mode not in PALETTES:
        mode = DEFAULT_MODE
    ctk.set_appearance_mode(mode)
    apply_ttk_theme()
    root = tk._default_root  # noqa: SLF001 — единственный способ достать корень Tk
    if root is not None:
        bg = palette(mode).window_bg
        for widget in _walk(root):
            # CTk-виджеты (CTk/CTkToplevel/CTkFrame) не принимают Tk-опцию
            # ``bg`` — они перекрашиваются сами через set_appearance_mode.
            if isinstance(widget, ctk.CTkBaseClass):
                continue
            try:
                if widget.winfo_class() in ('Toplevel', 'Frame'):
                    widget.configure(bg=bg)
            except (tk.TclError, ValueError):
                pass
        try:
            root.event_generate('<<ThemeChanged>>')
        except tk.TclError:
            pass


def _walk(widget: tk.Misc):
    for child in widget.winfo_children():
        yield child
        yield from _walk(child)


def apply_ttk_theme() -> None:
    """Настроить стили ttk (Treeview) под текущую тему."""
    pal = palette()
    style = ttk.Style()
    try:
        style.theme_use('clam')
    except tk.TclError:
        pass

    style.configure(
        'App.Treeview',
        background=pal.panel_bg,
        fieldbackground=pal.panel_bg,
        foreground=pal.text,
        rowheight=28,
        bordercolor=pal.border,
        lightcolor=pal.panel_bg,
        darkcolor=pal.panel_bg,
        relief='flat',
    )
    # Разделители между столбцами: рисуем рамкой ячейки ``::text``
    # (borderwidth + orient='vertical' + bordercolor) — линии живут внутри
    # таблицы, не перекрывают текст и не требуют canvas-оверлеев.
    try:
        style.element_options('Treeview.cell')
        style.configure('Treeview.Cell',
                        borderwidth=1, relief='solid',
                        bordercolor=pal.border, lightcolor=pal.border,
                        darkcolor=pal.border)
    except tk.TclError:
        pass
    style.configure(
        'App.Treeview.Heading',
        background=pal.header_bg,
        foreground=pal.text,
        font=('TkDefaultFont', 10, 'bold'),
        bordercolor=pal.border,
        lightcolor=pal.header_bg,
        darkcolor=pal.header_bg,
        relief='flat',
        padding=(8, 6),
    )
    try:
        style.element_options('Treeheading.cell')
        style.configure('Treeview.HeadingCell',
                        borderwidth=1, relief='solid',
                        bordercolor=pal.border, lightcolor=pal.border,
                        darkcolor=pal.border)
    except tk.TclError:
        pass
    style.map(
        'App.Treeview',
        background=[('selected', pal.selected)],
        foreground=[('selected', pal.selected_text)],
    )
    style.map(
        'App.Treeview.Heading',
        background=[('active', pal.hover)],
        foreground=[('active', pal.text)],
    )

