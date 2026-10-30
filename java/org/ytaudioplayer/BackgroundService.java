package org.ytaudioplayer;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.media.MediaMetadata;
import android.media.session.MediaSession;
import android.media.session.PlaybackState;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;

import java.io.InputStream;
import java.net.URL;

/**
 * Foreground presentation service.
 *
 * <p>This service deliberately does NOT own audio. Python owns the single
 * {@code android.media.MediaPlayer} instance. The service only:
 *
 * <ul>
 *   <li>keeps the process alive with a foreground notification + wake lock,</li>
 *   <li>publishes a {@link MediaSession} so the lock screen / Bluetooth / headset
 *       controls appear,</li>
 *   <li>renders the home-screen widget,</li>
 *   <li>relays every user command back to Python as a broadcast.</li>
 * </ul>
 *
 * <p>Python -> service (state updates): {@code ACTION_PLAY}, {@code ACTION_PAUSE},
 * {@code ACTION_RESUME}, {@code ACTION_POSITION}, {@code ACTION_STOP}.
 * <br>Service -> Python (commands): {@code ACTION_TOGGLE}, {@code ACTION_NEXT},
 * {@code ACTION_PREV}, {@code ACTION_SEEK}, {@code ACTION_STOP}.
 */
public class BackgroundService extends Service {
    // Python -> service: state updates.
    public static final String ACTION_PLAY = "org.ytaudioplayer.action.PLAY";
    public static final String ACTION_PAUSE = "org.ytaudioplayer.action.PAUSE";
    public static final String ACTION_RESUME = "org.ytaudioplayer.action.RESUME";
    public static final String ACTION_POSITION = "org.ytaudioplayer.action.POSITION";
    public static final String ACTION_STOP = "org.ytaudioplayer.action.STOP";

    // Service -> Python: commands.
    public static final String ACTION_TOGGLE = "org.ytaudioplayer.action.TOGGLE";
    public static final String ACTION_NEXT = "org.ytaudioplayer.action.NEXT";
    public static final String ACTION_PREV = "org.ytaudioplayer.action.PREV";
    public static final String ACTION_SEEK = "org.ytaudioplayer.action.SEEK";
    public static final String ACTION_TRACK_FINISHED =
            "org.ytaudioplayer.action.TRACK_FINISHED";

    public static final String EXTRA_TITLE = "title";
    public static final String EXTRA_ARTIST = "artist";
    public static final String EXTRA_ART_URL = "art_url";
    public static final String EXTRA_POSITION = "position";
    public static final String EXTRA_DURATION = "duration";

    // State published for the widget and for Python (pyjnius static fields).
    public static volatile boolean isRunning = false;
    public static volatile boolean isPlaying = false;
    public static volatile int positionMs = 0;
    public static volatile int durationMs = 0;
    public static volatile String currentTitle = "";
    public static volatile String currentArtist = "";
    public static volatile Bitmap artworkBitmap = null;

    private static final String CHANNEL_ID = "yt_audio_playback";
    private static final int NOTIFICATION_ID = 1001;

    private MediaSession session;
    private PowerManager.WakeLock wakeLock;

