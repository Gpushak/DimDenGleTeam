"""Модальные диалоги для CRUD операций на customtkinter."""
import customtkinter as ctk
from tkinter import messagebox
from typing import Optional

from api_client import ApiClient
import crud
from models import Box, ItemType, Item


class BoxDialog:
    """Диалог создания/редактирования контейнера."""
    def __init__(self, parent, client: ApiClient, mode: str, box: Optional[Box] = None, parent_id: Optional[int] = None):
        self.client = client
        self.mode = mode
        self.box = box
        self.result = False

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title('Новый контейнер' if mode == 'add' else 'Редактировать контейнер')
        self.dialog.geometry('400x250')
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets(parent_id)
        self.dialog.wait_window()

    def _create_widgets(self, default_parent_id: Optional[int]):
        frame = ctk.CTkFrame(self.dialog)
        frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Контейнеры грузим один раз: из них считаются и пути, и исключения.
        boxes = crud.BoxIndex.load(self.client)

        # Родитель
        ctk.CTkLabel(frame, text='Родительский контейнер:').grid(row=0, column=0, sticky='w', pady=5)
        self.parent_var = ctk.StringVar()
        parent_combo = ctk.CTkComboBox(frame, variable=self.parent_var, state='readonly', width=250)
        parent_combo.grid(row=0, column=1, pady=5)

        ROOT_LABEL = '— Корень —'
        candidates = boxes.all()
        if self.mode == 'edit' and self.box:
            # Себя и потомков исключаем: контейнер нельзя сделать потомком
            # самого себя (сервер вернул бы 409).
            forbidden = self._descendant_ids(boxes, self.box.box_id)
            forbidden.add(self.box.box_id)
            candidates = [b for b in candidates if b.box_id not in forbidden]

        self._parent_map = {ROOT_LABEL: None}
        self._parent_map.update({boxes.full_path(b.box_id): b.box_id for b in candidates})
        parent_combo.configure(values=list(self._parent_map))

        if self.mode == 'edit' and self.box:
            current = boxes.get(self.box.parent_id)
            self.parent_var.set(boxes.full_path(current.box_id) if current else ROOT_LABEL)
        elif default_parent_id is not None:
            self.parent_var.set(
                boxes.full_path(default_parent_id)
                if default_parent_id in self._parent_map.values()
                else ROOT_LABEL
            )
        else:
            self.parent_var.set(ROOT_LABEL)

        # Название
        ctk.CTkLabel(frame, text='Название:').grid(row=1, column=0, sticky='w', pady=5)
        self.name_var = ctk.StringVar()
        if self.mode == 'edit' and self.box:
            self.name_var.set(self.box.box_name)
        name_entry = ctk.CTkEntry(frame, textvariable=self.name_var, width=250)
        name_entry.grid(row=1, column=1, pady=5)
        name_entry.focus()

        # Тип
        ctk.CTkLabel(frame, text='Тип контейнера:').grid(row=2, column=0, sticky='w', pady=5)
        self.type_var = ctk.StringVar()
        type_combo = ctk.CTkComboBox(frame, variable=self.type_var, state='readonly', width=250)
        type_combo.grid(row=2, column=1, pady=5)

        box_types = crud.get_all_box_types(self.client)
        type_values = [bt.box_type_name for bt in box_types]
        type_combo.configure(values=type_values)
        self._type_map = {bt.box_type_name: bt.box_type_id for bt in box_types}

        current_type = self.box.box_type_name if (self.mode == 'edit' and self.box) else ''
        if current_type and current_type in self._type_map:
            self.type_var.set(current_type)
        elif box_types:
            self.type_var.set(box_types[0].box_type_name)

        # Кнопки
        btn_frame = ctk.CTkFrame(frame, fg_color='transparent')
        btn_frame.grid(row=3, column=0, columnspan=2, pady=15)
        ctk.CTkButton(btn_frame, text='Сохранить', command=self._save, width=100).pack(side='left', padx=5)
        ctk.CTkButton(btn_frame, text='Отмена', command=self.dialog.destroy, width=100).pack(side='left', padx=5)

    @staticmethod
    def _descendant_ids(boxes: crud.BoxIndex, box_id: int) -> set:
        """Все потомки контейнера (обход в ширину по загруженному индексу)."""
        result = set()
        queue = list(boxes.children_of(box_id))
        while queue:
            child = queue.pop()
            if child.box_id in result:
                continue
            result.add(child.box_id)
            queue.extend(boxes.children_of(child.box_id))
        return result

    def _save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror('Ошибка', 'Введите название')
            return

        type_name = self.type_var.get()
        box_type_id = self._type_map.get(type_name)
        if not box_type_id:
            messagebox.showerror('Ошибка', 'Выберите тип контейнера')
            return

        parent_path = self.parent_var.get()
        parent_id = self._parent_map.get(parent_path)

        try:
            if self.mode == 'add':
                crud.add_box(self.client, name, box_type_id, parent_id)
            else:
                crud.update_box(self.client, self.box.box_id, name, box_type_id, parent_id)
            self.result = True
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror('Ошибка', str(e))


