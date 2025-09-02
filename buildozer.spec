[buildozer]
log_level = 2
bin_dir = bin
warn_on_root = 1
# Если собираешь локально и хочешь кеш: uncomment
# build_dir = .buildozer

[app]
# --- Базовая информация ---
title = CNC Checklist
package.name = cncchecklist
package.domain = com.cnc.checklist
# Главный файл приложения (у тебя он не main.py)
source.dir = .
source.main = cnc_checklist_android.py
# Какие расширения брать в сборку
source.include_exts = py,kv,png,jpg,jpeg,svg,ttf,otf,ini,md,txt,atlas

# Версия приложения
version = 1.0.0
# (опционально) автоматическое увеличение версии по тэгам git
# version.regex = __version__ = ['"](.*)['"]
# version.filename = %(source.dir)s/app/__init__.py

# --- Зависимости Python/p4a ---
# Важно: фиксируем kivymd на 2.0.0 и добавляем доступ к хранилищу через SAF
requirements = python3,kivy,android,androidstorage4kivy,kivymd==2.0.0
# Если нужны PDF/шрифты с кириллицей в будущем:
# requirements = python3,kivy,android,androidstorage4kivy,kivymd==2.0.0,reportlab,pillow

# Включить поддержку AndroidX (рекомендуется для новых API)
android.enable_androidx = 1

# --- Права/разрешения ---
# Для сохранения отчётов и фотографий, камеры и будущей отправки по сети
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,CAMERA

# --- Ориентация/экран ---
# all | portrait | landscape
orientation = all
fullscreen = 0

# --- Архитектуры/цели ---
# Современные планшеты: arm64-v8a; при необходимости добавь armeabi-v7a
android.archs = arm64-v8a

# --- Штуки для иконок/прескрина (заполни при наличии) ---
# icon.filename = %(source.dir)s/media/icon.png
# presplash.filename = %(source.dir)s/media/presplash.png

# --- Buildozer/Gradle доп. опции (по необходимости) ---
# android.gradle_dependencies = androidx.core:core-ktx:1.13.1

# --- Ключи подписи (если подписываешь прямо в buildozer) ---
# (В CI мы подписываем отдельным шагом, поэтому тут можно не трогать)
# android.release_keystore = mykey.keystore
# android.release_keystore_pass = your_store_pass
# android.release_keyalias = your_alias
# android.release_keyalias_pass = your_key_pass

# --- Прочее ---
# Сократить размер apk за счёт удаления неиспользуемых библиотек
# android.strip_libs = 1

[android]
# Минимальная и целевая версии API
android.minapi = 26
android.api = 34

# Путь к SDK/NDK и версия build-tools — берутся из переменных окружения (CI)
# Локально можешь прописать абсолютные пути вместо $ANDROID_SDK_ROOT
android.sdk_dir = $ANDROID_SDK_ROOT
android.ndk_dir = $ANDROID_SDK_ROOT/ndk/25.1.8937393
android.build_tools = 34.0.0

# Bootstrap по умолчанию ok; если нужна webview: android.bootstrap = webview
# android.bootstrap = sdl2

# Если используешь Java 11 локально, убедись что JAVA_HOME указывает на JDK 11
# (в CI это делает actions/setup-java)

# Чистка потенциальных конфликтов Gradle (редко нужно)
# android.add_src = 
# android.add_jars = 

# Включить многопоточную сборку (ускоряет build)
# android.gradle_args = -Dorg.gradle.daemon=true -Dorg.gradle.jvmargs=-Xmx4g --no-parallel

# Если используешь NDK-библиотеки вручную, можно зафиксировать STL/ABI и т.д.
# android.ndk_api = 26

# Если понадобятся дополнительные ресурсы:
# android.add_assets = %(source.dir)s/assets

[buildozer:log]
# Фильтры логката (по желанию)
# android.logcat_filters = *:S python:D
