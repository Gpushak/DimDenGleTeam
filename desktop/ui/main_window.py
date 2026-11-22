"""Главное окно приложения на customtkinter.

Сверху — классическая строка меню (Файл, Правка, Вид, Операции, Справка).
Основная область: дерево контейнеров слева, таблица товаров справа.
Кнопки управления собраны внизу каждой панели, над строкой состояния.
Рамки и границы нигде не рисуются — панели различаются только фоном.
"""
import csv
import io
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import List, Optional

import customtkinter as ctk
from PIL import Image, ImageDraw

from api_client import ApiClient, ApiError
from database import set_api_base_url, normalize_base_url

import crud
from qrutil import qr_payload, qr_png_bytes
from models import Box, Item
from ui import theme
from ui.widgets import DarkScrollableFrame, DarkTableFrame

APP_NAME = 'Складской учёт'
APP_VERSION = '1.0.0'

# Текст модального окна «Справка → Руководство».
GUIDE_TEXT = """\
Сверху — строка меню. Под ней поиск и две панели: дерево контейнеров слева и таблица товаров справа. Дерево и таблица занимают всё свободное место, кнопки стоят внизу панелей, над строкой состояния.

Левая панель «Структура склада»

«+ Контейнер» — новый контейнер. Выбранный контейнер станет родителем. Пункты «Все товары» и «Без расположения» создают контейнер в корне склада.
«Изменить» — название и родитель выбранного контейнера.
«Удалить» — удалить контейнер. Товары не стираются и остаются в «Без расположения».
Щелчок по названию показывает товары контейнера. Значки ▼ и ▶ сворачивают ветку.

Правая панель «Все товары»

«+ Тип товара» — новый тип: название и вес одной единицы.
«+ Товар» — новая позиция. Если в дереве выбран контейнер, он подставляется в диалог.
«Изменить» — тип, количество и место выбранной строки.
«Удалить» — удалить выбранную позицию.
«QR» — QR-этикетка выбранного товара, её можно считать телефоном.

Поиск сразу фильтрует таблицу. «Вид → Обновить» и клавиша F5 сбрасывают поиск и заново читают данные с сервера.

Строка состояния показывает число позиций, общее количество, общий вес и показание весов. «Вид → Показать/Скрыть строку состояния» убирает и возвращает её. Пока строка видна, пункт отмечен галочкой.

Меню «Файл» сохраняет текущую таблицу в CSV для Excel или в текстовый файл и закрывает программу.
«Правка» переводит курсор в поиск или удаляет то, с чем работали последним: строку таблицы или контейнер.
«Вид» переключает светлую и тёмную тему и обновляет данные.
«Операции» — добавить контейнер, добавить товар, изменить и сгенерировать QR.
«Справка» — адрес сервера, сведения о программе и это окно.

Горячие клавиши
Ctrl+Q — выход
Ctrl+F — перейти к поиску
Delete — удалить выбранный контейнер или товар
F2 — изменить выбранный контейнер или товар
F5 — обновить данные с сервера

Delete и F2 не срабатывают, пока курсор в поле ввода. Ctrl+Q и Ctrl+F работают и при русской раскладке.
"""


