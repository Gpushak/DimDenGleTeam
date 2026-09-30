"""Главное окно приложения на customtkinter."""
import customtkinter as ctk
from tkinter import messagebox
from typing import Optional, List

from sqlalchemy.orm import Session

import crud
from models import Box, ItemType, Item


class TreeWidget(ctk.CTkScrollableFrame):
    """Виджет дерева контейнеров."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.nodes = {}  # box_id -> (button, children_frame)
        self.selected_box_id: Optional[int] = None
        self.on_select_callback = None
        
    def set_on_select(self, callback):
        self.on_select_callback = callback
        
    def clear(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.nodes.clear()
        
    def add_special_node(self, node_id, text):
        """Добавить специальный узел (Все товары, Без расположения)."""
        btn = ctk.CTkButton(
            self,
            text=text,
            command=lambda: self._on_node_click(node_id),
            anchor='w',
            height=30,
            fg_color='transparent',
            text_color=('black', 'white'),
            hover_color=('gray85', 'gray25')
        )
        btn.pack(fill='x', pady=2)
        self.nodes[node_id] = (btn, None)
        
    def add_box_node(self, box: Box, parent_id: Optional[int], level: int = 0):
        """Добавить узел контейнера."""
        type_name = box.box_type.box_type_name if box.box_type else ''
        label = f'{box.box_name} [{type_name}]'
        
        frame = ctk.CTkFrame(self, fg_color='transparent')
        frame.pack(fill='x', pady=1)
        
        # Отступ
        indent = ctk.CTkFrame(frame, width=level * 20, fg_color='transparent')
        indent.pack(side='left')
        
        # Кнопка
        btn = ctk.CTkButton(
            frame,
            text=label,
            command=lambda: self._on_node_click(box.box_id),
            anchor='w',
            height=30,
            fg_color='transparent',
            text_color=('black', 'white'),
            hover_color=('gray85', 'gray25')
        )
        btn.pack(side='left', fill='x', expand=True)
        
        # Контейнер для дочерних элементов
        children_frame = ctk.CTkFrame(self, fg_color='transparent')
        
        self.nodes[box.box_id] = (btn, children_frame)
        
    def _on_node_click(self, box_id):
        """Обработка клика по узлу."""
        # Снять выделение со всех
        for node_id, (btn, _) in self.nodes.items():
            btn.configure(fg_color='transparent')
            
        # Выделить текущий
        if box_id in self.nodes:
            btn, _ = self.nodes[box_id]
            btn.configure(fg_color=('gray75', 'gray35'))
            
        self.selected_box_id = box_id
        if self.on_select_callback:
            self.on_select_callback(box_id)
            
    def select_node(self, box_id):
        """Программно выбрать узел."""
        self._on_node_click(box_id)


class MainWindow:
    def __init__(self, root: ctk.CTk, session: Session):
        self.root = root
        self.session = session
        self.selected_box_id: Optional[int] = None

        self.root.title('Складской учёт')
        self.root.geometry('1200x700')
        
        # Настройка темы
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('blue')

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
        
        # Разделитель
        paned = ctk.CTkFrame(main_frame, fg_color='transparent')
        paned.pack(fill='both', expand=True)
        
        # Левая панель — дерево
        left_frame = ctk.CTkFrame(paned, width=350)
        left_frame.pack(side='left', fill='y', padx=(0, 5))
        left_frame.pack_propagate(False)
        
        ctk.CTkLabel(left_frame, text='Структура склада', font=ctk.CTkFont(size=14, weight='bold')).pack(anchor='w', pady=(5, 5))
        
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
        right_frame = ctk.CTkFrame(paned)
        right_frame.pack(side='left', fill='both', expand=True)
        
        # Заголовок
        self.items_header = ctk.CTkLabel(right_frame, text='Все товары', font=ctk.CTkFont(size=14, weight='bold'))
        self.items_header.pack(anchor='w', pady=(5, 5))
        
        # Кнопки управления товарами
        item_btn_frame = ctk.CTkFrame(right_frame, fg_color='transparent')
        item_btn_frame.pack(fill='x', pady=(0, 5))
        ctk.CTkButton(item_btn_frame, text='+ Тип товара', command=self._add_item_type, width=100).pack(side='left', padx=2)
        ctk.CTkButton(item_btn_frame, text='+ Товар', command=self._add_item, width=100).pack(side='left', padx=2)
        ctk.CTkButton(item_btn_frame, text='✎ Изменить', command=self._edit_item, width=100).pack(side='left', padx=2)
        ctk.CTkButton(item_btn_frame, text='✕ Удалить', command=self._delete_item, width=100).pack(side='left', padx=2)
        
        # Таблица товаров (используем Treeview из tkinter.ttk)
        import tkinter.ttk as ttk
        items_frame = ctk.CTkFrame(right_frame)
        items_frame.pack(fill='both', expand=True)
        
        cols = ('type', 'quantity', 'weight', 'date', 'location')
        self.items_tree = ttk.Treeview(items_frame, columns=cols, show='headings', height=20)
        self.items_tree.heading('type', text='Тип товара')
        self.items_tree.heading('quantity', text='Количество')
        self.items_tree.heading('weight', text='Вес')
        self.items_tree.heading('date', text='Дата')
        self.items_tree.heading('location', text='Расположение')
        
        self.items_tree.column('type', width=200)
        self.items_tree.column('quantity', width=80)
        self.items_tree.column('weight', width=100)
        self.items_tree.column('date', width=150)
        self.items_tree.column('location', width=250)
        
        scrollbar = ttk.Scrollbar(items_frame, orient='vertical', command=self.items_tree.yview)
        self.items_tree.configure(yscrollcommand=scrollbar.set)
        
        self.items_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Статус
        self.status_var = ctk.StringVar()
        ctk.CTkLabel(self.root, textvariable=self.status_var, anchor='w').pack(fill='x', padx=10, pady=(0, 5))

    def _refresh_all(self):
        self._refresh_tree()
        self._refresh_items()

    def _refresh_tree(self):
        self.tree.clear()
        
        # Специальные узлы
        self.tree.add_special_node(None, 'Все товары')
        self.tree.add_special_node(-1, 'Без расположения')
        
        # Корневые контейнеры
        root_boxes = crud.get_root_boxes(self.session)
        for box in root_boxes:
            self.tree.add_box_node(box, None, level=0)
            
    def _refresh_items(self):
        # Очистить таблицу
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)
            
        # Получить товары
        search_query = self.search_var.get().strip()
        if search_query:
            items = crud.search_items(self.session, search_query)
            self.items_header.configure(text=f'Результаты поиска: {search_query}')
        elif self.selected_box_id is None:
            items = crud.get_all_items(self.session)
            self.items_header.configure(text='Все товары')
        elif self.selected_box_id == -1:
            items = crud.get_items_without_box(self.session)
            self.items_header.configure(text='Товары без расположения')
        else:
            box = crud.get_box_by_id(self.session, self.selected_box_id)
            if box:
                items = crud.get_items_by_box(self.session, self.selected_box_id, include_children=True)
                self.items_header.configure(text=f'{box.box_name} — {box.full_path}')
            else:
                items = []
                self.items_header.configure(text='Контейнер не найден')
                
        # Заполнить таблицу
        for item in items:
            type_name = item.item_type.item_type_name if item.item_type else '—'
            weight = item.total_weight_g
            weight_str = f'{weight / 1000:.2f} кг' if weight > 1000 else f'{weight} г'
            date_str = item.date.strftime('%Y-%m-%d %H:%M') if item.date else ''
            location = crud.get_box_full_path(self.session, item.box_id)
            
            self.items_tree.insert('', 'end', iid=str(item.item_id), values=(
                type_name, item.quantity, weight_str, date_str, location
            ))
            
        # Статус
        total_qty = sum(i.quantity for i in items)
        total_weight = sum(i.total_weight_g for i in items)
        weight_str = f'{total_weight / 1000:.2f} кг' if total_weight > 1000 else f'{total_weight} г'
        self.status_var.set(f'Позиций: {len(items)} | Общее кол-во: {total_qty} | Общий вес: {weight_str}')

    def _on_tree_select(self, box_id):
        self.selected_box_id = box_id
        self._refresh_items()

    def _on_search(self):
        self._refresh_items()

    # ===== Box CRUD =====
    def _add_box(self):
        from ui.dialogs import BoxDialog
        parent_id = self.selected_box_id if self.selected_box_id and self.selected_box_id > 0 else None
        dialog = BoxDialog(self.root, self.session, mode='add', parent_id=parent_id)
        if dialog.result:
            self._refresh_all()

    def _edit_box(self):
        if self.selected_box_id is None or self.selected_box_id <= 0:
            messagebox.showinfo('Информация', 'Выберите контейнер для редактирования')
            return

        from ui.dialogs import BoxDialog
        box = crud.get_box_by_id(self.session, self.selected_box_id)
        if not box:
            return

        dialog = BoxDialog(self.root, self.session, mode='edit', box=box)
        if dialog.result:
            self._refresh_all()

    def _delete_box(self):
        if self.selected_box_id is None or self.selected_box_id <= 0:
            messagebox.showinfo('Информация', 'Выберите контейнер для удаления')
            return

        box = crud.get_box_by_id(self.session, self.selected_box_id)
        if not box:
            return

        if messagebox.askyesno('Подтверждение', f'Удалить контейнер "{box.box_name}"?\nТовары останутся без расположения.'):
            affected = crud.delete_box(self.session, self.selected_box_id)
            self.selected_box_id = None
            self._refresh_all()
            if affected > 0:
                messagebox.showinfo('Информация', f'{affected} товар(ов) остались без расположения')

    # ===== Item Type CRUD =====
    def _add_item_type(self):
        from ui.dialogs import ItemTypeDialog
        dialog = ItemTypeDialog(self.root, self.session, mode='add')
        if dialog.result:
            self._refresh_all()

    # ===== Item CRUD =====
    def _add_item(self):
        from ui.dialogs import ItemDialog
        default_box_id = self.selected_box_id if self.selected_box_id and self.selected_box_id > 0 else None
        dialog = ItemDialog(self.root, self.session, mode='add', default_box_id=default_box_id)
        if dialog.result:
            self._refresh_all()

    def _edit_item(self):
        selection = self.items_tree.selection()
        if not selection:
            messagebox.showinfo('Информация', 'Выберите товар для редактирования')
            return

        item_id = int(selection[0])
        item = self.session.get(Item, item_id)
        if not item:
            return

        from ui.dialogs import ItemDialog
        dialog = ItemDialog(self.root, self.session, mode='edit', item=item)
        if dialog.result:
            self._refresh_all()

    def _delete_item(self):
        selection = self.items_tree.selection()
        if not selection:
            messagebox.showinfo('Информация', 'Выберите товар для удаления')
            return

        item_id = int(selection[0])
        item = self.session.get(Item, item_id)
        if not item:
            return

        type_name = item.item_type.item_type_name if item.item_type else '—'
        if messagebox.askyesno('Подтверждение', f'Удалить товар "{type_name}"?'):
            crud.delete_item(self.session, item_id)
            self._refresh_all()
