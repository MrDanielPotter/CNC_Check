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
# ВАЖНО: kivymd зафиксирован на 2.0.0
requirements = python3,kivy==2.3.0,kivymd==2.0.0,reportlab,pillow,plyer,androidstorage4kivy

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
android.build_tools_version = 34.0.0
android.archs = arm64-v8a

# Splash screen и иконка
presplash.filename = assets/presplash.png
icon.filename = assets/icon.png

# Логирование Python в logcat (удобно для отладки)
android.logcat_filters = *:S python:D

# (опционально) локальные рецепты p4a
p4a.local_recipes =

[buildozer]
# Логи по-говорливее и куда класть бинарники
log_level = 2
bin_dir = bin

# Жёстко прокидываем пути SDK/NDK из env,
# чтобы buildozer/p4a не тянули preview и не искали свои
android.sdk_dir = %(ANDROID_HOME)s
android.ndk_dir = %(ANDROID_NDK_HOME)s

# Фиксируем версию build-tools
android.build_tools = 34.0.0
