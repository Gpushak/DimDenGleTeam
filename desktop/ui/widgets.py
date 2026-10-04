"""Вспомогательные виджеты для тёмной темы customtkinter.

Содержит:
* ``apply_dark_theme`` — настройка ttk-виджетов (Treeview, Scrollbar) под тёмную тему;
* ``AutoScrollbar``   — ttk.Scrollbar, который исчезает, когда содержимое помещается целиком;
* ``DarkScrollableFrame`` — CTkScrollableFrame с автоскрывающимся скроллбаром и тёмным фоном.
"""
import tkinter as tk
import tkinter.ttk as ttk

import customtkinter as ctk


# Палитра тёмной темы приложения (согласована с темой customtkinter 'dark').
# Константы используются внутри модуля; наружу отдаются те, что нужны UI.
DARK_PANEL = '#252525'       # фон панелей и области таблиц
DARK_HEADER = '#3a3d40'      # фон шапки таблицы
DARK_TEXT = '#e6e6e6'        # основной текст
DARK_BORDER = '#4a4d50'      # границы и разделители колонок
DARK_SELECTED = '#1f538d'    # выделение строки

# Цвета скроллбаров и строк таблицы — используются только здесь.
_SCROLLBAR = '#5c5c5c'
_ROW_ODD = '#2f2f2f'


def apply_dark_theme() -> None:
    """Настроить стили ttk так, чтобы таблицы соответствовали тёмной теме."""
    style = ttk.Style()
    try:
        style.theme_use('clam')
    except tk.TclError:
        pass

    style.configure(
        'Dark.Treeview',
        background=DARK_PANEL,
        fieldbackground=DARK_PANEL,
        foreground=DARK_TEXT,
        rowheight=28,
        bordercolor=DARK_BORDER,
        lightcolor=DARK_PANEL,
        darkcolor=DARK_PANEL,
        relief='flat',
    )
    style.configure(
        'Dark.Treeview.Heading',
        background=DARK_HEADER,
        foreground=DARK_TEXT,
        font=('TkDefaultFont', 10, 'bold'),
        bordercolor=DARK_BORDER,
        lightcolor=DARK_HEADER,
        darkcolor=DARK_HEADER,
        relief='raised',
        padding=(8, 6),
    )
    style.map(
        'Dark.Treeview',
        background=[('selected', DARK_SELECTED)],
        foreground=[('selected', '#ffffff')],
    )
    style.map(
        'Dark.Treeview.Heading',
        background=[('active', '#46494d')],
        foreground=[('active', '#ffffff')],
    )

    style.configure(
        'Dark.Vertical.TScrollbar',
        background=_SCROLLBAR,
        troughcolor=DARK_PANEL,
        bordercolor=DARK_BORDER,
        arrowcolor=DARK_TEXT,
        lightcolor=_SCROLLBAR,
        darkcolor=_SCROLLBAR,
    )
    style.configure(
        'Dark.Horizontal.TScrollbar',
        background=_SCROLLBAR,
        troughcolor=DARK_PANEL,
        bordercolor=DARK_BORDER,
        arrowcolor=DARK_TEXT,
        lightcolor=_SCROLLBAR,
        darkcolor=_SCROLLBAR,
    )


class AutoScrollbar(ttk.Scrollbar):
    """Скроллбар, который не показывается, если всё содержимое влезает.

    Стандартный ttk.Scrollbar всегда занимает место даже при полном
    видимом содержимом. Этот класс подавляет показ ``set``/``pack``/``grid``,
    когда область прокрутки равна окну просмотра (first == 0, last == 1).
    """

    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            # содержимое помещается целиком — прячем скроллбар
            self.forget()
            # блокируем отрисовку ползунка
            super().set(0.0, 1.0)
            return
        if not self.winfo_manager():
            self._autoshow()
        super().set(lo, hi)

    def _autoshow(self):
        """Показать скроллбар способом, которым его разместил владелец."""
        info = getattr(self, '_auto_place', None)
        if not info:
            return
        method, args, kwargs = info
        method(*args, **kwargs)


