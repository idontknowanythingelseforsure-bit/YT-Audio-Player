"""
YT Audio Player - Kivy port of the original tkinter desktop app.

This is the Android entry point used by Buildozer / python-for-android.

Audio backends:
  * Android -> android.media.MediaPlayer (via pyjnius)
  * Desktop -> python-vlc when available, otherwise Kivy SoundLoader

The original ``youtube_audio_player.pyw`` is kept untouched for the Windows
desktop build.
"""

import os
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.utils import platform

try:
    import yt_dlp
except Exception as exc:  # keep the UI usable even if yt-dlp is missing
    yt_dlp = None
    _YTDLP_IMPORT_ERROR = str(exc)
else:
    _YTDLP_IMPORT_ERROR = ""

try:
    from android.broadcast import BroadcastReceiver
except Exception:  # android module is only available on Android
    BroadcastReceiver = None

# --------------------------------------------------------------------------
# palette (matches the tkinter theme)
# --------------------------------------------------------------------------
BG = (0.071, 0.071, 0.071, 1)      # #121212
PANEL = (0.118, 0.118, 0.118, 1)   # #1E1E1E
BTN = (0.200, 0.200, 0.200, 1)     # #333333
ACCENT = (1.0, 0.341, 0.133, 1)    # #FF5722
FG = (1, 1, 1, 1)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_FILE = os.path.join(APP_DIR, "youtube_cookies.txt")
MAX_TRACKS = 500


# --------------------------------------------------------------------------
# audio backends
# --------------------------------------------------------------------------
try:
    from jnius import PythonJavaClass, java_method

    class _CompletionListener(PythonJavaClass):
        __javainterfaces__ = ["android/media/MediaPlayer$OnCompletionListener"]
        __javacontext__ = "app"

        def __init__(self, on_done):
            super().__init__()
            self._on_done = on_done

        @java_method("(Landroid/media/MediaPlayer;)V")
        def onCompletion(self, mp):
            self._on_done()
except Exception:  # jnius is only available on Android
    _CompletionListener = None


class AndroidPlayer:
    """Direct Android MediaPlayer (v0.2.0 working version)."""

    def __init__(self, on_complete=None):
        from jnius import autoclass

        media_player = autoclass("android.media.MediaPlayer")
        audio_manager = autoclass("android.media.AudioManager")

        self._audio_manager = audio_manager
        self.mp = media_player()
        self.mp.setAudioStreamType(audio_manager.STREAM_MUSIC)
        self._prepared = False
        self._completion = None
        if on_complete is not None and _CompletionListener is not None:
            self._completion = _CompletionListener(on_complete)
            self.mp.setOnCompletionListener(self._completion)

    def play(self, url, title="", artist="", art_url="", next_url=""):
        self.stop()
        self.mp.reset()
        self.mp.setAudioStreamType(self._audio_manager.STREAM_MUSIC)
        self.mp.setDataSource(url)
        self.mp.prepare()  # blocking, called from worker thread
        self.mp.start()
        self._prepared = True

    def pause(self):
        if self._prepared and self.mp.isPlaying():
            self.mp.pause()

    def resume(self):
        if self._prepared:
            self.mp.start()

    def stop(self):
        if self._prepared:
            try:
                self.mp.stop()
            except Exception:
                pass
        self._prepared = False

    def seek(self, ms):
        if self._prepared:
            self.mp.seekTo(int(ms))

    def position(self):
        if not self._prepared:
            return 0
        try:
            return int(self.mp.getCurrentPosition())
        except Exception:
            return 0

    def duration(self):
        if not self._prepared:
            return 0
        try:
            return int(self.mp.getDuration())
        except Exception:
            return 0

    def is_playing(self):
        try:
            return bool(self._prepared and self.mp.isPlaying())
        except Exception:
            return False


