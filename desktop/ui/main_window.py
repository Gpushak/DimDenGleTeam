"""Главное окно приложения на customtkinter.

Верхняя панель: название, выбор темы (светлая/тёмная), пункт «О программе».
Основная область: дерево контейнеров слева, таблица товаров справа.
Рамки и границы нигде не рисуются — панели различаются только фоном.
"""
import re
import io

import customtkinter as ctk
from PIL import Image
from tkinter import messagebox
from typing import Optional, List

from api_client import ApiClient, ApiError

import crud
from qrutil import qr_payload, qr_png_bytes
from models import Box, Item
from ui import theme
from ui.widgets import DarkScrollableFrame, DarkTableFrame

APP_NAME = 'Складской учёт'
APP_VERSION = '1.0.0'


def format_weight(grams: int) -> str:
    """Граммы в вид «450 г» / «1.25 кг» — общее для таблицы и строки статуса."""
    if grams >= 1000:
        return f'{grams / 1000:.2f} кг'
    return f'{grams} г'


class TreeWidget(DarkScrollableFrame):
    """Виджет дерева контейнеров.

    Плоская модель без ttk.Treeview: каждому контейнеру соответствует
    строка (кнопка-переключатель ▼/▶/• + кнопка выбора).

    Порядок строк задаётся не сортировкой по id, а явным списком обхода
    ``_order`` — узлы добавляются строго «родитель раньше потомков», и при
    любой перерисовке ряды переупаковываются именно в этом порядке. Так
    дерево не «переезжает» при обновлении данных или смене темы.

    Сворачивание работает рекурсивно: у свёрнутого узла скрыты потомки
    всех уровней, а при раскрытии родителя его дочерние узлы показываются
    со своим собственным состоянием (ранее свёрнутые остаются свёрнутыми).
    Состояние раскрытия живёт отдельно от виджетов (``_expanded_state``),
    поэтому переживает пересборку дерева (``clear`` + повторное добавление
    узлов) после CRUD-операций.

    Цвета узлов зависят от текущей темы: при событии ``<<ThemeChanged>>``
    все кнопки перекрашиваются.
    """

    INDENT = 18

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        # box_id -> запись узла (row/btn/toggle/level/has_children)
        self.nodes: dict = {}
        # Порядок обхода дерева: родитель раньше потомков.
        self._order: List = []
        # Сколько специальных узлов в начале _order (Все товары, Без расположения).
        self._special_count = 0
        # box_id -> развёрнут ли узел; сохраняется между пересборками.
        self._expanded_state: dict = {}
        self.selected_box_id: Optional[int] = None
        self.on_select_callback = None

        self.winfo_toplevel().bind('<<ThemeChanged>>',
                                   lambda _e=None: self._on_theme_change(), add='+')

    # ------------------------------------------------------------------ цвета
    @staticmethod
    def _text_color() -> tuple:
        pal = theme.palette()
        return (pal.text, pal.text)

    @classmethod
    def _muted_color(cls) -> tuple:
        pal = theme.palette()
        return (pal.muted_text, pal.muted_text)

    @staticmethod
    def _hover_color() -> tuple:
        pal = theme.palette()
        return (pal.hover, pal.hover)

    @staticmethod
    def _selected_colors() -> tuple:
        pal = theme.palette()
        return ((pal.selected, pal.selected), (pal.selected_text, pal.selected_text))

    def _on_theme_change(self):
        for node in self.nodes.values():
            btn = node['btn']
            toggle = node.get('toggle')
            if toggle is not None and toggle.winfo_exists():
                toggle.configure(text_color=self._muted_color(),
                                 hover_color=self._hover_color())
            if not btn.winfo_exists():
                continue
            if node['box_id'] == self.selected_box_id:
                fg, fg_text = self._selected_colors()
                btn.configure(fg_color=fg, text_color=fg_text)
            else:
                btn.configure(fg_color='transparent',
                              text_color=self._text_color())

    def set_on_select(self, callback):
        self.on_select_callback = callback

    def clear(self):
        """Удалить строки и записи узлов.

        Порядок обхода (``_order``) не сбрасывается: ``begin_build`` /
        ``finish_build`` вызываются вокруг пересборки и гарантируют, что
        список всегда соответствует добавленным узлам. Состояние раскрытия
        сохраняется между пересборками — свёрнутые ветки остаются свёрнутыми
        после CRUD-операций; вычеркнуть мёртвый id можно через ``forget_box``.
        """
        for widget in self.winfo_children():
            widget.destroy()
        self.nodes.clear()

    # ------------------------------------------------------------- пересборка
    def begin_build(self):
        """Начать пересборку дерева (сбрасывает порядок обхода)."""
        self._order = []
        self._special_count = 0

    def finish_build(self):
        """Завершить пересборку: применить видимость и обновить прокрутку."""
        self._apply_visibility()
        self._sync_scrollregion()

    # ------------------------------------------------------------------ API
    def add_special_node(self, node_id, text):
        """Добавить специальный узел (Все товары, Без расположения)."""
        row = ctk.CTkFrame(self, fg_color='transparent')
        btn = ctk.CTkButton(
            row,
            text=text,
            command=lambda nid=node_id: self._on_node_click(nid),
            anchor='w',
            height=30,
            corner_radius=6,
            border_width=0,
            fg_color='transparent',
            text_color=self._text_color(),
            hover_color=self._hover_color(),
        )
        btn.pack(fill='x', expand=True)
        self.nodes[node_id] = {'row': row, 'btn': btn, 'toggle': None,
                               'level': 0, 'has_children': False,
                               'box_id': node_id}
        # Специальные узлы всегда в начале, в порядке добавления.
        self._order.insert(self._special_count, node_id)
        self._special_count += 1

    def add_box_node(self, box: Box, parent_id: Optional[int] = None, level: int = 0,
                     has_children: bool = False, expanded: Optional[bool] = None):
        """Добавить узел контейнера (плоский ряд с отступом по уровню).

        ``expanded=None`` — состояние берётся из сохранённого (между
        пересборками дерева); новых узлов по умолчанию раскрыты.
        """
        # В дереве показываем только название контейнера, без типа в скобках
        label = box.box_name

        if expanded is None:
            expanded = self._expanded_state.get(box.box_id, True)
        self._expanded_state[box.box_id] = bool(expanded)

        row = ctk.CTkFrame(self, fg_color='transparent')

        toggle = ctk.CTkButton(
            row,
            width=24,
            height=30,
            corner_radius=6,
            border_width=0,
            text=self._toggle_text(has_children, expanded),
            fg_color='transparent',
            hover_color=self._hover_color(),
            text_color=self._muted_color(),
            command=lambda bid=box.box_id: self.toggle_node(bid),
        )
        toggle.pack(side='left', padx=(0, 2))

        btn = ctk.CTkButton(
            row,
            text=label,
            command=lambda bid=box.box_id: self._on_node_click(bid),
            anchor='w',
            height=30,
            corner_radius=6,
            border_width=0,
            fg_color='transparent',
            text_color=self._text_color(),
            hover_color=self._hover_color(),
        )
        btn.pack(side='left', fill='x', expand=True)

        self.nodes[box.box_id] = {'row': row, 'btn': btn, 'toggle': toggle,
                                  'level': level, 'has_children': has_children,
                                  'box_id': box.box_id}
        self._order.append(box.box_id)

    def forget_box(self, box_id: int):
        """Вычеркнуть узел из состояния (используется после удаления)."""
        self._expanded_state.pop(box_id, None)

    # ------------------------------------------------------- раскрытие узлов
    @staticmethod
    def _toggle_text(has_children: bool, expanded: bool) -> str:
        if not has_children:
            return '•'
        return '▼' if expanded else '▶'

    def _is_visible(self, box_id) -> bool:
        """Виден ли узел: все предки в цепочке должны быть развёрнуты."""
        node = self.nodes.get(box_id)
        while node is not None and node['level'] > 0:
            parent_id = self._find_parent_id(node)
            if parent_id is None:
                break
            parent = self.nodes.get(parent_id)
            if parent is None:
                break
            if parent['has_children'] and not self._expanded_state.get(parent_id, True):
                return False
            node = parent
        return True

    def _find_parent_id(self, node) -> Optional[int]:
        """Непосредственный родитель узла по списку обхода."""
        try:
            idx = self._order.index(node['box_id'])
        except ValueError:
            return None
        for i in range(idx - 1, -1, -1):
            candidate = self.nodes.get(self._order[i])
            if candidate is not None and candidate['level'] == node['level'] - 1:
                return self._order[i]
            if candidate is not None and candidate['level'] < node['level'] - 1:
                return None
        return None

    def _apply_visibility(self):
        """Переупаковать ряды в порядке обхода, скрывая ветки свёрнутых узлов.

        Сначала ``pack_forget`` применяется ко всем рядам, затем видимые
        переупаковываются строго по ``_order``. Иначе Tk добавляет только что
        упакованный виджет в конец очереди pack — после разворачивания узла
        его дочерние строки оказывались внизу списка вместо позиции сразу под
        родителем.
        """
        self._order = [bid for bid in self._order if bid in self.nodes]
        # 1. Скрыть все ряды, чтобы pack ниже шёл всегда в чистую очередь.
        for box_id in self._order:
            self.nodes[box_id]['row'].pack_forget()
        # 2. Показать только видимые — в правильном порядке обхода.
        for box_id in self._order:
            node = self.nodes[box_id]
            if self._is_visible(box_id):
                node['row'].pack(fill='x', pady=1,
                                 padx=(node['level'] * self.INDENT, 0))

    def _sync_scrollregion(self):
        """Обновить область прокрутки после изменения набора видимых строк."""
        self.update_idletasks()
        self._after_content_change()

    def toggle_node(self, box_id: int):
        """Развернуть/свернуть узел (публичный API для тестов и горячих клавиш)."""
        node = self.nodes.get(box_id)
        if not node or not node['has_children']:
            return
        expanded = not self._expanded_state.get(box_id, True)
        self._expanded_state[box_id] = expanded
        toggle = node['toggle']
        if toggle is not None and toggle.winfo_exists():
            toggle.configure(text=self._toggle_text(True, expanded))
        self._apply_visibility()
        self._sync_scrollregion()

    # совместимость со старым названием
    _toggle_node = toggle_node

    # ------------------------------------------------------------ выделение
    def _on_node_click(self, box_id):
        """Обработка клика по узлу."""
        # Снять выделение со всех
        for node in self.nodes.values():
            if node['btn'].winfo_exists():
                node['btn'].configure(fg_color='transparent',
                                      text_color=self._text_color())

        # Выделить текущий
        if box_id in self.nodes:
            fg, fg_text = self._selected_colors()
            self.nodes[box_id]['btn'].configure(fg_color=fg, text_color=fg_text)

        self.selected_box_id = box_id
        if self.on_select_callback:
            self.on_select_callback(box_id)

    def select_node(self, box_id):
        """Программно выбрать узел."""
        self._on_node_click(box_id)

    def reveal_node(self, box_id) -> None:
        """Развернуть всех предков узла, чтобы он стал видимым."""
        node = self.nodes.get(box_id)
        if node is None:
            return
        changed = False
        parent_id = self._find_parent_id(node)
        while parent_id is not None:
            parent = self.nodes.get(parent_id)
            if parent is None:
                break
            if parent['has_children'] and not self._expanded_state.get(parent_id, True):
                self._expanded_state[parent_id] = True
                if parent['toggle'] is not None and parent['toggle'].winfo_exists():
                    parent['toggle'].configure(text=self._toggle_text(True, True))
                changed = True
            node = parent
            parent_id = self._find_parent_id(node)
        if changed:
            self._apply_visibility()
            self._sync_scrollregion()


