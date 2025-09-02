[app]

# Имя приложения (будет отображаться на устройстве)
title = CNC Checklist

# Уникальное имя пакета (используется в Android)
package.name = cncchecklist
package.domain = com.cnc.checklist

# Каталог исходников
source.dir = .

# Какие файлы включить в сборку
source.include_exts = py,kv,json,ttf,png,jpg,md

# Версия приложения
version = 1.2

# Зависимости Python/Android
requirements = python3,kivy==2.3.0,kivymd,reportlab,pillow,plyer,androidstorage4kivy

# Язык/кодировка
# (по умолчанию достаточно оставить requirements)
# Можно явно указать:
# android.add_src = assets/DejaVuSans.ttf

# Поддерживаемая ориентация
orientation = landscape

# Полноэкранный режим (0 = нет)
fullscreen = 0

# Разрешения Android
android.permissions = INTERNET,CAMERA,READ_MEDIA_IMAGES,READ_MEDIA_VISUAL_USER_SELECTED,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# API и SDK настройки
android.api = 34
android.minapi = 26
android.ndk = 25b
android.sdk = 34
android.build_tools_version = 34.0.0
android.archs = arm64-v8a

# Splash screen и иконка
presplash.filename = assets/presplash.png
icon.filename = assets/icon.png

# Логирование Python в logcat (удобно для отладки)
android.logcat_filters = *:S python:D

# Кеширование ccache для ускорения повторных сборок
p4a.local_recipes =

# Если нужны сервисы (например, background-service), можно добавить здесь
# services =

[buildozer]

# Уровень логов
log_level = 2

# Хранение bin/ после сборки
bin_dir = bin