    @Override
    public void onCreate() {
        super.onCreate();
        isRunning = true;
        createNotificationChannel();

        PowerManager powerManager = (PowerManager) getSystemService(POWER_SERVICE);
        if (powerManager != null) {
            wakeLock = powerManager.newWakeLock(
                    PowerManager.PARTIAL_WAKE_LOCK, "YTAudioPlayer::Playback");
            wakeLock.setReferenceCounted(false);
        }

        session = new MediaSession(this, "YT Audio Player");
        session.setCallback(new MediaSession.Callback() {
            @Override
            public void onPlay() {
                broadcast(ACTION_RESUME);
            }

            @Override
            public void onPause() {
                broadcast(ACTION_PAUSE);
            }

            @Override
            public void onSkipToNext() {
                broadcast(ACTION_NEXT);
            }

            @Override
            public void onSkipToPrevious() {
                broadcast(ACTION_PREV);
            }

            @Override
            public void onSeekTo(long pos) {
                Intent intent = new Intent(ACTION_SEEK);
                intent.setPackage(getPackageName());
                intent.putExtra(EXTRA_POSITION, (int) pos);
                sendBroadcast(intent);
            }

            @Override
            public void onStop() {
                broadcast(ACTION_STOP);
            }
        });
        session.setActive(true);
        updatePlaybackState(PlaybackState.STATE_NONE);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        // Must happen before the 5 s startForegroundService() deadline.
        startForeground(NOTIFICATION_ID, buildNotification());

        if (wakeLock != null && !wakeLock.isHeld()) {
            wakeLock.acquire();
        }

        if (intent == null || intent.getAction() == null) {
            return START_NOT_STICKY;
        }

        String action = intent.getAction();
        switch (action) {
            case ACTION_PLAY:
                applyMetadata(intent);
                isPlaying = true;
                positionMs = 0;
                durationMs = Math.max(0, intent.getIntExtra(EXTRA_DURATION, 0));
                activateSession();
                updateNotification();
                updateWidget();
                break;

            case ACTION_PAUSE:
                isPlaying = false;
                activateSession();
                updatePlaybackState(PlaybackState.STATE_PAUSED);
                updateNotification();
                updateWidget();
                break;

            case ACTION_RESUME:
                isPlaying = true;
                activateSession();
                updatePlaybackState(PlaybackState.STATE_PLAYING);
                updateNotification();
                updateWidget();
                break;

            case ACTION_POSITION: {
                positionMs = Math.max(0, intent.getIntExtra(EXTRA_POSITION, positionMs));
                int duration = intent.getIntExtra(EXTRA_DURATION, durationMs);
                if (duration > 0) {
                    durationMs = duration;
                }
                if (session != null) {
                    updatePlaybackState(isPlaying
                            ? PlaybackState.STATE_PLAYING
                            : PlaybackState.STATE_PAUSED);
                }
                MediaWidgetProvider.updateProgress(this);
                break;
            }

            case ACTION_STOP:
                resetState();
                stopSelf();
                break;

            case ACTION_TOGGLE:
            case ACTION_NEXT:
            case ACTION_PREV:
                // Relay to Python; it owns the player and decides what happens.
                broadcast(action);
                break;

            case ACTION_SEEK: {
                Intent seek = new Intent(ACTION_SEEK);
                seek.setPackage(getPackageName());
                seek.putExtra(EXTRA_POSITION, intent.getIntExtra(EXTRA_POSITION, 0));
                sendBroadcast(seek);
                break;
            }

            default:
                break;
        }

        return START_NOT_STICKY;
    }

    @Override
    public void onDestroy() {
        isRunning = false;
        isPlaying = false;
        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
        }
        if (session != null) {
            session.setActive(false);
            session.release();
            session = null;
        }
        stopForeground(true);
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    // ---- state ----

    private void applyMetadata(Intent intent) {
        String title = intent.getStringExtra(EXTRA_TITLE);
        String artist = intent.getStringExtra(EXTRA_ARTIST);
        String artUrl = intent.getStringExtra(EXTRA_ART_URL);
        currentTitle = title == null ? "" : title;
        currentArtist = artist == null ? "" : artist;
        artworkBitmap = null;
        updateMetadata();
        loadArtwork(artUrl);
    }

    private void activateSession() {
        if (session != null) {
            session.setActive(true);
        }
        updatePlaybackState(isPlaying
                ? PlaybackState.STATE_PLAYING
                : PlaybackState.STATE_PAUSED);
    }

