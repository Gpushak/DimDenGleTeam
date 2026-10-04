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

# Один воркер (без --workers N): последнее показание весов хранится в памяти
# процесса, поэтому несколько воркеров рассыпали бы состояние /scale
# (см. app/routers/scale.py). Если весов станет много — состояние выносится в
# БД/Redis отдельной задачей.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]