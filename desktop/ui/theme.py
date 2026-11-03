"""Темы оформления приложения: светлая и тёмная.

Единый источник палитры для customtkinter-виджетов и ttk-таблицы.
Состояние (выбранный режим) сохраняется в simplecache customtkinter,
следующий запуск стартует с той же темой.
"""
from __future__ import annotations

import ctypes
import sys
import tkinter as tk
import tkinter.ttk as ttk
from dataclasses import dataclass
from pathlib import Path

import customtkinter as ctk
from customtkinter.windows.widgets.appearance_mode import CTkAppearanceModeBaseClass

# Смена цвета заголовка в customtkinter прячет окно (withdraw + update).
# Это и даёт паузу, и оставляет белую полосу, пока окно рисуется заново.
ctk.CTk._deactivate_windows_window_header_manipulation = True
ctk.CTkToplevel._deactivate_windows_window_header_manipulation = True


def _set_appearance_mode_fast(self, mode_string):
    """Перекрасить виджет без update_idletasks на каждом узле дерева."""
    CTkAppearanceModeBaseClass._set_appearance_mode(self, mode_string)
    self._draw()


ctk.CTkBaseClass._set_appearance_mode = _set_appearance_mode_fast

# CTkScrollbar._draw в конце вызывает canvas.update_idletasks(). Посреди
# смены темы этот сброс вложенно перерисовывает всё окно. Цвета к этому
# моменту уже заданы, геометрию Tk дорисует сам, когда обработчик вернётся.
_scrollbar_draw = ctk.CTkScrollbar._draw
_theme_switching = False


def _scrollbar_draw_fast(self, no_color_updates=False):
    if not _theme_switching:
        _scrollbar_draw(self, no_color_updates)
        return
    idle = self._canvas.update_idletasks
    self._canvas.update_idletasks = lambda: None
    try:
        _scrollbar_draw(self, no_color_updates)
    finally:
        self._canvas.update_idletasks = idle


ctk.CTkScrollbar._draw = _scrollbar_draw_fast

_THEME_FILE = Path(__file__).with_name("app_theme.json")
_color_theme_loaded = False


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
    window_bg='#e6e9ee',
    panel_bg='#ffffff',
    header_bg='#d5dbe3',
    text='#121417',
    muted_text='#3e4651',
    border='#b7bec8',
    selected='#165a96',
    selected_text='#ffffff',
    row_alt='#f2f4f7',
    hover='#d5dbe3',
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


def _ensure_color_theme() -> None:
    """Подменить стандартную тему customtkinter на палитру приложения."""
    global _color_theme_loaded
    if _color_theme_loaded:
        return
    ctk.set_default_color_theme(str(_THEME_FILE))
    _color_theme_loaded = True


def _colorref(hex_color: str) -> int:
    """#RRGGBB → COLORREF (0x00BBGGRR), как ждёт DWM."""
    hex_color = hex_color.lstrip("#")
    red = int(hex_color[0:2], 16)
    green = int(hex_color[2:4], 16)
    blue = int(hex_color[4:6], 16)
    return red | (green << 8) | (blue << 16)


def paint_titlebar(window, mode: str | None = None) -> None:
    """Покрасить заголовок Windows в цвет верхней панели.

    Иначе над окном остаётся системная белая полоса. Смена темы
    не прячет окно: customtkinter для этого делал withdraw().
    """
    if not sys.platform.startswith("win"):
        return
    try:
        if not window.winfo_exists():
            return
        hwnd = _window_hwnd(window)
    except (tk.TclError, AttributeError, OSError):
        return
    if not hwnd:
        return
    pal = palette(mode)
    dark = 1 if (mode or current_mode()) == "dark" else 0
    caption = _colorref(pal.panel_bg)
    text = _colorref(pal.text)
    # Отдельная загрузка DLL, чтобы не менять argtypes у общего windll,
    # которым пользуется сам Tk.
    dwm = ctypes.WinDLL("dwmapi", use_last_error=True)
    dwm.DwmSetWindowAttribute.argtypes = [
        ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint,
    ]
    dwm.DwmSetWindowAttribute.restype = ctypes.c_long
    # 19/20 — тёмный заголовок, 34 — кромка (белая линия Win11), 35 — фон, 36 — текст.
    for attr, value in ((20, dark), (19, dark), (34, caption), (35, caption), (36, text)):
        dwm.DwmSetWindowAttribute(
            hwnd, attr, ctypes.byref(ctypes.c_int(value)), ctypes.sizeof(ctypes.c_int),
        )

def _window_hwnd(window) -> int:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    user32.GetAncestor.restype = ctypes.c_void_p
    user32.GetParent.argtypes = [ctypes.c_void_p]
    user32.GetParent.restype = ctypes.c_void_p
    widget_id = window.winfo_id()
    hwnd = user32.GetAncestor(widget_id, 2)  # GA_ROOT
    if not hwnd:
        hwnd = user32.GetParent(widget_id)
    return int(hwnd or 0)


def _paint_open_windows(root) -> None:
    paint_titlebar(root)
    for widget in _walk(root):
        if widget.winfo_class() == "Toplevel":
            paint_titlebar(widget)


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
    _ensure_color_theme()
    global _theme_switching
    _theme_switching = True
    try:
        ctk.set_appearance_mode(mode)
    finally:
        _theme_switching = False
    apply_ttk_theme()
    root = tk._default_root  # noqa: SLF001 — единственный способ достать корень Tk
    if root is not None:
        bg = palette(mode).window_bg
        if isinstance(root, ctk.CTk):
            desired = (LIGHT.window_bg, DARK.window_bg)
            try:
                current = root.cget("fg_color")
                if tuple(current) != desired:
                    root.configure(fg_color=desired)
            except (tk.TclError, ValueError, TypeError):
                pass
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
        _paint_open_windows(root)
        # Окно ещё может быть не показано: Windows сбрасывает цвет
        # заголовка в момент первого отображения.
        def _repaint(widget=root):
            try:
                if widget.winfo_exists():
                    _paint_open_windows(widget)
            except tk.TclError:
                pass

        for delay in (0, 50, 200):
            root.after(delay, _repaint)


def _walk(widget: tk.Misc):
    for child in widget.winfo_children():
        yield child
        yield from _walk(child)


def apply_ttk_theme() -> None:
    """Настроить стили ttk (Treeview) под текущую тему."""
    pal = palette()
    style = ttk.Style()
    try:
        # theme_use шлёт <<ThemeChanged>> каждому виджету. Повторный вызов
        # на уже включённой теме делает то же самое и тормозит переключение.
        if style.theme_use() != 'clam':
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

