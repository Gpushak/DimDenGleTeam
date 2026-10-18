"""Проверка правок UI под Xvfb: перекраска подписей при смене темы и размеры диалогов."""
import sys

sys.path.insert(0, '/workspace/desktop')

import customtkinter as ctk
from ui import theme
from ui.main_window import MainWindow


class FakeClient:
    def get(self, path, params=None):
        if path == '/boxes':
            return [{'id': 1, 'name': 'Склад', 'box_type_id': 1,
                     'parent_id': None, 'box_type_name': 'Паллет'}]
        if path == '/box-types':
            return [{'id': 1, 'name': 'Паллет'}]
        if path == '/item-types':
            return [{'id': 1, 'name': 'Гвозди', 'weight_g': 5}]
        if path == '/items':
            return [{'id': 1, 'item_type_id': 1, 'box_id': 1, 'quantity': 3,
                     'weight_g': 15, 'box_name': 'Склад',
                     'item_type_name': 'Гвозди'}]
        if path == '/scale':
            from api_client import ApiError
            raise ApiError('no scale')
        return []

    def post(self, path, body=None):
        return {}

    def health(self):
        return {}


def label_color(win, attr):
    lbl = getattr(win, attr)
    col = lbl.cget('text_color')
    if isinstance(col, (tuple, list)):
        mode = theme.current_mode()
        col = col[0] if mode == 'light' else col[1] if len(col) > 1 else col[0]
    return str(col).lower()


def main():
    theme.apply_theme('dark')
    root = ctk.CTk()
    win = MainWindow(root, FakeClient(), scale_monitor=None)
    root.update()

    light_text = theme.LIGHT.text
    dark_text = theme.DARK.text
    print('dark:', {a: label_color(win, a) for a in
                    ('_search_label', '_tree_title', 'items_header')})
    assert all(label_color(win, a) == dark_text for a in
               ('_search_label', '_tree_title', 'items_header'))

    # переключаемся на светлую тему
    win._on_theme_selected('Светлая')
    root.update()
    print('light:', {a: label_color(win, a) for a in
                     ('_search_label', '_tree_title', 'items_header')})
    assert all(label_color(win, a) == light_text for a in
               ('_search_label', '_tree_title', 'items_header')), \
        'Подписи не перекрасились в светлой теме'

    # обратно в тёмную
    win._on_theme_selected('Тёмная')
    root.update()
    assert all(label_color(win, a) == dark_text for a in
               ('_search_label', '_tree_title', 'items_header'))

    # ---- диалоги: высота должна соответствовать содержимому ----
    from ui.dialogs import BoxDialog, ItemTypeDialog, ItemDialog

    orig = ctk.CTkToplevel.wait_window
    ctk.CTkToplevel.wait_window = lambda self: None
    try:
        d1 = BoxDialog(root, FakeClient(), mode='add', parent_id=None)
        d1.dialog.update_idletasks()
        req_h = d1.dialog.winfo_reqheight()
        geo_h = int(d1.dialog.geometry().split('x')[1].split('+')[0])
        print('BoxDialog: req_h=%s geo_h=%s (было фикс. 260)' % (req_h, geo_h))
        assert abs(geo_h - req_h) <= 2, 'BoxDialog: лишнее место снизу'
        d1.dialog.destroy()

        d2 = ItemTypeDialog(root, FakeClient(), mode='add')
        d2.dialog.update_idletasks()
        req_h = d2.dialog.winfo_reqheight()
        geo_h = int(d2.dialog.geometry().split('x')[1].split('+')[0])
        print('ItemTypeDialog: req_h=%s geo_h=%s (было фикс. 210)' % (req_h, geo_h))
        assert abs(geo_h - req_h) <= 2, 'ItemTypeDialog: лишнее место снизу'
        d2._closed = True
        if d2._after_id:
            d2.dialog.after_cancel(d2._after_id)
        d2.dialog.destroy()

        d3 = ItemDialog(root, FakeClient(), mode='add', default_box_id=1)
        d3.dialog.update_idletasks()
        req_h = d3.dialog.winfo_reqheight()
        geo_h = int(d3.dialog.geometry().split('x')[1].split('+')[0])
        print('ItemDialog: req_h=%s geo_h=%s (было фикс. 240)' % (req_h, geo_h))
        assert abs(geo_h - req_h) <= 2, 'ItemDialog: лишнее место снизу'
        d3.dialog.destroy()
    finally:
        ctk.CTkToplevel.wait_window = orig

    root.destroy()
    print('ALL OK')


if __name__ == '__main__':
    main()
