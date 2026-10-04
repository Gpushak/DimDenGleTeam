# Эмулятор весового модуля (Serial/HX711 → POST /scale).
#
# Контекст сборки — firmware/, Dockerfile лежит в weight_module/.
#
#   docker compose --profile scale up --build
#
# Прошивка weight_module.ino сюда НЕ копируется: её прошивают на Arduino,
# а не запускают в контейнере.

FROM python:3.12-slim

WORKDIR /app

COPY weight_module/emulator.py ./emulator.py

# pyserial нужен только для режима реального Serial; без него эмулятор
# работает в режиме симуляции тестовых весов.
RUN pip install --no-cache-dir pyserial

# Healthcheck проверяет, что эмулятор публикует показания в API, то есть
# что цикл жив и сервер доступен.
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=15s \
    CMD python -c "import os,json,urllib.request; s=json.load(urllib.request.urlopen(os.getenv('API_BASE_URL','http://api:8000')+'/scale', timeout=5)); raise SystemExit(0 if s.get('weight_g') is not None else 1)"

CMD ["python", "emulator.py"]