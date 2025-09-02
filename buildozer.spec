[app]
title = CNC Checklist
package.name = cncchecklist
package.domain = com.cnc.checklist
source.dir = .
source.include_exts = py,kv,json,ttf,png,jpg,md
version = 1.2

requirements = python3,kivy==2.3.0,kivymd==1.1.1,reportlab==3.6.13,pillow==10.3.0,plyer==2.1.0,androidstorage4kivy==0.1.1

orientation = landscape
fullscreen = 0

# Только современные пермишены (если не нужен прямой доступ к внешнему накопителю)
android.permissions = INTERNET,CAMERA,READ_MEDIA_IMAGES,READ_MEDIA_VISUAL_USER_SELECTED

android.api = 34
android.minapi = 26
android.ndk = 25b
android.sdk = 34
android.build_tools_version = 34.0.0
android.archs = arm64-v8a

presplash.filename = assets/presplash.png
icon.filename = assets/icon.png

android.use_androidx = 1
android.allow_backup = 0
android.logcat_filters = *:S python:D

[buildozer]
log_level = 2
bin_dir = bin
