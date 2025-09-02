[app]
title = CNC Checklist
package.name = cncchecklist
package.domain = com.cnc.checklist
source.dir = .
source.include_exts = py,kv,json,ttf,png,jpg,md
version = 1.2
requirements = python3,kivy==2.3.0,kivymd,reportlab,pillow,plyer,androidstorage4kivy
orientation = landscape
fullscreen = 0
android.permissions = INTERNET,CAMERA,READ_MEDIA_IMAGES,READ_MEDIA_VISUAL_USER_SELECTED,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 34
android.minapi = 26
android.archs = arm64-v8a
presplash.filename = assets/presplash.png
icon.filename = assets/icon.png
# Scoped storage true by default on modern Android

[buildozer]
log_level = 2

[android]
# Ensure FileProvider for camera temp files if needed
# (Buildozer will add automatically for plyer, but we keep defaults)
