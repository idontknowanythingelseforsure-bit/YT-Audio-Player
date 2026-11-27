# YT Audio Player

Direct download (no build needed):

- [YT_Audio_Player-v0.8.0-background.apk](https://github.com/idontknowanythingelseforsure-bit/YT-Audio-Player/raw/master/YT_Audio_Player-v0.8.0-background.apk) — Android (arm64-v8a)
- [YT_Audio_Player.exe](https://github.com/idontknowanythingelseforsure-bit/YT-Audio-Player/raw/master/YT_Audio_Player.exe) — Windows portable
- [YT_Audio_Player_Setup.exe](https://github.com/idontknowanythingelseforsure-bit/YT-Audio-Player/raw/master/YT_Audio_Player_Setup.exe) — Windows installer

All release assets: [latest release](https://github.com/idontknowanythingelseforsure-bit/YT-Audio-Player/releases/latest)

## v0.8.0 (Android)

Same playback core as v0.7.0 (direct Android `MediaPlayer`, lock-screen `MediaSession`, home-screen widget) plus desktop feature parity:

- **Queue No. field** — type the number of tracks to fetch (default `50`, up to `1000`), then press Play. Same as the desktop app.
- **Play stays enabled while playing**, so a new link/queue can be fetched without stopping first.
- **`?si=` tracking parameters are stripped** from links before yt-dlp sees them.
- **Playing row is highlighted and auto-scrolled** into view in the playlist.
- **Safer playlist parsing** — guards against empty yt-dlp results and normalizes entry URLs.

## Notes

- Debug APK signatures differ per CI build: uninstall the previous app before installing a new APK.
- Requires Android 5.0+ (minSdk 21), arm64-v8a.

## Source

`main.py` (Kivy Android app), `java/`, `android_res/`, `buildozer.spec`, `p4a_hooks.py`, `.github/workflows/`, `youtube_audio_player.pyw` (Windows tkinter/VLC app).
