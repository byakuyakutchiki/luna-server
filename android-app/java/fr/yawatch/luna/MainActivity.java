package fr.yawatch.luna;

import android.Manifest;
import android.animation.Animator;
import android.animation.AnimatorListenerAdapter;
import android.animation.ObjectAnimator;
import android.app.Activity;
import android.app.DownloadManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.provider.Settings;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.provider.MediaStore;
import android.util.TypedValue;
import android.view.Gravity;
import android.webkit.ValueCallback;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.DownloadListener;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.ConsoleMessage;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.URLUtil;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONObject;

import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import java.util.ArrayList;
import java.io.BufferedReader;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.MessageDigest;

public class MainActivity extends Activity {

    private static final String LUNA_URL = "https://luna-beta-674304336025.europe-west1.run.app";
    private static final int PERMISSION_REQUEST_CODE = 100;

    // ── Détection de chute ──────────────────────────────────────────
    // Chute libre : accélération totale < 4 m/s² (~0.4g) pendant ≥ 80ms
    // Impact      : pic > 22 m/s² (~2.2g) dans les 800ms qui suivent
    private static final float FREE_FALL_THRESHOLD  = 4.0f;   // m/s²
    private static final float IMPACT_THRESHOLD     = 22.0f;  // m/s²
    private static final long  FALL_WINDOW_MS       = 800L;
    private static final long  MIN_FREE_FALL_MS     = 80L;
    private static final long  CONFIRMATION_MS      = 30_000L; // 30s pour répondre
    private static final long  FALL_COOLDOWN_MS     = 60_000L; // 60s entre deux détections

    private SensorManager sensorManager;
    private Sensor accelerometer;
    private boolean inFreeFall = false;
    private long freeFallStart = 0L;
    private boolean fallAlertActive = false;
    private long lastFallTrigger = 0L;
    private float pendingPeakG = 0f;
    private String guardianSessionId = null;   // défini par JS via LunaBridge
    private double guardianLat = 0.0;
    private double guardianLng = 0.0;
    private String authToken = "";             // JWT transmis par le JS pour les requêtes natives

    // ── Reconnaissance vocale native Guardian ──────────────────────
    private static final String[] NATIVE_EMERGENCY_KW = {
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
    private static final long NATIVE_SR_COOLDOWN_MS = 15_000L; // pause pendant countdown JS
    private static final int  NATIVE_SR_MAX_ERRORS   = 6;      // max erreurs consécutives avant pause longue

    private SpeechRecognizer nativeSR = null;
    private boolean nativeSREnabled  = false;   // vrai quand Guardian est actif
    private boolean nativeSRListening= false;   // vrai quand le SR est démarré
    private final Handler nativeSRHandler = new Handler(Looper.getMainLooper());
    private Runnable nativeSRRestartTask = null;
    private int nativeSRErrorCount = 0;

    private final Handler fallHandler = new Handler(Looper.getMainLooper());
    private Runnable fallEscalationTask = null;
    private View fallOverlay = null;
    private TextView fallCountdownText = null;
    private static final int NOTIFICATION_PERMISSION_CODE = 101;
    private static final int FILE_CHOOSER_REQUEST_CODE = 102;
    private static final String CURRENT_VERSION = "3.1";
    private static final int CURRENT_VERSION_CODE = 22;
    private static final int CAMERA_PERMISSION_FOR_FILE = 103;
    private static final int CAMERA_CAPTURE_REQUEST_CODE = 104;
    private static final int GUARDIAN_MIC_PERMISSION_REQUEST = 77;
    private static final String CHANNEL_ID = "luna_messages";
    private WebView webView;
    private PermissionRequest pendingPermissionRequest;
    private ValueCallback<Uri[]> fileUploadCallback;
    private Uri cameraOutputUri;
    private boolean isInForeground = true;
    private int notificationId = 1000;
    private View splashView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Plein ecran immersif
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(
            WindowManager.LayoutParams.FLAG_FULLSCREEN,
            WindowManager.LayoutParams.FLAG_FULLSCREEN
        );

        // Creer le canal de notification (Android 8+)
        createNotificationChannel();

        // Demander la permission de notification (Android 13+)
        if (Build.VERSION.SDK_INT >= 33) {
            if (checkSelfPermission("android.permission.POST_NOTIFICATIONS") != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{"android.permission.POST_NOTIFICATIONS"}, NOTIFICATION_PERMISSION_CODE);
            }
        }