class DesktopPlayer:
    """Best-effort desktop backend used for local testing."""

    def __init__(self, on_complete=None):
        self._on_complete = on_complete
        self._instance = None
        self._player = None
        self._sound = None
        try:
            import vlc

            self._instance = vlc.Instance()
            self._player = self._instance.media_player_new()
        except Exception:
            self._player = None

    def play(self, url, title="", artist="", art_url="", next_url=""):
        if self._player is not None:
            media = self._instance.media_new(url)
            self._player.set_media(media)
            self._player.play()
            return
        from kivy.core.audio import SoundLoader

        if self._sound:
            self._sound.stop()
        self._sound = SoundLoader.load(url)
        if self._sound:
            self._sound.play()

    def pause(self):
        if self._player is not None:
            self._player.pause()
        elif self._sound:
            self._sound.stop()

    def resume(self):
        if self._player is not None:
            self._player.play()
        elif self._sound:
            self._sound.play()

    def stop(self):
        if self._player is not None:
            self._player.stop()
        elif self._sound:
            self._sound.stop()

    def seek(self, ms):
        if self._player is not None:
            self._player.set_time(int(ms))

    def position(self):
        if self._player is not None:
            return max(0, int(self._player.get_time()))
        if self._sound:
            return int((self._sound.get_pos() or 0) * 1000)
        return 0

    def duration(self):
        if self._player is not None:
            return max(0, int(self._player.get_length()))
        if self._sound:
            return int((self._sound.length or 0) * 1000)
        return 0

    def is_playing(self):
        if self._player is not None:
            return bool(self._player.is_playing())
        return bool(self._sound and self._sound.state == "play")


def make_player(on_complete=None):
    if platform == "android":
        return AndroidPlayer(on_complete)
    return DesktopPlayer(on_complete)


