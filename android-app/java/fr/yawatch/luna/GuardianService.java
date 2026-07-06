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
 * Phase 1 — Service Guardian foreground minimal.
 *
 * Responsabilite : afficher une notification permanente honnete lorsque
 * Guardian est demarre. Le service ne fait AUCUNE ecoute vocale, AUCUN
 * appel reseau et ne declenche AUCUN SOS en autonomie.
 *
 * Architecture : GuardianService est un capteur/reveilleur futur ; le chef
 * d'orchestre reste guardian.html (dans la WebView de MainActivity).
 */
public class GuardianService extends Service {

    private static final String CHANNEL_ID = "guardian_service";
    private static final int NOTIFICATION_ID = 1;

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String title = intent != null ? intent.getStringExtra("title") : null;
        String body = intent != null ? intent.getStringExtra("body") : null;

        if (title == null || title.isEmpty()) {
            title = "Luna Guardian";
        }
        if (body == null || body.isEmpty()) {
            body = "Protection active lorsque Guardian est ouvert.";
        }

        startForeground(NOTIFICATION_ID, buildNotification(title, body));

        // Phase 1 : START_NOT_STICKY. Si le service est tue par le systeme,
        // il ne redemarre pas tout seul. L'utilisateur doit rouvrir l'app
        // et appuyer sur "Demarrer". C'est un choix deliberement honnete
        // tant que le service n'assure pas encore une protection hors ecran
        // (pas d'ecoute vocale native en Phase 1).
        return START_NOT_STICKY;
    }

    @Override
    public void onDestroy() {
        stopForeground(true);
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "Guardian permanent",
                NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Notification persistante de protection Guardian");
            channel.setShowBadge(false);
            NotificationManager mgr = getSystemService(NotificationManager.class);
            if (mgr != null) {
                mgr.createNotificationChannel(channel);
            }
        }
    }

    private Notification buildNotification(String title, String body) {
        Intent intent = new Intent(this, MainActivity.class);
        intent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent pi = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= 26) {
            builder = new Notification.Builder(this, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(this);
        }

        builder.setSmallIcon(R.drawable.ic_notif_luna)
            .setContentTitle(title)
            .setContentText(body)
            .setOngoing(true)
            .setContentIntent(pi);

        if (body.length() > 40) {
            builder.setStyle(new Notification.BigTextStyle().bigText(body));
        }

        return builder.build();
    }
}