class ItemTypeDialog:
    """Диалог создания/редактирования типа товара."""
    def __init__(self, parent, client: ApiClient, mode: str, item_type: Optional[ItemType] = None):
        self.client = client
        self.mode = mode
        self.item_type = item_type
        self.result = False

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title('Новый тип товара' if mode == 'add' else 'Редактировать тип товара')
        self.dialog.geometry('400x180')
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets()
        self.dialog.wait_window()

    def _create_widgets(self):
        frame = ctk.CTkFrame(self.dialog)
        frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Название
        ctk.CTkLabel(frame, text='Название типа:').grid(row=0, column=0, sticky='w', pady=5)
        self.name_var = ctk.StringVar()
        if self.mode == 'edit' and self.item_type:
            self.name_var.set(self.item_type.item_type_name)
        name_entry = ctk.CTkEntry(frame, textvariable=self.name_var, width=250)
        name_entry.grid(row=0, column=1, pady=5)
        name_entry.focus()

        # Вес
        ctk.CTkLabel(frame, text='Вес (г):').grid(row=1, column=0, sticky='w', pady=5)
        self.weight_var = ctk.StringVar()
        if self.mode == 'edit' and self.item_type and self.item_type.weight_g is not None:
            self.weight_var.set(str(self.item_type.weight_g))
        weight_entry = ctk.CTkEntry(frame, textvariable=self.weight_var, width=250)
        weight_entry.grid(row=1, column=1, pady=5)

        # Кнопки
        btn_frame = ctk.CTkFrame(frame, fg_color='transparent')
        btn_frame.grid(row=2, column=0, columnspan=2, pady=15)
        ctk.CTkButton(btn_frame, text='Сохранить', command=self._save, width=100).pack(side='left', padx=5)
        ctk.CTkButton(btn_frame, text='Отмена', command=self.dialog.destroy, width=100).pack(side='left', padx=5)

    def _save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror('Ошибка', 'Введите название')
            return

        weight_str = self.weight_var.get().strip()
        weight_g = int(weight_str) if weight_str else None

        try:
            if self.mode == 'add':
                crud.add_item_type(self.client, name, weight_g)
            else:
                crud.update_item_type(self.client, self.item_type.item_type_id, name, weight_g)
            self.result = True
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror('Ошибка', str(e))


