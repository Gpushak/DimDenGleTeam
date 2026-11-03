"""Адрес сервера и serial-порт весов.

Этот модуль не открывает SQLite и не хранит склад. Единственные данные
десктопа — на сервере Warehouse API. Файл `server_url.txt` рядом с этим
модулем запоминает адрес, выбранный в окне «Сервер».
"""
import os
from pathlib import Path
from urllib.parse import urlparse

#: Общий сервер проекта через Tailscale. LAN-адрес 192.168.0.9 с других сетей
#: не открывается, а MagicDNS доступен участникам tailnet.
DEFAULT_API_BASE_URL = "http://warehouse-server.tail96180b.ts.net:8000"

_SAVED_URL = Path(__file__).with_name("server_url.txt")


def _is_loopback(host: str) -> bool:
    name = (host or "").lower().strip("[]")
    return name in {"localhost", "::1", "0.0.0.0"} or name.startswith("127.")


def normalize_base_url(url: str) -> str:
    """Приводит адрес к виду http(s)://host[:port] без завершающего слэша.

    Локальный API (localhost / 127.0.0.1) не принимается: десктоп и телефон
    должны смотреть в один общий сервер.
    """
    text = (url or "").strip().rstrip("/")
    if not text:
        raise ValueError("Адрес сервера пустой")
    if not text.startswith(("http://", "https://")):
        text = "http://" + text
    host = urlparse(text).hostname
    if not host or _is_loopback(host):
        raise ValueError(
            "Десктоп не подключается к локальному API. "
            "Укажите адрес общего сервера."
        )
    return text


def _configured_url(raw: str) -> str | None:
    """Нормализованный адрес либо None, если строка пустая или это локальный API."""
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return normalize_base_url(text)
    except ValueError as error:
        if "локальному API" in str(error):
            return None
        raise


def api_base_url() -> str:
    """Адрес API: сохранённый в окне «Сервер», иначе API_BASE_URL, иначе общий сервер.

    Сохранённый или переменная с localhost / 127.0.0.1 пропускаются.
    """
    if _SAVED_URL.is_file():
        saved = _configured_url(_SAVED_URL.read_text(encoding="utf-8"))
        if saved:
            return saved
    env = _configured_url(os.getenv("API_BASE_URL", ""))
    if env:
        return env
    return DEFAULT_API_BASE_URL


def set_api_base_url(url: str) -> str:
    """Запоминает адрес и возвращает нормализованный вариант."""
    normalized = normalize_base_url(url)
    _SAVED_URL.write_text(normalized + "\n", encoding="utf-8")
    return normalized


def serial_port() -> str:
    return os.getenv("SERIAL_PORT", os.getenv("SERIAL_DEVICE", ""))
