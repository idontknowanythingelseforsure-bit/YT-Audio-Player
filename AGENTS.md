# AGENTS.md

Repo: I:\Projects\REA\YT Audio Player (Windows, PowerShell). Git repo, remote `idontknowanythingelseforsure-bit/YT-Audio-Player`, branch `master`.

## Layout
- `main.py` — Kivy app. `AndroidPlayer` owns `android.media.MediaPlayer` directly (this is the working playback path; do not move playback into the Java service).
- `java/org/ytaudioplayer/BackgroundService.java` — foreground service: `MediaSession`, `MediaStyle` notification, widget refresh. Its `MediaSession.Callback` broadcasts actions back to Python instead of controlling playback itself.
- `java/org/ytaudioplayer/MediaWidgetProvider.java` — home-screen widget provider.
- `android_res/` — widget layout, `xml/media_widget_info.xml`, drawables. Wired via `android.add_resources`.
- `p4a_hooks.py` — p4a `after_apk_build` hook: injects `--native-service` and patches the generated manifest with the widget receiver.
- `dist/` — built APKs. v0.2.0/v0.4.0 are direct-playback builds without the widget. v0.3.0 was broken (service owned playback). v0.7.0 is the current build: direct playback + lock-screen MediaSession + home widget (commit `f4d5c0e`).
- `playlists_data.json` — audio playlist data.
- Desktop/Windows extras at repo root: `YT_Audio_Player.exe`, `youtube_audio_player.pyw`, `export_cookies.py`, `youtube_cookies.txt`, icons.

## Notes
- PowerShell execution policy blocks `npx`; use `powershell -ExecutionPolicy Bypass -Command "..."` or `cmd /c`.
- Builds run in GitHub Actions (`.github/workflows/build_apk.yml`) on push to `master`; artifact `YT_Audio_Player-apk`, ~13 min. `buildozer` is not installed locally.
- App id/namespace `org.ytaudioplayer.ytaudioplayer`; Java package `org.ytaudioplayer`.
- Debug APK signatures differ per CI build — uninstall the old app before installing a new one.
- No local test suite.
