[app]

# ---------------------------------------------------------------------------
# Application identity
# ---------------------------------------------------------------------------
title = YT Audio Player
package.name = ytaudioplayer
package.domain = org.ytaudioplayer

# ---------------------------------------------------------------------------
# Source files
# ---------------------------------------------------------------------------
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,txt,ico,json
source.exclude_dirs = .git,bin,.buildozer,__pycache__,tests,.github
source.exclude_patterns = *.exe,*.pyw,*.apk,*.zip

version = 0.7.0

# ---------------------------------------------------------------------------
# Python requirements
#
# python-for-android installs pure-Python packages with ``--no-deps``, so
# every runtime dependency of yt-dlp has to be listed explicitly here.
# ``brotli`` and ``pycryptodomex`` are intentionally omitted: they are C
# extensions with no p4a recipe, and yt-dlp treats both as optional.
# ---------------------------------------------------------------------------
requirements = python3,kivy,pyjnius,android,openssl,sqlite3,yt-dlp,certifi,requests,urllib3,charset-normalizer,idna,mutagen

orientation = portrait
fullscreen = 0

# icon.png is generated from youtube_audio_icon.ico
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/icon.png

# ---------------------------------------------------------------------------
# Android configuration
# ---------------------------------------------------------------------------
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WAKE_LOCK,FOREGROUND_SERVICE,POST_NOTIFICATIONS

# Background playback: compile the Java foreground service and declare it in
# AndroidManifest.xml via a p4a hook (--native-service). The service is added
# inside <application> by the hook, which avoids hand-editing the manifest.
android.add_src = java
# Home-screen widget layouts, widget metadata and control icons.
android.add_resources = android_res
p4a.hook = p4a_hooks.py
android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
# Build only the 64-bit ARM target to keep CI time reasonable.
# Add armeabi-v7a here if you also need 32-bit devices.
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True
android.enable_androidx = True

[buildozer]
log_level = 2
warn_on_root = 1