        // WebView + splash overlay
        webView = new WebView(this);
        FrameLayout root = new FrameLayout(this);
        root.addView(webView, new FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT,
            FrameLayout.LayoutParams.MATCH_PARENT));
        splashView = buildSplash();
        root.addView(splashView, new FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT,
            FrameLayout.LayoutParams.MATCH_PARENT));
        setContentView(root);
        // Sécurité : disparaît après 6s même si la page ne charge pas
        webView.postDelayed(this::hideSplash, 6000);

        // Bridge JavaScript -> Android
        webView.addJavascriptInterface(new LunaBridge(), "LunaBridge");

        // Initialiser le capteur accéléromètre pour la détection de chute
        sensorManager = (SensorManager) getSystemService(SENSOR_SERVICE);
        if (sensorManager != null) {
            accelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
        }

        // Configuration WebView
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setAllowFileAccess(true);
        settings.setCacheMode(WebSettings.LOAD_NO_CACHE);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(true);
        settings.setSupportZoom(false);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        settings.setDefaultFontSize(16);
        settings.setSupportMultipleWindows(true); // nécessaire pour window.open() / target="_blank"

        // Geolocation support
        settings.setGeolocationEnabled(true);

        // Version dans le User-Agent pour auto-update
        settings.setUserAgentString(settings.getUserAgentString() + " LunaApp/" + CURRENT_VERSION);

        // Cookies (pour la session JWT)
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true);

        // WebChromeClient: gere les permissions camera/micro/geoloc + window.open
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onCreateWindow(WebView view, boolean isDialog, boolean isUserGesture, android.os.Message resultMsg) {
                // window.open() et target="_blank" → extraire l'URL et l'ouvrir nativement
                WebView tempView = new WebView(MainActivity.this);
                tempView.setWebViewClient(new WebViewClient() {
                    @Override
                    public boolean shouldOverrideUrlLoading(WebView v, String url) {
                        if (url != null && !url.startsWith(LUNA_URL)) {
                            try {
                                Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                                startActivity(intent);
                            } catch (Exception ignored) { }
                        }
                        return true;
                    }
                });
                WebView.WebViewTransport transport = (WebView.WebViewTransport) resultMsg.obj;
                transport.setWebView(tempView);
                resultMsg.sendToTarget();
                return true;
            }

            @Override
            public void onGeolocationPermissionsShowPrompt(String origin, android.webkit.GeolocationPermissions.Callback callback) {
                if (Build.VERSION.SDK_INT >= 23) {
                    if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
                        requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION}, PERMISSION_REQUEST_CODE + 10);
                    }
                }
                callback.invoke(origin, true, false);
            }

            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback,
                                             FileChooserParams params) {
                if (fileUploadCallback != null) {
                    fileUploadCallback.onReceiveValue(null);
                }
                fileUploadCallback = callback;

                try {
                    boolean wantCamera = false;
                    if (Build.VERSION.SDK_INT >= 21) {
                        wantCamera = params.isCaptureEnabled();
                    }
                    String[] acceptTypes = params.getAcceptTypes();
                    boolean isImage = false;
                    if (acceptTypes != null) {
                        for (String t : acceptTypes) {
                            if (t != null && (t.startsWith("image/") || t.equals("image/*"))) {
                                isImage = true;
                                break;
                            }
                        }
                    }

                    if (wantCamera) {
                        launchCameraCapture();
                        return true;
                    }

                    if (Build.VERSION.SDK_INT >= 23) {
                        if (isImage && checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
                            requestPermissions(new String[]{Manifest.permission.CAMERA}, CAMERA_PERMISSION_FOR_FILE);
                            return true;
                        }
                    }

                    Intent fileIntent = new Intent(Intent.ACTION_GET_CONTENT);
                    fileIntent.setType(isImage ? "image/*" : "*/*");
                    fileIntent.addCategory(Intent.CATEGORY_OPENABLE);
                    if (acceptTypes != null && acceptTypes.length > 0) {
                        fileIntent.putExtra(Intent.EXTRA_MIME_TYPES, acceptTypes);
                    }
                    Intent chooser = Intent.createChooser(fileIntent, "Choisir un fichier");
                    startActivityForResult(chooser, FILE_CHOOSER_REQUEST_CODE);
                } catch (Exception e) {
                    if (fileUploadCallback != null) {
                        fileUploadCallback.onReceiveValue(null);
                        fileUploadCallback = null;
                    }
                    return false;
                }
                return true;
            }

            @Override
            public boolean onConsoleMessage(ConsoleMessage cm) {
                String level = "debug";
                if (cm.messageLevel() == ConsoleMessage.MessageLevel.ERROR) level = "error";
                else if (cm.messageLevel() == ConsoleMessage.MessageLevel.WARNING) level = "warn";
                else if (cm.messageLevel() == ConsoleMessage.MessageLevel.LOG) level = "info";
                String loc = cm.sourceId().replaceAll(".*/", "") + ":" + cm.lineNumber();
                sendLog(level, cm.message() + "  [" + loc + "]", "js/" + Build.MODEL);
                return false; // laisser le log natif aussi
            }

            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                // Sécurité : refuser caméra/micro à toute origine autre que Luna
                String origin = request.getOrigin().toString();
                if (!origin.startsWith(LUNA_URL) && !origin.contains("daily.co")) {
                    request.deny();
                    return;
                }
                if (Build.VERSION.SDK_INT >= 23) {
                    boolean needCamera = false;
                    boolean needAudio = false;
                    for (String res : request.getResources()) {
                        if (res.equals(PermissionRequest.RESOURCE_VIDEO_CAPTURE)) needCamera = true;
                        if (res.equals(PermissionRequest.RESOURCE_AUDIO_CAPTURE)) needAudio = true;
                    }

                    boolean cameraOk = !needCamera || checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED;
                    boolean audioOk = !needAudio || checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED;

                    if (cameraOk && audioOk) {
                        runOnUiThread(() -> request.grant(request.getResources()));
                    } else {
                        pendingPermissionRequest = request;
                        String[] perms;
                        if (needCamera && needAudio) {
                            perms = new String[]{ Manifest.permission.CAMERA, Manifest.permission.RECORD_AUDIO };
                        } else if (needCamera) {
                            perms = new String[]{ Manifest.permission.CAMERA };
                        } else {
                            perms = new String[]{ Manifest.permission.RECORD_AUDIO };
                        }
                        requestPermissions(perms, PERMISSION_REQUEST_CODE);
                    }
                } else {
                    runOnUiThread(() -> request.grant(request.getResources()));
                }
            }
        });

        // Gerer les telechargements (APK auto-update via DownloadManager)
        webView.setDownloadListener(new DownloadListener() {
            @Override
            public void onDownloadStart(String url, String userAgent, String contentDisposition, String mimetype, long contentLength) {
                try {
                    DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
                    request.setTitle("Luna - Mise a jour");
                    request.setDescription("Telechargement de la mise a jour Luna...");
                    request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                    String filename = URLUtil.guessFileName(url, contentDisposition, mimetype);
                    request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, filename);
                    request.setMimeType("application/vnd.android.package-archive");

                    DownloadManager dm = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
                    if (dm != null) {
                        dm.enqueue(request);
                        Toast.makeText(MainActivity.this, "Telechargement en cours... Ouvre la notification pour installer.", Toast.LENGTH_LONG).show();
                    }
                } catch (Exception e) {
                    Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                    startActivity(intent);
                }
            }
        });

        // Garde la navigation dans le WebView (bloque les sorties externes)
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                if (url == null) return true;
                // Autoriser : Luna, navigation WebView interne, fichiers/données WebRTC
                if (url.startsWith(LUNA_URL)
                        || url.startsWith("about:")
                        || url.startsWith("blob:")
                        || url.startsWith("data:")) {
                    return false;
                }
                // Liens externes (Google Maps, etc.) → ouvrir dans l'appli/navigateur natif
                try {
                    Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    startActivity(intent);
                } catch (Exception ignored) { }
                return true; // le WebView ne navigue pas
            }

            @Override
            public void onReceivedSslError(WebView view, android.webkit.SslErrorHandler handler, android.net.http.SslError error) {
                sendLog("error", "SSL error: " + error.toString(), "webview/" + Build.MODEL);
                handler.cancel();
            }

            @Override
            public void onReceivedError(WebView view, int errorCode, String description, String failingUrl) {
                sendLog("error", "WebView err " + errorCode + ": " + description + " — " + failingUrl, "webview/" + Build.MODEL);
            }

            @Override
            public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                sendLog("nav", "LOAD START: " + url, "nav/" + Build.MODEL);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                sendLog("nav", "LOAD OK: " + url, "nav/" + Build.MODEL);
                runOnUiThread(() -> hideSplash());
            }
        });

        // Vider le cache avant de charger (force la mise a jour)
        webView.clearCache(true);

        // Charge Luna
        sendLog("info", "APP START v" + CURRENT_VERSION + " (" + CURRENT_VERSION_CODE + ") — " + Build.MODEL + " Android " + Build.VERSION.RELEASE, "apk/" + Build.MODEL);
        webView.loadUrl(LUNA_URL);

        // Démarrage à froid déclenché par Guardian (bouton SOS notif ou mot-clé vocal du service)
        handleGuardianIntent(getIntent());

        // Verification auto-update en arriere-plan
        checkForUpdate();
    }

    /** Construit l'écran de chargement brandé YAWatch / Luna. */
    private View buildSplash() {
        float dp = getResources().getDisplayMetrics().density;

        FrameLayout frame = new FrameLayout(this);
        frame.setBackgroundColor(0xFF020810);

        LinearLayout center = new LinearLayout(this);
        center.setOrientation(LinearLayout.VERTICAL);
        center.setGravity(Gravity.CENTER_HORIZONTAL);

        // "YAWatch" — blanc, gros, bold
        TextView tvTitle = new TextView(this);
        tvTitle.setText("YAWatch");
        tvTitle.setTextColor(0xFFE5E7EB);
        tvTitle.setTextSize(TypedValue.COMPLEX_UNIT_SP, 38f);
        tvTitle.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        tvTitle.setLetterSpacing(0.10f);
        tvTitle.setGravity(Gravity.CENTER);

        // "LUNA" — vert iris, espacé
        TextView tvSub = new TextView(this);
        tvSub.setText("L U N A");
        tvSub.setTextColor(0xFF10B981);
        tvSub.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12f);
        tvSub.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        tvSub.setLetterSpacing(0.65f);
        tvSub.setGravity(Gravity.CENTER);

        LinearLayout.LayoutParams subLp = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.WRAP_CONTENT,
            LinearLayout.LayoutParams.WRAP_CONTENT);
        subLp.topMargin = (int)(10 * dp);

        // Trait séparateur iris
        android.view.View bar = new android.view.View(this);
        bar.setBackgroundColor(0xFF10B981);
        LinearLayout.LayoutParams barLp = new LinearLayout.LayoutParams(
            (int)(48 * dp), (int)(1.5f * dp));
        barLp.topMargin = (int)(14 * dp);
        barLp.gravity = Gravity.CENTER_HORIZONTAL;

        center.addView(tvTitle);
        center.addView(tvSub, subLp);
        center.addView(bar, barLp);

        FrameLayout.LayoutParams centerLp = new FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.WRAP_CONTENT,
            FrameLayout.LayoutParams.WRAP_CONTENT,
            Gravity.CENTER);
        frame.addView(center, centerLp);
        return frame;
    }

    /** Fait disparaître le splash en fondu. Sécurisé : idempotent. */
    private void hideSplash() {
        if (splashView == null || splashView.getVisibility() != View.VISIBLE) return;
        ObjectAnimator anim = ObjectAnimator.ofFloat(splashView, "alpha", 1f, 0f);
        anim.setDuration(450);
        anim.addListener(new AnimatorListenerAdapter() {
            @Override public void onAnimationEnd(Animator a) {
                splashView.setVisibility(View.GONE);
            }
        });
        anim.start();
    }

    /**
     * Heartbeat APK — signale au serveur que l'APK est vivante sur ce téléphone.
     * Appelé à chaque onResume() : au démarrage et retour au premier plan.
     * Même pattern que sendLog() : thread séparé, timeout 4s, silencieux en cas d'erreur.
     */
    private void sendHeartbeat() {
        new Thread(() -> {
            try {
                URL url = new URL(LUNA_URL + "/api/apk/heartbeat");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setRequestProperty("User-Agent", "LunaApp/" + CURRENT_VERSION + " Android/" + Build.VERSION.RELEASE);
                conn.setDoOutput(true);
                conn.setConnectTimeout(4000);
                conn.setReadTimeout(4000);
                JSONObject json = new JSONObject();
                json.put("apk_version", CURRENT_VERSION);
                json.put("device_role", "fondateur");
                json.put("cloud_url", LUNA_URL);
                json.put("android_version", Build.VERSION.RELEASE);
                json.put("device_model", Build.MODEL);
                json.put("last_screen", "app_resume");
                byte[] bytes = json.toString().getBytes("UTF-8");
                conn.getOutputStream().write(bytes);
                conn.getInputStream().close();
                conn.disconnect();
            } catch (Exception ignored) {}
        }).start();
    }

    /**
     * Envoie un log au serveur Luna en arrière-plan (non bloquant).
     */
    private void sendLog(final String level, final String msg, final String src) {
        new Thread(() -> {
            try {
                URL url = new URL(LUNA_URL + "/api/logs/client");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setDoOutput(true);
                conn.setConnectTimeout(4000);
                conn.setReadTimeout(4000);
                JSONObject json = new JSONObject();
                json.put("level", level);
                json.put("msg", msg);
                json.put("src", src);
                byte[] bytes = json.toString().getBytes("UTF-8");
                conn.getOutputStream().write(bytes);
                conn.getInputStream().close();
                conn.disconnect();
            } catch (Exception ignored) {}
        }).start();
    }

    /**
     * Cree le canal de notification pour Luna (Android 8+).
     */
    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "Messages Luna",
                NotificationManager.IMPORTANCE_DEFAULT
            );
            channel.setDescription("Notifications des messages de Luna");
            channel.enableVibration(true);
            NotificationManager mgr = getSystemService(NotificationManager.class);
            if (mgr != null) {
                mgr.createNotificationChannel(channel);
            }
        }
    }

    /**
     * Affiche une notification Android native.
     */
    private void postNotification(String title, String body) {
        try {
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
                .setAutoCancel(true)
                .setContentIntent(pi);

            if (body.length() > 40) {
                builder.setStyle(new Notification.BigTextStyle().bigText(body));
            }

            NotificationManager mgr = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
            if (mgr != null) {
                mgr.notify(notificationId++, builder.build());
            }
        } catch (Exception e) {
            // Silencieux
        }
    }

    /**
     * Bridge JavaScript -> Android pour les notifications.
     * Appele depuis le JS: LunaBridge.showNotification("Luna", "Bonjour !")
     */
    public class LunaBridge {
        @JavascriptInterface
        public void showNotification(String title, String body) {
            runOnUiThread(() -> postNotification(title, body));
        }

        @JavascriptInterface
        public boolean isAppInForeground() {
            return isInForeground;
        }

        /** Transmet le JWT client au code natif pour les requêtes authentifiées. */
        @JavascriptInterface
        public void setAuthToken(String token) {
            authToken = (token != null) ? token : "";
        }

        /** Appelé par le JS quand Guardian démarre — active la détection de chute. */
        @JavascriptInterface
        public void setGuardianSession(String sessionId) {
            guardianSessionId = (sessionId != null && !sessionId.isEmpty()) ? sessionId : null;
            if (sensorManager != null && accelerometer != null && guardianSessionId != null) {
                sensorManager.unregisterListener(fallDetector);
                sensorManager.registerListener(fallDetector, accelerometer, SensorManager.SENSOR_DELAY_GAME);
            } else if (sensorManager != null && guardianSessionId == null) {
                sensorManager.unregisterListener(fallDetector);
            }
        }

        /** Appelé par le JS quand Guardian s'arrête — désactive la détection. */
        @JavascriptInterface
        public void clearGuardianSession() {
            guardianSessionId = null;
            if (sensorManager != null) sensorManager.unregisterListener(fallDetector);
            if (fallAlertActive) cancelFallAlertInternal(false);
        }

        /**
         * Démarre la reconnaissance vocale native Guardian.
         * Appelé par le JS après guardianStart() pour couvrir l'arrière-plan.
         */
        @JavascriptInterface
        public void startNativeVoiceGuardian() {
            runOnUiThread(() -> {
                nativeSREnabled = true;
                nativeSRErrorCount = 0;
                startNativeSR();
            });
        }

        /**
         * Arrête la reconnaissance vocale native Guardian.
         * Appelé par le JS lors de guardianStop() / _cleanupSession().
         */
        @JavascriptInterface
        public void stopNativeVoiceGuardian() {
            runOnUiThread(MainActivity.this::stopNativeSR);
        }

        /** Appelé par le JS quand l'utilisateur répond "Je vais bien" depuis l'UI in-app. */
        @JavascriptInterface
        public void cancelFallAlert() {
            cancelFallAlertInternal(true);
        }

        /** Appelé par le JS pour escalader immédiatement (bouton SOS in-app). */
        @JavascriptInterface
        public void triggerSosImmediate() {
            escalateFallImmediately();
        }

        /** Met à jour la position GPS utilisée lors de l'envoi d'alerte chute. */
        @JavascriptInterface
        public void updateGuardianPosition(double lat, double lng) {
            guardianLat = lat;
            guardianLng = lng;
        }

        /**
         * Démarre le Foreground Service Guardian avec notification permanente.
         * Appelé par guardianStart() côté JS.
         * @param status   Texte d'état : "Protégé · GPS actif"
         * @param contacts Noms des contacts de confiance : "Madeleine, Julien"
         */
        @JavascriptInterface
        public void startGuardianService(String status, String contacts) {
            runOnUiThread(() -> {
                Intent intent = new Intent(MainActivity.this, GuardianService.class);
                intent.setAction(GuardianService.ACTION_START);
                if (status   != null) intent.putExtra("status",   status);
                if (contacts != null) intent.putExtra("contacts", contacts);
                if (Build.VERSION.SDK_INT >= 26) {
                    startForegroundService(intent);
                } else {
                    startService(intent);
                }
            });
        }

        /**
         * Arrête le Foreground Service Guardian et retire la notification permanente.
         * Appelé par guardianStop() / _cleanupSession() côté JS.
         */
        @JavascriptInterface
        public void stopGuardianService() {
            runOnUiThread(() -> {
                Intent intent = new Intent(MainActivity.this, GuardianService.class);
                intent.setAction(GuardianService.ACTION_STOP);
                startService(intent);
            });
        }

        /**
         * Met à jour le contenu de la notification Guardian sans redémarrer le service.
         * Appelé par updateRisk() côté JS à chaque changement d'état.
         * @param status    Texte d'état
         * @param contacts  Noms des contacts (peut être vide)
         * @param emergency true = mode urgence (notification rouge haute priorité)
         */
        @JavascriptInterface
        public void updateGuardianNotification(String status, String contacts, boolean emergency) {
            runOnUiThread(() -> GuardianService.updateStatus(status, contacts, emergency));
        }

        /**
         * PROTECTION PERMANENTE (toggle Paramètres → Guardian).
         * Démarre le Foreground Service avec écoute mot-clé en arrière-plan et/ou mini-bulle overlay.
         * L'écoute survit à la fermeture de l'app (mais ne peut être DÉMARRÉE qu'app ouverte).
         * @param listen  écoute mot-clé « au secours »/« à l'aide » par-dessus les autres apps
         * @param overlay mini-bulle système discrète et déplaçable
         */
        @JavascriptInterface
        public void setGuardianProtection(boolean listen, boolean overlay) {
            runOnUiThread(() -> {
                SharedPreferences sp = getSharedPreferences("guardian", Context.MODE_PRIVATE);
                boolean on = listen || overlay;
                sp.edit()
                  .putBoolean("protection_enabled", on)
                  .putBoolean("listen_enabled", listen)
                  .putBoolean("overlay_enabled", overlay)
                  .apply();

                if (!on) {
                    Intent stop = new Intent(MainActivity.this, GuardianService.class);
                    stop.setAction(GuardianService.ACTION_STOP);
                    startService(stop);
                    return;
                }

                // Permission overlay (spéciale) : ouvre l'écran Réglages si absente
                if (overlay && Build.VERSION.SDK_INT >= 23 && !Settings.canDrawOverlays(MainActivity.this)) {
                    try {
                        startActivity(new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                            Uri.parse("package:" + getPackageName())));
                    } catch (Exception ignored) {}
                }

                // Micro requis pour écouter : ne lancer l'écoute QUE si la permission est accordée
                boolean micGranted = checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                        == PackageManager.PERMISSION_GRANTED;
                boolean canListen = listen && micGranted;
                if (listen && !micGranted) {
                    try { requestPermissions(new String[]{ Manifest.permission.RECORD_AUDIO }, GUARDIAN_MIC_PERMISSION_REQUEST); }
                    catch (Exception ignored) {}
                }
                // Éviter le double micro : si le service écoute, couper l'écoute in-app
                if (canListen) stopNativeSR();

                Intent svc = new Intent(MainActivity.this, GuardianService.class);
                svc.setAction(GuardianService.ACTION_START);
                svc.putExtra("status", "Protégé");
                svc.putExtra("listen", canListen);
                svc.putExtra("overlay", overlay);
                if (Build.VERSION.SDK_INT >= 26) startForegroundService(svc);
                else startService(svc);
            });
        }

        /** État persistant du toggle (pour refléter l'interrupteur dans l'UI). */
        @JavascriptInterface
        public boolean isGuardianProtectionOn() {
            return getSharedPreferences("guardian", Context.MODE_PRIVATE)
                    .getBoolean("protection_enabled", false);
        }
    }

    // ── Native SpeechRecognizer — Guardian Voice Core ──────────────

    /** Normalise le texte pour la comparaison (accents, casse, ponctuation). */
    private String normalizeSpeech(String text) {
        if (text == null) return "";
        String nfd = java.text.Normalizer.normalize(text, java.text.Normalizer.Form.NFD);
        return nfd
            .replaceAll("\\p{InCombiningDiacriticalMarks}+", "")
            .toLowerCase()
            .replaceAll("[''']", "'")
            .replaceAll("[^a-z' ]", " ")
            .replaceAll("\\s+", " ")
            .trim();
    }

    /** Vérifie si le texte contient un mot-clé d'urgence. */
    private boolean matchesEmergencyKw(String text) {
        String n = normalizeSpeech(text);
        for (String kw : NATIVE_EMERGENCY_KW) {
            if (n.contains(kw)) return true;
        }
        return false;
    }

    /** Lance la reconnaissance vocale native (doit être appelé depuis le UI thread). */
    private void startNativeSR() {
        if (!nativeSREnabled) return;
        if (nativeSR != null) return; // déjà actif
        if (!SpeechRecognizer.isRecognitionAvailable(this)) return;

        nativeSR = SpeechRecognizer.createSpeechRecognizer(this);
        nativeSR.setRecognitionListener(new RecognitionListener() {
            @Override public void onReadyForSpeech(Bundle params) {
                nativeSRListening = true;
                nativeSRErrorCount = 0;
            }
            @Override public void onBeginningOfSpeech() {}
            @Override public void onRmsChanged(float rmsdB) {}
            @Override public void onBufferReceived(byte[] buffer) {}
            @Override public void onEndOfSpeech() { nativeSRListening = false; }

            @Override
            public void onError(int error) {
                nativeSRListening = false;
                nativeSR.destroy();
                nativeSR = null;
                if (!nativeSREnabled) return;
                nativeSRErrorCount++;
                // no-match / timeout → normal, redémarrer rapidement
                boolean fast = (error == SpeechRecognizer.ERROR_NO_MATCH
                             || error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT);
                // busy → attendre un peu
                boolean busy = (error == SpeechRecognizer.ERROR_RECOGNIZER_BUSY);
                long delay;
                if (nativeSRErrorCount >= NATIVE_SR_MAX_ERRORS) {
                    delay = 30_000L; // pause longue après trop d'erreurs consécutives
                } else if (fast)  { delay = 200L;  }
                else if (busy)    { delay = 1_500L; }
                else              { delay = Math.min(2000L * nativeSRErrorCount, 20_000L); }
                scheduleNativeSRRestart(delay);
            }

            @Override
            public void onResults(Bundle results) {
                nativeSRListening = false;
                ArrayList<String> matches =
                    results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                float[] scores = results.getFloatArray(SpeechRecognizer.CONFIDENCE_SCORES);
                if (matches != null) {
                    for (int i = 0; i < matches.size(); i++) {
                        if (matchesEmergencyKw(matches.get(i))) {
                            float conf = (scores != null && i < scores.length) ? scores[i] : 0.6f;
                            onNativeEmergencyDetected(matches.get(i), conf);
                            // Pause SR pendant le countdown JS (NATIVE_SR_COOLDOWN_MS)
                            if (nativeSR != null) { nativeSR.destroy(); nativeSR = null; }
                            scheduleNativeSRRestart(NATIVE_SR_COOLDOWN_MS);
                            return;
                        }
                    }
                }
                // Aucun mot-clé → redémarrer immédiatement
                if (nativeSR != null) { nativeSR.destroy(); nativeSR = null; }
                scheduleNativeSRRestart(200L);
            }

            @Override
            public void onPartialResults(Bundle partialResults) {
                // Résultats partiels : détecter sans attendre la fin de l'énoncé
                ArrayList<String> partial =
                    partialResults.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                if (partial != null) {
                    for (String text : partial) {
                        if (matchesEmergencyKw(text)) {
                            onNativeEmergencyDetected(text, 0.7f);
                            if (nativeSR != null) { nativeSR.destroy(); nativeSR = null; }
                            scheduleNativeSRRestart(NATIVE_SR_COOLDOWN_MS);
                            return;
                        }
                    }
                }
            }

            @Override public void onEvent(int eventType, Bundle params) {}
        });

        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                        RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "fr-FR");
        intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3);
        intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
        // Silence courts : sensibilité maximale pour détecter même les mots isolés
        intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 1500L);
        intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 800L);
        intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS, 300L);

        try {
            nativeSR.startListening(intent);
        } catch (Exception e) {
            nativeSR.destroy();
            nativeSR = null;
            scheduleNativeSRRestart(3000L);
        }
    }

    /** Arrête la reconnaissance vocale native et annule tout restart planifié. */
    private void stopNativeSR() {
        nativeSREnabled = false;
        nativeSRListening = false;
        if (nativeSRRestartTask != null) {
            nativeSRHandler.removeCallbacks(nativeSRRestartTask);
            nativeSRRestartTask = null;
        }
        if (nativeSR != null) {
            try { nativeSR.stopListening(); } catch (Exception ignored) {}
            nativeSR.destroy();
            nativeSR = null;
        }
    }

    /** Planifie un redémarrage du SR après un délai (dé-dupliqué). */
    private void scheduleNativeSRRestart(long delayMs) {
        if (nativeSRRestartTask != null) return; // déjà planifié
        nativeSRRestartTask = () -> {
            nativeSRRestartTask = null;
            if (nativeSREnabled) startNativeSR();
        };
        nativeSRHandler.postDelayed(nativeSRRestartTask, delayMs);
    }

    /**
     * Déclenché quand un mot-clé d'urgence est détecté nativement.
     * Réveille l'écran si nécessaire et notifie le JS pour lancer le countdown.
     */
    private void onNativeEmergencyDetected(String text, float confidence) {
        runOnUiThread(() -> {
            // Réveiller l'écran si l'app est en arrière-plan
            if (!isInForeground) {
                getWindow().addFlags(
                    WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON  |
                    WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON  |
                    WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED
                );
                webView.onResume(); // débloque l'exécution JS
            }
            // Échapper le texte pour injection JS safe
            String safe = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "");
            webView.evaluateJavascript(
                "if(window.lunaEmergencyVoiceDetected)" +
                " window.lunaEmergencyVoiceDetected('" + safe + "'," + confidence + ");",
                null
            );
        });
    }

    /**
     * Verifie si une nouvelle version est disponible sur le serveur.
     * Exige un champ apk_sha256 valide (64 hex) pour démarrer la mise à jour.
     */
    private void checkForUpdate() {
        new Thread(() -> {
            try {
                URL url = new URL(LUNA_URL + "/api/app/version");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(10000);
                conn.setReadTimeout(10000);

                if (conn.getResponseCode() == 200) {
                    BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                    StringBuilder sb = new StringBuilder();
                    String line;
                    while ((line = reader.readLine()) != null) {
                        sb.append(line);
                    }
                    reader.close();

                    JSONObject json = new JSONObject(sb.toString());
                    int serverVersionCode = json.optInt("version_code", 0);
                    String apkUrl = json.optString("apk_url", "");
                    String apkSha256 = json.optString("apk_sha256", "");

                    // Refuser toute mise à jour sans SHA-256 valide (64 hex)
                    if (serverVersionCode > CURRENT_VERSION_CODE
                            && !apkUrl.isEmpty()
                            && apkSha256.matches("[0-9a-fA-F]{64}")) {
                        downloadAndVerifyUpdate(LUNA_URL + apkUrl, apkSha256);
                    }
                }
                conn.disconnect();
            } catch (Exception e) {
                // Silencieux
            }
        }).start();
    }

    /**
     * Télécharge l'APK, vérifie SHA-256 ET signature Android, dépose dans
     * Téléchargements uniquement si les deux contrôles passent.
     */
    private void downloadAndVerifyUpdate(String apkUrl, String expectedSha256) {
        new Thread(() -> {
            // Nom unique par timestamp — évite la race condition si deux threads tournent
            java.io.File tmpFile = new java.io.File(getCacheDir(),
                "luna_update_" + System.currentTimeMillis() + ".apk");
            try {
                URL url = new URL(apkUrl);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setConnectTimeout(30000);
                conn.setReadTimeout(60000);
                if (conn.getResponseCode() != 200) { conn.disconnect(); return; }

                MessageDigest digest = MessageDigest.getInstance("SHA-256");
                try (InputStream in = conn.getInputStream();
                     FileOutputStream out = new FileOutputStream(tmpFile)) {
                    byte[] buf = new byte[8192];
                    int n;
                    while ((n = in.read(buf)) != -1) {
                        digest.update(buf, 0, n);
                        out.write(buf, 0, n);
                    }
                }
                conn.disconnect();

                // Contrôle 1 : SHA-256
                byte[] hashBytes = digest.digest();
                StringBuilder hex = new StringBuilder(64);
                for (byte b : hashBytes) hex.append(String.format("%02x", b));
                if (!hex.toString().equalsIgnoreCase(expectedSha256)) {
                    return; // APK corrompu ou falsifié
                }

                // Contrôle 2 : signature Android (même clé que l'app installée)
                if (!verifyApkSignature(tmpFile)) {
                    runOnUiThread(() -> Toast.makeText(MainActivity.this,
                        "Mise à jour rejetée : signature non reconnue.",
                        Toast.LENGTH_LONG).show());
                    return;
                }

                // Les deux contrôles OK → copier vers Téléchargements
                java.io.File destFile = new java.io.File(
                    Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS),
                    "Luna-Proprio.apk");
                try (java.io.FileInputStream fis = new java.io.FileInputStream(tmpFile);
                     FileOutputStream fos = new FileOutputStream(destFile)) {
                    byte[] buf = new byte[8192];
                    int n;
                    while ((n = fis.read(buf)) != -1) fos.write(buf, 0, n);
                }

                runOnUiThread(() -> Toast.makeText(MainActivity.this,
                    "Mise à jour Luna vérifiée ! Ouvre Téléchargements pour installer.",
                    Toast.LENGTH_LONG).show());
            } catch (Exception e) {
                // Silencieux
            } finally {
                tmpFile.delete(); // nettoyage garanti quelle que soit l'issue
            }
        }).start();
    }

    /**
     * Vérifie que l'APK téléchargé est signé avec la même clé que l'app installée.
     * Empêche l'installation d'un APK signé par une autre clé (même si SHA-256 OK).
     */
    @SuppressWarnings("deprecation")
    private boolean verifyApkSignature(java.io.File apkFile) {
        try {
            android.content.pm.PackageManager pm = getPackageManager();
            android.content.pm.PackageInfo newPkg = pm.getPackageArchiveInfo(
                apkFile.getAbsolutePath(),
                android.content.pm.PackageManager.GET_SIGNATURES);
            if (newPkg == null || newPkg.signatures == null || newPkg.signatures.length == 0) {
                return false;
            }
            android.content.pm.PackageInfo currentPkg = pm.getPackageInfo(
                getPackageName(),
                android.content.pm.PackageManager.GET_SIGNATURES);
            if (currentPkg.signatures == null || currentPkg.signatures.length == 0) {
                return false;
            }
            return currentPkg.signatures[0].equals(newPkg.signatures[0]);
        } catch (Exception e) {
            return false; // En cas de doute, refuser
        }
    }

    /** Ouvre l'appareil photo natif et renvoie l'URI au WebView (Formulaires / scan). */
    private void launchCameraCapture() {
        if (Build.VERSION.SDK_INT >= 23) {
            if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{Manifest.permission.CAMERA}, CAMERA_PERMISSION_FOR_FILE);
                return;
            }
        }
        try {
            ContentValues values = new ContentValues();
            values.put(MediaStore.Images.Media.TITLE, "Luna_scan_" + System.currentTimeMillis());
            values.put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg");
            if (Build.VERSION.SDK_INT >= 29) {
                values.put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/Luna");
                values.put(MediaStore.Images.Media.IS_PENDING, 1);
            }
            cameraOutputUri = getContentResolver().insert(
                    MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values);
            if (cameraOutputUri == null) {
                Toast.makeText(this, "Impossible d'ouvrir la camera.", Toast.LENGTH_SHORT).show();
                if (fileUploadCallback != null) {
                    fileUploadCallback.onReceiveValue(null);
                    fileUploadCallback = null;
                }
                return;
            }
            Intent cameraIntent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
            cameraIntent.putExtra(MediaStore.EXTRA_OUTPUT, cameraOutputUri);
            cameraIntent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION | Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivityForResult(cameraIntent, CAMERA_CAPTURE_REQUEST_CODE);
        } catch (Exception e) {
            Toast.makeText(this, "Erreur camera: " + e.getMessage(), Toast.LENGTH_SHORT).show();
            if (fileUploadCallback != null) {
                fileUploadCallback.onReceiveValue(null);
                fileUploadCallback = null;
            }
            cameraOutputUri = null;
        }
    }

    private void finishFileUpload(Uri[] results) {
        if (fileUploadCallback != null) {
            fileUploadCallback.onReceiveValue(results);
            fileUploadCallback = null;
        }
        cameraOutputUri = null;
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == CAMERA_CAPTURE_REQUEST_CODE) {
            Uri[] results = null;
            if (resultCode == Activity.RESULT_OK && cameraOutputUri != null) {
                if (Build.VERSION.SDK_INT >= 29) {
                    ContentValues done = new ContentValues();
                    done.put(MediaStore.Images.Media.IS_PENDING, 0);
                    try {
                        getContentResolver().update(cameraOutputUri, done, null, null);
                    } catch (Exception ignored) { }
                }
                results = new Uri[]{cameraOutputUri};
            }
            finishFileUpload(results);
            return;
        }
        if (requestCode == FILE_CHOOSER_REQUEST_CODE) {
            Uri[] results = null;
            if (resultCode == Activity.RESULT_OK) {
                if (data != null) {
                    if (data.getClipData() != null) {
                        int count = data.getClipData().getItemCount();
                        results = new Uri[count];
                        for (int i = 0; i < count; i++) {
                            results[i] = data.getClipData().getItemAt(i).getUri();
                        }
                    } else if (data.getData() != null) {
                        results = new Uri[]{data.getData()};
                    } else if (data.getDataString() != null) {
                        results = new Uri[]{Uri.parse(data.getDataString())};
                    }
                }
                if (results == null && cameraOutputUri != null) {
                    results = new Uri[]{cameraOutputUri};
                }
            }
            finishFileUpload(results);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);

        if (requestCode == PERMISSION_REQUEST_CODE && pendingPermissionRequest != null) {
            boolean allGranted = true;
            for (int result : grantResults) {
                if (result != PackageManager.PERMISSION_GRANTED) {
                    allGranted = false;
                    break;
                }
            }

            if (allGranted) {
                final PermissionRequest req = pendingPermissionRequest;
                runOnUiThread(() -> req.grant(req.getResources()));
            } else {
                final PermissionRequest req = pendingPermissionRequest;
                runOnUiThread(() -> req.deny());
            }
            pendingPermissionRequest = null;
        }

        if (requestCode == CAMERA_PERMISSION_FOR_FILE) {
            if (fileUploadCallback == null) return;
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                launchCameraCapture();
            } else {
                Toast.makeText(this, "Autorisez la camera dans Parametres > Luna > Autorisations.", Toast.LENGTH_LONG).show();
                finishFileUpload(null);
            }
        }

        if (requestCode == GUARDIAN_MIC_PERMISSION_REQUEST) {
            boolean granted = grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED;
            SharedPreferences sp = getSharedPreferences("guardian", Context.MODE_PRIVATE);
            boolean listen = sp.getBoolean("listen_enabled", false);
            boolean overlay = sp.getBoolean("overlay_enabled", false);

            if (granted && listen) {
                stopNativeSR();
                Intent svc = new Intent(MainActivity.this, GuardianService.class);
                svc.setAction(GuardianService.ACTION_START);
                svc.putExtra("status", "Protégé");
                svc.putExtra("listen", true);
                svc.putExtra("overlay", overlay);
                if (Build.VERSION.SDK_INT >= 26) startForegroundService(svc);
                else startService(svc);
                Toast.makeText(this, "Guardian écoute active.", Toast.LENGTH_SHORT).show();
            } else if (listen) {
                Toast.makeText(this, "Autorisez le micro dans Parametres > Luna > Autorisations pour activer Guardian.", Toast.LENGTH_LONG).show();
            }
        }
    }

    // ── Détection de chute ────────────────────────────────────────────

    private final SensorEventListener fallDetector = new SensorEventListener() {
        @Override
        public void onSensorChanged(SensorEvent event) {
            if (fallAlertActive) return;
            float x = event.values[0], y = event.values[1], z = event.values[2];
            float total = (float) Math.sqrt(x * x + y * y + z * z);
            long now = System.currentTimeMillis();

            if (total < FREE_FALL_THRESHOLD) {
                if (!inFreeFall) {
                    inFreeFall = true;
                    freeFallStart = now;
                }
            } else {
                if (inFreeFall) {
                    inFreeFall = false;
                    long freeFallDuration = now - freeFallStart;
                    if (freeFallDuration >= MIN_FREE_FALL_MS
                            && freeFallDuration < FALL_WINDOW_MS
                            && total > IMPACT_THRESHOLD
                            && (now - lastFallTrigger) > FALL_COOLDOWN_MS) {
                        pendingPeakG = total / SensorManager.GRAVITY_EARTH;
                        onFallDetected();
                    }
                }
            }
        }

        @Override
        public void onAccuracyChanged(Sensor sensor, int accuracy) {}
    };

    private void onFallDetected() {
        if (guardianSessionId == null || guardianSessionId.isEmpty()) return;
        fallAlertActive = true;
        lastFallTrigger = System.currentTimeMillis();

        runOnUiThread(() -> {
            // Réveiller l'écran
            getWindow().addFlags(
                WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON |
                WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON |
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED
            );
            showFallOverlay();
            // Notifier le JS pour l'UI in-app
            String sessionSafe = guardianSessionId.replaceAll("[^a-zA-Z0-9_-]", "");
            webView.evaluateJavascript(
                "if(window.lunaFallDetected) window.lunaFallDetected('" + sessionSafe + "', 30);",
                null
            );
        });

        postFallNotification();
        startFallCountdown();
    }

    private void showFallOverlay() {
        if (fallOverlay != null) return;
        float dp = getResources().getDisplayMetrics().density;

        FrameLayout overlay = new FrameLayout(this);
        overlay.setBackgroundColor(0xEE0A0A0A);

        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setGravity(Gravity.CENTER_HORIZONTAL);
        card.setBackgroundColor(0xFF111827);
        card.setPadding((int)(24*dp), (int)(32*dp), (int)(24*dp), (int)(32*dp));

        TextView tvIcon = new TextView(this);
        tvIcon.setText("⚠️");
        tvIcon.setTextSize(TypedValue.COMPLEX_UNIT_SP, 56f);
        tvIcon.setGravity(Gravity.CENTER);

        TextView tvTitle = new TextView(this);
        tvTitle.setText("Chute détectée");
        tvTitle.setTextColor(0xFFF9FAFB);
        tvTitle.setTextSize(TypedValue.COMPLEX_UNIT_SP, 22f);
        tvTitle.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        tvTitle.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams lpTitle = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        lpTitle.topMargin = (int)(12*dp);

        TextView tvSub = new TextView(this);
        tvSub.setText("Vos contacts seront alertés si vous ne répondez pas.");
        tvSub.setTextColor(0xFF9CA3AF);
        tvSub.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14f);
        tvSub.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams lpSub = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        lpSub.topMargin = (int)(8*dp);

        fallCountdownText = new TextView(this);
        fallCountdownText.setText("30");
        fallCountdownText.setTextColor(0xFFEF4444);
        fallCountdownText.setTextSize(TypedValue.COMPLEX_UNIT_SP, 64f);
        fallCountdownText.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        fallCountdownText.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams lpCount = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        lpCount.topMargin = (int)(20*dp);

        Button btnOk = new Button(this);
        btnOk.setText("Je vais bien ✓");
        btnOk.setTextColor(0xFF111827);
        btnOk.setTextSize(TypedValue.COMPLEX_UNIT_SP, 18f);
        btnOk.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        btnOk.setBackgroundColor(0xFF10B981);
        LinearLayout.LayoutParams lpOk = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, (int)(60*dp));
        lpOk.topMargin = (int)(24*dp);
        btnOk.setOnClickListener(v -> cancelFallAlertInternal(true));

        Button btnSos = new Button(this);
        btnSos.setText("SOS — Alerter maintenant");
        btnSos.setTextColor(0xFFF9FAFB);
        btnSos.setTextSize(TypedValue.COMPLEX_UNIT_SP, 15f);
        btnSos.setBackgroundColor(0xFFDC2626);
        LinearLayout.LayoutParams lpSos = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, (int)(52*dp));
        lpSos.topMargin = (int)(10*dp);
        btnSos.setOnClickListener(v -> escalateFallImmediately());

        card.addView(tvIcon);
        card.addView(tvTitle, lpTitle);
        card.addView(tvSub, lpSub);
        card.addView(fallCountdownText, lpCount);
        card.addView(btnOk, lpOk);
        card.addView(btnSos, lpSos);

        int cardW = (int)(320*dp);
        FrameLayout.LayoutParams cardLp = new FrameLayout.LayoutParams(cardW,
            FrameLayout.LayoutParams.WRAP_CONTENT, Gravity.CENTER);
        overlay.addView(card, cardLp);

        FrameLayout root = (FrameLayout) webView.getParent();
        root.addView(overlay, new FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
        fallOverlay = overlay;
    }

    private void hideFallOverlay() {
        if (fallOverlay != null) {
            FrameLayout root = (FrameLayout) webView.getParent();
            root.removeView(fallOverlay);
            fallOverlay = null;
            fallCountdownText = null;
        }
        getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
    }

    private void startFallCountdown() {
        final long[] remaining = {CONFIRMATION_MS / 1000};
        fallEscalationTask = new Runnable() {
            @Override
            public void run() {
                remaining[0]--;
                if (fallCountdownText != null) {
                    runOnUiThread(() -> fallCountdownText.setText(String.valueOf(remaining[0])));
                }
                if (remaining[0] <= 0) {
                    escalateFallImmediately();
                } else {
                    fallHandler.postDelayed(this, 1000L);
                }
            }
        };
        fallHandler.postDelayed(fallEscalationTask, 1000L);
    }

    private void cancelFallAlertInternal(boolean userConfirmedOk) {
        if (fallEscalationTask != null) {
            fallHandler.removeCallbacks(fallEscalationTask);
            fallEscalationTask = null;
        }
        fallAlertActive = false;
        runOnUiThread(() -> {
            hideFallOverlay();
            webView.evaluateJavascript("if(window.lunaFallCancelled) window.lunaFallCancelled();", null);
        });
        if (userConfirmedOk && guardianSessionId != null) {
            final String sid = guardianSessionId;
            final String token = authToken;
            new Thread(() -> {
                try {
                    URL url = new URL(LUNA_URL + "/api/guardian/verify-response/" + sid);
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("POST");
                    conn.setRequestProperty("Content-Type", "application/json");
                    if (token != null && !token.isEmpty()) {
                        conn.setRequestProperty("Authorization", "Bearer " + token);
                    }
                    conn.setDoOutput(true);
                    conn.setConnectTimeout(4000);
                    conn.setReadTimeout(4000);
                    JSONObject json = new JSONObject();
                    json.put("ok", true);
                    conn.getOutputStream().write(json.toString().getBytes("UTF-8"));
                    conn.getInputStream().close();
                    conn.disconnect();
                } catch (Exception ignored) {}
            }).start();
        }
    }

    private void escalateFallImmediately() {
        if (fallEscalationTask != null) {
            fallHandler.removeCallbacks(fallEscalationTask);
            fallEscalationTask = null;
        }
        runOnUiThread(() -> hideFallOverlay());
        fallAlertActive = false;
        sendFallToBackend();
    }

    private void sendFallToBackend() {
        if (guardianSessionId == null || guardianSessionId.isEmpty()) return;
        final String sid = guardianSessionId;
        final float peakG = pendingPeakG;
        final double lat = guardianLat;
        final double lng = guardianLng;
        final String token = authToken;
        if (token == null || token.isEmpty()) {
            sendLog("error", "Fall backend POST skipped: no auth token", "guardian/" + Build.MODEL);
            return;
        }
        new Thread(() -> {
            try {
                URL url = new URL(LUNA_URL + "/api/guardian/fall-detected/" + sid);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setRequestProperty("Authorization", "Bearer " + token);
                conn.setDoOutput(true);
                conn.setConnectTimeout(6000);
                conn.setReadTimeout(6000);
                JSONObject json = new JSONObject();
                json.put("peak_g", peakG);
                if (lat != 0.0) json.put("lat", lat);
                if (lng != 0.0) json.put("lng", lng);
                conn.getOutputStream().write(json.toString().getBytes("UTF-8"));
                int responseCode = conn.getResponseCode();
                conn.getInputStream().close();
                conn.disconnect();
                sendLog("warn", "Fall escalated to backend peak_g=" + peakG + " code=" + responseCode, "guardian/" + Build.MODEL);
            } catch (Exception e) {
                sendLog("error", "Fall backend POST failed: " + e.getMessage(), "guardian/" + Build.MODEL);
            }
        }).start();
    }

    private void postFallNotification() {
        try {
            Intent intent = new Intent(this, MainActivity.class);
            intent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
            PendingIntent pi = PendingIntent.getActivity(
                this, 0, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

            Notification.Builder builder;
            if (Build.VERSION.SDK_INT >= 26) {
                builder = new Notification.Builder(this, CHANNEL_ID);
            } else {
                builder = new Notification.Builder(this);
            }
            builder.setSmallIcon(R.drawable.ic_notif_luna)
                .setContentTitle("⚠️ Chute détectée — Luna Guardian")
                .setContentText("Appuyez si vous allez bien — alerte dans 30 secondes")
                .setAutoCancel(true)
                .setPriority(Notification.PRIORITY_MAX)
                .setContentIntent(pi);

            NotificationManager mgr = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
            if (mgr != null) mgr.notify(9001, builder.build());
        } catch (Exception ignored) {}
    }

    // ── Fin détection de chute ────────────────────────────────────────

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    /**
     * Appelé quand MainActivity reçoit un Intent entrant (singleTask).
     * Permet au bouton SOS de la notification de déclencher l'alerte depuis l'arrière-plan.
     */
    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleGuardianIntent(intent);
    }

    /** Traite les intents Guardian : bouton SOS notif, et mot-clé vocal détecté par le service. */
    private void handleGuardianIntent(Intent intent) {
        if (intent == null) return;
        // Bouton « SOS » de la notification
        if (intent.getBooleanExtra("guardian_sos", false)) {
            getWindow().addFlags(
                WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON  |
                WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON  |
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED
            );
            webView.post(() -> webView.evaluateJavascript(
                "if(typeof triggerSOS==='function'&&window.SID){triggerSOS();}" +
                "else if(typeof openSosModal==='function'){openSosModal();}",
                null
            ));
        }
        // Mot-clé d'urgence détecté par GuardianService (app éventuellement fermée)
        if (intent.hasExtra("guardian_voice_sos")) {
            String text = intent.getStringExtra("guardian_voice_sos");
            float conf  = intent.getFloatExtra("guardian_voice_conf", 0.7f);
            intent.removeExtra("guardian_voice_sos"); // éviter le re-déclenchement
            getWindow().addFlags(
                WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON  |
                WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON  |
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED
            );
            fireVoiceSosJs((text != null) ? text : "", conf, 4);
        }
    }

    /** Appelle window.lunaEmergencyVoiceDetected côté JS, avec quelques tentatives le temps
     *  que la page soit chargée (cas démarrage à froid depuis le service). */
    private void fireVoiceSosJs(String text, float conf, int attemptsLeft) {
        if (webView == null || attemptsLeft <= 0) return;
        String safe = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "");
        webView.evaluateJavascript(
            "(function(){if(window.lunaEmergencyVoiceDetected){window.lunaEmergencyVoiceDetected('"
                + safe + "'," + conf + ");return true;}return false;})();",
            value -> {
                if (!"true".equals(value)) {
                    nativeSRHandler.postDelayed(() -> fireVoiceSosJs(text, conf, attemptsLeft - 1), 1500L);
                }
            }
        );
    }

    @Override
    protected void onResume() {
        super.onResume();
        isInForeground = true;
        webView.onResume();
        sendHeartbeat();
        getWindow().getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_FULLSCREEN
        );
        // Activer la détection de chute si une session Guardian est active
        if (sensorManager != null && accelerometer != null && guardianSessionId != null) {
            sensorManager.registerListener(fallDetector, accelerometer, SensorManager.SENSOR_DELAY_GAME);
        }
        // Relancer le SR natif si Guardian vocal était actif et est mort (ex: après screen lock)
        if (nativeSREnabled && nativeSR == null && nativeSRRestartTask == null) {
            scheduleNativeSRRestart(500L);
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        isInForeground = false;
        webView.onPause();
        // Désactiver le capteur pour économiser la batterie (la détection ne fonctionne qu'au premier plan)
        if (sensorManager != null) {
            sensorManager.unregisterListener(fallDetector);
        }
    }
}