def _fmt_time(ms):
    if not ms or ms < 0:
        return "00:00"
    seconds = int(ms / 1000)
    return "%02d:%02d" % (seconds // 60, seconds % 60)


def _paint(widget, rgba):
    """Give a widget a solid background colour."""
    with widget.canvas.before:
        Color(*rgba)
        rect = Rectangle(pos=widget.pos, size=widget.size)
    widget.bind(
        pos=lambda w, v: setattr(rect, "pos", v),
        size=lambda w, v: setattr(rect, "size", v),
    )


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------
class RootWidget(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.app = app
        self._build()

    def _label(self, text="", color=FG, size=11, bold=False, height=None, **kwargs):
        label = Label(
            text=text,
            color=color,
            font_size=sp(size),
            bold=bold,
            halign="left",
            valign="middle",
            **kwargs
        )
        if height is not None:
            label.size_hint_y = None
            label.height = height
        label.bind(size=lambda w, s: setattr(w, "text_size", (s[0] - dp(4), None)))
        return label

    def _button(self, text, callback, bg=BTN, color=FG, size=11, **kwargs):
        button = Button(
            text=text,
            background_normal="",
            background_down="",
            background_color=bg,
            color=color,
            font_size=sp(size),
            **kwargs
        )
        button.bind(on_release=callback)
        return button

    def _build(self):
        # ---- title bar ----
        bar = BoxLayout(size_hint_y=None, height=dp(36), spacing=0)
        _paint(bar, (0, 0, 0, 1))
        bar.add_widget(
            self._label(
                "YT Audio Player",
                color=ACCENT,
                bold=True,
                size=13,
                padding=[dp(10), 0, 0, 0],
            )
        )
        bar.add_widget(
            self._button(
                "_",
                lambda *_: self.app.minimize(),
                bg=(0, 0, 0, 1),
                size_hint_x=None,
                width=dp(44),
            )
        )
        bar.add_widget(
            self._button(
                "X",
                lambda *_: self.app.stop(),
                bg=(0, 0, 0, 1),
                size_hint_x=None,
                width=dp(44),
            )
        )
        self.add_widget(bar)

        body = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(6))
        self.add_widget(body)

        # ---- link row ----
        link_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        link_row.add_widget(
            self._label("Link", size=11, size_hint_x=None, width=dp(34))
        )
        self.link_input = TextInput(
            multiline=False,
            font_size=sp(12),
            background_color=PANEL,
            foreground_color=FG,
            cursor_color=FG,
            padding=[dp(6), dp(9)],
        )
        link_row.add_widget(self.link_input)
        link_row.add_widget(
            self._button(
                "Paste",
                lambda *_: self.app.paste_link(),
                size_hint_x=None,
                width=dp(58),
                size=10,
            )
        )
        link_row.add_widget(
            self._button(
                "Clear",
                lambda *_: self.app.clear_link(),
                size_hint_x=None,
                width=dp(54),
                size=10,
            )
        )
        body.add_widget(link_row)

        body.add_widget(
            self._label(
                "Audio Only Mode Active",
                color=ACCENT,
                bold=True,
                size=11,
                height=dp(22),
            )
        )

        # ---- control buttons ----
        controls = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(5))
        self.play_btn = self._button(
            "> Play", lambda *_: self.app.start_play(), bg=ACCENT, size=10
        )
        self.pause_btn = self._button(
            "II Pause", lambda *_: self.app.toggle_pause(), size=10
        )
        self.stop_btn = self._button(
            "[] Stop", lambda *_: self.app.stop_play(), size=10
        )
        self.prev_btn = self._button(
            "<< Prev", lambda *_: self.app.play_prev(), size=10
        )
        self.next_btn = self._button(
            ">> Next", lambda *_: self.app.play_next(), size=10
        )
        for button in (
            self.play_btn,
            self.pause_btn,
            self.stop_btn,
            self.prev_btn,
            self.next_btn,
        ):
            controls.add_widget(button)
        body.add_widget(controls)

        # ---- timeline ----
        timeline = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(8))
        self.time_label = self._label(
            "00:00 / 00:00", size=11, size_hint_x=None, width=dp(96)
        )
        self.slider = Slider(min=0, max=100, value=0)
        self.slider.bind(
            on_touch_down=self._on_slider_down,
            on_touch_up=self._on_slider_up,
        )
        timeline.add_widget(self.time_label)
        timeline.add_widget(self.slider)
        body.add_widget(timeline)

        # ---- status / title ----
        self.status_label = self._label("Ready.", color=ACCENT, size=11, height=dp(36))
        body.add_widget(self.status_label)
        self.title_label = self._label(
            "No track selected", size=11, bold=True, height=dp(36)
        )
        body.add_widget(self.title_label)

        # ---- playlist ----
        body.add_widget(self._label("Playlist Queue:", size=11, height=dp(22)))
        scroll = ScrollView(size_hint=(1, 1))
        self.playlist_layout = BoxLayout(
            orientation="vertical", size_hint_y=None, spacing=dp(2)
        )
        self.playlist_layout.bind(
            minimum_height=self.playlist_layout.setter("height")
        )
        scroll.add_widget(self.playlist_layout)
        body.add_widget(scroll)

    # ---- slider callbacks ----
    def _on_slider_down(self, slider, touch):
        if slider.collide_point(*touch.pos):
            self.app.is_seeking = True
        return False

    def _on_slider_up(self, slider, touch):
        if self.app.is_seeking:
            self.app.seek_to(slider.value)
            self.app.is_seeking = False
        return False

    # ---- playlist ----
    def set_playlist(self, tracks):
        self.playlist_layout.clear_widgets()
        for index, track in enumerate(tracks):
            button = Button(
                text="%d. %s" % (index + 1, track["title"]),
                size_hint_y=None,
                height=dp(36),
                halign="left",
                valign="middle",
                background_normal="",
                background_down="",
                background_color=PANEL,
                color=FG,
                font_size=sp(11),
            )
            button.bind(
                size=lambda w, s: setattr(w, "text_size", (s[0] - dp(12), None))
            )
            button.bind(
                on_release=lambda _b, i=index: self.app.play_index(i)
            )
            self.playlist_layout.add_widget(button)


