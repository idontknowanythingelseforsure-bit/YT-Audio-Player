# YT Audio Player

YouTube audio playlist player. Ships as a Windows desktop app and an Android APK.

## Layout

| File | Purpose |
| --- | --- |
| `main.py` | Kivy UI used by Buildozer for the Android APK |
| `buildozer.spec` | python-for-android / Buildozer configuration |
| `youtube_audio_player.pyw` | Original tkinter desktop app |
| `youtube audio play.pyw` | Older copy of the desktop app |
| `export_cookies.py` | Exports Firefox YouTube cookies |
| `youtube_cookies.txt` | Optional Netscape cookie file |
| `icon.png` | Android icon (converted from `youtube_audio_icon.ico`) |
| `YT_Audio_Player.exe` | Pre-built Windows executable |

## Build the Android APK

The APK is built by GitHub Actions (`.github/workflows/build_apk.yml`) on every
push to `main`/`master`, or manually via **Actions → Build APK → Run workflow**.
The finished APK is attached to the run as the `YT_Audio_Player-apk` artifact.

To build locally on Linux:

```bash
sudo apt install -y git zip unzip openjdk-17-jdk autoconf libtool pkg-config \
  zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
pip install buildozer "cython==0.29.36"
buildozer -v android debug
```

The APK is written to `bin/`.

## Desktop

```powershell
pip install yt-dlp python-vlc
python youtube_audio_player.pyw
```

## Notes

- `yt-dlp` needs to be up to date for YouTube to keep working.
- The Android build uses `android.media.MediaPlayer`, so no VLC install is needed
  on the phone.
- **Background playback:** audio keeps playing when the app is minimized or the
  screen is off. A foreground service + partial wake lock keeps the process alive
  and Android shows a low-priority "Playing audio in the background" notification.
  On Android 13+ allow the notification permission when prompted.
- `youtube_cookies.txt` is optional. On Android it is only used if present in the
  app bundle; it is not required.
- Only `arm64-v8a` is built by default. Add `armeabi-v7a` to `android.archs` in
  `buildozer.spec` if you need 32-bit devices.
