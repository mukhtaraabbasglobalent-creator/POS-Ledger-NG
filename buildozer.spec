[app]

title = POS Ledger NG
package.name = posledgerng
package.domain = com.mukhtaraliyu

source.dir = android_app
source.include_exts = py,png,jpg,jpeg,kv,json,db
source.exclude_exts = spec
source.exclude_dirs = tests,.git,__pycache__,.buildozer

version = 1.0

requirements = python3,kivy,charset-normalizer==2.1.1

orientation = portrait
fullscreen = 0

android.permissions = INTERNET
android.allow_cleartext = True

android.api = 34
android.minapi = 24
android.ndk_api = 24
android.archs = arm64-v8a

android.enable_androidx = True

# icon.filename = data/icon.png
# presplash.filename = data/presplash.png


[buildozer]

log_level = 2
warn_on_root = 0