# --------------------------------------------------------------------------
# application
# --------------------------------------------------------------------------
class YTPlayerApp(App):
    is_seeking = BooleanProperty(False)
    is_playing = BooleanProperty(False)

    def build(self):
        Window.clearcolor = BG
        if platform == "android":
            Window.softinput_mode = "below_target"
        Window.bind(on_keyboard=self._on_keyboard)

        self.title = "YT Audio Player"
        self.playlist = []
        self.current_index = 0
        self._paused = False
        self._finished_guard = False
        self._notification_permission_requested = False
        self._last_service_sync = 0.0
        self.player = make_player(self._on_track_finished)

        self.root_widget = RootWidget(app=self)
        self._receiver = None
        self._setup_service_receiver()
        Clock.schedule_interval(self._tick, 0.5)
        return self.root_widget

    # ---- thread-safe UI helpers ----
    def _status(self, text):
        Clock.schedule_once(
            lambda dt: setattr(self.root_widget.status_label, "text", text)
        )

    def _title(self, text):
        Clock.schedule_once(
            lambda dt: setattr(self.root_widget.title_label, "text", text)
        )

    def _on_keyboard(self, window, key, *args):
        if key == 27:  # ESC / Android back button
            self.stop()
            return True
        return False

    def minimize(self):
        if platform == "android":
            try:
                from jnius import autoclass

                activity = autoclass("org.kivy.android.PythonActivity").mActivity
                activity.moveTaskToBack(True)
            except Exception as exc:
                self._status("Minimize failed: %s" % exc)
        else:
            Window.minimize()

    # ---- background playback service ----
    def _request_notification_permission(self):
        if platform != "android":
            return
        try:
            from android.permissions import request_permissions

            request_permissions(["android.permission.POST_NOTIFICATIONS"])
        except Exception:
            pass

    def _background_service_intent(self):
        from jnius import autoclass

        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        service_class = autoclass("org.ytaudioplayer.BackgroundService")
        intent = autoclass("android.content.Intent")()
        intent.setClass(activity, service_class)
        return activity, intent

    def _start_background_service(self):
        if platform != "android":
            return
        if not self._notification_permission_requested:
            self._notification_permission_requested = True
            self._request_notification_permission()
        try:
            from jnius import autoclass

            activity, intent = self._background_service_intent()
            if autoclass("android.os.Build$VERSION").SDK_INT >= 26:
                activity.startForegroundService(intent)
            else:
                activity.startService(intent)
        except Exception as exc:
            self._status("Background service error: %s" % exc)

    def _stop_background_service(self):
        if platform != "android":
            return
        try:
            activity, intent = self._background_service_intent()
            activity.stopService(intent)
        except Exception:
            pass

    def _notify_service(self, action, **extras):
        """Push playback state to the presentation service.

        The service never plays audio; it only renders the notification,
        the lock-screen MediaSession and the home-screen widget.
        """
        if platform != "android":
            return
        try:
            from jnius import autoclass

            activity, intent = self._background_service_intent()
            intent.setAction(action)
            for key, value in extras.items():
                if isinstance(value, int):
                    intent.putExtra(key, int(value))
                else:
                    intent.putExtra(key, str(value))

            sdk = autoclass("android.os.Build$VERSION").SDK_INT
            if sdk >= 26:
                try:
                    activity.startForegroundService(intent)
                    return
                except Exception:
                    pass
            activity.startService(intent)
        except Exception as exc:
            self._status("Service sync error: %s" % exc)

    # ---- lock-screen / widget command bridge ----
    def _setup_service_receiver(self):
        """Listen for NEXT / PREV / TRACK_FINISHED broadcasts from the service."""
        if platform != "android" or BroadcastReceiver is None:
            return
        try:
            self._receiver = BroadcastReceiver(
                self._on_service_broadcast,
                actions=[
                    "org.ytaudioplayer.action.TRACK_FINISHED",
                    "org.ytaudioplayer.action.TOGGLE",
                    "org.ytaudioplayer.action.NEXT",
                    "org.ytaudioplayer.action.PREV",
                    "org.ytaudioplayer.action.SEEK",
                    "org.ytaudioplayer.action.RESUME",
                    "org.ytaudioplayer.action.PAUSE",
                    "org.ytaudioplayer.action.STOP",
                ],
            )
            self._receiver.start()
        except Exception as exc:
            self._status("Service receiver error: %s" % exc)

    def _on_service_broadcast(self, context, intent):
        try:
            action = intent.getAction()
        except Exception:
            return
        if action == "org.ytaudioplayer.action.TRACK_FINISHED":
            self._on_track_finished()
        elif action == "org.ytaudioplayer.action.TOGGLE":
            self.toggle_pause()
        elif action == "org.ytaudioplayer.action.NEXT":
            self.play_next()
        elif action == "org.ytaudioplayer.action.PREV":
            self.play_prev()
        elif action == "org.ytaudioplayer.action.SEEK":
            try:
                position = int(intent.getIntExtra("position", 0))
            except Exception:
                position = 0
            if self.is_playing:
                self.player.seek(position)
                self._notify_service(
                    "org.ytaudioplayer.action.POSITION",
                    position=position,
                    duration=self.player.duration(),
                )
        elif action == "org.ytaudioplayer.action.RESUME":
            self.player.resume()
            self._paused = False
            self._status("Playing...")
            self._ui_playing(False)
            self._notify_service("org.ytaudioplayer.action.RESUME")
        elif action == "org.ytaudioplayer.action.PAUSE":
            self.player.pause()
            self._paused = True
            self._status("Paused.")
            self._ui_playing(True)
            self._notify_service("org.ytaudioplayer.action.PAUSE")
        elif action == "org.ytaudioplayer.action.STOP":
            self.stop_play()

    # ---- link helpers ----
    def paste_link(self):
        try:
            from kivy.core.clipboard import Clipboard

            text = Clipboard.paste()
            if text:
                self.root_widget.link_input.text = text.strip()
                self._status("Link pasted.")
            else:
                self._status("Clipboard is empty.")
        except Exception as exc:
            self._status("Clipboard error: %s" % exc)

    def clear_link(self):
        self.root_widget.link_input.text = ""

    # ---- yt-dlp options ----
    def _ydl_opts(self, **extra):
        options = {
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": False,
            "socket_timeout": 30,
        }
        if os.path.exists(COOKIES_FILE):
            options["cookiefile"] = COOKIES_FILE
        options.update(extra)
        return options

    # ---- playlist extraction ----
    def start_play(self):
        if yt_dlp is None:
            self._status("yt-dlp unavailable: %s" % _YTDLP_IMPORT_ERROR)
            return
        url = self.root_widget.link_input.text.strip()
        if not url:
            self._status("Please paste a YouTube link first.")
            return
        self._ui_loading()
        self._start_background_service()
        self._status("Fetching playlist...")
        self.root_widget.set_playlist([])
        self._title("Loading...")
        threading.Thread(
            target=self._extract_playlist, args=(url,), daemon=True
        ).start()

    def _extract_playlist(self, url):
        options = self._ydl_opts(
            noplaylist=False,
            extract_flat="in_playlist",
            playlistend=MAX_TRACKS,
        )
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)

            tracks = []
            entries = info.get("entries")
            if entries:
                for entry in entries:
                    if not entry:
                        continue
                    video_url = entry.get("url") or (
                        "https://www.youtube.com/watch?v=%s" % entry.get("id")
                    )
                    tracks.append(
                        {
                            "url": video_url,
                            "title": entry.get("title") or "Unknown",
                        }
                    )
            else:
                tracks.append(
                    {
                        "url": info.get("webpage_url") or url,
                        "title": info.get("title") or "Unknown",
                    }
                )

            if not tracks:
                self._status("No playable videos found.")
                self._ui_idle()
                return

            self.playlist = tracks
            self.current_index = 0
            Clock.schedule_once(
                lambda dt: self.root_widget.set_playlist(tracks)
            )
            self._status("Loaded %d track(s)." % len(tracks))
            Clock.schedule_once(lambda dt: self.play_current_track())
        except Exception as exc:
            self._status("Error: %s" % exc)
            self._ui_idle()

    # ---- playback ----
    def play_index(self, index):
        self.current_index = index
        self.play_current_track()

    def play_current_track(self):
        if not self.playlist or self.current_index >= len(self.playlist):
            self.stop_play()
            return
        track = self.playlist[self.current_index]
        Clock.schedule_once(lambda dt: self._ui_loading(), 0)
        self._start_background_service()
        self._title("Loading: %s..." % track["title"])
        self._status("Resolving stream URL...")
        threading.Thread(
            target=self._resolve_and_play, args=(track,), daemon=True
        ).start()

    def _resolve_and_play(self, track):
        options = self._ydl_opts(format="bestaudio/best", noplaylist=True)
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(track["url"], download=False)

            stream_url = info.get("url")
            if not stream_url:
                formats = info.get("formats") or []
                if formats:
                    stream_url = formats[-1].get("url")
            if not stream_url:
                raise RuntimeError("Could not extract stream URL.")

            self.player.play(
                stream_url,
                info.get("title") or track["title"],
                info.get("uploader")
                or info.get("artist")
                or info.get("channel")
                or "",
                info.get("thumbnail") or "",
            )
            self._paused = False
            self._finished_guard = False
            self.is_playing = True
            self._status("Playing...")
            self._title(track["title"])
            self._notify_service(
                "org.ytaudioplayer.action.PLAY",
                title=info.get("title") or track["title"],
                artist=info.get("uploader")
                or info.get("artist")
                or info.get("channel")
                or "",
                art_url=info.get("thumbnail") or "",
                duration=int(self.player.duration()),
            )
            Clock.schedule_once(lambda dt: self._ui_playing(False))
        except Exception as exc:
            self._status("Error: %s. Skipping..." % exc)
            Clock.schedule_once(lambda dt: self.play_next(), 2)

    def toggle_pause(self):
        if not self.is_playing:
            return
        if self._paused:
            self.player.resume()
            self._paused = False
            self._status("Playing...")
            self._ui_playing(False)
            self._notify_service("org.ytaudioplayer.action.RESUME")
        else:
            self.player.pause()
            self._paused = True
            self._status("Paused.")
            self._ui_playing(True)
            self._notify_service("org.ytaudioplayer.action.PAUSE")

    def stop_play(self):
        self.is_playing = False
        self._paused = False
        self._finished_guard = False
        try:
            self.player.stop()
        except Exception:
            pass
        self._notify_service("org.ytaudioplayer.action.STOP")
        self._stop_background_service()
        self._status("Stopped.")
        self._title("No track selected")
        Clock.schedule_once(self._reset_ui, 0)

    def _reset_ui(self, dt):
        self.root_widget.time_label.text = "00:00 / 00:00"
        self.root_widget.slider.value = 0
        self._ui_idle()

    def play_next(self):
        if self.current_index < len(self.playlist) - 1:
            self.current_index += 1
            self.play_current_track()
        else:
            self._status("End of playlist reached.")
            self.stop_play()

    def play_prev(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.play_current_track()

    def seek_to(self, percent):
        total = self.player.duration()
        if total > 0:
            position = int(float(percent) / 100.0 * total)
            self.player.seek(position)
            self._notify_service(
                "org.ytaudioplayer.action.POSITION",
                position=position,
                duration=int(total),
            )

    # ---- UI state ----
    def _ui_loading(self):
        r = self.root_widget
        r.play_btn.disabled = True
        r.pause_btn.disabled = True
        r.stop_btn.disabled = True
        r.prev_btn.disabled = True
        r.next_btn.disabled = True
        r.pause_btn.text = "II Pause"

    def _ui_idle(self):
        r = self.root_widget
        r.play_btn.disabled = False
        r.pause_btn.disabled = True
        r.stop_btn.disabled = True
        r.prev_btn.disabled = True
        r.next_btn.disabled = True
        r.pause_btn.text = "II Pause"

    def _ui_playing(self, paused):
        r = self.root_widget
        r.play_btn.disabled = True
        r.pause_btn.disabled = False
        r.stop_btn.disabled = False
        r.prev_btn.disabled = False
        r.next_btn.disabled = False
        r.pause_btn.text = "> Resume" if paused else "II Pause"

    # ---- clock ----
    def _tick(self, dt):
        if not self.is_playing:
            return
        r = self.root_widget
        current = self.player.position()
        total = self.player.duration()
        if total > 0:
            r.time_label.text = "%s / %s" % (_fmt_time(current), _fmt_time(total))
            if not self.is_seeking:
                r.slider.value = (current / float(total)) * 100.0
        if platform == "android" and total > 0:
            now = Clock.get_time()
            if now - self._last_service_sync >= 1.0:
                self._last_service_sync = now
                self._notify_service(
                    "org.ytaudioplayer.action.POSITION",
                    position=int(current),
                    duration=int(total),
                )
        if (
            platform != "android"
            and total > 0
            and current >= total - 400
            and not self._paused
            and not self.player.is_playing()
        ):
            self._on_track_finished()

    def _on_track_finished(self):
        if not self.is_playing or self._paused or self._finished_guard:
            return
        self._finished_guard = True
        try:
            self.play_next()
        finally:
            threading.Timer(1.5, self._clear_finished_guard).start()

    def _clear_finished_guard(self):
        self._finished_guard = False

    # ---- android lifecycle ----
    def on_pause(self):
        # Keep the audio playing while the app is in the background / screen off.
        # The foreground service keeps the process alive.
        return True

    def on_stop(self):
        try:
            self.player.stop()
        except Exception:
            pass
        self._stop_background_service()


if __name__ == "__main__":
    YTPlayerApp().run()
