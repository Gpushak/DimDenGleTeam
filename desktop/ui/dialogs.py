"""Модальные диалоги для CRUD операций на customtkinter."""
import customtkinter as ctk
from tkinter import messagebox
from typing import Optional

from sqlalchemy.orm import Session

import crud
from models import Box, ItemType, Item


class BoxDialog:
    """Диалог создания/редактирования контейнера."""
    def __init__(self, parent, session: Session, mode: str, box: Optional[Box] = None, parent_id: Optional[int] = None):
        self.session = session
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

        # Родитель
        ctk.CTkLabel(frame, text='Родительский контейнер:').grid(row=0, column=0, sticky='w', pady=5)
        self.parent_var = ctk.StringVar()
        parent_combo = ctk.CTkComboBox(frame, variable=self.parent_var, state='readonly', width=250)
        parent_combo.grid(row=0, column=1, pady=5)

        parents = [('', None)]  # Корень
        all_boxes = crud.get_all_boxes(self.session)
        if self.mode == 'edit' and self.box:
            exclude_ids = self._get_descendant_ids(self.box.box_id)
            exclude_ids.append(self.box.box_id)
            all_boxes = [b for b in all_boxes if b.box_id not in exclude_ids]

        parent_values = ['— Корень —']
        self._parent_map = {'— Корень —': None}
        for b in all_boxes:
            path = b.full_path
            parent_values.append(path)
            self._parent_map[path] = b.box_id

        parent_combo.configure(values=parent_values)

        if self.mode == 'edit' and self.box:
            current_parent_path = self.box.parent.full_path if self.box.parent else '— Корень —'
            self.parent_var.set(current_parent_path)
        elif default_parent_id is not None:
            for path, bid in self._parent_map.items():
                if bid == default_parent_id:
                    self.parent_var.set(path)
                    break
        else:
            self.parent_var.set('— Корень —')

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

        box_types = crud.get_all_box_types(self.session)
        type_values = [bt.box_type_name for bt in box_types]
        type_combo.configure(values=type_values)
        self._type_map = {bt.box_type_name: bt.box_type_id for bt in box_types}

        if self.mode == 'edit' and self.box and self.box.box_type:
            self.type_var.set(self.box.box_type.box_type_name)
        elif box_types:
            self.type_var.set(box_types[0].box_type_name)

        # Кнопки
        btn_frame = ctk.CTkFrame(frame, fg_color='transparent')
        btn_frame.grid(row=3, column=0, columnspan=2, pady=15)
        ctk.CTkButton(btn_frame, text='Сохранить', command=self._save, width=100).pack(side='left', padx=5)
        ctk.CTkButton(btn_frame, text='Отмена', command=self.dialog.destroy, width=100).pack(side='left', padx=5)

    def _get_descendant_ids(self, box_id: int):
        result = []
        children = crud.get_child_boxes(self.session, box_id)
        for child in children:
            result.append(child.box_id)
            result.extend(self._get_descendant_ids(child.box_id))
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
                crud.add_box(self.session, name, box_type_id, parent_id)
            else:
                crud.update_box(self.session, self.box.box_id, name, box_type_id, parent_id)
            self.result = True
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror('Ошибка', str(e))


class ItemTypeDialog:
    """Диалог создания/редактирования типа товара."""
    def __init__(self, parent, session: Session, mode: str, item_type: Optional[ItemType] = None):
        self.session = session
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
                crud.add_item_type(self.session, name, weight_g)
            else:
                crud.update_item_type(self.session, self.item_type.item_type_id, name, weight_g)
            self.result = True
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror('Ошибка', str(e))


class ItemDialog:
    """Диалог создания/редактирования товара."""
    def __init__(self, parent, session: Session, mode: str, item: Optional[Item] = None, default_box_id: Optional[int] = None):
        self.session = session
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

        item_types = crud.get_all_item_types(self.session)
        type_values = []
        self._type_map = {}
        for it in item_types:
            label = f'{it.item_type_name} ({it.weight_g}г)' if it.weight_g else it.item_type_name
            type_values.append(label)
            self._type_map[label] = it.item_type_id

        type_combo.configure(values=type_values)

        if self.mode == 'edit' and self.item and self.item.item_type:
            it = self.item.item_type
            label = f'{it.item_type_name} ({it.weight_g}г)' if it.weight_g else it.item_type_name
            self.type_var.set(label)
        elif item_types:
            it = item_types[0]
            label = f'{it.item_type_name} ({it.weight_g}г)' if it.weight_g else it.item_type_name
            self.type_var.set(label)

        # Контейнер
        ctk.CTkLabel(frame, text='Расположение:').grid(row=1, column=0, sticky='w', pady=5)
        self.box_var = ctk.StringVar()
        box_combo = ctk.CTkComboBox(frame, variable=self.box_var, state='readonly', width=280)
        box_combo.grid(row=1, column=1, pady=5)

        boxes_options = [('Без расположения', None)]
        all_boxes = crud.get_all_boxes(self.session)
        for b in all_boxes:
            boxes_options.append((b.full_path, b.box_id))

        box_values = [b[0] for b in boxes_options]
        box_combo.configure(values=box_values)
        self._box_map = {b[0]: b[1] for b in boxes_options}

        if self.mode == 'edit' and self.item:
            if self.item.box:
                self.box_var.set(self.item.box.full_path)
            else:
                self.box_var.set('Без расположения')
        elif default_box_id is not None:
            for path, bid in boxes_options:
                if bid == default_box_id:
                    self.box_var.set(path)
                    break
        else:
            self.box_var.set('Без расположения')

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
                crud.add_item(self.session, item_type_id, box_id, quantity)
            else:
                crud.update_item(self.session, self.item.item_id, item_type_id, box_id, quantity)
            self.result = True
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror('Ошибка', str(e))
