"""Вспомогательные виджеты, согласованные с темой приложения.

Содержит:
* ``AutoScrollbar``       — ttk.Scrollbar, исчезающий, когда содержимое помещается целиком;
* ``DarkTableFrame``      — панель со Treeview без лишних рамок и с автоскроллбарами;
* ``DarkScrollableFrame`` — CTkScrollableFrame с тонким ползунком прокрутки.

Названия классов сохранены для совместимости с существующим кодом UI,
но цвета берутся из текущей темы (``ui.theme``), а не зашиты как тёмные.
"""
import tkinter as tk
import tkinter.ttk as ttk

import customtkinter as ctk

from ui import theme


# ------------------------------------------------------------------ совместимость
def apply_dark_theme() -> None:
    """Устаревший алиас: настраивает ttk-стили под текущую тему."""
    theme.apply_ttk_theme()


#: Палитра по умолчанию (используется только если тема ещё не выбрана).
DARK_PANEL = theme.DARK.panel_bg
DARK_HEADER = theme.DARK.header_bg
DARK_TEXT = theme.DARK.text
DARK_BORDER = theme.DARK.border
DARK_SELECTED = theme.DARK.selected


class AutoScrollbar(ttk.Scrollbar):
    """Скроллбар, который не показывается, если всё содержимое влезает.

    Стандартный ttk.Scrollbar всегда занимает место даже при полном
    видимом содержимом. Этот класс подавляет показ ``set``, когда область
    прокрутки равна окну просмотра (first == 0, last == 1).
    """

    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            # содержимое помещается целиком — прячем скроллбар
            self.forget()
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
    """Панель со Treeview и скроллбарами, исчезающими без необходимости.

    * фон панели берётся из текущей темы;
    * рамок нет: панель отличима фоном, разграничителями служат только
      шапка таблицы и тонкие разделители колонок;
    * вертикальный скроллбар появляется только если строк больше, чем видно;
    * горизонтальный — только если колонки не влезают по ширине;
    * при смене темы (событие ``<<ThemeChanged>>``) перекрашивается сам.
    """

    def __init__(self, master, columns=None, headings=None, column_widths=None,
                 **kwargs):
        kwargs.setdefault('fg_color', 'transparent')
        kwargs.setdefault('corner_radius', 8)
        super().__init__(master, **kwargs)

        pal = theme.palette()
        self.configure(fg_color=pal.panel_bg)

        self.tree = ttk.Treeview(
            self,
            columns=tuple(columns or ()),
            show='headings',
            style='App.Treeview',
            selectmode='browse',
        )

        # переменная позиции горизонтальной прокрутки (отслеживается снаружи)
        self.xview_var = tk.StringVar()

        self._vbar = AutoScrollbar(self, orient='vertical',
                                   style='App.Vertical.TScrollbar',
                                   command=self.tree.yview)
        self._hbar = AutoScrollbar(self, orient='horizontal',
                                   style='App.Horizontal.TScrollbar',
                                   command=self._xview_command)
        self.tree.configure(yscrollcommand=self._vbar.set, xscrollcommand=self._xset)

        self._vbar._auto_place = (self._vbar.pack, (), {'side': 'right', 'fill': 'y'})
        self._hbar._auto_place = (self._hbar.pack, (), {'side': 'bottom', 'fill': 'x'})

        # Полоса разделителей колонок поверх шапки таблицы создаётся здесь,
        # до раскладки: порядок pack важен — сначала полосы скроллов по
        # краям, затем Treeview. Иначе при появлении скроллбаров полоса
        # смещается относительно таблицы и метки колонок «съезжают».
        self._sep_height = 6
        self._sep_canvas = tk.Canvas(
            self, height=self._sep_height, highlightthickness=0, bd=0,
            bg=pal.header_bg, takefocus=0,
        )

        # Клик по полосе разделителей (она лежит поверх шапки Treeview и
        # перехватывает события заголовков) прокидывается в дерево: сортировка
        # по клику на колонку работает через heading(command=...).
        def _forward(event):
            col = self.tree.identify_column(event.x - self.tree.winfo_x())
            if col and col != '#0':
                try:
                    index = int(col[1:]) - 1
                    cmd = self.tree.heading(self.tree['columns'][index], 'command')
                    if cmd:
                        self.tree.tk.eval(cmd)
                except (ValueError, IndexError, tk.TclError):
                    pass
            return 'break'

        self._sep_canvas.bind('<Button-1>', _forward)
        self._sep_canvas.bind('<Double-1>', _forward)

        self._vbar.pack(side='right', fill='y')
        self._hbar.pack(side='bottom', fill='x')
        self.tree.pack(side='left', fill='both', expand=True)
        # Поверх шапки Treeview (place не участвует в раскладке pack и не
        # сдвигает строки таблицы).
        self._place_separators_strip()

        for col in (columns or ()):
            width = (column_widths or {}).get(col, 120)
            text = (headings or {}).get(col, col)
            self.tree.heading(col, text=text, anchor='w')
            self.tree.column(col, width=width, minwidth=60, anchor='w', stretch=True)

        # Чередование строк для читаемости
        self.tree.tag_configure('oddrow', background=pal.row_alt)
        self.tree.tag_configure('evenrow', background=pal.panel_bg)
        self._row_count = 0

        self._sep_canvas.bind('<Configure>',
                              lambda e: self.refresh_column_separators())
        self._sep_pending = None
        self.tree.bind('<Configure>',
                       lambda e: self.refresh_column_separators(), add='+')

        # Перекраска при переключении темы.
        toplevel = self.winfo_toplevel()
        toplevel.bind('<<ThemeChanged>>', lambda _e=None: self._on_theme_change(), add='+')

    # ------------------------------------------------------------------ theme
    def _on_theme_change(self):
        pal = theme.palette()
        self.configure(fg_color=pal.panel_bg)
        self._sep_canvas.configure(bg=pal.header_bg)
        self.tree.tag_configure('oddrow', background=pal.row_alt)
        self.tree.tag_configure('evenrow', background=pal.panel_bg)
        self.refresh_column_separators()

    # ------------------------------------------------------------- separators
    def _place_separators_strip(self):
        """Разместить полосу разделителей поверх шапки Treeview.

        Полоса перекрывает только верхние пиксели заголовков колонок, не
        участвуя в раскладке pack — строки таблицы не смещаются вниз, а
        сама полоса всегда точно выровнена по колонкам (в отличие от
        отдельной строки над таблицей, которая «выезжала» из-за разницы
        краёв с областью прокрутки).
        """
        tree = self.tree
        # Левый край полосы совпадает с левым краём области строк дерева:
        # при горизонтальной прокрутке ttk рисует колонки со сдвигом ровно
        # на эту величину, поэтому разделители остаются под границами
        # заголовков без дополнительных поправок.
        try:
            bbox = tree.bbox('#0')
        except tk.TclError:
            bbox = None  # корневой элемент не виден (например, show='headings')
        left = tree.winfo_x() + (bbox[0] if bbox else 0)
        width = max(1, tree.winfo_width() - (left - tree.winfo_x()))
        self._sep_canvas.place(x=left, y=tree.winfo_y(), width=width,
                               height=self._sep_height, anchor='nw')
        # place() и так поднимает окно над pack-братьями, но перестрахуемся:
        # для tk.Canvas tkraise — это метод канваса, а не окна, поэтому
        # поднимаем окно напрямую через Tk-команду raise.
        try:
            self._sep_canvas.tk.call(self._sep_canvas._w, 'raise')  # noqa: SLF001
        except tk.TclError:
            pass

    def refresh_column_separators(self):
        """Перерисовать вертикальные разделители между колонками Treeview."""
        if self._sep_pending is not None:
            try:
                self.after_cancel(self._sep_pending)
            except Exception:
                pass
        self._sep_pending = self.after_idle(self._redraw_separators)

    def _redraw_separators(self):
        self._sep_pending = None
        if not self._sep_canvas.winfo_exists() or not self.tree.winfo_exists():
            return
        self._place_separators_strip()
        self._draw_column_separators()

    def _draw_column_separators(self):
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

        # Смещение горизонтальной прокрутки: bbox первой колонки при
        # прокрутке уходит влево за левый край (координата x отрицательна).
        offset = 0
        children = tree.get_children()
        if children:
            bbox = tree.bbox(children[0], cols[0])
            if bbox:
                offset = max(0, -bbox[0])

        # Полоса лежит поверх шапки Treeview; её левый край совпадает с
        # областью строк — перевод координат через winfo_rootx.
        dx = tree.winfo_rootx() - canvas.winfo_rootx()

        x = dx - offset
        border = theme.palette().border
        for c in cols[:-1]:
            x += tree.column(c, 'width')
            if 0 < x < w:
                canvas.create_line(x, 0, x, h, fill=border)

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
    """CTkScrollableFrame с ползунком прокрутки, скрытым когда он не нужен.

    Встроенный CTkScrollbar всегда занимает место справа; здесь он заменяется
    на собственный canvas-скроллбар, который рисуется только при реальной
    необходимости (содержимое выше области просмотра). Цвета обновляются
    при смене темы.
    """

    BAR_WIDTH = 12
    BAR_TROUGH = 'transparent'

    def __init__(self, master, **kwargs):
        kwargs.setdefault('fg_color', 'transparent')
        kwargs.setdefault('label_text', '')
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

        toplevel = self.winfo_toplevel()
        toplevel.bind('<<ThemeChanged>>', lambda _e=None: self._schedule_redraw(), add='+')

    def _bar_color(self) -> str:
        return theme.palette().scrollbar

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
                                            fill=self._bar_color(), outline='')
        except tk.TclError:
            # Tk < 8.7 не поддерживает сглаженные углы у прямоугольников
            self._auto_bar.create_rectangle(pad, top, w - pad, bottom,
                                            fill=self._bar_color(), outline='')

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
