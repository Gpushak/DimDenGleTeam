"""Адрес сервера и serial-порт весов.

Этот модуль не открывает SQLite и не хранит склад. Единственные данные
десктопа — на сервере Warehouse API. Файл `server_url.txt` рядом с этим
модулем запоминает адрес, выбранный в окне «Сервер».
"""
import os
from pathlib import Path

#: Общий сервер проекта (LAN), если адрес ещё не сохранён и не задан API_BASE_URL.
DEFAULT_API_BASE_URL = "http://192.168.0.9:8000"

_SAVED_URL = Path(__file__).with_name("server_url.txt")


def normalize_base_url(url: str) -> str:
    """Приводит адрес к виду http(s)://host[:port] без завершающего слэша."""
    text = (url or "").strip().rstrip("/")
    if not text:
        raise ValueError("Адрес сервера пустой")
    if not text.startswith(("http://", "https://")):
        text = "http://" + text
    return text


def api_base_url() -> str:
    """Адрес API: сохранённый в окне «Сервер», иначе API_BASE_URL, иначе общий сервер."""
    if _SAVED_URL.is_file():
        saved = _SAVED_URL.read_text(encoding="utf-8").strip()
        if saved:
            return normalize_base_url(saved)
    env = os.getenv("API_BASE_URL", "").strip()
    if env:
        return normalize_base_url(env)
    return DEFAULT_API_BASE_URL


def set_api_base_url(url: str) -> str:
    """Запоминает адрес и возвращает нормализованный вариант."""
    normalized = normalize_base_url(url)
    _SAVED_URL.write_text(normalized + "\n", encoding="utf-8")
    return normalized


def serial_port() -> str:
    return os.getenv("SERIAL_PORT", os.getenv("SERIAL_DEVICE", ""))
