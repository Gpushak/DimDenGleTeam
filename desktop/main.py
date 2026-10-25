"""Точка входа в приложение складского учёта."""
import customtkinter as ctk
from tkinter import messagebox

from api_client import ApiClient, ApiError
from database import api_base_url, serial_port, normalize_base_url
from scale import ScaleMonitor
from ui.main_window import MainWindow

LOCAL_API_BASE_URL = 'http://127.0.0.1:8000'


def _candidate_urls():
    primary = api_base_url()
    urls = [primary]
    local = LOCAL_API_BASE_URL
    if normalize_base_url(primary) != local:
        urls.append(local)
    return urls


def _connect_client():
    last_error = None
    for url in _candidate_urls():
        client = ApiClient(url, timeout=3.0)
        try:
            client.health()
            client.timeout = 8.0
            return client
        except ApiError as error:
            last_error = error
    raise last_error


def main():
    try:
        client = _connect_client()
    except ApiError as error:
        # Проверяем доступность сервера до создания окна: диалог ошибки
        # показывается на скрытом корне, иначе Tk ругается на отсутствие окна.
        tried = '\n'.join(_candidate_urls())
        error_root = ctk.CTk()
        error_root.withdraw()
        messagebox.showerror(
            'Сервер недоступен',
            f'{error}\n\nПриложение не хранит свою базу: данные только на сервере.\n'
            f'Проверенные адреса:\n{tried}\n\n'
            'Запустите API (docker compose up или uvicorn) '
            'либо укажите адрес переменной API_BASE_URL.',
            parent=error_root,
        )
        error_root.destroy()
        return

    root = ctk.CTk()
    monitor = ScaleMonitor(client, port=serial_port())
    app = MainWindow(root, client, scale_monitor=monitor)

    # Весы обновляют таблицу товаров: публичное событие вместо вызова
    # приватного метода окна извне.
    def on_weight(_value):
        root.after(0, app.refresh_items)

    monitor.on_weight = on_weight
    monitor.start()
    try:
        root.mainloop()
    finally:
        monitor.stop()


if __name__ == '__main__':
    main()