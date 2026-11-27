import tkinter as tk
from tkinter import ttk, messagebox
import threading
import yt_dlp
import vlc
import os
import sys
import ctypes

class YouTubePlayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YT Audio Player")
        self.root.geometry("360x480") 
        self.root.configure(bg="#121212")
        
        # Custom black/orange title bar
        self.root.overrideredirect(True) 
        
        # Apply taskbar and icon fixes after window is drawn
        self.root.after(10, self.set_appwindow)
        self.root.after(20, self.load_icon)
        
        # VLC Setup
        self.vlc_instance = vlc.Instance()
        self.player = self.vlc_instance.media_player_new()
        
        # Playlist Management
        self.playlist = []
        self.current_index = 0
        self.is_playing = False
        self.max_playlist_items = 1000 
        
        self.events = self.player.event_manager()
        self.events.event_attach(vlc.EventType.MediaPlayerEndReached, self.on_end_reached)
        
        # Variables for Custom Scroll Slider
        self.is_scrolling = False
        self.playlist_scroll_var = tk.DoubleVar(value=0)
        
        self._setup_styles()
        self._build_ui()

    # --- Window & Taskbar Fixes ---
    def set_appwindow(self):
        # Forces the borderless window to show up in the Windows taskbar
        try:
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = style & ~WS_EX_TOOLWINDOW
            style = style | WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            
            # Trick Windows into refreshing the taskbar
            self.root.withdraw()
            self.root.after(10, self.root.deiconify)
        except Exception:
            pass

    def load_icon(self):
        # Handles icon loading for both raw .pyw and PyInstaller .exe
        try:
            if getattr(sys, 'frozen', False):
                # Path when running as compiled .exe
                base_path = sys._MEIPASS
            else:
                # Path when running as .pyw script
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            icon_path = os.path.join(base_path, "youtube_audio_icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

    # --- WORKING MINIMIZE LOGIC ---
    def minimize_window(self, event=None):
        # Tell Windows to minimize the window to the taskbar
        self.root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        ctypes.windll.user32.ShowWindow(hwnd, 6) # 6 = Minimize

        # Bind a one-time event to restore the custom borderless look when un-minimized
        self.root.bind("<Map>", self.on_restore)

    def on_restore(self, event):
        # This triggers when the window is brought back from the taskbar
        self.root.unbind("<Map>")
        self.root.overrideredirect(True)
        self.root.after(10, self.set_appwindow)

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TScale", background="#121212", troughcolor="#333333", bordercolor="#333333", lightcolor="#FF5722", darkcolor="#FF5722")

    def _build_ui(self):
        BG = "#121212"
        FG = "#FFFFFF"
        ACCENT = "#FF5722" # Orange
        
        # ================= CUSTOM TITLE BAR =================
        title_bar = tk.Frame(self.root, bg="#000000", height=30)
        title_bar.pack(fill=tk.X, side=tk.TOP)
        title_bar.pack_propagate(False)
        
        title_bar.bind("<ButtonPress-1>", self.start_move)
        title_bar.bind("<B1-Motion>", self.do_move)
        
        tk.Label(title_bar, text="▶ YT Audio Player", bg="#000000", fg=ACCENT, font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=10)
        
        close_btn = tk.Label(title_bar, text="✕", bg="#000000", fg="#FFFFFF", font=("Arial", 11), cursor="hand2")
        close_btn.pack(side=tk.RIGHT, padx=10)
        close_btn.bind("<Button-1>", lambda e: self.root.destroy())

        min_btn = tk.Label(title_bar, text="—", bg="#000000", fg="#FFFFFF", font=("Arial", 11, "bold"), cursor="hand2")
        min_btn.pack(side=tk.RIGHT, padx=5)
        min_btn.bind("<Button-1>", self.minimize_window)

        # ================= MAIN UI =================
        tk.Label(self.root, text="Link", bg=BG, fg=FG, font=("Arial", 9)).place(x=10, y=45)
        self.link_var = tk.StringVar()
        tk.Entry(self.root, textvariable=self.link_var, bg="#1E1E1E", fg=FG, insertbackground=FG, borderwidth=0, font=("Arial", 9)).place(x=45, y=43, width=210, height=22)
        
        tk.Button(self.root, text="Paste", command=self.paste_link, bg="#333333", fg=FG, relief="flat", font=("Arial", 8), borderwidth=0).place(x=260, y=41, width=45, height=24)
        tk.Button(self.root, text="Clear", command=lambda: self.link_var.set(""), bg="#333333", fg=FG, relief="flat", font=("Arial", 8), borderwidth=0).place(x=310, y=41, width=40, height=24)

        tk.Label(self.root, text="🎵 Audio Only", bg=BG, fg=ACCENT, font=("Arial", 9, "bold")).place(x=10, y=80)
        
        tk.Label(self.root, text="Queue No.", bg=BG, fg=ACCENT, font=("Arial", 8)).place(x=220, y=78, width=85)
        self.queue_var = tk.StringVar(value="50")
        tk.Entry(self.root, textvariable=self.queue_var, bg="#1E1E1E", fg=FG, insertbackground=FG, borderwidth=0, font=("Arial", 9), justify="center").place(x=290, y=78, width=50, height=20)

        self.play_btn = tk.Button(self.root, text="▶ Play", command=self.start_play, bg=ACCENT, fg="white", relief="flat", activebackground="#E64A19", font=("Arial", 8), borderwidth=0)
        self.play_btn.place(x=10, y=110, width=50, height=25)
        
        self.pause_btn = tk.Button(self.root, text="⏸ Pause", command=self.toggle_pause, bg="#333333", fg="white", relief="flat", state="disabled", font=("Arial", 8), borderwidth=0)
        self.pause_btn.place(x=65, y=110, width=55, height=25)
        
        self.stop_btn = tk.Button(self.root, text="■ Stop", command=self.stop_play, bg="#333333", fg="white", relief="flat", state="disabled", font=("Arial", 8), borderwidth=0)
        self.stop_btn.place(x=125, y=110, width=55, height=25)
        
        self.prev_btn = tk.Button(self.root, text="⏮ Prev", command=self.play_prev, bg="#333333", fg="white", relief="flat", state="disabled", font=("Arial", 8), borderwidth=0)
        self.prev_btn.place(x=185, y=110, width=55, height=25)
        
        self.next_btn = tk.Button(self.root, text="⏭ Next", command=self.play_next, bg="#333333", fg="white", relief="flat", state="disabled", font=("Arial", 8), borderwidth=0)
        self.next_btn.place(x=245, y=110, width=55, height=25)

        self.time_var = tk.StringVar(value="00:00 / 00:00")
        tk.Label(self.root, textvariable=self.time_var, fg=FG, bg=BG, font=("Arial", 9)).place(x=10, y=155)

        self.time_slider = ttk.Scale(self.root, from_=0, to=100, orient="horizontal", command=self.on_seek, style="TScale")
        self.time_slider.place(x=90, y=155, width=260)
        self.is_seeking = False 

        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(self.root, textvariable=self.status_var, fg=ACCENT, bg=BG, wraplength=340, justify="left", font=("Arial", 9)).place(x=10, y=185)

        self.title_var = tk.StringVar(value="No track selected")
        tk.Label(self.root, textvariable=self.title_var, fg=FG, bg=BG, font=("Arial", 9, "bold"), wraplength=340, justify="left").place(x=10, y=205)

        # ================= PLAYLIST SECTION =================
        tk.Label(self.root, text="Playlist Queue:", bg=BG, fg=FG, font=("Arial", 9)).place(x=10, y=235)
        
        self.playlist_box = tk.Listbox(self.root, bg="#1E1E1E", fg=FG, selectbackground=ACCENT, selectforeground="black", borderwidth=0, highlightthickness=0, font=("Arial", 9))
        self.playlist_box.place(x=10, y=260, width=310, height=205)
        self.playlist_box.bind("<Double-Button-1>", self.on_playlist_double_click)
        
        # --- CUSTOM SCROLL SLIDER REPLACING SCROLLBAR ---
        self.scroll_slider = ttk.Scale(self.root, from_=0, to=100, orient="vertical", command=self.on_playlist_scroll, style="TScale")
        self.scroll_slider.place(x=325, y=260, width=15, height=205)
        
        self.scroll_slider.bind("<ButtonPress-1>", lambda e: setattr(self, 'is_scrolling', True))
        self.scroll_slider.bind("<ButtonRelease-1>", lambda e: setattr(self, 'is_scrolling', False))
        
        self.playlist_box.bind("<MouseWheel>", self._on_mousewheel)
        self.playlist_box.bind("<Button-4>", self._on_mousewheel)
        self.playlist_box.bind("<Button-5>", self._on_mousewheel)
        
        self.playlist_box.config(yscrollcommand=self._on_listbox_scroll)

    # --- Custom Scroll Slider Logic ---
    def _on_listbox_scroll(self, first, last):
        if not self.is_scrolling:
            try:
                first = float(first)
                pos = first * 100
                self.playlist_scroll_var.set(pos)
                self.scroll_slider.set(pos)
            except ValueError:
                pass

    def on_playlist_scroll(self, value):
        if self.is_scrolling:
            self.playlist_box.yview_moveto(float(value) / 100.0)

    def _on_mousewheel(self, event):
        delta = -1 if event.delta > 0 or event.num == 4 else 1
        self.playlist_box.yview_scroll(delta, "units")
        self._on_listbox_scroll(*self.playlist_box.yview())
        return "break"

    # ---------------- Helpers ----------------
    def _get_cookies_file(self):
        return os.path.join(os.path.dirname(__file__), "youtube_cookies.txt")

    def paste_link(self):
        try:
            self.link_var.set(self.root.clipboard_get().strip())
            self.status_var.set("Link pasted.")
        except tk.TclError:
            self.status_var.set("Clipboard is empty.")

    def set_status(self, text):
        self.root.after(0, lambda: self.status_var.set(text))

    def format_time(self, ms):
        if ms < 0: return "00:00"
        seconds = int(ms / 1000)
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def update_buttons(self, play_state, nav_state):
        self.root.after(0, lambda: self.play_btn.config(state=play_state))
        self.root.after(0, lambda: self.stop_btn.config(state=nav_state))
        self.root.after(0, lambda: self.prev_btn.config(state=nav_state))
        self.root.after(0, lambda: self.next_btn.config(state=nav_state))
        if play_state == "disabled":
            self.root.after(0, lambda: self.pause_btn.config(state="disabled", text="⏸ Pause"))

    def on_playlist_double_click(self, event):
        selection = self.playlist_box.curselection()
        if selection and self.playlist:
            self.current_index = selection[0]
            self.play_current_track()

    # ---------------- Playback Logic ----------------
    def start_play(self):
        url = self.link_var.get().strip()
        if not url:
            messagebox.showwarning("Missing link", "Please paste a YouTube link first.")
            return
            
        # Clean URL to remove tracking params that break yt-dlp
        if '?si=' in url:
            url = url.split('?si=')[0]
            
        try:
            val = int(self.queue_var.get().strip())
            if val > 0:
                self.max_playlist_items = val
        except Exception:
            pass

        self.update_buttons("disabled", "disabled")
        self.set_status("Fetching playlist...")
        self.playlist_box.delete(0, tk.END)
        self.title_var.set("Loading...")
        
        threading.Thread(target=self._extract_playlist, args=(url,), daemon=True).start()

    def _extract_playlist(self, url):
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": False, 
            "extract_flat": "in_playlist",
            "playlistend": self.max_playlist_items,
            "cookies": self._get_cookies_file(),
        }

        if not os.path.exists(self._get_cookies_file()):
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "export_cookies", os.path.join(os.path.dirname(__file__), "export_cookies.py")
                )
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, 'export_cookies'):
                        mod.export_cookies()
            except Exception:
                pass

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                self.playlist = []
                
                if info is None:
                    self.set_status("Error: No info returned from yt-dlp.")
                    self.update_buttons("normal", "disabled")
                    return

                # Handle Playlist vs Single Video & NoneType errors
                if 'entries' in info and info['entries']:
                    for entry in info['entries']:
                        if entry:
                            v_url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
                            self.playlist.append({'url': v_url, 'title': entry.get('title', 'Unknown')})
                else:
                    # Safely handle single video links
                    video_url = info.get('url') or info.get('webpage_url') or url
                    video_title = info.get('title') or "Unknown Title"
                    self.playlist.append({'url': video_url, 'title': video_title})

                if not self.playlist:
                    self.set_status("No playable videos found.")
                    self.update_buttons("normal", "disabled")
                    return

                for idx, track in enumerate(self.playlist):
                    self.root.after(0, lambda i=idx, t=track['title']: self.playlist_box.insert(tk.END, f"{i+1}. {t}"))

                self.current_index = 0
                self.set_status(f"Loaded {len(self.playlist)} tracks.")
                self.root.after(0, self.play_current_track)

        except Exception as e:
            self.set_status(f"Error: {e}")
            self.update_buttons("normal", "disabled")

    def play_current_track(self):
        if not self.playlist or self.current_index >= len(self.playlist):
            self.stop_play()
            return

        self.playlist_box.selection_clear(0, tk.END)
        self.playlist_box.selection_set(self.current_index)
        self.playlist_box.see(self.current_index)
        self._on_listbox_scroll(*self.playlist_box.yview())

        track = self.playlist[self.current_index]
        self.title_var.set(f"Loading: {track['title']}...")
        self.set_status("Resolving stream URL...")
        
        threading.Thread(target=self._resolve_and_play, args=(track['url'],), daemon=True).start()

    def _resolve_and_play(self, url):
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "cookies": self._get_cookies_file(),
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Safely extract stream URL
                stream_url = info.get("url")
                if not stream_url and info.get("formats"):
                    stream_url = info.get("formats")[-1].get("url")
                    
                if not stream_url:
                    raise RuntimeError("Could not extract stream URL.")

                media = self.vlc_instance.media_new(stream_url)
                self.player.set_media(media)

                self.player.play()
                self.set_status("Playing...")
                self.title_var.set(self.playlist[self.current_index]['title'])
                self.is_playing = True
                
                self.update_buttons("normal", "normal")
                self.root.after(0, lambda: self.pause_btn.config(state="normal", text="⏸ Pause"))
                self.root.after(0, self.update_timeline)

        except Exception as e:
            self.set_status(f"Error: {e}. Skipping...")
            self.root.after(2000, self.play_next)

    def toggle_pause(self):
        if self.is_playing:
            self.player.pause()
            state = self.player.get_state()
            if state == vlc.State.Paused:
                self.pause_btn.config(text="▶ Resume")
                self.set_status("Paused.")
            else:
                self.pause_btn.config(text="⏸ Pause")
                self.set_status("Playing...")

    def stop_play(self):
        self.is_playing = False
        self.player.stop()
        self.set_status("Stopped.")
        self.title_var.set("No track selected")
        self.time_var.set("00:00 / 00:00")
        self.time_slider.set(0)
        self.update_buttons("normal", "disabled")
        self.pause_btn.config(text="⏸ Pause")

    def on_end_reached(self, event):
        if self.is_playing:
            self.root.after(100, self.play_next)

    def play_next(self):
        if self.current_index < len(self.playlist) - 1:
            self.current_index += 1
            self.play_current_track()
        else:
            self.set_status("End of playlist reached.")
            self.stop_play()

    def play_prev(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.play_current_track()

    def on_seek(self, value):
        if not self.is_seeking or not self.is_playing:
            return
        total = self.player.get_length()
        if total > 0:
            self.player.set_time(int((float(value) / 100) * total))

    def update_timeline(self):
        if not self.is_playing: return
            
        current = self.player.get_time()
        total = self.player.get_length()

        if total > 0:
            self.time_var.set(f"{self.format_time(current)} / {self.format_time(total)}")
            if not self.is_seeking:
                self.time_slider.set((current / total) * 100)

        if self.is_playing:
            self.root.after(500, self.update_timeline)

if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubePlayerApp(root)
    
    app.time_slider.bind("<ButtonPress-1>", lambda e: setattr(app, 'is_seeking', True))
    app.time_slider.bind("<ButtonRelease-1>", lambda e: setattr(app, 'is_seeking', False))
    
    root.mainloop()