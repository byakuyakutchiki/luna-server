package fr.yawatch.luna;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;

/**
 * Guardian Foreground Service — présence protectrice permanente.
 *
 * Maintient une notification persistante avec l'état Guardian (protégé / vérif / urgence).
 * Garde le processus Luna vivant même quand l'app est en arrière-plan.
 * Un bouton "🆘 Urgence SOS" dans la notification envoie un broadcast à SosReceiver.
 */
public class GuardianService extends Service {

    static final String ACTION_START  = "fr.yawatch.luna.GUARDIAN_START";
    static final String ACTION_STOP   = "fr.yawatch.luna.GUARDIAN_STOP";
    static final String ACTION_UPDATE = "fr.yawatch.luna.GUARDIAN_UPDATE";

    private static final int    NOTIF_ID         = 2001;
    private static final String CHANNEL_NORMAL   = "luna_guardian";
    private static final String CHANNEL_ALERT    = "luna_guardian_alert";

    private static GuardianService sInstance;

    private String  mStatus    = "Protégé";
    private String  mContacts  = "";
    private boolean mEmergency = false;

    /** Vrai si le service tourne actuellement. */
    public static boolean isRunning() { return sInstance != null; }

    /**
     * Met à jour la notification depuis le thread principal de MainActivity.
     * Appelé par LunaBridge.updateGuardianNotification().
     */
    public static void updateStatus(String status, String contacts, boolean emergency) {
        if (sInstance == null) return;
        sInstance.mStatus    = (status   != null) ? status   : "Protégé";
        sInstance.mContacts  = (contacts != null) ? contacts : "";
        sInstance.mEmergency = emergency;
        sInstance.pushNotification();
    }

    @Override
    public void onCreate() {
        super.onCreate();
        sInstance = this;
        createChannels();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null) {
            String action = intent.getAction();
            if (ACTION_STOP.equals(action)) {
                if (Build.VERSION.SDK_INT >= 24) {
                    stopForeground(STOP_FOREGROUND_REMOVE);
                } else {
                    stopForeground(true);
                }
                stopSelf();
                return START_NOT_STICKY;
            }
            if (ACTION_START.equals(action) || ACTION_UPDATE.equals(action)) {
                String s = intent.getStringExtra("status");
                String c = intent.getStringExtra("contacts");
                if (s != null) mStatus   = s;
                if (c != null) mContacts = c;
                mEmergency = intent.getBooleanExtra("emergency", false);
            }
        }
        pushNotification();
        return START_STICKY;
    }

    private void pushNotification() {
        Notification notif = buildNotification();
        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(NOTIF_ID, notif,
                android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC);
        } else {
            startForeground(NOTIF_ID, notif);
        }
        // Forcer la mise à jour si déjà en foreground
        NotificationManager mgr = getSystemService(NotificationManager.class);
        if (mgr != null) mgr.notify(NOTIF_ID, notif);
    }

    private Notification buildNotification() {
        // Intent : tap sur la notification → ouvre MainActivity
        Intent openIntent = new Intent(this, MainActivity.class);
        openIntent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent openPi = PendingIntent.getActivity(this, 0, openIntent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        // Intent : bouton SOS → SosReceiver → MainActivity
        Intent sosIntent = new Intent(this, SosReceiver.class);
        sosIntent.setAction("fr.yawatch.luna.SOS_ACTION");
        PendingIntent sosPi = PendingIntent.getBroadcast(this, 1, sosIntent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        String channelId = mEmergency ? CHANNEL_ALERT : CHANNEL_NORMAL;
        String title     = mEmergency ? "🆘 ALERTE GUARDIAN"  : "🛡 Luna Guardian";
        String body      = mEmergency
            ? "SOS activé · Contacts alertés"
            : (mStatus + (mContacts.isEmpty() ? "" : " · " + mContacts));

        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= 26) {
            builder = new Notification.Builder(this, channelId);
        } else {
            builder = new Notification.Builder(this);
            builder.setPriority(mEmergency ? Notification.PRIORITY_HIGH : Notification.PRIORITY_LOW);
        }

        builder
            .setSmallIcon(R.drawable.ic_guardian_shield)
            .setContentTitle(title)
            .setContentText(body)
            .setContentIntent(openPi)
            .setOngoing(true)
            .setAutoCancel(false)
            .setCategory(Notification.CATEGORY_SERVICE)
            .addAction(0, "🆘 Urgence SOS", sosPi);

        if (Build.VERSION.SDK_INT >= 31) {
            builder.setForegroundServiceBehavior(Notification.FOREGROUND_SERVICE_IMMEDIATE);
        }

        return builder.build();
    }

    private void createChannels() {
        if (Build.VERSION.SDK_INT < 26) return;
        NotificationManager mgr = getSystemService(NotificationManager.class);
        if (mgr == null) return;

        // Canal normal : silencieux, permanent, discret
        NotificationChannel normal = new NotificationChannel(
            CHANNEL_NORMAL,
            "Guardian — Présence protectrice",
            NotificationManager.IMPORTANCE_LOW
        );
        normal.setDescription("Indique que Guardian surveille activement");
        normal.setShowBadge(false);
        normal.setSound(null, null);
        mgr.createNotificationChannel(normal);

        // Canal urgence : haute priorité, son + vibration
        NotificationChannel alert = new NotificationChannel(
            CHANNEL_ALERT,
            "Guardian — Alerte urgence",
            NotificationManager.IMPORTANCE_HIGH
        );
        alert.setDescription("Alerte SOS Guardian — urgence active");
        alert.setShowBadge(true);
        alert.enableVibration(true);
        mgr.createNotificationChannel(alert);
    }

    @Override
    public IBinder onBind(Intent intent) { return null; }

    @Override
    public void onDestroy() {
        super.onDestroy();
        sInstance = null;
    }
}
