# Android-приложение складского учёта

Часть проекта «АСУ складского учёта с весовым модулем и QR-идентификацией».

## Стек
- Java
- Android Studio
- Retrofit + OkHttp + Gson
- CameraX + ML Kit Barcode Scanning
- Room
- WorkManager

## Сборка
./gradlew assembleDebug

APK: app/build/outputs/apk/debug/app-debug.apk

## Настройка сервера
Адрес API задаётся в `app/build.gradle` в поле `buildConfigField API_BASE_URL`.
По умолчанию `http://10.0.2.2:8000/` — это адрес хоста из эмулятора Android.

## Реализовано
- LoginActivity — авторизация через POST /auth/login
- TokenStore — хранение JWT в SharedPreferences
- ApiClient — Retrofit с логированием

## Планируется
- ListsActivity — список складских списков
- ListDetailActivity — позиции списка
- ScanActivity — сканирование QR
- WeighActivity — отображение веса с сервера
- WorkManager — фоновая синхронизация

## Endpoints
- POST /auth/login

## Промпты
См. prompts.md
