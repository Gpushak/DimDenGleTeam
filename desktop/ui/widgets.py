"""Вспомогательные виджеты, согласованные с темой приложения.

Содержит:
* ``DarkTableFrame``      — панель со Treeview без лишних рамок;
* ``DarkScrollableFrame`` — прокручиваемая панель (без полос прокрутки).

Полосы прокрутки (скроллбары) из интерфейса убраны целиком: ни вертикальных,
ни горизонтальных скроллбаров нигде не отображается. Прокрутка содержимого
сохранилась через колесо мыши и клавиатуру.

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


class ColumnSeparatorPlugin:
    """Вертикальные линии-разделители между столбцами Treeview.

    Реализация опирается на штатный механизм ttk: элемент ``::text``
    (экземпляр ``Treeview.Cell``) рисуется для каждой ячейки, и если у
    этого типа элементов включена однопиксельная рамка цвета границы
    (настраивается в ``ui.theme.apply_ttk_theme``), то между столбцами
    появляются ровные разделительные линии на всю высоту таблицы —
    включая шапку (через ``Treeheading.cell``).

    Никаких canvas-оверлеев поверх таблицы больше нет: раньше они
    перекрывали содержимое (было видно только линии) и обращались к
    несуществующему API (``element cget ::text -widget``), из-за чего
    приложение падало с ``AttributeError``. Плагин сводится к безопасному
    вызову перерисовки; сам он не создаёт новых окон и ничего не рисует.
    """

    def __init__(self, tree: ttk.Treeview):
        self.tree = tree

    def redraw(self):
        """Перерисовать дерево, чтобы ttk заново отрисовал рамки ячеек."""
        tree = self.tree
        try:
            if tree.winfo_exists() and tree.winfo_viewable():
                tree.item(tree, redisplay=True)
        except tk.TclError:
            pass

    def attach(self):
        """Совместимость со старым кодом: принудительная перерисовка."""
        self.redraw()

    def place_overlay(self):
        """Совместимость: оверлей больше не используется."""
        pass

    def set_known_widths(self, widths: dict):
        """Совместимость: карта ширин не нужна — линии рисует сам ttk."""
        self.redraw()

    def destroy(self):
        pass

class DarkTableFrame(ctk.CTkFrame):
    """Панель со Treeview без рамок и без полос прокрутки.

    * фон панели берётся из текущей темы;
    * рамок нет: панель отличима фоном, разграничителями служат только
      шапка таблицы и тонкие разделители колонок;
    * скроллбары не создаются и не отображаются вовсе; строки, не
      помещающиеся по высоте/ширине, доступны колесом мыши;
    * над таблицей нет «выпирающих» полос: разделители рисуются поверх
      самой таблицы через ``ColumnSeparatorPlugin``;
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

        # Скроллбары не создаются: y/xscrollcommand просто игнорирует
        # вызовы ttk (сигнатура (first, last)).
        self.tree.configure(yscrollcommand=lambda *_a: None,
                            xscrollcommand=lambda *_a: None)

        # Переменная позиции горизонтального пролистывания (оставлена для
        # совместимости со старыми ссылками, внешним кодом не используется).
        self.xview_var = tk.StringVar(value='0.0 1.0')

        self.tree.pack(fill='both', expand=True)

        for col in (columns or ()):
            width = (column_widths or {}).get(col, 120)
            text = (headings or {}).get(col, col)
            self.tree.heading(col, text=text, anchor='w')
            self.tree.column(col, width=width, minwidth=60, anchor='w', stretch=True)

        # Разделители между столбцами: рисуются самим ttk рамками ячеек
        # (см. ColumnSeparatorPlugin), никаких оверлеев над таблицей.
        self._sep_plugin = ColumnSeparatorPlugin(self.tree)
        self._sep_plugin.set_known_widths({c: (column_widths or {}).get(c, 120)
                                           for c in (columns or ())})

        # Чередование строк для читаемости
        self.tree.tag_configure('oddrow', background=pal.row_alt)
        self.tree.tag_configure('evenrow', background=pal.panel_bg)
        self._row_count = 0

        # Прокрутка колесом мыши вместо скроллбара.
        self._bind_mousewheel(self.tree)

        # Перекраска при переключении темы.
        toplevel = self.winfo_toplevel()
        toplevel.bind('<<ThemeChanged>>', lambda _e=None: self._on_theme_change(), add='+')

    # ------------------------------------------------------------- mousewheel
    @staticmethod
    def _bind_mousewheel(widget):
        """Колесо мыши прокручивает таблицу вверх/вниз."""
        def _on_mousewheel(event):
            delta = -1 if getattr(event, 'num', None) == 5 else 1
            if getattr(event, 'delta', 0):
                delta = -1 if event.delta > 0 else 1
            try:
                widget.yview_scroll(delta, 'units')
            except tk.TclError:
                pass
            return 'break'

        widget.bind('<MouseWheel>', _on_mousewheel)
        widget.bind('<Button-4>', _on_mousewheel)
        widget.bind('<Button-5>', _on_mousewheel)

    # ------------------------------------------------------------------ theme
    def _on_theme_change(self):
        pal = theme.palette()
        self.configure(fg_color=pal.panel_bg)
        self.tree.tag_configure('oddrow', background=pal.row_alt)
        self.tree.tag_configure('evenrow', background=pal.panel_bg)
        self.refresh_column_separators()

    # ------------------------------------------------------------- separators
    def refresh_column_separators(self):
        """Перерисовать вертикальные разделители между колонками Treeview."""
        plugin = getattr(self, '_sep_plugin', None)
        if plugin is not None:
            plugin.redraw()

    def clear(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self._row_count = 0


class DarkScrollableFrame(ctk.CTkScrollableFrame):
    """Прокручиваемая панель без видимых полос прокрутки.

    Нативный ``CTkScrollbar`` библиотечного ``CTkScrollableFrame`` полностью
    удалён из разметки и скрыт: никакого скроллбара справа не отображается
    (ни когда содержимое влезает, ни когда оно длиннее окна). Прокрутка
    осталась доступной колесом мыши и клавиатурой.
    """

    def __init__(self, master, **kwargs):
        kwargs.setdefault('fg_color', 'transparent')
        kwargs.setdefault('label_text', '')
        super().__init__(master, **kwargs)
        self._hide_scrollbar()

    # ---------------------------------------------------------------- scrollbar
    def _hide_scrollbar(self):
        """Убрать нативный скроллбар из разметки и скрыть его."""
        sb = getattr(self, '_scrollbar', None)
        if sb is None:
            return
        try:
            sb.grid_forget()
            sb.grid_remove()
        except Exception:
            pass

    def _create_grid(self):
        super()._create_grid()
        # Любая перестройка сетки (corner_radius / border_width / label_text)
        # возвращает полосу в grid — убираем её снова.
        if hasattr(self, '_parent_frame'):
            self._hide_scrollbar()

    # ------------------------------------------------------------ содержимое
    def _after_content_change(self):
        """Обновить scrollregion после изменения набора содержимого."""
        self._parent_canvas.update_idletasks()
        bbox = self._parent_canvas.bbox('all')
        if bbox:
            self._parent_canvas.configure(scrollregion=bbox)
