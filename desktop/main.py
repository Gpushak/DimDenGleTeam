"""Точка входа в приложение складского учёта."""
import customtkinter as ctk
from tkinter import messagebox

from api_client import ApiClient, ApiError
from database import api_base_url, serial_port
from scale import ScaleMonitor
from ui.main_window import MainWindow


def main():
    client = ApiClient(api_base_url())
    try:
        client.health()
    except ApiError as error:
        # Проверяем доступность сервера до создания окна: диалог ошибки
        # показывается на скрытом корне, иначе Tk ругается на отсутствие окна.
        error_root = ctk.CTk()
        error_root.withdraw()
        messagebox.showerror(
            'Сервер недоступен',
            f'{error}\n\nСначала запустите API:\n'
            '  docker compose up -d api\n'
            '  или локально:\n'
            '  cd server && uvicorn app.main:app --host 0.0.0.0 --port 8000',
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