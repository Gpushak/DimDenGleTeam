FROM python:3.12-slim

WORKDIR /app

# ВНИМАНИЕ: контекст сборки — корень репозитория (см. docker-compose.yml),
# поэтому все пути ниже начинаются с server/. Образ использует пакет shared/,
# который лежит рядом с server/, — ради него контекст и был расширен.

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/app ./app
COPY server/db ./db

# Пакет shared — единый источник протокола весов и QR; app/protocol.py
# импортирует его как from shared.protocol import ...
COPY shared ./shared

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]