    private void resetState() {
        isPlaying = false;
        positionMs = 0;
        durationMs = 0;
        currentTitle = "";
        currentArtist = "";
        artworkBitmap = null;
        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
        }
        if (session != null) {
            session.setActive(false);
        }
        updateMetadata();
        updatePlaybackState(PlaybackState.STATE_STOPPED);
        updateNotification();
        updateWidget();
    }

    private void broadcast(String action) {
        Intent intent = new Intent(action);
        intent.setPackage(getPackageName());
        sendBroadcast(intent);
    }

    // ---- media session / notification ----

    private void updateMetadata() {
        if (session == null) {
            return;
        }
        MediaMetadata.Builder builder = new MediaMetadata.Builder()
                .putString(MediaMetadata.METADATA_KEY_TITLE, currentTitle)
                .putString(MediaMetadata.METADATA_KEY_ARTIST, currentArtist)
                .putString(MediaMetadata.METADATA_KEY_ALBUM, "YT Audio Player")
                .putLong(MediaMetadata.METADATA_KEY_DURATION, durationMs);
        if (artworkBitmap != null) {
            builder.putBitmap(MediaMetadata.METADATA_KEY_ALBUM_ART, artworkBitmap);
            builder.putBitmap(MediaMetadata.METADATA_KEY_ART, artworkBitmap);
        }
        session.setMetadata(builder.build());
    }

    private void updatePlaybackState(int state) {
        if (session == null) {
            return;
        }
        long actions = PlaybackState.ACTION_PLAY
                | PlaybackState.ACTION_PAUSE
                | PlaybackState.ACTION_PLAY_PAUSE
                | PlaybackState.ACTION_STOP
                | PlaybackState.ACTION_SKIP_TO_NEXT
                | PlaybackState.ACTION_SKIP_TO_PREVIOUS
                | PlaybackState.ACTION_SEEK_TO;
        float speed = state == PlaybackState.STATE_PLAYING ? 1.0f : 0.0f;
        session.setPlaybackState(new PlaybackState.Builder()
                .setActions(actions)
                .setState(state, positionMs, speed)
                .build());
    }

    private Notification buildNotification() {
        Intent openIntent = new Intent(this, org.kivy.android.PythonActivity.class);
        openIntent.setFlags(
                Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent contentIntent = PendingIntent.getActivity(
                this, 0, openIntent, pendingFlags());

        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder = new Notification.Builder(this, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(this);
        }

        builder.setContentTitle(
                        currentTitle.isEmpty() ? "YT Audio Player" : currentTitle)
                .setContentText(currentArtist.isEmpty()
                        ? "Playing audio in the background"
                        : currentArtist)
                .setSmallIcon(android.R.drawable.ic_media_play)
                .setContentIntent(contentIntent)
                .setVisibility(Notification.VISIBILITY_PUBLIC)
                .setOngoing(isPlaying)
                .setShowWhen(false);

        if (artworkBitmap != null) {
            builder.setLargeIcon(artworkBitmap);
        }

        int playIcon = isPlaying
                ? android.R.drawable.ic_media_pause
                : android.R.drawable.ic_media_play;
        String playTitle = isPlaying ? "Pause" : "Play";
        builder.addAction(android.R.drawable.ic_media_previous, "Previous",
                actionIntent(ACTION_PREV, 1));
        builder.addAction(playIcon, playTitle, actionIntent(ACTION_TOGGLE, 2));
        builder.addAction(android.R.drawable.ic_media_next, "Next",
                actionIntent(ACTION_NEXT, 3));

        if (session != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            builder.setStyle(new Notification.MediaStyle()
                    .setMediaSession(session.getSessionToken())
                    .setShowActionsInCompactView(0, 1, 2));
        }
        return builder.build();
    }

    private PendingIntent actionIntent(String action, int requestCode) {
        Intent intent = new Intent(this, BackgroundService.class);
        intent.setAction(action);
        return PendingIntent.getService(this, requestCode, intent, pendingFlags());
    }

    private int pendingFlags() {
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            flags |= PendingIntent.FLAG_IMMUTABLE;
        }
        return flags;
    }

    private void updateNotification() {
        NotificationManager manager =
                (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        if (manager != null) {
            manager.notify(NOTIFICATION_ID, buildNotification());
        }
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManager manager =
                    (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
            if (manager != null) {
                NotificationChannel channel = new NotificationChannel(
                        CHANNEL_ID,
                        "Audio playback",
                        NotificationManager.IMPORTANCE_LOW);
                channel.setDescription("Media controls for YT Audio Player");
                channel.setShowBadge(false);
                manager.createNotificationChannel(channel);
            }
        }
    }

    private void updateWidget() {
        MediaWidgetProvider.updateAll(this);
    }

    // ---- artwork ----

    private void loadArtwork(final String artUrl) {
        if (artUrl == null || artUrl.isEmpty()) {
            return;
        }
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    InputStream stream = new URL(artUrl).openStream();
                    Bitmap bitmap = BitmapFactory.decodeStream(stream);
                    stream.close();
                    if (bitmap != null) {
                        int width = bitmap.getWidth();
                        int height = bitmap.getHeight();
                        float scale = Math.min(256f / width, 256f / height);
                        int newWidth = Math.max(1, (int) (width * scale));
                        int newHeight = Math.max(1, (int) (height * scale));
                        artworkBitmap = Bitmap.createScaledBitmap(
                                bitmap, newWidth, newHeight, true);
                        updateMetadata();
                        updateNotification();
                        updateWidget();
                    }
                } catch (Exception ignored) {
                }
            }
        }).start();
    }
}
