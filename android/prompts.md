# Промпты, использованные при разработке Android-части

## Каркас проекта
> Создай структуру пакетов для Android-приложения на Java: data.model, data.api, data.local, data.repo, ui, util.

## Retrofit-клиент
> Настрой Retrofit с Gson и OkHttp logging interceptor, таймауты 15 секунд, baseUrl из BuildConfig.

## Экран логина
> Сделай Activity на Java: два EditText (логин, пароль), Button, ProgressBar. POST /auth/login через Retrofit, сохранение JWT в SharedPreferences, валидация пустых полей.

## DTO
> Создай LoginRequest и LoginResponse для авторизации.

## Список складских списков
> Activity с RecyclerView, FAB для создания, загрузка через GET /inventory/lists. Адаптер с DiffUtil.

## Детальный экран списка
> Activity с RecyclerView позиций, загрузка через GET /inventory/lists/{id}/items, удаление через DELETE /inventory/items/{id} с AlertDialog-подтверждением.

## ScanActivity
> Activity на CameraX с PreviewView и ImageAnalysis. Запрос разрешения CAMERA в рантайме. Анализ кадров через ML Kit Barcode Scanning, формат QR_CODE. При распознавании — вернуть raw value в вызывающую Activity через setResult.

## WeighActivity
> Activity с опросом GET /weigh/session/{id} каждые 1.5 секунды через Handler. Показ брутто/тары/нетто. Кнопка «Подтвердить» активна только при stable=true, POST /weigh/confirm.

## Создание списка
> Activity с EditText и Button, POST /inventory/lists через Retrofit, возврат RESULT_OK.

## Настройки
> Activity с EditText для адреса сервера и кнопкой logout. SettingsStore на SharedPreferences. ApiClient пересоздаёт Retrofit при смене baseUrl.

## Room-кэш
> Entity, DAO и Database для списков и позиций. Repository с логикой «сеть → кэш»: при успехе сохраняем в Room, при ошибке — читаем из Room.

## WorkManager
> Worker для периодической синхронизации списков раз в 15 минут с требованием NetworkType.CONNECTED. Планировщик с enqueueUniquePeriodicWork. Ручной запуск через OneTimeWorkRequest.

## Тесты
> Unit-тесты парсинга QR-строки. Тест ApiService через MockWebServer: enqueue ответ, проверить код и тело.