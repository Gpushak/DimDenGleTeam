# Android-приложение складского учёта

Часть проекта «АСУ складского учёта с весовым модулем и QR-идентификацией».

## Стек
- Java 17
- Android Studio, minSdk 24, targetSdk 34
- Retrofit 2.9 + OkHttp 4.12 + Gson
- CameraX 1.3 + ML Kit Barcode Scanning
- Room 2.6
- WorkManager 2.9
- ViewBinding

## Сборка
./gradlew assembleDebug

APK: app/build/outputs/apk/debug/app-debug.apk

## Запуск тестов
./gradlew test

## Настройка сервера
По умолчанию `http://10.0.2.2:8000/` — адрес хоста из эмулятора Android.
Меняется в приложении: экран «Настройки» (шестерёнка в тулбаре списков).
Сохранённый URL применяется при следующем запросе.

## Реализовано
- **LoginActivity** — авторизация через `POST /auth/login`, JWT в SharedPreferences
- **ListsActivity** — список складских списков (`GET /inventory/lists`), FAB создания, меню «Обновить» и «Настройки»
- **ListDetailActivity** — позиции списка (`GET /inventory/lists/{id}/items`), удаление (`DELETE /inventory/items/{id}`)
- **ScanActivity** — CameraX + ML Kit, сканирование QR, возврат значения
- **WeighActivity** — опрос веса (`GET /weigh/session/{id}`), подтверждение (`POST /weigh/confirm`)
- **CreateListActivity** — создание списка (`POST /inventory/lists`)
- **SettingsActivity** — смена адреса сервера, logout
- **Room-кэш** — списки и позиции сохраняются локально, офлайн-режим
- **WorkManager** — периодическая синхронизация раз в 15 минут + ручной запуск
- **Unit-тесты** — парсинг QR, ApiService с MockWebServer

## Архитектура
- `data/api` — Retrofit-интерфейс и клиент
- `data/model` — DTO для API
- `data/local` — Room-база, DAO, Entity, настройки, токен
- `data/repo` — репозитории с логикой «сеть → кэш»
- `data/sync` — WorkManager-задачи
- `ui` — Activity и адаптеры

## Endpoints
- `POST /auth/login`
- `GET /inventory/lists`
- `POST /inventory/lists`
- `GET /inventory/lists/{id}/items`
- `DELETE /inventory/items/{id}`
- `POST /inventory/scan`
- `GET /weigh/session/{id}`
- `POST /weigh/confirm`

## Промпты
См. prompts.md