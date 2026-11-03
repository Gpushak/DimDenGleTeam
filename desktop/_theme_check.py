"""Проверка контраста светлой темы, скорости переключения и верхней полосы."""
import sys
import time

sys.path.insert(0, '.')

import customtkinter as ctk
from PIL import ImageGrab
from api_client import ApiError
from ui import theme
from ui.main_window import MainWindow


class Fake:
    base_url = 'http://example'

    def get(self, path, params=None):
        if path == '/boxes':
            return [{'id': 1, 'name': 'Склад', 'box_type_id': 1,
                     'parent_id': None, 'box_type_name': 'Паллет'}]
        if path == '/box-types':
            return [{'id': 1, 'name': 'Паллет'}]
        if path == '/item-types':
            return [{'id': 1, 'name': 'Гвозди', 'weight_g': 5}]
        if path == '/items':
            return []
        if path == '/scale':
            raise ApiError('x')
        return []

    def post(self, path, body=None):
        return {}

    def health(self):
        return {}


def pump(root, ms=300):
    root.after(ms, root.quit)
    root.mainloop()


def pick(color, index):
    if isinstance(color, (tuple, list)):
        return color[index]
    return color


def channel(value):
    value = value / 255
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def luminance(hex_color):
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join(c * 2 for c in hex_color)
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def main():
    root = ctk.CTk()
    root.geometry('1200x700+80+80')
    win = MainWindow(root, Fake(), scale_monitor=None)
    root.update()
    pump(root, 400)

    started = time.perf_counter()
    win._on_theme_selected('Светлая')
    root.update()
    light_s = time.perf_counter() - started
    print(f'switch to light: {light_s:.3f}s')
    assert light_s < 0.8, light_s

    button = win._refresh_button
    entry = None

    def walk(widget):
        nonlocal entry
        for child in widget.winfo_children():
            if entry is None and child.__class__.__name__ == 'CTkEntry':
                entry = child
            walk(child)

    walk(root)
    fg = pick(button.cget('fg_color'), 0)
    text = pick(button.cget('text_color'), 0)
    ratio = contrast(fg, text)
    print(f'button fg={fg} text={text} contrast={ratio:.2f} border={button.cget("border_width")}')
    assert ratio >= 4.5, ratio

    efg = pick(entry.cget('fg_color'), 0)
    eborder = pick(entry.cget('border_color'), 0)
    etext = pick(entry.cget('text_color'), 0)
    print(f'entry fg={efg} border={eborder} text={etext} width={entry.cget("border_width")}')
    assert entry.cget('border_width') >= 1
    assert contrast(efg, etext) >= 7
    assert contrast(efg, eborder) >= 3

    seg = win.theme_switch
    sfg = pick(seg.cget('selected_color'), 0)
    stext = pick(seg.cget('text_color'), 0)
    print(f'segment selected={sfg} text={stext} contrast={contrast(sfg, stext):.2f}')
    assert contrast(sfg, stext) >= 4.5

    started = time.perf_counter()
    win._on_theme_selected('Тёмная')
    root.update()
    dark_s = time.perf_counter() - started
    print(f'switch to dark: {dark_s:.3f}s')
    assert dark_s < 0.8, dark_s
    pump(root, 250)

    x, y = root.winfo_rootx(), root.winfo_rooty()
    w = root.winfo_width()
    shot = ImageGrab.grab(bbox=(x, y - 48, x + min(w, 700), y + 40))
    shot.save('_theme_top_dark.png')
    # Верх клиентской области (y = 48 в кадре, т.к. захват начат на 48 px выше).
    pixels = [shot.getpixel((20, row))[:3] for row in range(shot.height)]
    print('dark top pixels', pixels[:8], '... client', pixels[48:56])

    win._on_theme_selected('Светлая')
    root.update()
    pump(root, 250)
    shot = ImageGrab.grab(bbox=(x, y - 48, x + min(w, 700), y + 80))
    shot.save('_theme_top_light.png')
    print('ALL OK')
    root.destroy()


if __name__ == '__main__':
    main()