def _action_icon(kind: str) -> ctk.CTkImage:
    """Тонкий белый знак 16×16: на синей кнопке он совпадает с цветом подписи."""
    image = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    ink = (255, 255, 255, 255)
    if kind == 'edit':
        # Карандаш: грифель, корпус и кончик.
        draw.line((7, 25, 22, 10), fill=ink, width=3)
        draw.polygon([(21, 6), (27, 12), (22, 12)], fill=ink)
        draw.line((5, 27, 9, 23), fill=ink, width=3)
    elif kind == 'delete':
        # Корзина: ручка, крышка и контур ящика.
        draw.line((11, 5, 21, 5), fill=ink, width=3)
        draw.line((5, 10, 27, 10), fill=ink, width=3)
        draw.rounded_rectangle((7, 13, 25, 28), radius=2, outline=ink, width=2)
        draw.line((12, 17, 12, 24), fill=ink, width=2)
        draw.line((16, 17, 16, 24), fill=ink, width=2)
        draw.line((20, 17, 20, 24), fill=ink, width=2)
    else:
        # QR: три угловых маркера и несколько модулей.
        for origin_x, origin_y in ((4, 4), (18, 4), (4, 18)):
            draw.rectangle((origin_x, origin_y, origin_x + 9, origin_y + 9),
                           outline=ink, width=2)
            draw.rectangle((origin_x + 3, origin_y + 3, origin_x + 6, origin_y + 6),
                           fill=ink)
        for origin_x, origin_y in ((19, 19), (24, 19), (19, 24), (25, 25)):
            draw.rectangle((origin_x, origin_y, origin_x + 2, origin_y + 2), fill=ink)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(16, 16))


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

        self.winfo_toplevel().bind('<<ThemeChanged>>', self._on_theme_event, add='+')

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

    def _on_theme_event(self, event=None):
        # ttk рассылает <<ThemeChanged>> каждому виджету, а привязка на окне
        # срабатывает для всех из-за bindtags. Красим дерево один раз.
        if event is not None and event.widget is not self.winfo_toplevel():
            return
        self._on_theme_change()

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


class ThemedMenu:
    """Пункты одного выпадающего меню. Рисуется заново при каждом открытии."""

    def __init__(self):
        self.items: List[dict] = []

    def add_command(self, label, command=None, accelerator=''):
        self.items.append({'kind': 'command', 'label': label,
                           'command': command, 'accelerator': accelerator})

    def add_separator(self):
        self.items.append({'kind': 'separator'})

    def add_checkbutton(self, label, variable, command=None):
        self.items.append({'kind': 'check', 'label': label,
                           'variable': variable, 'command': command})

    def add_radiobutton(self, label, value, variable, command=None):
        self.items.append({'kind': 'radio', 'label': label, 'value': value,
                           'variable': variable, 'command': command})


