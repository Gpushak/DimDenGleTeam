"""HTTP-клиент к Warehouse API — единый источник данных десктопа."""
from __future__ import annotations

import json
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ApiError(Exception):
    def __init__(self, message: str, status: Optional[int] = None, detail: Any = None):
        super().__init__(message)
        self.status = status
        self.detail = detail


class ApiClient:
    def __init__(self, base_url: Optional[str] = None, timeout: float = 8.0):
        from database import api_base_url
        self.base_url = (base_url or api_base_url()).rstrip("/")
        self.timeout = timeout

    def health(self) -> dict:
        return self.get("/health")

    def get(self, path: str, params: Optional[dict] = None) -> Any:
        query = ""
        if params:
            filtered = {k: v for k, v in params.items() if v is not None}
            if filtered:
                query = "?" + urlencode(filtered)
        return self._request("GET", path + query)

    def post(self, path: str, body: Optional[dict] = None) -> Any:
        return self._request("POST", path, body)

    def patch(self, path: str, body: Optional[dict] = None) -> Any:
        return self._request("PATCH", path, body)

    def delete(self, path: str) -> Any:
        return self._request("DELETE", path)

    def _request(self, method: str, path: str, body: Optional[dict] = None) -> Any:
        url = self.base_url + path
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                if not raw:
                    return None
                return json.loads(raw)
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(detail)
                message = payload.get("detail", detail)
            except json.JSONDecodeError:
                message = detail or str(error)
            raise ApiError(str(message), status=error.code, detail=detail) from error
        except TimeoutError as error:
            # Python 3.10+ (в т.ч. 3.14) отдаёт TimeoutError из urlopen напрямую,
            # без обёртки URLError — иначе main.py падает, не показав диалог.
            raise ApiError(
                f"Сервер не отвечает ({self.base_url}): превышено время ожидания. "
                "Запустите API: uvicorn app.main:app --app-dir server --port 8000"
            ) from error
        except URLError as error:
            raise ApiError(
                f"Сервер недоступен ({self.base_url}): {error.reason}. "
                "Запустите API: uvicorn app.main:app --app-dir server --port 8000"
            ) from error
        except OSError as error:
            raise ApiError(
                f"Сервер недоступен ({self.base_url}): {error}. "
                "Запустите API: uvicorn app.main:app --app-dir server --port 8000"
            ) from error