def natural_key(text: str):
    """Ключ естественной сортировки: 'Ячейка 2' < 'Ячейка 10'."""
    parts = re.split(r'(\d+)', str(text))
    return [int(p) if p.isdigit() else p.lower() for p in parts]


class MainWindow:
    # колонки таблицы товаров: (iid, заголовок, ширина)
    COLUMNS = (
        ('type', 'Тип товара', 200),
        ('quantity', 'Количество', 100),
        ('weight', 'Вес', 110),
        ('location', 'Расположение', 250),
    )

    def __init__(self, root: ctk.CTk, client: ApiClient, scale_monitor=None):
        self.root = root
        self.client = client
        self.scale_monitor = scale_monitor
        self.selected_box_id: Optional[int] = None

        self.root.title(APP_NAME)
        self.root.geometry('1200x700')
        self.root.minsize(900, 560)

        # Тема: применяем сохранённый режим (simplecache customtkinter)
        ctk.set_default_color_theme('blue')
        theme.apply_theme(theme.current_mode())

        # Данные последней выборки и состояние сортировки таблицы
        self._current_rows: List[tuple] = []   # (item_id, values tuple)
        self._sort_column: Optional[str] = None
        self._sort_reverse: bool = False

        self._create_widgets()
        self._refresh_all()

    # ============================================================ верхняя панель
    def _create_topbar(self):
        pal = theme.palette()
        bar = ctk.CTkFrame(self.root, fg_color=pal.panel_bg, corner_radius=0,
                           border_width=0, height=52)
        bar.pack(fill='x', side='top')
        bar.pack_propagate(False)
        self._topbar = bar

        self._topbar_title = ctk.CTkLabel(
            bar, text=APP_NAME,
            font=ctk.CTkFont(size=16, weight='bold'),
            text_color=pal.text,
        )
        self._topbar_title.pack(side='left', padx=(18, 0))

        # Правая часть панели: тема + «О программе»
        right = ctk.CTkFrame(bar, fg_color='transparent')
        right.pack(side='right', padx=(0, 12))

        self._theme_label = ctk.CTkLabel(right, text='Тема:',
                                         text_color=pal.muted_text)
        self._theme_label.pack(side='left', padx=(0, 6))

        # Сегменты сразу с русскими подписями — без обращения к приватным
        # атрибутам CTkSegmentedButton (совместимо с customtkinter >= 6.0).
        self._THEME_CAPTIONS = {'light': 'Светлая', 'dark': 'Тёмная'}
        self._THEME_VALUES = {caption: mode
                              for mode, caption in self._THEME_CAPTIONS.items()}
        self.theme_switch = ctk.CTkSegmentedButton(
            right,
            values=[self._THEME_CAPTIONS['light'], self._THEME_CAPTIONS['dark']],
            height=30,
            corner_radius=8,
            border_width=0,
            font=ctk.CTkFont(size=13),
            command=self._on_theme_selected,
        )
        self.theme_switch.set(self._THEME_CAPTIONS[theme.current_mode()])
        self.theme_switch.pack(side='left', padx=(0, 10))

        self._about_button = ctk.CTkButton(
            right, text='О программе', width=110, height=30,
            corner_radius=8, border_width=0,
            fg_color='transparent',
            hover_color=pal.hover, text_color=pal.text,
            command=self._show_about,
        )
        self._about_button.pack(side='left')

        # Тонкая линия-разделитель вместо рамки
        self._topbar_sep = ctk.CTkFrame(self.root, fg_color=pal.border, height=1,
                                       corner_radius=0, border_width=0)
        self._topbar_sep.pack(fill='x', side='top')

    def _on_theme_selected(self, caption: str):
        mode = self._THEME_VALUES.get(caption, theme.current_mode())
        theme.apply_theme(mode)
        # Статичные панели (верхняя/нижняя) перекрашиваем под новую тему
        self._retopaint_chrome()

    def _show_about(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title('О программе')
        dialog.geometry('420x300')
        dialog.transient(self.root)
        dialog.resizable(False, False)
        try:
            dialog.grab_set()
        except Exception:
            pass

        pal = theme.palette()
        dialog.configure(fg_color=pal.window_bg)

        frame = ctk.CTkFrame(dialog, fg_color=pal.panel_bg, corner_radius=12,
                             border_width=0)
        frame.pack(fill='both', expand=True, padx=16, pady=16)

        ctk.CTkLabel(frame, text=APP_NAME,
                     font=ctk.CTkFont(size=20, weight='bold'),
                     text_color=pal.text).pack(pady=(20, 4))
        ctk.CTkLabel(frame, text=f'Версия {APP_VERSION}',
                     text_color=pal.muted_text).pack()
        ctk.CTkLabel(
            frame,
            text='Учёт товаров на складе: структура контейнеров,\n'
                 'позиции, весы, QR-этикетки.\n\n'
                 'Qwentory Team',
            justify='center', text_color=pal.text,
        ).pack(pady=14)
        ctk.CTkButton(frame, text='Закрыть', width=120, border_width=0,
                      command=dialog.destroy).pack(pady=(0, 18))

        # Диалог поверх родителя, по центру окна
        dialog.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - 420) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - 300) // 2
        dialog.geometry(f'+{max(x, 0)}+{max(y, 0)}')

    # ============================================================== содержимое
    def _create_widgets(self):
        self._create_topbar()

        # Главный контейнер
        main_frame = ctk.CTkFrame(self.root, fg_color='transparent')
        main_frame.pack(fill='both', expand=True, padx=14, pady=(10, 6))

        # Поиск
        search_frame = ctk.CTkFrame(main_frame, fg_color='transparent')
        search_frame.pack(fill='x', pady=(0, 10))

        # Подпись хранится как атрибут: при смене темы перекрашивается в
        # _retopaint_chrome(), иначе в светлой теме оставался тёмный текст.
        self._search_label = ctk.CTkLabel(search_frame, text='Поиск:',
                                          text_color=theme.palette().text)
        self._search_label.pack(side='left', padx=(0, 6))
        self.search_var = ctk.StringVar()
        self.search_var.trace_add('write', lambda *_: self._on_search())
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var,
                                    width=300, border_width=0, corner_radius=8,
                                    height=34)
        search_entry.pack(side='left')

        # Основная область: две панели без рамок, разделены тонкой линией
        paned = ctk.CTkFrame(main_frame, fg_color='transparent')
        paned.pack(fill='both', expand=True)

        # Левая панель — дерево
        left_frame = ctk.CTkFrame(paned, width=330, fg_color='transparent',
                                  corner_radius=0, border_width=0)
        left_frame.pack(side='left', fill='y', padx=(0, 0))
        left_frame.pack_propagate(False)

        self._tree_title = ctk.CTkLabel(left_frame, text='Структура склада',
                                        font=ctk.CTkFont(size=14, weight='bold'),
                                        text_color=theme.palette().text)
        self._tree_title.pack(anchor='w', pady=(2, 6))

        # Кнопки управления деревом
        tree_btn_frame = ctk.CTkFrame(left_frame, fg_color='transparent')
        tree_btn_frame.pack(fill='x', pady=(0, 6))
        for text, command in (('+ Контейнер', self._add_box),
                              ('✎ Изменить', self._edit_box),
                              ('✕ Удалить', self._delete_box)):
            ctk.CTkButton(tree_btn_frame, text=text, command=command,
                          width=100, height=30, corner_radius=8,
                          border_width=0).pack(side='left', padx=(0, 6))

        # Дерево
        self.tree = TreeWidget(left_frame)
        self.tree.pack(fill='both', expand=True)
        self.tree.set_on_select(self._on_tree_select)

        # Тонкий вертикальный разделитель вместо рамок панелей
        ctk.CTkFrame(paned, width=1, fg_color=theme.palette().border,
                     corner_radius=0, border_width=0).pack(side='left', fill='y',
                                                           padx=(8, 10))

        # Правая панель — товары
        right_frame = ctk.CTkFrame(paned, fg_color='transparent',
                                   corner_radius=0, border_width=0)
        right_frame.pack(side='left', fill='both', expand=True)

        # Заголовок (перекрашивается при смене темы)
        self.items_header = ctk.CTkLabel(right_frame, text='Все товары',
                                         font=ctk.CTkFont(size=14, weight='bold'),
                                         text_color=theme.palette().text)
        self.items_header.pack(anchor='w', pady=(2, 6))

        # Кнопки управления товарами
        item_btn_frame = ctk.CTkFrame(right_frame, fg_color='transparent')
        item_btn_frame.pack(fill='x', pady=(0, 6))
        for text, command, width in (('+ Тип товара', self._add_item_type, 110),
                                     ('+ Товар', self._add_item, 90),
                                     ('✎ Изменить', self._edit_item, 100),
                                     ('✕ Удалить', self._delete_item, 100),
                                     ('QR', self._show_qr, 60)):
            ctk.CTkButton(item_btn_frame, text=text, command=command,
                          width=width, height=30, corner_radius=8,
                          border_width=0).pack(side='left', padx=(0, 6))

        # Таблица товаров
        cols = tuple(c[0] for c in self.COLUMNS)
        headings = {c[0]: c[1] for c in self.COLUMNS}
        widths = {c[0]: c[2] for c in self.COLUMNS}
        self.table = DarkTableFrame(right_frame, columns=cols, headings=headings,
                                    column_widths=widths)
        self.table.pack(fill='both', expand=True, pady=(0, 4))
        self.items_tree = self.table.tree

        # Сортировка по клику на шапку
        for col, title, _w in self.COLUMNS:
            self.items_tree.heading(col, command=lambda c=col: self._sort_by_column(c))

        # Строка состояния внизу — тонкая линия сверху вместо рамки
        pal = theme.palette()
        self._status_sep = ctk.CTkFrame(self.root, fg_color=pal.border, height=1,
                                       corner_radius=0, border_width=0)
        self._status_sep.pack(fill='x', side='bottom')
        self._status_bar = ctk.CTkFrame(self.root, fg_color=pal.panel_bg,
                                       corner_radius=0, border_width=0, height=32)
        self._status_bar.pack(fill='x', side='bottom')
        self._status_bar.pack_propagate(False)
        self.status_var = ctk.StringVar()
        self._status_label = ctk.CTkLabel(self._status_bar, textvariable=self.status_var,
                                         anchor='w', text_color=pal.muted_text)
        self._status_label.pack(fill='x', padx=14)

    def _retopaint_chrome(self):
        """Перекрасить статичные элементы (панели, разделители) под текущую тему."""
        pal = theme.palette()
        if hasattr(self, '_topbar'):
            self._topbar.configure(fg_color=pal.panel_bg)
            self._topbar_title.configure(text_color=pal.text)
            self._theme_label.configure(text_color=pal.muted_text)
            self._about_button.configure(hover_color=pal.hover, text_color=pal.text)
            self._topbar_sep.configure(fg_color=pal.border)
        if hasattr(self, '_status_bar'):
            self._status_bar.configure(fg_color=pal.panel_bg)
            self._status_label.configure(text_color=pal.muted_text)
            self._status_sep.configure(fg_color=pal.border)
        # Подписи вне верхней панели
        if hasattr(self, '_search_label'):
            self._search_label.configure(text_color=pal.text)
        if hasattr(self, 'items_header'):
            self.items_header.configure(text_color=pal.text)
        if hasattr(self, '_tree_title'):
            self._tree_title.configure(text_color=pal.text)

    # ------------------------------------------------------------------ data
    def refresh_items(self):
        """Перерисовывает таблицу товаров.

        Публичный метод: его вызывает монитор весов (`desktop/main.py`),
        когда показание изменилось.
        """
        try:
            self._refresh_items()
        except ApiError as error:
            self.status_var.set(f'Ошибка обновления: {error}')

    def _refresh_all(self):
        try:
            self._refresh_tree()
            self._refresh_items()
        except ApiError as error:
            messagebox.showerror('Сервер', str(error))

    def _show_qr(self):
        selection = self.items_tree.selection()
        if not selection:
            messagebox.showinfo('Информация', 'Выберите товар, чтобы сформировать QR-этикетку')
            return
        item = crud.get_item_by_id(self.client, int(selection[0]))
        if not item:
            return

        payload = qr_payload('item', item.item_id)
        try:
            pil_image = Image.open(io.BytesIO(qr_png_bytes(payload)))
            photo = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(220, 220))
        except Exception as error:
            messagebox.showerror('QR', str(error))
            return

        pal = theme.palette()
        dialog = ctk.CTkToplevel(self.root)
        dialog.title('QR-этикетка')
        dialog.geometry('360x420')
        dialog.transient(self.root)
        dialog.configure(fg_color=pal.window_bg)
        ctk.CTkLabel(dialog, text=payload, wraplength=320).pack(pady=8)
        label = ctk.CTkLabel(dialog, image=photo, text='')
        label.pack(pady=8)
        dialog._qr_image = photo
        ctk.CTkButton(dialog, text='Закрыть', border_width=0,
                      command=dialog.destroy).pack(pady=8)

    def _refresh_tree(self):
        selected = self.selected_box_id
        # Состояние раскрытия (self.tree._expanded_state) НЕ сбрасывается:
        # свёрнутые ветки остаются свёрнутыми после обновления данных.
        self.tree.clear()
        self.tree.begin_build()

        # Специальные узлы
        self.tree.add_special_node(None, 'Все товары')
        self.tree.add_special_node(-1, 'Без расположения')

        # Полное дерево контейнеров (корни + все вложенные уровни)
        all_boxes = crud.get_all_boxes(self.client)
        children_map: dict = {}
        for b in all_boxes:
            parent = b.parent_id
            # Страховка от «сирот»: удалённый/несуществующий родитель
            # означает корневой уровень, иначе такой контейнер исчез бы из дерева.
            if parent is not None and not any(x.box_id == parent for x in all_boxes):
                parent = None
            children_map.setdefault(parent, []).append(b)
        for lst in children_map.values():
            lst.sort(key=lambda b: natural_key(b.box_name))

        # Порядок обхода = порядок добавления: родитель раньше потомков,
        # дети — в естественном порядке названий («Ящик 2» перед «Ящик 10»).
        visited: set = set()

        def walk(parent_id, level):
            for box in children_map.get(parent_id, []):
                if box.box_id in visited:      # защита от циклов parent_id
                    continue
                visited.add(box.box_id)
                has_children = bool(children_map.get(box.box_id))
                self.tree.add_box_node(box, parent_id, level=level,
                                       has_children=has_children)
                if has_children:
                    walk(box.box_id, level + 1)

        walk(None, 0)

        # Узлы, не попавшие в обход (циклы в иерархии), показываем корнями,
        # чтобы они не пропадали бесследно.
        for b in sorted(all_boxes, key=lambda b: natural_key(b.box_name)):
            if b.box_id not in visited:
                has_children = bool(children_map.get(b.box_id))
                self.tree.add_box_node(b, None, level=0, has_children=has_children)

        self.tree.finish_build()

        if selected is not None and selected in self.tree.nodes:
            self.tree.reveal_node(selected)
            self.tree.select_node(selected)
        else:
            self.tree.select_node(None)

    # --------------------------------------------------------------- sorting
    def _sort_key_for_row(self, row, col):
        index = [c[0] for c in self.COLUMNS].index(col)
        value = row[1][index]
        if col == 'quantity':
            try:
                return (0, float(value))
            except (TypeError, ValueError):
                return (0, 0)
        if col == 'weight':
            # '1.50 кг' -> граммы; '300 г' -> граммы
            m = re.match(r'^([\d.,]+)\s*(кг|г)?$', str(value).strip())
            if m:
                num = float(m.group(1).replace(',', '.'))
                return (0, num * 1000 if m.group(2) == 'кг' else num)
            return (0, 0)
        return (2, natural_key(value))

    def _sort_by_column(self, col):
        if self._sort_column == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = col
            self._sort_reverse = False
        self._render_items_table()

    def _heading_text(self, col, base_title):
        if self._sort_column == col:
            arrow = ' ▼' if not self._sort_reverse else ' ▲'
            return base_title + arrow
        return base_title

    # ------------------------------------------------------------------ items
    def _collect_current_items(self, boxes: crud.BoxIndex) -> List[Item]:
        """Товары для текущего выделения + заголовок раздела."""
        search_query = self.search_var.get().strip()

        if search_query:
            self.items_header.configure(text=f'Результаты поиска: {search_query}')
            return crud.search_items(self.client, search_query, boxes)

        if self.selected_box_id is None:
            self.items_header.configure(text='Все товары')
            return crud.get_all_items(self.client)

        if self.selected_box_id == -1:
            self.items_header.configure(text='Товары без расположения')
            return crud.get_items_without_box(self.client)

        box = boxes.get(self.selected_box_id)
        if box is None:
            self.items_header.configure(text='Контейнер не найден')
            return []

        self.items_header.configure(text=f'{box.box_name} — {box.full_path}')
        return crud.get_items_by_box(self.client, self.selected_box_id, include_children=True)

    def _refresh_items(self):
        # Контейнеры загружаются один раз на перерисовку: без этого
        # вызов full_path() для каждой строки давал бы запрос на каждую.
        boxes = crud.BoxIndex.load(self.client)
        items = self._collect_current_items(boxes)

        self._current_rows = []
        for item in items:
            type_name = item.item_type.item_type_name if item.item_type else '—'
            weight_str = format_weight(item.total_weight_g)
            self._current_rows.append((
                str(item.item_id),
                (type_name, item.quantity, weight_str, boxes.full_path(item.box_id)),
            ))

        self._render_items_table()

        # Статус
        total_qty = sum(i.quantity for i in items)
        total_weight = sum(i.total_weight_g for i in items)
        scale = ''
        if self.scale_monitor and self.scale_monitor.last_weight is not None:
            scale = f' | Весы: {self.scale_monitor.last_weight:.1f} г'
        self.status_var.set(
            f'Позиций: {len(items)} | Общее кол-во: {total_qty} '
            f'| Общий вес: {format_weight(total_weight)}{scale}'
        )

    def _render_items_table(self):
        keep_selection = self.items_tree.selection()
        keep_iid = keep_selection[0] if keep_selection else None

        self.table.clear()

        rows = self._current_rows
        if self._sort_column is not None:
            rows = sorted(rows, key=lambda r: self._sort_key_for_row(r, self._sort_column),
                          reverse=self._sort_reverse)

        for iid, values in rows:
            self.items_tree.insert('', 'end', iid=iid, values=values,
                                   tags=('evenrow',) if self.table._row_count % 2 == 0 else ('oddrow',))
            self.table._row_count += 1

        # Обновить индикаторы сортировки в шапках
        for col, title, _w in self.COLUMNS:
            self.items_tree.heading(col, text=self._heading_text(col, title))

        if keep_iid and self.items_tree.exists(keep_iid):
            self.items_tree.selection_set(keep_iid)
            self.items_tree.see(keep_iid)

        self.items_tree.update_idletasks()
        self.table.refresh_column_separators()

    # -------------------------------------------------------------- handlers
    def _on_tree_select(self, box_id):
        self.selected_box_id = box_id
        self._refresh_items()

    def _on_search(self):
        self._refresh_items()

    # ===== Box CRUD =====
    def _add_box(self):
        from ui.dialogs import BoxDialog
        parent_id = self.selected_box_id if self.selected_box_id and self.selected_box_id > 0 else None
        dialog = BoxDialog(self.root, self.client, mode='add', parent_id=parent_id)
        if dialog.result:
            self._refresh_all()

    def _edit_box(self):
        if self.selected_box_id is None or self.selected_box_id <= 0:
            messagebox.showinfo('Информация', 'Выберите контейнер для редактирования')
            return

        from ui.dialogs import BoxDialog
        box = crud.get_box_by_id(self.client, self.selected_box_id)
        if not box:
            return

        dialog = BoxDialog(self.root, self.client, mode='edit', box=box)
        if dialog.result:
            self._refresh_all()

    def _delete_box(self):
        if self.selected_box_id is None or self.selected_box_id <= 0:
            messagebox.showinfo('Информация', 'Выберите контейнер для удаления')
            return

        box = crud.get_box_by_id(self.client, self.selected_box_id)
        if not box:
            return

        if messagebox.askyesno('Подтверждение', f'Удалить контейнер "{box.box_name}"?\nТовары останутся без расположения.'):
            affected = crud.delete_box(self.client, self.selected_box_id)
            self.selected_box_id = None
            self._refresh_all()
            if affected > 0:
                messagebox.showinfo('Информация', f'{affected} товар(ов) остались без расположения')

    # ===== Item Type CRUD =====
    def _add_item_type(self):
        from ui.dialogs import ItemTypeDialog
        dialog = ItemTypeDialog(self.root, self.client, mode='add')
        if dialog.result:
            self._refresh_all()

    # ===== Item CRUD =====
    def _add_item(self):
        from ui.dialogs import ItemDialog
        default_box_id = self.selected_box_id if self.selected_box_id and self.selected_box_id > 0 else None
        dialog = ItemDialog(self.root, self.client, mode='add', default_box_id=default_box_id)
        if dialog.result:
            self._refresh_all()

    def _edit_item(self):
        selection = self.items_tree.selection()
        if not selection:
            messagebox.showinfo('Информация', 'Выберите товар для редактирования')
            return

        item_id = int(selection[0])
        item = crud.get_item_by_id(self.client, item_id)
        if not item:
            return

        from ui.dialogs import ItemDialog
        dialog = ItemDialog(self.root, self.client, mode='edit', item=item)
        if dialog.result:
            self._refresh_all()

    def _delete_item(self):
        selection = self.items_tree.selection()
        if not selection:
            messagebox.showinfo('Информация', 'Выберите товар для удаления')
            return

        item_id = int(selection[0])
        item = crud.get_item_by_id(self.client, item_id)
        if not item:
            return

        type_name = item.item_type.item_type_name if item.item_type else '—'
        if messagebox.askyesno('Подтверждение', f'Удалить товар "{type_name}"?'):
            crud.delete_item(self.client, item_id)
            self._refresh_all()
