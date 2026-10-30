"""python-for-android hooks for YT Audio Player.

Buildozer passes ``p4a.hook`` to every p4a command.

* ``before_apk_build`` runs just before p4a generates AndroidManifest.xml, so
  the native foreground service can be declared through p4a's supported
  ``--native-service`` flag instead of injecting raw XML (which breaks the
  ``<application>`` opening tag).
* ``after_apk_build`` runs right after the manifest has been generated, which
  is where the home-screen widget receiver has to be added (p4a has no flag
  for receivers).
"""

import os

NATIVE_SERVICE = "org.ytaudioplayer.BackgroundService"

WIDGET_RECEIVER = """
        <receiver
            android:name="org.ytaudioplayer.MediaWidgetProvider"
            android:exported="false">
            <intent-filter>
                <action android:name="android.appwidget.action.APPWIDGET_UPDATE" />
            </intent-filter>
            <meta-data
                android:name="android.appwidget.provider"
                android:resource="@xml/media_widget_info" />
        </receiver>
"""


def before_apk_build(toolchain):
    """Declare BackgroundService inside <application> in the manifest."""
    unknown = toolchain.args.unknown_args
    if "--native-service" not in unknown:
        unknown += ["--native-service", NATIVE_SERVICE]


def after_apk_build(toolchain):
    """Add the home-screen widget receiver to the generated manifest."""
    try:
        dist_dir = toolchain._dist.dist_dir
    except Exception:
        return

    manifest = os.path.join(dist_dir, "src", "main", "AndroidManifest.xml")
    if not os.path.exists(manifest):
        return

    with open(manifest, "r", encoding="utf-8") as handle:
        text = handle.read()

    if "MediaWidgetProvider" in text:
        return

    text = text.replace("</application>", WIDGET_RECEIVER + "    </application>")
    with open(manifest, "w", encoding="utf-8") as handle:
        handle.write(text)
