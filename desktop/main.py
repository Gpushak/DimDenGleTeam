"""Точка входа в приложение складского учёта."""
import customtkinter as ctk

from database import init_db, get_session
from ui.main_window import MainWindow


def main():
    # Инициализация БД (создание таблиц + демо-данные)
    init_db()

    # Создание главного окна
    root = ctk.CTk()
    session = get_session()

    try:
        app = MainWindow(root, session)
        root.mainloop()
    finally:
        session.close()


if __name__ == '__main__':
    main()