class ThemedMenuBar(ctk.CTkFrame):
    """Строка меню в цветах текущей темы.

    Системное меню Windows рисуется отдельно и не принимает цвета окна,
    поэтому пункты — обычные кнопки панели, а список открывается своим окном.
    """

    def __init__(self, master):
        pal = theme.palette()
        super().__init__(master, fg_color=pal.panel_bg, corner_radius=0,
                         border_width=0, height=34)
        self.pack_propagate(False)
        self._entries = []
        self._popup = None
        self._open_index = None
        toplevel = self.winfo_toplevel()
        toplevel.bind('<Escape>', self._on_escape, add='+')
        # Клик мимо списка закрывает его. CTk запрещает bind_all на своих
        # виджетах — вешаем обработчик через tk.
        tk.Misc.bind_all(toplevel, '<Button-1>', self._on_global_click, add='+')

    def add_cascade(self, label: str, menu: ThemedMenu) -> ThemedMenu:
        pal = theme.palette()
        index = len(self._entries)
        button = ctk.CTkButton(
            self, text=label,
            width=max(52, 11 * len(label) + 18), height=26,
            corner_radius=4, border_width=0,
            fg_color='transparent', hover_color=pal.hover,
            text_color=pal.text, font=ctk.CTkFont(size=13),
            command=lambda i=index: self._on_title_click(i),
        )
        button.pack(side='left', padx=(8 if index == 0 else 0, 2), pady=4)
        button.bind('<Enter>', lambda _event, i=index: self._on_title_enter(i), add='+')
        self._entries.append((label, menu, button))
        return menu

    def cascade_labels(self) -> List[str]:
        return [label for label, _menu, _button in self._entries]

    def apply_theme(self):
        """Перекрасить полосу и закрыть открытый список: он собран в старых цветах."""
        self.close()
        pal = theme.palette()
        self.configure(fg_color=pal.panel_bg)
        for _label, _menu, button in self._entries:
            button.configure(fg_color='transparent', hover_color=pal.hover,
                             text_color=pal.text)

    def close(self):
        popup = self._popup
        self._popup = None
        self._open_index = None
        if popup is not None:
            try:
                popup.destroy()
            except tk.TclError:
                pass
        pal = theme.palette()
        for _label, _menu, button in self._entries:
            try:
                if button.winfo_exists():
                    button.configure(fg_color='transparent', text_color=pal.text,
                                     hover_color=pal.hover)
            except tk.TclError:
                pass

    def _on_title_click(self, index: int):
        if self._open_index == index:
            self.close()
            return
        self._open_menu(index)

    def _on_title_enter(self, index: int):
        # Как в обычном меню: пока список открыт, наведение переключает его.
        if self._open_index is not None and self._open_index != index:
            self._open_menu(index)

    def _open_menu(self, index: int):
        self.close()
        label, menu, button = self._entries[index]
        pal = theme.palette()
        button.configure(fg_color=pal.hover, text_color=pal.text)
        self._open_index = index
        self._popup = self._build_popup(menu, button)

    def _build_popup(self, menu: ThemedMenu, anchor):
        """Список внутри главного окна: цвета те же, что у панелей."""
        pal = theme.palette()
        top = self.winfo_toplevel()
        popup = ctk.CTkFrame(top, fg_color=pal.panel_bg, corner_radius=0,
                             border_width=1, border_color=pal.border)

        for item in menu.items:
            if item['kind'] == 'separator':
                ctk.CTkFrame(popup, fg_color=pal.border, height=1,
                             corner_radius=0, border_width=0).pack(
                    fill='x', padx=8, pady=4)
                continue
            self._add_row(popup, item, pal)

        x = anchor.winfo_rootx() - top.winfo_rootx()
        y = anchor.winfo_rooty() - top.winfo_rooty() + anchor.winfo_height()
        popup.place(x=x, y=y)
        popup.update_idletasks()
        width = max(popup.winfo_reqwidth(), 1)
        height = max(popup.winfo_reqheight(), 1)
        if x + width > top.winfo_width() - 4:
            x = max(4, top.winfo_width() - width - 4)
        if y + height > top.winfo_height() - 4:
            above = anchor.winfo_rooty() - top.winfo_rooty() - height
            y = max(4, above)
        popup.place(x=x, y=y)
        popup.lift()
        return popup

    def _add_row(self, shell, item, pal):
        row = ctk.CTkFrame(shell, fg_color=pal.panel_bg, corner_radius=4,
                           height=30, border_width=0)
        row.pack(fill='x', padx=4, pady=1)
        row.pack_propagate(False)

        marked = False
        if item['kind'] == 'check':
            marked = bool(item['variable'].get())
        elif item['kind'] == 'radio':
            marked = str(item['variable'].get()) == str(item['value'])
        mark = ctk.CTkLabel(row, text='✓' if marked else '', width=18,
                            text_color=pal.text, fg_color=pal.panel_bg)
        mark.pack(side='left', padx=(6, 0))
        caption = ctk.CTkLabel(row, text=item['label'], anchor='w',
                               text_color=pal.text, fg_color=pal.panel_bg)
        caption.pack(side='left', fill='x', expand=True, padx=(2, 8))
        accelerator = item.get('accelerator') or ''
        accel = None
        if accelerator:
            accel = ctk.CTkLabel(row, text=accelerator, text_color=pal.muted_text,
                                 fg_color=pal.panel_bg)
            accel.pack(side='right', padx=(8, 10))

        def activate(_event=None, current=item):
            self._run_item(current)
            return 'break'

        def enter(_event=None):
            self._paint_row(row, pal.hover, pal.text, pal.muted_text)

        def leave(event):
            target = row.winfo_containing(event.x_root, event.y_root)
            if self._widget_inside(target, row):
                return
            self._paint_row(row, pal.panel_bg, pal.text, pal.muted_text)

        for widget in (row, mark, caption, accel):
            if widget is None:
                continue
            widget.bind('<Button-1>', activate)
            widget.bind('<Enter>', enter)
            widget.bind('<Leave>', leave)

    @staticmethod
    def _paint_row(row, background, text, muted):
        row.configure(fg_color=background)
        children = row.winfo_children()
        # Три виджета — отметка, подпись и сочетание клавиш. Сочетание тусклее.
        for index, child in enumerate(children):
            color = muted if len(children) > 2 and index == len(children) - 1 else text
            try:
                child.configure(fg_color=background, text_color=color)
            except tk.TclError:
                pass

    def _run_item(self, item):
        if item['kind'] == 'check':
            item['variable'].set(not bool(item['variable'].get()))
        elif item['kind'] == 'radio':
            item['variable'].set(item['value'])
        command = item.get('command')
        self.close()
        if command is not None:
            command()

    def _on_escape(self, _event=None):
        if self._popup is None:
            return None
        self.close()
        return 'break'

    def _on_global_click(self, event):
        if self._popup is None:
            return None
        widget = event.widget
        if self._widget_inside(widget, self._popup) or self._is_title(widget):
            return None
        self.close()
        return None

    def _is_title(self, widget) -> bool:
        titles = {button for _label, _menu, button in self._entries}
        while widget is not None:
            if widget in titles:
                return True
            widget = getattr(widget, 'master', None)
        return False

    @staticmethod
    def _widget_inside(widget, ancestor) -> bool:
        while widget is not None:
            if widget == ancestor:
                return True
            widget = getattr(widget, 'master', None)
        return False


