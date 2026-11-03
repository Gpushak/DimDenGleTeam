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


_live_combos: list = []
_combo_click_bound = False


def _dispatch_form_combo_click(event):
    """Один общий обработчик клика для всех полей, пока они живы."""
    for combo in list(_live_combos):
        try:
            alive = bool(combo.winfo_exists())
        except tk.TclError:
            alive = False
        if not alive:
            try:
                _live_combos.remove(combo)
            except ValueError:
                pass
            continue
        combo._on_global_click(event)


class FormComboBox(ctk.CTkComboBox):
    """Выпадающий список, чьё меню совпадает по ширине с самим полем.

    Штатное меню customtkinter — это ``tkinter.Menu``: его ширина считается
    по самому длинному пункту и не равна ширине поля. Здесь список
    открывается отдельным окном ровно той ширины, которую поле занимает
    в диалоге (в том числе когда поле растянуто на свободное место).
    """

    _MAX_VISIBLE_ROWS = 8

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._form_popup = None
        _live_combos.append(self)
        global _combo_click_bound
        if not _combo_click_bound:
            # CTkBaseClass запрещает bind_all на своих виджетах — вешаем
            # обработчик через tk, чтобы клик снаружи закрывал список.
            tk.Misc.bind_all(self, '<Button-1>', _dispatch_form_combo_click, add='+')
            _combo_click_bound = True
        if self._state == 'readonly':
            self._entry.bind('<Button-1>', self._on_entry_click, add='+')
        tk.Misc.bind(self, '<Destroy>', self._on_destroy, add='+')

    def _on_entry_click(self, event):
        self._clicked(event)
        return 'break'

    def _clicked(self, event=None):
        if self._form_popup is not None:
            self._close_form_popup()
            return
        if self._state is not tk.DISABLED and len(self._values) > 0:
            self._open_form_popup()

    def _open_dropdown_menu(self):
        self._open_form_popup()

    def _on_destroy(self, event):
        if event.widget is not self:
            return
        self._close_form_popup()
        try:
            _live_combos.remove(self)
        except ValueError:
            pass

    def destroy(self):
        self._close_form_popup()
        try:
            _live_combos.remove(self)
        except ValueError:
            pass
        super().destroy()

    def _open_form_popup(self):
        if self._form_popup is not None:
            self._close_form_popup()
        values = list(self._values or [])
        if not values or self._state is tk.DISABLED:
            return

        self.update_idletasks()
        width = self.winfo_width()
        if width <= 1:
            width = max(self.winfo_reqwidth(), 1)

        pal = theme.palette()
        popup = tk.Toplevel(self)
        popup.withdraw()
        popup.overrideredirect(True)
        try:
            popup.transient(self.winfo_toplevel())
        except tk.TclError:
            pass

        visible = min(len(values), self._MAX_VISIBLE_ROWS)
        try:
            list_font = self._entry.cget('font')
        except tk.TclError:
            list_font = ('Segoe UI', 13)

        # width=1 — запрошенная ширина списка минимальна, фактическую
        # задаёт оболочка ровно по ширине поля. Длинный текст обрезается,
        # а не раздвигает окно.
        shell = tk.Frame(
            popup,
            width=width,
            height=10,
            bg=pal.panel_bg,
            highlightthickness=1,
            highlightbackground=pal.border,
        )
        shell.pack_propagate(False)
        listbox = tk.Listbox(
            shell,
            width=1,
            height=visible,
            bg=pal.panel_bg,
            fg=pal.text,
            selectbackground=pal.hover,
            selectforeground=pal.text,
            activestyle='none',
            exportselection=False,
            relief='flat',
            borderwidth=0,
            highlightthickness=0,
            font=list_font,
            cursor='hand2',
        )
        listbox.pack(fill='both', expand=True)
        for value in values:
            listbox.insert('end', value)

        current = self.get()
        if current in values:
            index = values.index(current)
            listbox.selection_set(index)
            listbox.activate(index)
            listbox.see(index)

        popup.update_idletasks()
        height = max(listbox.winfo_reqheight() + 2, 1)
        shell.configure(width=width, height=height)

        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 2
        screen_x = self.winfo_vrootx()
        screen_y = self.winfo_vrooty()
        screen_w = self.winfo_vrootwidth()
        screen_h = self.winfo_vrootheight()
        if y + height > screen_y + screen_h:
            y = max(self.winfo_rooty() - height - 2, screen_y)
        if x + width > screen_x + screen_w:
            x = max(screen_x + screen_w - width, screen_x)

        popup.geometry(f'{width}x{height}+{x}+{y}')
        popup.minsize(width, height)
        popup.maxsize(width, height)
        shell.pack()
        popup.deiconify()
        popup.geometry(f'{width}x{height}+{x}+{y}')
        try:
            popup.attributes('-topmost', True)
        except tk.TclError:
            pass
        popup.lift()
        listbox.focus_set()

        def pick_at(event):
            index = listbox.nearest(event.y)
            bbox = listbox.bbox(index) if 0 <= index < len(values) else None
            if bbox is None or event.y > bbox[1] + bbox[3]:
                return 'break'
            value = values[index]
            self._close_form_popup()
            self._dropdown_callback(value)
            return 'break'

        def pick_active(_event=None):
            selected = listbox.curselection()
            if not selected:
                self._close_form_popup()
                return 'break'
            value = values[selected[0]]
            self._close_form_popup()
            self._dropdown_callback(value)
            return 'break'

        def on_wheel(event):
            if getattr(event, 'delta', 0):
                listbox.yview_scroll(-1 if event.delta > 0 else 1, 'units')
            elif getattr(event, 'num', None) == 4:
                listbox.yview_scroll(-1, 'units')
            elif getattr(event, 'num', None) == 5:
                listbox.yview_scroll(1, 'units')
            return 'break'

        # Горизонтальная прокрутка сдвинула бы текст и визуально
        # изменила ширину содержимого — держим его у левого края.
        def _keep_x_origin(*_args):
            if listbox.xview()[0] > 0:
                listbox.xview_moveto(0)

        listbox.configure(xscrollcommand=_keep_x_origin)
        listbox.bind('<ButtonRelease-1>', pick_at)
        listbox.bind('<Return>', pick_active)
        listbox.bind('<Escape>', lambda _e: self._close_form_popup())
        listbox.bind('<MouseWheel>', on_wheel)
        listbox.bind('<Button-4>', on_wheel)
        listbox.bind('<Button-5>', on_wheel)
        popup.bind('<Escape>', lambda _e: self._close_form_popup())
        self._form_popup = popup

    def _close_form_popup(self):
        popup = self._form_popup
        self._form_popup = None
        if popup is None:
            return
        try:
            if popup.winfo_exists():
                popup.destroy()
        except tk.TclError:
            pass

    def _on_global_click(self, event):
        popup = self._form_popup
        if popup is None:
            return
        try:
            if not self.winfo_exists() or not popup.winfo_exists():
                self._form_popup = None
                return
        except tk.TclError:
            self._form_popup = None
            return
        # Клик по самому полю обрабатывает _clicked (открыть/закрыть).
        if self._pointer_inside(self, event) or self._pointer_inside(popup, event):
            return
        self._close_form_popup()

    @staticmethod
    def _pointer_inside(widget, event) -> bool:
        try:
            x = widget.winfo_rootx()
            y = widget.winfo_rooty()
            width = widget.winfo_width()
            height = widget.winfo_height()
        except tk.TclError:
            return False
        return x <= event.x_root < x + width and y <= event.y_root < y + height
