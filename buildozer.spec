[buildozer]
log_level = 2
warn_on_root = 1
bin_dir = bin

[app]
# --- Основное ---
title = CNC Checklist
package.name = cncchecklist
package.domain = com.cnc.checklist

# Главный файл приложения
source.dir = .
source.main = cnc_checklist_android.py

# Включаемые расширения
source.include_exts = py,kv,png,jpg,jpeg,svg,ttf,otf,ini,md,txt,atlas

# Версия приложения
version = 1.0.0

# --- Python и библиотеки ---
requirements = python3,kivy,android,androidstorage4kivy,kivymd==2.0.0
# Совместимый AGP для JDK 17
android.gradle_dependencies = com.android.tools.build:gradle:7.4.2

# --- Разрешения ---
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,CAMERA

# --- Экран ---
orientation = portrait
fullscreen = 0

# --- Архитектуры ---
android.archs = arm64-v8a

# --- SDK/NDK ---
# Обязательно прописываем пути, чтобы Buildozer НЕ качал свой SDK
android.api = 34
android.minapi = 26
android.build_tools = 34.0.0
android.sdk_dir = $ANDROID_SDK_ROOT
android.ndk_dir = $ANDROID_SDK_ROOT/ndk/25.1.8937393
# Автоматически соглашаться с лицензиями
android.accept_sdk_license = True

# Включаем AndroidX
android.enable_androidx = 1

# --- Прочее ---
# android.strip_libs = 1  # уменьшение размера apk