class MainWindow:
    # Подписи переключателя темы. Оставлены для вызова _on_theme_selected
    # (проверка контраста и ручное переключение по названию режима).
    _THEME_CAPTIONS = {'light': 'Светлая', 'dark': 'Тёмная'}
    _THEME_VALUES = {'Светлая': 'light', 'Тёмная': 'dark'}

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

        # Тема: палитра приложения и сохранённый режим (simplecache customtkinter).
        theme.apply_theme(theme.current_mode())

        # Данные последней выборки и состояние сортировки таблицы
        self._current_rows: List[tuple] = []   # (item_id, values tuple)
        self._sort_column: Optional[str] = None
        self._sort_reverse: bool = False
        self._suppress_search = False
        # Куда смотрят «Изменить» и «Удалить» в меню: дерево или таблица.
        self._command_target = 'box'
        # Пока таблица перерисовывается, её <<TreeviewSelect>> не меняет цель.
        self._rendering_table = False
        # Программный select_node при пересборке дерева — не смена цели команд.
        self._refreshing_tree = False

        self._create_widgets()
        self._refresh_all()

    # =============================================================== строка меню
    def _create_menubar(self):
        """Строка меню в цветах темы, выше рабочей области."""
        self._theme_var = tk.StringVar(value=theme.current_mode())
        self._status_visible = tk.BooleanVar(value=True)

        bar = ThemedMenuBar(self.root)
        bar.pack(side='top', fill='x')
        self._menu_bar = bar

        pal = theme.palette()
        self._menu_sep = ctk.CTkFrame(self.root, fg_color=pal.border, height=1,
                                      corner_radius=0, border_width=0)
        self._menu_sep.pack(side='top', fill='x')

        file_menu = bar.add_cascade('Файл', ThemedMenu())
        file_menu.add_command('Экспорт в Excel (CSV)', command=self._export_csv)
        file_menu.add_command('Экспорт в txt', command=self._export_txt)
        file_menu.add_separator()
        file_menu.add_command('Выход', command=self._quit, accelerator='Ctrl+Q')

        edit_menu = bar.add_cascade('Правка', ThemedMenu())
        edit_menu.add_command('Поиск', command=self._focus_search, accelerator='Ctrl+F')
        edit_menu.add_separator()
        edit_menu.add_command('Удалить', command=self._delete_current, accelerator='Delete')

        view_menu = bar.add_cascade('Вид', ThemedMenu())
        view_menu.add_radiobutton('Светлая тема', 'light', self._theme_var,
                                  command=self._on_theme_radio)
        view_menu.add_radiobutton('Тёмная тема', 'dark', self._theme_var,
                                  command=self._on_theme_radio)
        view_menu.add_separator()
        view_menu.add_command('Обновить', command=self._refresh_all, accelerator='F5')
        view_menu.add_separator()
        view_menu.add_checkbutton('Показать/Скрыть строку состояния',
                                  self._status_visible,
                                  command=self._toggle_status_bar)

        ops_menu = bar.add_cascade('Операции', ThemedMenu())
        ops_menu.add_command('Добавить контейнер', command=self._add_box)
        ops_menu.add_command('Добавить товар', command=self._add_item)
        ops_menu.add_separator()
        ops_menu.add_command('Изменить', command=self._edit_current, accelerator='F2')
        ops_menu.add_command('Сгенерировать QR', command=self._show_qr)

        help_menu = bar.add_cascade('Справка', ThemedMenu())
        help_menu.add_command('Сервер', command=self._show_server_dialog)
        help_menu.add_command('О программе', command=self._show_about)
        help_menu.add_separator()
        help_menu.add_command('Руководство', command=self._show_guide)

        self.root.bind('<Control-KeyPress>', self._on_control_key)
        self.root.bind('<F5>', self._on_f5)
        self.root.bind('<F2>', self._on_f2)
        self.root.bind('<Delete>', self._on_delete_key)

    def _paint_menus(self):
        """Перекрасить строку меню под текущую тему."""
        if hasattr(self, '_menu_bar'):
            self._menu_bar.apply_theme()
        if hasattr(self, '_menu_sep'):
            self._menu_sep.configure(fg_color=theme.palette().border)

    def _on_theme_radio(self):
        self._apply_mode(self._theme_var.get())

    def _on_theme_selected(self, caption: str):
        """Переключить тему по подписи «Светлая»/«Тёмная» или по ключу режима."""
        mode = self._THEME_VALUES.get(caption, caption)
        if mode not in ('light', 'dark'):
            mode = theme.current_mode()
        self._apply_mode(mode)

    def _apply_mode(self, mode: str):
        theme.apply_theme(mode)
        if getattr(self, '_theme_var', None) is not None and self._theme_var.get() != mode:
            self._theme_var.set(mode)
        self._retopaint_chrome()

    def _show_about(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title('О программе')
        dialog.geometry('420x340')
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
                 'позиции, весы, QR-этикетки.\n'
                 'Своей базы нет — все данные на сервере.\n\n'
                 'Qwentory Team',
            justify='center', text_color=pal.text,
        ).pack(pady=14)
        ctk.CTkButton(frame, text='Закрыть', width=120, border_width=0,
                      command=dialog.destroy).pack(pady=(0, 18))

        from ui.dialogs import _center_dialog
        _center_dialog(dialog, self.root, 420, 340)

    def _show_server_dialog(self):
        """Смена адреса общего сервера. Адрес проверяется запросом /health."""
        from ui.dialogs import _fit_dialog

        dialog = ctk.CTkToplevel(self.root)
        dialog.title('Сервер')
        dialog.transient(self.root)
        dialog.resizable(False, False)
        try:
            dialog.grab_set()
        except Exception:
            pass

        pal = theme.palette()
        dialog.configure(fg_color=pal.window_bg)
        frame = ctk.CTkFrame(dialog, fg_color='transparent')
        frame.pack(fill='both', expand=True, padx=16, pady=14)

        entry = ctk.CTkEntry(frame, width=440)
        entry.pack(fill='x', pady=(0, 12))
        entry.insert(0, self.client.base_url)

        def save():
            try:
                url = normalize_base_url(entry.get())
            except ValueError as error:
                messagebox.showerror('Сервер', str(error), parent=dialog)
                return
            probe = ApiClient(url)
            try:
                health = probe.health()
            except ApiError as error:
                messagebox.showerror('Сервер', str(error), parent=dialog)
                return
            set_api_base_url(url)
            self.client.base_url = url
            self._refresh_all()
            messagebox.showinfo(
                'Сервер',
                f'Подключено к {url}\n'
                f'База сервера: {health.get("database_path", "—")}',
                parent=dialog,
            )
            dialog.destroy()

        buttons = ctk.CTkFrame(frame, fg_color='transparent')
        buttons.pack(anchor='e')
        ctk.CTkButton(buttons, text='Сохранить', width=120, border_width=0,
                      command=save).pack(side='left', padx=(0, 8))
        ctk.CTkButton(buttons, text='Отмена', width=100, border_width=0,
                      fg_color='transparent', hover_color=pal.hover, text_color=pal.text,
                      command=dialog.destroy).pack(side='left')

        _fit_dialog(dialog, self.root, 480)

    # ============================================================== содержимое
    def _create_widgets(self):
        self._create_menubar()

        # Главный контейнер. Строка меню уже стоит над клиентской областью.
        main_frame = ctk.CTkFrame(self.root, fg_color='transparent')
        main_frame.pack(fill='both', expand=True, padx=14, pady=(10, 6))
        self._main_frame = main_frame

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
        self.search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var,
                                         width=300, corner_radius=8, height=34)
        self.search_entry.pack(side='left')

        # Основная область: две панели без рамок, разделены тонкой линией
        paned = ctk.CTkFrame(main_frame, fg_color='transparent')
        paned.pack(fill='both', expand=True)

        # Левая панель — дерево
        left_frame = ctk.CTkFrame(paned, width=368, fg_color='transparent',
                                  corner_radius=0, border_width=0)
        left_frame.pack(side='left', fill='y', padx=(0, 0))
        left_frame.pack_propagate(False)

        self._tree_title = ctk.CTkLabel(left_frame, text='Структура склада',
                                        font=ctk.CTkFont(size=14, weight='bold'),
                                        text_color=theme.palette().text)
        self._tree_title.pack(anchor='w', pady=(2, 6))

        # Кнопки — внизу панели, дерево забирает всё место между заголовком и ними.
        # side='bottom' пакуется раньше expand-виджета, иначе pack отдаст высоту дереву.
        self._tree_btn_frame = ctk.CTkFrame(left_frame, fg_color='transparent')
        self._tree_btn_frame.pack(side='bottom', fill='x', pady=(8, 0))
        self._edit_icon = _action_icon('edit')
        self._delete_icon = _action_icon('delete')
        self._qr_icon = _action_icon('qr')
        self._box_buttons = []
        for text, command, width in (('+ Контейнер', self._add_box, 112),
                                     ('Изменить', self._edit_box, 122),
                                     ('Удалить', self._delete_box, 116)):
            self._box_buttons.append(
                self._toolbar_button(self._tree_btn_frame, text, command, width))

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

        # Кнопки — под таблицей, в одну линию, над строкой состояния окна.
        self._item_btn_frame = ctk.CTkFrame(right_frame, fg_color='transparent')
        self._item_btn_frame.pack(side='bottom', fill='x', pady=(8, 0))
        self._item_buttons = []
        for text, command, width in (('+ Тип товара', self._add_item_type, 110),
                                     ('+ Товар', self._add_item, 90),
                                     ('Изменить', self._edit_item, 122),
                                     ('Удалить', self._delete_item, 116),
                                     ('QR', self._show_qr, 78)):
            self._item_buttons.append(
                self._toolbar_button(self._item_btn_frame, text, command, width))

        # Таблица товаров
        cols = tuple(c[0] for c in self.COLUMNS)
        headings = {c[0]: c[1] for c in self.COLUMNS}
        widths = {c[0]: c[2] for c in self.COLUMNS}
        self.table = DarkTableFrame(right_frame, columns=cols, headings=headings,
                                    column_widths=widths)
        self.table.pack(fill='both', expand=True)
        self.items_tree = self.table.tree
        self.items_tree.bind('<<TreeviewSelect>>', self._on_item_select, add='+')
        self.items_tree.bind('<Button-1>', self._mark_item_target, add='+')

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

    def _toolbar_button(self, parent, text, command, width):
        """Кнопка нижней панели. У части кнопок знак стоит перед текстом."""
        icon = None
        if text == 'Изменить':
            icon = self._edit_icon
        elif text == 'Удалить':
            icon = self._delete_icon
        elif text == 'QR':
            icon = self._qr_icon
        button = ctk.CTkButton(
            parent, text=text, command=command,
            width=width, height=30, corner_radius=8, border_width=0,
            image=icon, compound='left',
        )
        button.pack(side='left', padx=(0, 6))
        return button

    def _retopaint_chrome(self):
        """Перекрасить статичные элементы (меню, разделители) под текущую тему."""
        pal = theme.palette()
        self._paint_menus()
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
        """Перечитывает дерево и таблицу с сервера без фильтра поиска.

        Список контейнера — только его прямые товары, как на телефоне после
        «Обновить».
        """
        self._suppress_search = True
        try:
            self.search_var.set('')
        finally:
            self._suppress_search = False
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

        from ui.dialogs import _center_dialog
        _center_dialog(dialog, self.root, 360, 420)

    def _refresh_tree(self):
        selected = self.selected_box_id
        # Состояние раскрытия (self.tree._expanded_state) НЕ сбрасывается:
        # свёрнутые ветки остаются свёрнутыми после обновления данных.
        self._refreshing_tree = True
        try:
            self._rebuild_tree(selected)
        finally:
            self._refreshing_tree = False

    def _rebuild_tree(self, selected):
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
        return crud.get_items_by_box(self.client, self.selected_box_id, include_children=False)

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
            f'Позиций: {len(items)} | '
            f'Общее кол-во: {total_qty} | Общий вес: {format_weight(total_weight)}{scale}'
        )

    def _ordered_rows(self) -> List[tuple]:
        """Строки таблицы в том порядке, в каком они сейчас показаны."""
        rows = list(self._current_rows)
        if self._sort_column is not None:
            rows.sort(key=lambda row: self._sort_key_for_row(row, self._sort_column),
                      reverse=self._sort_reverse)
        return rows

    def _render_items_table(self):
        keep_selection = self.items_tree.selection()
        keep_iid = keep_selection[0] if keep_selection else None

        self._rendering_table = True
        try:
            self.table.clear()

            for iid, values in self._ordered_rows():
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
        finally:
            self._rendering_table = False

    # -------------------------------------------------------------- handlers
    def _on_tree_select(self, box_id):
        # Клик по дереву. Повторный select при пересборке цель команд не меняет.
        if not self._refreshing_tree:
            self._command_target = 'box'
        self.selected_box_id = box_id
        self._refresh_items()

    def _mark_item_target(self, event=None):
        """Клик по строке таблицы: следующие Изменить/Удалить относятся к товару."""
        if event is not None:
            region = self.items_tree.identify_region(event.x, event.y)
            if region in ('heading', 'separator', 'nothing'):
                return
        self._command_target = 'item'

    def _on_item_select(self, _event=None):
        if self._rendering_table:
            return
        self._command_target = 'item'

    def _edit_current(self, _event=None):
        """Изменить контейнер или товар — то, с чем работали последним."""
        if self._command_target == 'item' and self.items_tree.selection():
            self._edit_item()
        else:
            self._edit_box()

    def _delete_current(self, _event=None):
        """Удалить контейнер или товар — то, с чем работали последним."""
        if self._command_target == 'item' and self.items_tree.selection():
            self._delete_item()
        else:
            self._delete_box()

    def _export_csv(self):
        """Сохранить текущую таблицу в CSV, который открывается в Excel."""
        self._export_table(
            title='Экспорт в Excel (CSV)',
            extension='.csv',
            filetypes=(('CSV, Excel', '*.csv'), ('Все файлы', '*.*')),
            initial='товары.csv',
            delimiter=';',
        )

    def _export_txt(self):
        """Сохранить текущую таблицу в текстовый файл."""
        self._export_table(
            title='Экспорт в txt',
            extension='.txt',
            filetypes=(('Текст', '*.txt'), ('Все файлы', '*.*')),
            initial='товары.txt',
            delimiter='\t',
        )

    def _export_table(self, *, title, extension, filetypes, initial, delimiter):
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title=title,
            defaultextension=extension,
            filetypes=filetypes,
            initialfile=initial,
        )
        if not path:
            return
        headers = [column_title for _iid, column_title, _width in self.COLUMNS]
        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as handle:
                writer = csv.writer(handle, delimiter=delimiter, lineterminator='\n')
                writer.writerow(headers)
                for _iid, values in self._ordered_rows():
                    writer.writerow(values)
        except OSError as error:
            messagebox.showerror('Экспорт', str(error), parent=self.root)
            return
        messagebox.showinfo(
            'Экспорт',
            f'Сохранено строк: {len(self._current_rows)}\n{path}',
            parent=self.root,
        )

    def _quit(self, _event=None):
        self.root.destroy()
        return 'break'

    def _focus_search(self, _event=None):
        self.search_entry.focus_set()
        try:
            self.search_entry.select_range(0, 'end')
        except tk.TclError:
            pass
        return 'break'

    def _dialog_open(self) -> bool:
        try:
            return self.root.grab_current() is not None
        except tk.TclError:
            return False

    def _focus_is_editor(self) -> bool:
        widget = self.root.focus_get()
        if widget is None:
            return False
        try:
            kind = widget.winfo_class()
        except tk.TclError:
            return False
        return kind in ('Entry', 'Text', 'TEntry', 'Spinbox', 'TCombobox')

    def _on_control_key(self, event):
        """Ctrl+Q и Ctrl+F. На Windows keycode не зависит от раскладки."""
        keysym = (event.keysym or '').lower()
        # keycode — виртуальная клавиша Windows (не зависит от раскладки),
        # keysym — латиница или кириллица на этой же физической клавише.
        if event.keycode == 81 or keysym in ('q', 'cyrillic_shorti'):
            if self._dialog_open():
                return 'break'
            return self._quit()
        if event.keycode == 70 or keysym in ('f', 'cyrillic_a'):
            if self._dialog_open():
                return 'break'
            return self._focus_search()
        return None

    def _on_f5(self, _event=None):
        if self._dialog_open():
            return 'break'
        self._refresh_all()
        return 'break'

    def _on_f2(self, _event=None):
        if self._dialog_open() or self._focus_is_editor():
            return 'break' if self._dialog_open() else None
        self._edit_current()
        return 'break'

    def _on_delete_key(self, _event=None):
        if self._dialog_open() or self._focus_is_editor():
            return None
        self._delete_current()
        return 'break'

    def _toggle_status_bar(self):
        visible = bool(self._status_visible.get())
        self._status_sep.pack_forget()
        self._status_bar.pack_forget()
        if not visible:
            return
        self._status_sep.pack(fill='x', side='bottom')
        self._status_bar.pack(fill='x', side='bottom')

    def _show_guide(self):
        """Модальное окно: что делают кнопки и какие есть сочетания клавиш.

        Высота подгоняется под текст, чтобы список клавиш был виден целиком.
        Если на низком экране окно не влезает, текст прокручивается колёсиком.
        """
        from ui.dialogs import _center_dialog

        dialog = ctk.CTkToplevel(self.root)
        dialog.title('Руководство')
        dialog.transient(self.root)
        dialog.resizable(True, True)
        dialog.minsize(520, 360)
        try:
            dialog.grab_set()
        except Exception:
            pass

        pal = theme.palette()
        dialog.configure(fg_color=pal.window_bg)
        frame = ctk.CTkFrame(dialog, fg_color=pal.panel_bg, corner_radius=12,
                             border_width=0)
        frame.pack(fill='both', expand=True, padx=16, pady=16)

        ctk.CTkLabel(frame, text='Руководство',
                     font=ctk.CTkFont(size=18, weight='bold'),
                     text_color=pal.text).pack(anchor='w', padx=16, pady=(14, 6))

        ctk.CTkButton(frame, text='Закрыть', width=120, border_width=0,
                      command=dialog.destroy).pack(side='bottom', pady=(0, 14))

        scroller = DarkScrollableFrame(frame, fg_color='transparent')
        scroller.pack(fill='both', expand=True, padx=8, pady=(0, 8))
        body = ctk.CTkLabel(
            scroller, text=GUIDE_TEXT, justify='left', anchor='nw',
            text_color=pal.text, wraplength=560,
            font=ctk.CTkFont(size=13),
        )
        body.pack(fill='x', anchor='w', padx=8)

        dialog.bind('<Escape>', lambda _event: dialog.destroy())
        dialog.update_idletasks()
        screen_h = dialog.winfo_screenheight()
        # _place_dialog умножает высоту на масштаб окна — оставляем запас.
        scaling = dialog._get_window_scaling() or 1
        max_h = max(360, int(screen_h / scaling) - 80)
        # Заголовок, кнопка «Закрыть» и поля вокруг текста.
        height = min(body.winfo_reqheight() + 168, max_h)
        _center_dialog(dialog, self.root, 640, height)

    def _on_search(self):
        if self._suppress_search:
            return
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