class DarkTableFrame(ctk.CTkFrame):
    """Тёмная панель со Treeview и скроллбарами, исчезающими без необходимости.

    * фон панели соответствует тёмной теме приложения;
    * вертикальный скроллбар появляется только если строк больше, чем видно;
    * горизонтальный скроллбар — только если колонки не влезают по ширине;
    * ``xview_var`` меняется при прокрутке (для перерисовки разделителей колонок).
    """

    def __init__(self, master, columns=None, headings=None, column_widths=None,
                 **kwargs):
        super().__init__(master, fg_color=DARK_PANEL, border_width=1,
                         border_color=DARK_BORDER, corner_radius=8, **kwargs)

        self.tree = ttk.Treeview(
            self,
            columns=tuple(columns or ()),
            show='headings',
            style='Dark.Treeview',
            selectmode='browse',
        )

        # переменная позиции горизонтальной прокрутки (отслеживается снаружи)
        self.xview_var = tk.StringVar()

        self._vbar = AutoScrollbar(self, orient='vertical', command=self.tree.yview)
        self._hbar = AutoScrollbar(self, orient='horizontal', command=self._xview_command)
        self.tree.configure(yscrollcommand=self._vbar.set, xscrollcommand=self._xset)

        self._vbar._auto_place = (self._vbar.pack, (), {'side': 'right', 'fill': 'y'})
        self._hbar._auto_place = (self._hbar.pack, (), {'side': 'bottom', 'fill': 'x'})

        # Полоса разделителей колонок над таблицей создаётся здесь, до
        # раскладки: порядок pack важен — сначала полосы скроллов по краям
        # и линейка сверху, затем Treeview. Иначе при появлении скроллбаров
        # полоса смещается относительно таблицы и метки колонок «съезжают».
        self._sep_height = 6
        self._sep_canvas = tk.Canvas(
            self, height=self._sep_height, highlightthickness=0, bd=0,
            bg=DARK_PANEL, cursor='tcross', takefocus=0,
        )

        self._vbar.pack(side='right', fill='y')
        self._hbar.pack(side='bottom', fill='x')
        self._sep_canvas.pack(side='top', fill='x')
        self.tree.pack(side='left', fill='both', expand=True)

        for col in (columns or ()):
            width = (column_widths or {}).get(col, 120)
            text = (headings or {}).get(col, col)
            self.tree.heading(col, text=text, anchor='w')
            self.tree.column(col, width=width, minwidth=60, anchor='w', stretch=True)

        # Чередование строк для читаемости
        self.tree.tag_configure('oddrow', background=_ROW_ODD)
        self.tree.tag_configure('evenrow', background=DARK_PANEL)
        self._row_count = 0

        # Полоса разделителей (_sep_canvas) создана выше, до раскладки.
        self._sep_canvas.bind('<Configure>',
                              lambda e: self.refresh_column_separators())
        self._sep_pending = None
        self.tree.bind('<Configure>',
                       lambda e: self.refresh_column_separators(), add='+')

    def refresh_column_separators(self):
        """Перерисовать вертикальные разделители между колонками Treeview."""
        if self._sep_pending is not None:
            try:
                self.after_cancel(self._sep_pending)
            except Exception:
                pass
        self._sep_pending = self.after_idle(self._draw_column_separators)

    def _draw_column_separators(self):
        self._sep_pending = None
        canvas = self._sep_canvas
        tree = self.tree
        canvas.delete('all')
        if not canvas.winfo_exists() or not tree.winfo_exists():
            return
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w <= 1 or h <= 1:
            return
        cols = tree['columns']
        if len(cols) < 2:
            return

        # смещение горизонтальной прокрутки в пикселях
        first, last = tree.xview()
        total_w = sum(tree.column(c, 'width') for c in cols)
        offset = int(first * total_w)

        # Границы колонок (метки на полосе над таблицей). Полоса лежит
        # над Treeview, поэтому её левый край смещён относительно таблицы —
        # координаты пересчитываются через winfo_pointerxy-независимый
        # перевод: x_полосы = x_таблицы + (tree.rootx - canvas.rootx).
        dx = tree.winfo_rootx() - canvas.winfo_rootx()
        h = canvas.winfo_height()

        x = -offset + dx
        for c in cols[:-1]:
            x += tree.column(c, 'width')
            if 0 < x < w:
                canvas.create_line(x, 0, x, h, fill=DARK_BORDER)

    def _xview_command(self, *args):
        self.tree.xview(*args)
        self._sync_xview_var()

    def _xset(self, lo, hi):
        self._hbar.set(lo, hi)
        self.xview_var.set(f'{lo} {hi}')
        self.refresh_column_separators()

    def _sync_xview_var(self):
        lo, hi = self.tree.xview()
        self.xview_var.set(f'{lo} {hi}')

    def clear(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self._row_count = 0


class DarkScrollableFrame(ctk.CTkScrollableFrame):
    """CTkScrollableFrame с тёмным фоном и скроллбаром, скрытым когда он не нужен.

    Встроенный CTkScrollbar всегда занимает место справа; здесь он заменяется
    на собственный canvas-скроллбар, который рисуется только при реальной
    необходимости (содержимое выше области просмотра).
    """

    BAR_WIDTH = 12
    BAR_COLOR = ('#b0b0b0', '#5c5c5c')
    BAR_TROUGH = 'transparent'

    def __init__(self, master, **kwargs):
        kwargs.setdefault('fg_color', DARK_PANEL)
        super().__init__(master, **kwargs)

        # Родительский CTkFrame перерисовывает свой canvas при любом
        # изменении размера — после этого перерисуем и наш скроллбар,
        # чтобы он не оказался под фоном рамки.
        parent_canvas = self._parent_frame._canvas
        parent_canvas.bind('<Configure>', lambda e: self._schedule_redraw(), add=True)

        self._auto_bar = tk.Canvas(
            self._parent_frame,
            width=self._apply_widget_scaling(self.BAR_WIDTH),
            height=1,
            highlightthickness=0,
            bd=0,
            bg=self._canvas_bg(),
        )
        self._auto_bar.place(x=-self._apply_widget_scaling(self.BAR_WIDTH + 6), rely=0.5,
                             anchor='e', relheight=0.94)
        self._auto_bar.bind('<Button-1>', self._bar_clicked)
        self._auto_bar.bind('<B1-Motion>', self._bar_drag)

        self._parent_canvas.configure(yscrollcommand=self._auto_set)
        self._parent_canvas.bind('<Configure>', lambda e: self._schedule_redraw(), add=True)

        self._thumb_start = 0.0
        self._thumb_end = 1.0
        self._drag_offset = 0.0
        self._redraw_job = None

    def _canvas_bg(self) -> str:
        fg = self._parent_frame.cget('fg_color')
        color = self._parent_frame.cget('bg_color') if fg == 'transparent' else fg
        return self._apply_appearance_mode(color)

    # -- синхронизация с канвасом -------------------------------------------
    def _auto_set(self, lo, hi):
        self._thumb_start = float(lo)
        self._thumb_end = float(hi)
        self._schedule_redraw()

    def _schedule_redraw(self):
        """Перерисовать ползунок после завершения текущих событий Tk."""
        if self._redraw_job is not None:
            try:
                self.winfo_toplevel().after_cancel(self._redraw_job)
            except Exception:
                pass
        try:
            self._redraw_job = self.winfo_toplevel().after_idle(self._redraw_bar)
        except Exception:
            self._redraw_bar()

    def _after_content_change(self):
        """Обновить scrollregion и видимость скроллбара после изменения содержимого."""
        self._parent_canvas.update_idletasks()
        bbox = self._parent_canvas.bbox('all')
        if bbox:
            self._parent_canvas.configure(scrollregion=bbox)
        self._redraw_bar()

    @property
    def _needs_scroll(self) -> bool:
        region = self._parent_canvas.bbox('all')
        if not region:
            return False
        content_h = region[3] - region[1]
        return content_h > self._parent_canvas.winfo_height() + 1

    def _redraw_bar(self):
        self._redraw_job = None
        if not self._auto_bar.winfo_exists():
            return
        self._auto_bar.configure(bg=self._canvas_bg())
        self._auto_bar.delete('all')
        if not self._needs_scroll:
            return
        h = self._auto_bar.winfo_height()
        w = self._auto_bar.winfo_width()
        if h <= 1 or w <= 1:
            return
        top = max(0, int(self._thumb_start * h))
        bottom = min(h, int(self._thumb_end * h))
        if bottom - top < 20:
            bottom = min(h, top + 20)
        pad = 2
        try:
            self._auto_bar.create_rectangle(pad, top, w - pad, bottom, radius=4,
                                            fill=self._apply_appearance_mode(self.BAR_COLOR),
                                            outline='')
        except tk.TclError:
            # Tk < 8.7 не поддерживает сглаженные углы у прямоугольников
            self._auto_bar.create_rectangle(pad, top, w - pad, bottom,
                                            fill=self._apply_appearance_mode(self.BAR_COLOR),
                                            outline='')

    # -- взаимодействие -------------------------------------------------------
    def _value_from_y(self, y):
        h = max(1, self._auto_bar.winfo_height())
        length = self._thumb_end - self._thumb_start
        center = min(max(y / h, length / 2), 1 - length / 2)
        start = center - length / 2
        self._parent_canvas.yview_moveto(start)

    def _bar_clicked(self, event):
        h = max(1, self._auto_bar.winfo_height())
        self._drag_offset = ((self._thumb_start + self._thumb_end) / 2) - event.y / h
        self._value_from_y(event.y)

    def _bar_drag(self, event):
        h = max(1, self._auto_bar.winfo_height())
        self._value_from_y(event.y + self._drag_offset * h)
