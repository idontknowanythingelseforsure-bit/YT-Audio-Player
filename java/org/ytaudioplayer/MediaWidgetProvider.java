package org.ytaudioplayer;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.widget.RemoteViews;

import org.ytaudioplayer.ytaudioplayer.R;

/**
 * Home-screen media widget.
 *
 * The widget is a thin view over the static state published by
 * {@link BackgroundService}. Button taps are forwarded to the service, which
 * then broadcasts NEXT / PREV back to Python so the playlist index stays in
 * sync.
 */
public class MediaWidgetProvider extends AppWidgetProvider {
    public static final String ACTION_WIDGET_TOGGLE =
            "org.ytaudioplayer.action.WIDGET_TOGGLE";
    public static final String ACTION_WIDGET_NEXT =
            "org.ytaudioplayer.action.WIDGET_NEXT";
    public static final String ACTION_WIDGET_PREV =
            "org.ytaudioplayer.action.WIDGET_PREV";

    @Override
    public void onUpdate(Context context, AppWidgetManager manager, int[] appWidgetIds) {
        for (int appWidgetId : appWidgetIds) {
            manager.updateAppWidget(appWidgetId, buildViews(context));
        }
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        super.onReceive(context, intent);
        String action = intent.getAction();
        if (ACTION_WIDGET_TOGGLE.equals(action)) {
            sendServiceAction(context, BackgroundService.ACTION_TOGGLE);
        } else if (ACTION_WIDGET_NEXT.equals(action)) {
            sendServiceAction(context, BackgroundService.ACTION_NEXT);
        } else if (ACTION_WIDGET_PREV.equals(action)) {
            sendServiceAction(context, BackgroundService.ACTION_PREV);
        }
    }

    private static void sendServiceAction(Context context, String action) {
        Intent intent = new Intent(context, BackgroundService.class);
        intent.setAction(action);
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent);
            } else {
                context.startService(intent);
            }
        } catch (Exception ignored) {
            try {
                context.startService(intent);
            } catch (Exception ignoredToo) {
            }
        }
    }

    /** Full refresh, called by the service whenever metadata changes. */
    public static void updateAll(Context context) {
        AppWidgetManager manager = AppWidgetManager.getInstance(context);
        ComponentName provider = new ComponentName(context, MediaWidgetProvider.class);
        int[] ids = manager.getAppWidgetIds(provider);
        for (int appWidgetId : ids) {
            manager.updateAppWidget(appWidgetId, buildViews(context));
        }
    }

    /** Cheap refresh for the progress bar, called once a second while playing. */
    public static void updateProgress(Context context) {
        AppWidgetManager manager = AppWidgetManager.getInstance(context);
        ComponentName provider = new ComponentName(context, MediaWidgetProvider.class);
        int[] ids = manager.getAppWidgetIds(provider);
        if (ids.length == 0) {
            return;
        }
        RemoteViews views = new RemoteViews(
                context.getPackageName(), R.layout.media_widget);
        int max = Math.max(BackgroundService.durationMs, 1);
        int progress = Math.max(0, Math.min(BackgroundService.positionMs, max));
        views.setProgressBar(R.id.widget_progress, max, progress, false);
        for (int appWidgetId : ids) {
            manager.partiallyUpdateAppWidget(appWidgetId, views);
        }
    }

    private static RemoteViews buildViews(Context context) {
        RemoteViews views = new RemoteViews(
                context.getPackageName(), R.layout.media_widget);

        String title = BackgroundService.currentTitle;
        String artist = BackgroundService.currentArtist;
        views.setTextViewText(
                R.id.widget_title,
                title == null || title.isEmpty() ? "YT Audio Player" : title);
        views.setTextViewText(
                R.id.widget_artist,
                artist == null ? "" : artist);
        views.setImageViewResource(
                R.id.widget_play,
                BackgroundService.isPlaying
                        ? R.drawable.widget_pause
                        : R.drawable.widget_play);

        if (BackgroundService.artworkBitmap != null) {
            views.setImageViewBitmap(
                    R.id.widget_art, BackgroundService.artworkBitmap);
        } else {
            views.setImageViewResource(
                    R.id.widget_art, R.drawable.widget_placeholder);
        }

        int max = Math.max(BackgroundService.durationMs, 1);
        int progress = Math.max(0, Math.min(BackgroundService.positionMs, max));
        views.setProgressBar(R.id.widget_progress, max, progress, false);

        views.setOnClickPendingIntent(
                R.id.widget_prev,
                broadcast(context, ACTION_WIDGET_PREV, 11));
        views.setOnClickPendingIntent(
                R.id.widget_play,
                broadcast(context, ACTION_WIDGET_TOGGLE, 12));
        views.setOnClickPendingIntent(
                R.id.widget_next,
                broadcast(context, ACTION_WIDGET_NEXT, 13));
        return views;
    }

    private static PendingIntent broadcast(Context context, String action, int code) {
        Intent intent = new Intent(context, MediaWidgetProvider.class);
        intent.setAction(action);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            flags |= PendingIntent.FLAG_IMMUTABLE;
        }
        return PendingIntent.getBroadcast(context, code, intent, flags);
    }
}
