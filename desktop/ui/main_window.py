"""Главное окно приложения на customtkinter."""
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
from ui.widgets import (
    apply_dark_theme,
    DarkScrollableFrame,
    DarkTableFrame,
    DARK_PANEL,
    DARK_BORDER,
)


def format_weight(grams: int) -> str:
    """Граммы в вид «450 г» / «1.25 кг» — общее для таблицы и строки статуса."""
    if grams >= 1000:
        return f'{grams / 1000:.2f} кг'
    return f'{grams} г'


class TreeWidget(DarkScrollableFrame):
    """Виджет дерева контейнеров.

    Узлы хранятся плоским списком: для каждого контейнера создаётся строка
    с кнопкой-переключателем (▼/▶/•) и кнопкой выбора. Дочерние узлы
    вставляются сразу после родителя, поэтому вложенные контейнеры
    отображаются полностью (в предыдущей версии рисовались только
    корневые узлы).
    """

    INDENT = 18
    SELECTED_COLOR = ('#cfe3ff', '#1f538d')
    NORMAL_TEXT_COLOR = ('black', 'white')
    HOVER_COLOR = ('gray85', 'gray25')

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        # box_id -> запись узла
        self.nodes: dict = {}
        self.selected_box_id: Optional[int] = None
        self.on_select_callback = None

    def set_on_select(self, callback):
        self.on_select_callback = callback

    def clear(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.nodes.clear()

    # ------------------------------------------------------------------ API
    def add_special_node(self, node_id, text):
        """Добавить специальный узел (Все товары, Без расположения)."""
        row = ctk.CTkFrame(self, fg_color='transparent')
        btn = ctk.CTkButton(
            row,
            text=text,
            command=lambda: self._on_node_click(node_id),
            anchor='w',
            height=30,
            corner_radius=6,
            fg_color='transparent',
            text_color=self.NORMAL_TEXT_COLOR,
            hover_color=self.HOVER_COLOR,
        )
        btn.pack(fill='x', expand=True)
        row.pack(fill='x', pady=1)
        self.nodes[node_id] = {'row': row, 'btn': btn, 'toggle': None,
                               'level': 0, 'expanded': True, 'has_children': False}

    def add_box_node(self, box: Box, parent_id: Optional[int], level: int = 0,
                     has_children: bool = False, expanded: bool = True):
        """Добавить узел контейнера (плоский ряд с отступом по уровню)."""
        # В дереве показываем только название контейнера, без типа в скобках
        label = box.box_name

        row = ctk.CTkFrame(self, fg_color='transparent')
        row.pack(fill='x', pady=1, padx=(level * self.INDENT, 0))

        toggle = ctk.CTkButton(
            row,
            width=24,
            height=30,
            corner_radius=6,
            text=self._toggle_text(has_children, expanded),
            fg_color='transparent',
            hover_color=self.HOVER_COLOR,
            text_color=('#666666', '#bbbbbb'),
            command=lambda bid=box.box_id: self._toggle_node(bid),
        )
        toggle.pack(side='left', padx=(0, 2))

        btn = ctk.CTkButton(
            row,
            text=label,
            command=lambda bid=box.box_id: self._on_node_click(bid),
            anchor='w',
            height=30,
            corner_radius=6,
            fg_color='transparent',
            text_color=self.NORMAL_TEXT_COLOR,
            hover_color=self.HOVER_COLOR,
        )
        btn.pack(side='left', fill='x', expand=True)

        self.nodes[box.box_id] = {'row': row, 'btn': btn, 'toggle': toggle,
                                  'level': level,
                                  'expanded': expanded, 'has_children': has_children}

    # ------------------------------------------------------- раскрытие узлов
    @staticmethod
    def _toggle_text(has_children: bool, expanded: bool) -> str:
        if not has_children:
            return '•'
        return '▼' if expanded else '▶'

    def _apply_visibility(self):
        """Скрыть/показать ряды в соответствии с состоянием раскрытия.

        Узлы идут в порядке обхода дерева (родитель раньше потомков),
        поэтому достаточно одного «горизонта»: всё, что находится глубже
        свёрнутого узла, скрыто до его родителя.
        """
        max_visible_level = 10 ** 9
        # Специальные узлы (id None / -1) идут первыми, затем контейнеры по id —
        # порядок обхода дерева: родитель раньше потомков.
        def node_order(box_id):
            return (0, 0) if not isinstance(box_id, int) else (1, box_id)
        for box_id, node in sorted(self.nodes.items(), key=lambda kv: node_order(kv[0])):
            if node['level'] > max_visible_level:
                node['row'].pack_forget()
                continue
            node['row'].pack(fill='x', pady=1, padx=(node['level'] * self.INDENT, 0))

            if node['has_children'] and not node['expanded']:
                max_visible_level = node['level'] - 1
            else:
                max_visible_level = 10 ** 9

    def _toggle_node(self, box_id: int):
        node = self.nodes.get(box_id)
        if not node or not node['has_children']:
            return
        node['expanded'] = not node['expanded']
        node['toggle'].configure(text=self._toggle_text(node['has_children'], node['expanded']))
        self._apply_visibility()
        self.update_idletasks()
        self._after_content_change()

    # ------------------------------------------------------------ выделение
    def _on_node_click(self, box_id):
        """Обработка клика по узлу."""
        # Снять выделение со всех
        for node in self.nodes.values():
            node['btn'].configure(fg_color='transparent',
                                  text_color=self.NORMAL_TEXT_COLOR)

        # Выделить текущий
        if box_id in self.nodes:
            self.nodes[box_id]['btn'].configure(
                fg_color=self.SELECTED_COLOR, text_color=('white', 'white'))

        self.selected_box_id = box_id
        if self.on_select_callback:
            self.on_select_callback(box_id)

    def select_node(self, box_id):
        """Программно выбрать узел."""
        self._on_node_click(box_id)


def natural_key(text: str):
    """Ключ естественной сортировки: 'Ячейка 2' < 'Ячейка 10'."""
    parts = re.split(r'(\d+)', str(text))
    return [int(p) if p.isdigit() else p.lower() for p in parts]


class MainWindow:
    # колонки таблицы товаров: (iid, заголовок, ширина, ключ значения)
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

        self.root.title('Складской учёт')
        self.root.geometry('1200x700')

        # Настройка темы
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('blue')
        apply_dark_theme()

        # Данные последней выборки и состояние сортировки таблицы
        self._current_rows: List[tuple] = []   # (item_id, values tuple)
        self._sort_column: Optional[str] = None
        self._sort_reverse: bool = False

        self._create_widgets()
        self._refresh_all()

    def _create_widgets(self):
        # Главный контейнер
        main_frame = ctk.CTkFrame(self.root, fg_color='transparent')
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Поиск
        search_frame = ctk.CTkFrame(main_frame, fg_color='transparent')
        search_frame.pack(fill='x', pady=(0, 10))

        ctk.CTkLabel(search_frame, text='Поиск:').pack(side='left', padx=(0, 5))
        self.search_var = ctk.StringVar()
        self.search_var.trace('w', lambda *_: self._on_search())
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var, width=300)
        search_entry.pack(side='left')

        # Основная область
        paned = ctk.CTkFrame(main_frame, fg_color='transparent')
        paned.pack(fill='both', expand=True)

        # Левая панель — дерево
        left_frame = ctk.CTkFrame(paned, width=350, fg_color=DARK_PANEL,
                                  border_width=1, border_color=DARK_BORDER)
        left_frame.pack(side='left', fill='y', padx=(0, 5))
        left_frame.pack_propagate(False)

        ctk.CTkLabel(left_frame, text='Структура склада',
                     font=ctk.CTkFont(size=14, weight='bold')).pack(anchor='w', pady=(5, 5))

        # Кнопки управления деревом
        tree_btn_frame = ctk.CTkFrame(left_frame, fg_color='transparent')
        tree_btn_frame.pack(fill='x', pady=(0, 5))
        ctk.CTkButton(tree_btn_frame, text='+ Контейнер', command=self._add_box, width=100).pack(side='left', padx=2)
        ctk.CTkButton(tree_btn_frame, text='✎ Изменить', command=self._edit_box, width=100).pack(side='left', padx=2)
        ctk.CTkButton(tree_btn_frame, text='✕ Удалить', command=self._delete_box, width=100).pack(side='left', padx=2)

        # Дерево
        self.tree = TreeWidget(left_frame)
        self.tree.pack(fill='both', expand=True)
        self.tree.set_on_select(self._on_tree_select)

        # Правая панель — товары
        right_frame = ctk.CTkFrame(paned, fg_color=DARK_PANEL,
                                   border_width=1, border_color=DARK_BORDER)
        right_frame.pack(side='left', fill='both', expand=True)

        # Заголовок
        self.items_header = ctk.CTkLabel(right_frame, text='Все товары',
                                         font=ctk.CTkFont(size=14, weight='bold'))
        self.items_header.pack(anchor='w', pady=(5, 5))

        # Кнопки управления товарами
        item_btn_frame = ctk.CTkFrame(right_frame, fg_color='transparent')
        item_btn_frame.pack(fill='x', pady=(0, 5))
        ctk.CTkButton(item_btn_frame, text='+ Тип товара', command=self._add_item_type, width=100).pack(side='left', padx=2)
        ctk.CTkButton(item_btn_frame, text='+ Товар', command=self._add_item, width=100).pack(side='left', padx=2)
        ctk.CTkButton(item_btn_frame, text='✎ Изменить', command=self._edit_item, width=100).pack(side='left', padx=2)
        ctk.CTkButton(item_btn_frame, text='✕ Удалить', command=self._delete_item, width=100).pack(side='left', padx=2)
        ctk.CTkButton(item_btn_frame, text='QR', command=self._show_qr, width=70).pack(side='left', padx=2)

        # Таблица товаров
        cols = tuple(c[0] for c in self.COLUMNS)
        headings = {c[0]: c[1] for c in self.COLUMNS}
        widths = {c[0]: c[2] for c in self.COLUMNS}
        self.table = DarkTableFrame(right_frame, columns=cols, headings=headings,
                                    column_widths=widths)
        self.table.pack(fill='both', expand=True, padx=8, pady=(0, 8))
        self.items_tree = self.table.tree

        # Разделители колонок + сортировка по клику на шапку
        for col, title, _w in self.COLUMNS:
            self.items_tree.heading(col, command=lambda c=col: self._sort_by_column(c))

        # Статус
        self.status_var = ctk.StringVar()
        ctk.CTkLabel(self.root, textvariable=self.status_var, anchor='w').pack(fill='x', padx=10, pady=(0, 5))

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

        dialog = ctk.CTkToplevel(self.root)
        dialog.title('QR-этикетка')
        dialog.geometry('360x420')
        dialog.transient(self.root)
        ctk.CTkLabel(dialog, text=payload, wraplength=320).pack(pady=8)
        label = ctk.CTkLabel(dialog, image=photo, text='')
        label.pack(pady=8)
        dialog._qr_image = photo
        ctk.CTkButton(dialog, text='Закрыть', command=dialog.destroy).pack(pady=8)

    def _refresh_tree(self):
        selected = self.selected_box_id
        self.tree.clear()

        # Специальные узлы
        self.tree.add_special_node(None, 'Все товары')
        self.tree.add_special_node(-1, 'Без расположения')

        # Полное дерево контейнеров (корни + все вложенные уровни)
        all_boxes = crud.get_all_boxes(self.client)
        children_map: dict = {}
        for b in all_boxes:
            children_map.setdefault(b.parent_id, []).append(b)
        for lst in children_map.values():
            lst.sort(key=lambda b: natural_key(b.box_name))

        def walk(parent_id, level):
            for box in children_map.get(parent_id, []):
                has_children = bool(children_map.get(box.box_id))
                self.tree.add_box_node(box, parent_id, level=level,
                                       has_children=has_children, expanded=True)
                if has_children:
                    walk(box.box_id, level + 1)

        walk(None, 0)

        self.tree._apply_visibility()
        self.tree.update_idletasks()
        self.tree._after_content_change()

        if selected is not None and selected in self.tree.nodes:
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
