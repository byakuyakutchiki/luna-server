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
import android.media.AudioManager;
import android.provider.Settings;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.os.Build;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.TextView;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.util.ArrayList;
import java.util.UUID;

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

    private static final String TAG = "LunaGuardianService";

    static final String ACTION_START  = "fr.yawatch.luna.GUARDIAN_START";
    static final String ACTION_STOP   = "fr.yawatch.luna.GUARDIAN_STOP";
    static final String ACTION_UPDATE = "fr.yawatch.luna.GUARDIAN_UPDATE";

    // URL de la page Guardian (même valeur que MainActivity)
    private static final String LUNA_URL = "http://192.168.1.45:8000/guardian";
    // URL racine du backend pour les appels API natifs (sans /guardian)
    private static final String BACKEND_BASE_URL = "http://192.168.1.45:8000";

    private static final int    NOTIF_ID         = 2001;
    private static final String CHANNEL_NORMAL   = "luna_guardian";
    private static final String CHANNEL_ALERT    = "luna_guardian_alert_silent";

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
    private static final long VOICE_EMERGENCY_DEBOUNCE_MS = 30_000L;

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
    private VoskKeywordSpotter mVoskSpotter  = null;
    private boolean          mUsingVosk      = false;
    private long             mLastVoiceEmergencyAt = 0L;
    private String           mLastVoiceEmergencyText = "";

    // RUNTIME-FIX-001 : suppression des bips système du SpeechRecognizer
    private AudioManager     mAudioManager   = null;
    private int              mSavedSystemVolume = -1;
    private static final boolean SILENT_RECOGNIZER = true;

    // Capture du contexte après un mot-clé (issue #32)
    private boolean          mCaptureActive   = false;
    private StringBuilder    mCaptureBuffer   = new StringBuilder();
    private float            mCaptureConfidence = 0.7f;
    private final Handler    mCaptureHandler  = new Handler(Looper.getMainLooper());
    private Runnable         mCaptureEndTask  = null;
    private static final long CAPTURE_WINDOW_MS = 6_000L;

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
        sendEvent("GUARDIAN_SERVICE_STARTED", "GuardianService créé");
    }

    /**
     * L'utilisateur ferme l'app depuis les applications recentes (geste normal de
     * fermeture). Sans ce callback, le service s'arrete et plus rien ne surveille
     * (voix, chute) jusqu'a reouverture manuelle. On relance immediatement le service
     * en foreground avec l'etat courant, pour que la protection continue.
     */
    @Override
    public void onTaskRemoved(Intent rootIntent) {
        super.onTaskRemoved(rootIntent);
        sendEvent("GUARDIAN_TASK_REMOVED", "App fermee depuis recents — relance du service");
        Intent restart = new Intent(getApplicationContext(), GuardianService.class);
        restart.setAction(ACTION_START);
        restart.putExtra("status", mStatus);
        restart.putExtra("contacts", mContacts);
        restart.putExtra("emergency", mEmergency);
        restart.putExtra("listen", mListenEnabled);
        restart.putExtra("overlay", mOverlayEnabled);
        try {
            if (Build.VERSION.SDK_INT >= 26) {
                getApplicationContext().startForegroundService(restart);
            } else {
                getApplicationContext().startService(restart);
            }
        } catch (Exception e) {
            sendEvent("GUARDIAN_TASK_REMOVED_RESTART_FAILED", e.getClass().getSimpleName() + ": " + e.getMessage());
        }
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
            ? (!mLastSosMessage.isEmpty() ? mLastSosMessage : "SOS déclenché — en attente de confirmation")
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
            CHANNEL_ALERT, "Guardian — Alerte urgence", NotificationManager.IMPORTANCE_LOW);
        alert.setDescription("Alerte SOS Guardian — urgence active");
        alert.setShowBadge(true);
        alert.setSound(null, null);
        alert.enableVibration(false);
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

    // RUNTIME-FIX-001 : coupe/restaure les sons système pour éviter les bips
    // de début/fin d'écoute du SpeechRecognizer.
    private void suppressSystemSounds() {
        if (!SILENT_RECOGNIZER) return;
        if (mAudioManager == null) {
            mAudioManager = (AudioManager) getSystemService(AudioManager.class);
        }
        if (mAudioManager == null) return;
        try {
            if (mSavedSystemVolume < 0) {
                mSavedSystemVolume = mAudioManager.getStreamVolume(AudioManager.STREAM_SYSTEM);
            }
            mAudioManager.setStreamVolume(AudioManager.STREAM_SYSTEM, 0, 0);
            android.util.Log.i("GUARDIAN_AUDIO", "silent_mode_enabled; suppressing_tts_during_listen");
        } catch (Exception e) {
            android.util.Log.w("GUARDIAN_AUDIO", "suppressSystemSounds failed: " + e.getMessage());
        }
    }

    private void restoreSystemSounds() {
        if (!SILENT_RECOGNIZER) return;
        if (mAudioManager == null || mSavedSystemVolume < 0) return;
        try {
            mAudioManager.setStreamVolume(AudioManager.STREAM_SYSTEM, mSavedSystemVolume, 0);
            android.util.Log.i("GUARDIAN_AUDIO", "recognizer_restart_no_sound; restored system volume");
        } catch (Exception e) {
            android.util.Log.w("GUARDIAN_AUDIO", "restoreSystemSounds failed: " + e.getMessage());
        }
        mSavedSystemVolume = -1;
    }

    /** Démarre l'écoute (doit tourner sur le main thread — c'est le cas dans un Service). */
    private void startListening() {
        if (!mListenEnabled) return;
        if (mSR != null || mUsingVosk) return;
        if (tryStartVoskListening()) return;
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            sendEvent("VOICE_LISTENER_FAILED", "SpeechRecognizer non disponible");
            return;
        }
        android.util.Log.i(TAG, "VOICE_LISTENER_STARTED");
        sendEvent("VOICE_LISTENER_STARTED", "Démarrage SpeechRecognizer GuardianService");
        suppressSystemSounds();

        // Test local : utiliser le recognizer cloud Google pour fiabiliser la reconnaissance.
        // Le mode on-device (Soda) retournait des résultats vides sur ce téléphone.
        mSR = SpeechRecognizer.createSpeechRecognizer(this);

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
                String errorName = "error_" + error;
                if (error == SpeechRecognizer.ERROR_NO_MATCH) errorName = "NO_MATCH";
                else if (error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT) errorName = "SPEECH_TIMEOUT";
                else if (error == SpeechRecognizer.ERROR_RECOGNIZER_BUSY) errorName = "RECOGNIZER_BUSY";
                else if (error == SpeechRecognizer.ERROR_NETWORK) errorName = "NETWORK";
                else if (error == SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS) errorName = "PERMISSIONS";
                android.util.Log.w(TAG, "VOICE_LISTENER_FAILED error=" + errorName + " capture=" + mCaptureActive);
                sendEvent("VOICE_LISTENER_FAILED", "SpeechRecognizer error=" + errorName + " capture=" + mCaptureActive);
                boolean fast = (error == SpeechRecognizer.ERROR_NO_MATCH
                             || error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT);
                boolean busy = (error == SpeechRecognizer.ERROR_RECOGNIZER_BUSY);
                long delay;
                if (mCaptureActive) {
                    // Pendant la fenêtre de capture on redémarre vite pour ne pas perdre le contexte.
                    delay = fast ? 300L : (busy ? 800L : 1500L);
                } else if (mSRErrorCount >= SR_MAX_ERRORS) {
                    delay = 30_000L;
                } else if (fast) {
                    // Background safety: restart quickly so a distress phrase is not missed
                    // between two one-shot SpeechRecognizer sessions. System sounds stay muted.
                    delay = 500L;
                } else if (busy) {
                    delay = 1_500L;
                } else {
                    delay = Math.min(2000L * mSRErrorCount, 20_000L);
                }
                scheduleRestart(delay);
            }

            @Override public void onResults(Bundle results) {
                mSRListening = false;
                ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                float[] scores = results.getFloatArray(SpeechRecognizer.CONFIDENCE_SCORES);
                String all = (matches != null) ? String.join(" | ", matches) : "(empty)";
                android.util.Log.i(TAG, "VOICE_RESULTS " + all + " capture=" + mCaptureActive);
                sendEvent("VOICE_RESULTS", all + " capture=" + mCaptureActive);

                if (mCaptureActive) {
                    if (matches != null && !matches.isEmpty()) {
                        appendCapture(matches.get(0));
                    }
                    if (mSR != null) { mSR.destroy(); mSR = null; }
                    // Redémarrage rapide pour capter la suite du contexte pendant les 6 s.
                    scheduleRestart(150L);
                    return;
                }

                if (matches != null) {
                    for (int i = 0; i < matches.size(); i++) {
                        if (matchesKw(matches.get(i))) {
                            float conf = (scores != null && i < scores.length) ? scores[i] : 0.6f;
                            android.util.Log.w(TAG, "VOICE_KEYWORD_MATCH final=" + matches.get(i));
                            startCaptureWindow(matches.get(i), conf);
                            if (mSR != null) { mSR.destroy(); mSR = null; }
                            scheduleRestart(150L);
                            return;
                        }
                    }
                }
                if (mSR != null) { mSR.destroy(); mSR = null; }
                scheduleRestart(3_000L);
            }

            @Override public void onPartialResults(Bundle partialResults) {
                ArrayList<String> partial = partialResults.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                if (partial == null || partial.isEmpty()) return;
                String joined = String.join(" ", partial);
                android.util.Log.i(TAG, "VOICE_PARTIAL " + joined + " capture=" + mCaptureActive);
                sendEvent("VOICE_PARTIAL", joined + " capture=" + mCaptureActive);

                if (mCaptureActive) {
                    appendCapture(joined);
                    return;
                }

                for (String text : partial) {
                    if (matchesKw(text)) {
                        android.util.Log.w(TAG, "VOICE_KEYWORD_MATCH partial=" + text);
                        startCaptureWindow(text, 0.7f);
                        // On continue à écouter : les résultats partiels suivants enrichiront le contexte.
                        return;
                    }
                }
            }

            @Override public void onEvent(int eventType, Bundle params) {}
        });

        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "fr-FR");
        intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 5);
        intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
        // Sessions plus tolérantes : laisser le temps à la phrase de détresse d'arriver
        // même si l'utilisateur parle juste après le redémarrage du recognizer.
        intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS, 8_000L);
        intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 10_000L);
        intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 5_000L);

        try {
            mSR.startListening(intent);
        } catch (Exception e) {
            if (mSR != null) { mSR.destroy(); mSR = null; }
            scheduleRestart(3000L);
        }
    }

    private boolean tryStartVoskListening() {
        String availability = VoskKeywordSpotter.availabilityReason(this);
        if (!availability.startsWith("available:")) {
            android.util.Log.i(TAG, "VOSK_POC_UNAVAILABLE " + availability + "; fallback=SpeechRecognizer");
            sendEvent("VOSK_POC_UNAVAILABLE", availability + "; fallback=SpeechRecognizer");
            return false;
        }
        mUsingVosk = true;
        mVoskSpotter = new VoskKeywordSpotter(this, new VoskKeywordSpotter.Listener() {
            @Override public void onReady(String modelPath) {
                android.util.Log.w(TAG, "VOSK_POC_READY model=" + modelPath);
                sendEvent("VOSK_POC_READY", modelPath);
            }
            @Override public void onPartial(String text) {
                android.util.Log.i(TAG, "VOSK_POC_PARTIAL " + text);
            }
            @Override public void onFinal(String text) {
                android.util.Log.i(TAG, "VOSK_POC_FINAL " + text);
                sendEvent("VOSK_POC_FINAL", text);
            }
            @Override public void onKeyword(String text, float confidence) {
                android.util.Log.w(TAG, "VOSK_POC_KEYWORD " + text);
                sendEvent("VOSK_POC_KEYWORD", text);
                onEmergencyDetected(text, confidence);
            }
            @Override public void onError(String message) {
                android.util.Log.e(TAG, "VOSK_POC_ERROR " + message);
                sendEvent("VOSK_POC_ERROR", message);
                mUsingVosk = false;
                mVoskSpotter = null;
                scheduleRestart(1000L);
            }
            @Override public void onStopped() {
                android.util.Log.i(TAG, "VOSK_POC_STOPPED");
                mUsingVosk = false;
                mVoskSpotter = null;
            }
        });
        mVoskSpotter.start();
        return true;
    }

    private void stopListening() {
        mSRListening = false;
        stopCapture();
        if (mRestartTask != null) { mHandler.removeCallbacks(mRestartTask); mRestartTask = null; }
        if (mVoskSpotter != null) {
            try { mVoskSpotter.stop(); } catch (Exception ignored) {}
            mVoskSpotter = null;
            mUsingVosk = false;
        }
        if (mSR != null) {
            try { mSR.stopListening(); } catch (Exception ignored) {}
            try { mSR.destroy(); } catch (Exception ignored) {}
            mSR = null;
        }
        // RUNTIME-FIX-001 : restaurer le volume système uniquement à l'arrêt définitif
        if (!mListenEnabled) {
            restoreSystemSounds();
        }
    }

    private void scheduleRestart(long delayMs) {
        if (mRestartTask != null) return;
        mRestartTask = () -> { mRestartTask = null; if (mListenEnabled) startListening(); };
        mHandler.postDelayed(mRestartTask, delayMs);
    }

    /** Démarre la fenêtre de capture du contexte après un mot-clé. */
    private void startCaptureWindow(String initialText, float confidence) {
        if (mCaptureActive) return;
        mCaptureActive = true;
        mCaptureBuffer.setLength(0);
        if (initialText != null && !initialText.isEmpty()) {
            mCaptureBuffer.append(initialText);
        }
        mCaptureConfidence = confidence;
        android.util.Log.w(TAG, "VOICE_CAPTURE_START text=" + initialText);
        sendEvent("VOICE_CAPTURE_START", "text=" + initialText);
        if (mCaptureEndTask != null) mCaptureHandler.removeCallbacks(mCaptureEndTask);
        mCaptureEndTask = () -> {
            mCaptureActive = false;
            mCaptureEndTask = null;
            String full = mCaptureBuffer.toString().trim();
            android.util.Log.w(TAG, "VOICE_CAPTURE_END full=" + full);
            sendEvent("VOICE_CAPTURE_END", "full=" + full);
            onEmergencyDetected(full.isEmpty() ? initialText : full, mCaptureConfidence);
            if (mSR != null) { try { mSR.stopListening(); } catch (Exception ignored) {} }
            scheduleRestart(SR_COOLDOWN_MS);
        };
        mCaptureHandler.postDelayed(mCaptureEndTask, CAPTURE_WINDOW_MS);
    }

    private void appendCapture(String text) {
        if (!mCaptureActive || text == null || text.isEmpty()) return;
        if (mCaptureBuffer.length() > 0) mCaptureBuffer.append(" ");
        mCaptureBuffer.append(text);
    }

    private void stopCapture() {
        mCaptureActive = false;
        if (mCaptureEndTask != null) {
            mCaptureHandler.removeCallbacks(mCaptureEndTask);
            mCaptureEndTask = null;
        }
        mCaptureBuffer.setLength(0);
    }

    /** Dernier message de confirmation reel renvoye par le serveur apres un SOS (vide = pas
     * encore de reponse serveur). Remplace le texte optimiste fige "Contacts alertes". */
    private volatile String mLastSosMessage = "";

    /** Mot-clé détecté : déclenche le SOS natif puis ouvre l'app pour l'UI/contexte. */
    private void onEmergencyDetected(String text, float confidence) {
        String safe = (text != null) ? text.trim() : "";
        String normalized = normalize(safe);
        if (normalized.isEmpty()) {
            android.util.Log.w(TAG, "VOICE_EMERGENCY_SKIPPED empty_text");
            sendEvent("VOICE_EMERGENCY_SKIPPED", "empty_text");
            return;
        }
        long now = System.currentTimeMillis();
        if (mLastVoiceEmergencyAt > 0L && (now - mLastVoiceEmergencyAt) < VOICE_EMERGENCY_DEBOUNCE_MS) {
            android.util.Log.w(TAG, "VOICE_EMERGENCY_DEBOUNCED previous=" + mLastVoiceEmergencyText + " text=" + safe);
            sendEvent("VOICE_EMERGENCY_DEBOUNCED", "previous=" + mLastVoiceEmergencyText + " text=" + safe);
            return;
        }
        mLastVoiceEmergencyText = normalized;
        mLastVoiceEmergencyAt = now;
        mEmergency = true;
        pushNotification();
        boolean nativeWillPost = hasSavedGuardianSession();
        android.util.Log.w(TAG, "VOICE_EMERGENCY_DETECTED nativeWillPost=" + nativeWillPost + " text=" + safe);
        if (nativeWillPost) {
            triggerNativeVoiceSos(safe, confidence);
        }
        Intent launch = new Intent(this, MainActivity.class);
        launch.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        if (!nativeWillPost) {
            // Fallback legacy: no persisted SID, let the WebView try once it opens.
            launch.putExtra("guardian_voice_sos", safe);
            launch.putExtra("guardian_voice_conf", confidence);
        }
        try { startActivity(launch); } catch (Exception ignored) {}
    }

    private boolean hasSavedGuardianSession() {
        try {
            String sid = getSharedPreferences("guardian", MODE_PRIVATE).getString("guardian_session_id", "");
            return sid != null && !sid.trim().isEmpty();
        } catch (Exception ignored) {
            return false;
        }
    }

    /**
     * P0 safety: when Guardian runs in background, do not depend on WebView startup
     * to fire the emergency. The JS path still runs after the app opens, but the
     * native service posts the SOS immediately using the last session saved by JS.
     */
    private void triggerNativeVoiceSos(String text, float confidence) {
        new Thread(() -> {
            try {
                android.content.SharedPreferences sp = getSharedPreferences("guardian", MODE_PRIVATE);
                String sid = sp.getString("guardian_session_id", "");
                if (sid == null || sid.trim().isEmpty()) {
                    android.util.Log.e(TAG, "VOICE_SOS_NATIVE_SKIPPED missing_guardian_session_id text=" + text);
                    sendEvent("VOICE_SOS_NATIVE_SKIPPED", "missing_guardian_session_id text=" + text);
                    return;
                }

                String incidentId = "apk_voice_" + System.currentTimeMillis() + "_" + UUID.randomUUID().toString().substring(0, 8);
                JSONObject json = new JSONObject();
                json.put("incident_id", incidentId);
                json.put("source", "vocal");
                json.put("context", text != null ? text : "");
                json.put("transcript", text != null ? text : "");
                json.put("confidence", confidence);
                json.put("client", "GuardianService");

                String safeSid = URLEncoder.encode(sid, "UTF-8");
                URL url = new URL(BACKEND_BASE_URL + "/api/guardian/sos/" + safeSid);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setRequestProperty("User-Agent", "LunaApp/GuardianService Android/" + Build.VERSION.RELEASE);
                String token = sp.getString("auth_token", "");
                if (token != null && !token.isEmpty()) {
                    conn.setRequestProperty("Authorization", "Bearer " + token);
                }
                conn.setDoOutput(true);
                conn.setConnectTimeout(6000);
                conn.setReadTimeout(8000);
                OutputStream out = conn.getOutputStream();
                out.write(json.toString().getBytes("UTF-8"));
                out.close();

                int code = conn.getResponseCode();
                BufferedReader reader = null;
                try {
                    reader = new BufferedReader(new InputStreamReader(
                        code >= 200 && code < 400 ? conn.getInputStream() : conn.getErrorStream()
                    ));
                    StringBuilder body = new StringBuilder();
                    String line;
                    while ((line = reader.readLine()) != null && body.length() < 500) body.append(line);
                    android.util.Log.w(TAG, "VOICE_SOS_NATIVE_POST status=" + code + " sid=" + sid + " body=" + body.toString());
                    sendEvent("VOICE_SOS_NATIVE_POST", "status=" + code + " sid=" + sid + " body=" + body.toString());
                    try {
                        JSONObject respJson = new JSONObject(body.toString());
                        mLastSosMessage = respJson.optString("message", "");
                    } catch (Exception ignored) {
                        mLastSosMessage = "SOS déclenché — confirmation serveur illisible";
                    }
                    pushNotification();
                } finally {
                    if (reader != null) try { reader.close(); } catch (Exception ignored) {}
                    conn.disconnect();
                }
            } catch (Exception e) {
                android.util.Log.e(TAG, "VOICE_SOS_NATIVE_FAILED " + e.getClass().getSimpleName() + ": " + e.getMessage());
                sendEvent("VOICE_SOS_NATIVE_FAILED", e.getClass().getSimpleName() + ": " + e.getMessage());
            }
        }).start();
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
        sendEvent("GUARDIAN_SERVICE_STOPPED", "GuardianService détruit");
        stopListening();
        restoreSystemSounds();
        hideOverlay();
        sInstance = null;
    }

    /** Envoie un événement de diagnostic au backend Luna. */
    private void sendEvent(String eventType, String message) {
        new Thread(() -> {
            try {
                JSONObject json = new JSONObject();
                json.put("device_id", Build.MODEL + "_" + Build.ID);
                json.put("event_type", eventType);
                json.put("message", message);

                URL url = new URL(BACKEND_BASE_URL + "/api/apk/event");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setRequestProperty("User-Agent", "LunaApp/GuardianService Android/" + Build.VERSION.RELEASE);
                conn.setDoOutput(true);
                conn.setConnectTimeout(4000);
                conn.setReadTimeout(4000);
                OutputStream out = conn.getOutputStream();
                out.write(json.toString().getBytes("UTF-8"));
                out.close();
                int code = conn.getResponseCode();
                android.util.Log.i(TAG, "sendEvent " + eventType + " status=" + code);
                conn.getInputStream().close();
                conn.disconnect();
            } catch (Exception e) { android.util.Log.w(TAG, "sendEvent failed " + eventType + ": " + e.getClass().getSimpleName() + ": " + e.getMessage()); }
        }).start();
    }
}