class ItemDialog:
    """Диалог создания/редактирования товара."""
    def __init__(self, parent, client: ApiClient, mode: str, item: Optional[Item] = None, default_box_id: Optional[int] = None):
        self.client = client
        self.mode = mode
        self.item = item
        self.result = False

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title('Новый товар' if mode == 'add' else 'Редактировать товар')
        self.dialog.geometry('450x220')
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets(default_box_id)
        self.dialog.wait_window()

    def _create_widgets(self, default_box_id: Optional[int]):
        frame = ctk.CTkFrame(self.dialog)
        frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Тип товара
        ctk.CTkLabel(frame, text='Тип товара:').grid(row=0, column=0, sticky='w', pady=5)
        self.type_var = ctk.StringVar()
        type_combo = ctk.CTkComboBox(frame, variable=self.type_var, state='readonly', width=280)
        type_combo.grid(row=0, column=1, pady=5)

        def label_for(item_type: ItemType) -> str:
            return f'{item_type.item_type_name} ({item_type.weight_g}г)' if item_type.weight_g \
                else item_type.item_type_name

        item_types = crud.get_all_item_types(self.client)
        self._type_map = {label_for(t): t.item_type_id for t in item_types}
        type_combo.configure(values=list(self._type_map))

        if self.mode == 'edit' and self.item and self.item.item_type:
            current = label_for(self.item.item_type)
            self.type_var.set(current if current in self._type_map else '')
        elif item_types:
            self.type_var.set(label_for(item_types[0]))

        # Контейнер
        ctk.CTkLabel(frame, text='Расположение:').grid(row=1, column=0, sticky='w', pady=5)
        self.box_var = ctk.StringVar()
        box_combo = ctk.CTkComboBox(frame, variable=self.box_var, state='readonly', width=280)
        box_combo.grid(row=1, column=1, pady=5)

        NO_BOX_LABEL = 'Без расположения'
        boxes = crud.BoxIndex.load(self.client)

        self._box_map = {NO_BOX_LABEL: None}
        self._box_map.update({boxes.full_path(b.box_id): b.box_id for b in boxes.all()})
        box_combo.configure(values=list(self._box_map))

        if self.mode == 'edit' and self.item:
            # Путь берём из индекса: ответ позиции содержит лишь имя
            # контейнера, но не цепочку родителей.
            self.box_var.set(boxes.full_path(self.item.box_id))
        elif default_box_id is not None:
            self.box_var.set(
                boxes.full_path(default_box_id)
                if default_box_id in self._box_map.values()
                else NO_BOX_LABEL
            )
        else:
            self.box_var.set(NO_BOX_LABEL)

        # Количество
        ctk.CTkLabel(frame, text='Количество:').grid(row=2, column=0, sticky='w', pady=5)
        self.qty_var = ctk.StringVar()
        if self.mode == 'edit' and self.item:
            self.qty_var.set(str(self.item.quantity))
        else:
            self.qty_var.set('1')
        qty_entry = ctk.CTkEntry(frame, textvariable=self.qty_var, width=280)
        qty_entry.grid(row=2, column=1, pady=5)

        # Кнопки
        btn_frame = ctk.CTkFrame(frame, fg_color='transparent')
        btn_frame.grid(row=3, column=0, columnspan=2, pady=15)
        ctk.CTkButton(btn_frame, text='Сохранить', command=self._save, width=100).pack(side='left', padx=5)
        ctk.CTkButton(btn_frame, text='Отмена', command=self.dialog.destroy, width=100).pack(side='left', padx=5)

    def _save(self):
        type_label = self.type_var.get()
        item_type_id = self._type_map.get(type_label)
        if not item_type_id:
            messagebox.showerror('Ошибка', 'Выберите тип товара')
            return

        box_label = self.box_var.get()
        box_id = self._box_map.get(box_label)

        try:
            quantity = int(self.qty_var.get())
            if quantity < 1:
                raise ValueError('Количество должно быть >= 1')
        except ValueError as e:
            messagebox.showerror('Ошибка', f'Неверное количество: {e}')
            return

        try:
            if self.mode == 'add':
                crud.add_item(self.client, item_type_id, box_id, quantity)
            else:
                crud.update_item(self.client, self.item.item_id, item_type_id, box_id, quantity)
            self.result = True
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror('Ошибка', str(e))
