package fr.yawatch.luna;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.provider.Settings;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.TextView;

import java.util.ArrayList;

/**
 * Guardian Foreground Service — protection système permanente.
 *
 * - Maintient une NOTIFICATION discrète (barre d'état) : l'indicateur « Guardian actif ».
 * - Optionnel : ÉCOUTE MOT-CLÉ en arrière-plan (SpeechRecognizer fr-FR on-device) qui
 *   fonctionne PAR-DESSUS les autres apps, app fermée. Mot-clé détecté → SOS YAWATCH.
 * - Optionnel : MINI-BULLE overlay système discrète et déplaçable (TYPE_APPLICATION_OVERLAY).
 *
 * L'écoute survit à la fermeture de l'app, mais (contrainte Android 12+) elle ne peut
 * être DÉMARRÉE que pendant que l'app est au premier plan.
 */
public class GuardianService extends Service {

    static final String ACTION_START  = "fr.yawatch.luna.GUARDIAN_START";
    static final String ACTION_STOP   = "fr.yawatch.luna.GUARDIAN_STOP";
    static final String ACTION_UPDATE = "fr.yawatch.luna.GUARDIAN_UPDATE";

    private static final int    NOTIF_ID         = 2001;
    private static final String CHANNEL_NORMAL   = "luna_guardian";
    private static final String CHANNEL_ALERT    = "luna_guardian_alert";

    // ── Écoute mot-clé (mêmes mots-clés que MainActivity « Guardian Voice Core ») ──
    private static final String[] EMERGENCY_KW = {
        "a l aide", "au secours", "aide moi", "aidez moi",
        "besoin d aide", "j ai besoin d aide",
        "je me sens mal",
        "je peux pas respirer", "je ne peux pas respirer",
        "j arrive pas a respirer", "je suis blesse",
        "je ne peux pas bouger", "je peux pas bouger",
        "appelle les secours", "appelle quelqu un",
        "appel urgent", "urgence", "emergency", "help",
        "a laide", "secours", "je suis tombe", "je suis tombee"
    };
    private static final long SR_COOLDOWN_MS = 15_000L;
    private static final int  SR_MAX_ERRORS  = 6;

    private static GuardianService sInstance;

    private String  mStatus    = "Protégé";
    private String  mContacts  = "";
    private boolean mEmergency = false;

    // Écoute
    private boolean          mListenEnabled  = false;
    private SpeechRecognizer mSR             = null;
    private boolean          mSRListening    = false;
    private int              mSRErrorCount   = 0;
    private final Handler    mHandler        = new Handler(Looper.getMainLooper());
    private Runnable         mRestartTask    = null;

    // Bulle overlay
    private boolean        mOverlayEnabled = false;
    private View           mOverlayView    = null;
    private WindowManager  mWM             = null;

    public static boolean isRunning() { return sInstance != null; }
    public static boolean isListening() { return sInstance != null && sInstance.mListenEnabled; }

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
                stopListening();
                hideOverlay();
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
                // Modes optionnels (par défaut : on conserve l'état courant si non précisé)
                mListenEnabled  = intent.getBooleanExtra("listen",  mListenEnabled);
                mOverlayEnabled = intent.getBooleanExtra("overlay", mOverlayEnabled);
            }
        }
        pushNotification();
        if (mListenEnabled) startListening(); else stopListening();
        if (mOverlayEnabled) showOverlay();   else hideOverlay();
        return START_STICKY;
    }

    // ───────────────────────── NOTIFICATION ─────────────────────────

    private void pushNotification() {
        Notification notif = buildNotification();
        if (Build.VERSION.SDK_INT >= 29) {
            int type = android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC;
            if (mListenEnabled && Build.VERSION.SDK_INT >= 30) {
                type |= android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE;
            }
            try {
                startForeground(NOTIF_ID, notif, type);
            } catch (Exception e) {
                startForeground(NOTIF_ID, notif);
            }
        } else {
            startForeground(NOTIF_ID, notif);
        }
        NotificationManager mgr = getSystemService(NotificationManager.class);
        if (mgr != null) mgr.notify(NOTIF_ID, notif);
    }

    private Notification buildNotification() {
        Intent openIntent = new Intent(this, MainActivity.class);
        openIntent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent openPi = PendingIntent.getActivity(this, 0, openIntent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        Intent sosIntent = new Intent(this, SosReceiver.class);
        sosIntent.setAction("fr.yawatch.luna.SOS_ACTION");
        PendingIntent sosPi = PendingIntent.getBroadcast(this, 1, sosIntent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        String channelId = mEmergency ? CHANNEL_ALERT : CHANNEL_NORMAL;
        String title     = mEmergency ? "🆘 ALERTE GUARDIAN"  : "🛡 Luna Guardian";
        String listenTag = mListenEnabled ? " · écoute active" : "";
        String body      = mEmergency
            ? "SOS activé · Contacts alertés"
            : (mStatus + listenTag + (mContacts.isEmpty() ? "" : " · " + mContacts));

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

        NotificationChannel normal = new NotificationChannel(
            CHANNEL_NORMAL, "Guardian — Présence protectrice", NotificationManager.IMPORTANCE_LOW);
        normal.setDescription("Indique que Guardian surveille activement");
        normal.setShowBadge(false);
        normal.setSound(null, null);
        mgr.createNotificationChannel(normal);

        NotificationChannel alert = new NotificationChannel(
            CHANNEL_ALERT, "Guardian — Alerte urgence", NotificationManager.IMPORTANCE_HIGH);
        alert.setDescription("Alerte SOS Guardian — urgence active");
        alert.setShowBadge(true);
        alert.enableVibration(true);
        mgr.createNotificationChannel(alert);
    }

    // ───────────────────────── ÉCOUTE MOT-CLÉ ─────────────────────────

    private String normalize(String text) {
        if (text == null) return "";
        String nfd = java.text.Normalizer.normalize(text, java.text.Normalizer.Form.NFD);
        return nfd
            .replaceAll("\\p{InCombiningDiacriticalMarks}+", "")
            .toLowerCase()
            .replaceAll("['‘’]", "'")
            .replaceAll("[^a-z' ]", " ")
            .replaceAll("\\s+", " ")
            .trim();
    }

    private boolean matchesKw(String text) {
        String n = normalize(text);
        for (String kw : EMERGENCY_KW) {
            if (n.contains(kw)) return true;
        }
        return false;
    }

    /** Démarre l'écoute (doit tourner sur le main thread — c'est le cas dans un Service). */
    private void startListening() {
        if (!mListenEnabled) return;
        if (mSR != null) return;
        if (!SpeechRecognizer.isRecognitionAvailable(this)) return;

        try {
            if (Build.VERSION.SDK_INT >= 31
                    && SpeechRecognizer.isOnDeviceRecognitionAvailable(this)) {
                mSR = SpeechRecognizer.createOnDeviceSpeechRecognizer(this);
            } else {
                mSR = SpeechRecognizer.createSpeechRecognizer(this);
            }
        } catch (Exception e) {
            mSR = SpeechRecognizer.createSpeechRecognizer(this);
        }

        mSR.setRecognitionListener(new RecognitionListener() {
            @Override public void onReadyForSpeech(Bundle params) { mSRListening = true; mSRErrorCount = 0; }
            @Override public void onBeginningOfSpeech() {}
            @Override public void onRmsChanged(float rmsdB) {}
            @Override public void onBufferReceived(byte[] buffer) {}
            @Override public void onEndOfSpeech() { mSRListening = false; }

            @Override public void onError(int error) {
                mSRListening = false;
                if (mSR != null) { mSR.destroy(); mSR = null; }
                if (!mListenEnabled) return;
                mSRErrorCount++;
                boolean fast = (error == SpeechRecognizer.ERROR_NO_MATCH
                             || error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT);
                boolean busy = (error == SpeechRecognizer.ERROR_RECOGNIZER_BUSY);
                long delay;
                if (mSRErrorCount >= SR_MAX_ERRORS) delay = 30_000L;
                else if (fast)  delay = 200L;
                else if (busy)  delay = 1_500L;
                else            delay = Math.min(2000L * mSRErrorCount, 20_000L);
                scheduleRestart(delay);
            }

            @Override public void onResults(Bundle results) {
                mSRListening = false;
                ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                float[] scores = results.getFloatArray(SpeechRecognizer.CONFIDENCE_SCORES);
                if (matches != null) {
                    for (int i = 0; i < matches.size(); i++) {
                        if (matchesKw(matches.get(i))) {
                            float conf = (scores != null && i < scores.length) ? scores[i] : 0.6f;
                            onEmergencyDetected(matches.get(i), conf);
                            if (mSR != null) { mSR.destroy(); mSR = null; }
                            scheduleRestart(SR_COOLDOWN_MS);
                            return;
                        }
                    }
                }
                if (mSR != null) { mSR.destroy(); mSR = null; }
                scheduleRestart(200L);
            }

            @Override public void onPartialResults(Bundle partialResults) {
                ArrayList<String> partial = partialResults.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                if (partial != null) {
                    for (String text : partial) {
                        if (matchesKw(text)) {
                            onEmergencyDetected(text, 0.7f);
                            if (mSR != null) { mSR.destroy(); mSR = null; }
                            scheduleRestart(SR_COOLDOWN_MS);
                            return;
                        }
                    }
                }
            }

            @Override public void onEvent(int eventType, Bundle params) {}
        });

        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "fr-FR");
        intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3);
        intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
        intent.putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true);
        intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 1500L);
        intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 800L);
        intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS, 300L);

        try {
            mSR.startListening(intent);
        } catch (Exception e) {
            if (mSR != null) { mSR.destroy(); mSR = null; }
            scheduleRestart(3000L);
        }
    }

    private void stopListening() {
        mSRListening = false;
        if (mRestartTask != null) { mHandler.removeCallbacks(mRestartTask); mRestartTask = null; }
        if (mSR != null) {
            try { mSR.stopListening(); } catch (Exception ignored) {}
            try { mSR.destroy(); } catch (Exception ignored) {}
            mSR = null;
        }
    }

    private void scheduleRestart(long delayMs) {
        if (mRestartTask != null) return;
        mRestartTask = () -> { mRestartTask = null; if (mListenEnabled) startListening(); };
        mHandler.postDelayed(mRestartTask, delayMs);
    }

    /** Mot-clé détecté : ouvre l'app avec le flag SOS vocal → le JS déclenche le SOS YAWATCH. */
    private void onEmergencyDetected(String text, float confidence) {
        mEmergency = true;
        pushNotification();
        String safe = (text != null) ? text : "";
        Intent launch = new Intent(this, MainActivity.class);
        launch.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        launch.putExtra("guardian_voice_sos", safe);
        launch.putExtra("guardian_voice_conf", confidence);
        try { startActivity(launch); } catch (Exception ignored) {}
    }

    // ───────────────────────── BULLE OVERLAY ─────────────────────────

    private void showOverlay() {
        if (!mOverlayEnabled) return;
        if (mOverlayView != null) return;
        if (Build.VERSION.SDK_INT >= 23 && !Settings.canDrawOverlays(this)) return; // permission absente
        mWM = (WindowManager) getSystemService(WINDOW_SERVICE);
        if (mWM == null) return;

        int sz = (int) TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, 46f, getResources().getDisplayMetrics());
        TextView bubble = new TextView(this);
        bubble.setText("🛡");
        bubble.setTextSize(TypedValue.COMPLEX_UNIT_SP, 20f);
        bubble.setGravity(Gravity.CENTER);
        GradientDrawable bg = new GradientDrawable();
        bg.setShape(GradientDrawable.OVAL);
        bg.setColor(Color.parseColor("#CC0F172A"));
        bg.setStroke(2, Color.parseColor("#3422C55E"));
        bubble.setBackground(bg);
        bubble.setAlpha(0.92f);

        int type = (Build.VERSION.SDK_INT >= 26)
            ? WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            : WindowManager.LayoutParams.TYPE_PHONE;
        final WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
            sz, sz, type,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
            PixelFormat.TRANSLUCENT);
        lp.gravity = Gravity.TOP | Gravity.START;
        lp.x = 24;
        lp.y = (int) (getResources().getDisplayMetrics().heightPixels * 0.35);

        bubble.setOnTouchListener(new View.OnTouchListener() {
            int initX, initY; float touchX, touchY; boolean moved;
            @Override public boolean onTouch(View v, MotionEvent e) {
                switch (e.getAction()) {
                    case MotionEvent.ACTION_DOWN:
                        initX = lp.x; initY = lp.y; touchX = e.getRawX(); touchY = e.getRawY(); moved = false;
                        return true;
                    case MotionEvent.ACTION_MOVE:
                        int dx = (int) (e.getRawX() - touchX), dy = (int) (e.getRawY() - touchY);
                        if (Math.abs(dx) > 8 || Math.abs(dy) > 8) moved = true;
                        lp.x = initX + dx; lp.y = initY + dy;
                        try { mWM.updateViewLayout(mOverlayView, lp); } catch (Exception ignored) {}
                        return true;
                    case MotionEvent.ACTION_UP:
                        if (!moved) {
                            Intent open = new Intent(GuardianService.this, MainActivity.class);
                            open.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
                            try { startActivity(open); } catch (Exception ignored) {}
                        }
                        return true;
                }
                return false;
            }
        });

        mOverlayView = bubble;
        try { mWM.addView(mOverlayView, lp); }
        catch (Exception e) { mOverlayView = null; }
    }

    private void hideOverlay() {
        if (mOverlayView != null && mWM != null) {
            try { mWM.removeView(mOverlayView); } catch (Exception ignored) {}
        }
        mOverlayView = null;
    }

    @Override
    public IBinder onBind(Intent intent) { return null; }

    @Override
    public void onDestroy() {
        super.onDestroy();
        stopListening();
        hideOverlay();
        sInstance = null;
    }
}
