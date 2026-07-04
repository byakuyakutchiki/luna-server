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
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
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
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.MessageDigest;

public class MainActivity extends Activity {

    // URL backend : production Luna Beta / Guardian
    private static final String LUNA_URL = "https://luna-beta-gly3g647na-ew.a.run.app/guardian";
    private static final int PERMISSION_REQUEST_CODE = 100;
    private static final int NOTIFICATION_PERMISSION_CODE = 101;
    private static final int FILE_CHOOSER_REQUEST_CODE = 102;
    // Version lue depuis le manifeste Android (source de verite)
    private int getCurrentVersionCode() {
        try {
            return getPackageManager().getPackageInfo(getPackageName(), 0).versionCode;
        } catch (Exception e) {
            return 0;
        }
    }

    private String getCurrentVersionName() {
        try {
            return getPackageManager().getPackageInfo(getPackageName(), 0).versionName;
        } catch (Exception e) {
            return "unknown";
        }
    }
    private static final int CAMERA_PERMISSION_FOR_FILE = 103;
    private static final int CAMERA_CAPTURE_REQUEST_CODE = 104;
    private static final String CHANNEL_ID = "luna_messages";
    private WebView webView;
    private PermissionRequest pendingPermissionRequest;
    private ValueCallback<Uri[]> fileUploadCallback;
    private Uri cameraOutputUri;
    private boolean isInForeground = true;
    private int notificationId = 1000;
    private View splashView;

    // Anti-double-clic sur telechargement APK
    private String lastDownloadUrl = "";
    private long lastDownloadTime = 0;
    private static final long DOWNLOAD_DEBOUNCE_MS = 4000;

    // Version / compatibilite backend
    private String backendVersion = "unknown";
    private String backendRevision = "unknown";
    private String backendEnvironment = "unknown";
    private int backendMinVersionCode = 0;
    private int backendRecommendedVersionCode = 0;
    private boolean backendForceUpdate = false;
    private String lastTriggerStatus = "-";
    private String lastGuardianSessionId = "-";
    private boolean backendVersionChecked = false;
    private boolean backendVersionOk = true;

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

        // Bridge JavaScript -> Android pour les notifications
        webView.addJavascriptInterface(new LunaBridge(), "LunaBridge");

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
        settings.setUserAgentString(settings.getUserAgentString() + " LunaApp/" + getCurrentVersionName());

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
                    // Garde-fou anti-double-clic / anti-superposition
                    long now = System.currentTimeMillis();
                    if (url != null && url.equals(lastDownloadUrl) && (now - lastDownloadTime) < DOWNLOAD_DEBOUNCE_MS) {
                        return;
                    }
                    lastDownloadUrl = url != null ? url : "";
                    lastDownloadTime = now;

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
        sendLog("info", "APP START v" + getCurrentVersionName() + " (" + getCurrentVersionCode() + ") — " + Build.MODEL + " Android " + Build.VERSION.RELEASE, "apk/" + Build.MODEL);
        webView.loadUrl(LUNA_URL);

        // Verification compatibilite APK/backend + auto-update en arriere-plan
        checkBackendVersion();

        // Ecran debug : long-press sur le WebView affiche les infos version/backend
        webView.setOnLongClickListener(v -> {
            showDebugPanel();
            return true;
        });
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
                conn.setRequestProperty("User-Agent", "LunaApp/" + getCurrentVersionName() + " Android/" + Build.VERSION.RELEASE);
                conn.setDoOutput(true);
                conn.setConnectTimeout(4000);
                conn.setReadTimeout(4000);
                JSONObject json = new JSONObject();
                json.put("apk_version", getCurrentVersionName());
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

        @JavascriptInterface
        public String getApkVersionInfo() {
            try {
                JSONObject info = new JSONObject();
                info.put("apk_version_code", getCurrentVersionCode());
                info.put("apk_version_name", getCurrentVersionName());
                info.put("backend_url", LUNA_URL);
                info.put("backend_version", backendVersion);
                info.put("cloud_run_revision", backendRevision);
                info.put("environment", backendEnvironment);
                info.put("compatible", backendVersionOk);
                info.put("min_apk_version_code", backendMinVersionCode);
                info.put("last_trigger_status", lastTriggerStatus);
                info.put("last_guardian_session_id", lastGuardianSessionId);
                return info.toString();
            } catch (Exception e) {
                return "{}";
            }
        }

        @JavascriptInterface
        public void setLastTriggerStatus(String status) {
            lastTriggerStatus = status;
        }

        @JavascriptInterface
        public void setLastGuardianSessionId(String sessionId) {
            lastGuardianSessionId = sessionId;
        }

        @JavascriptInterface
        public void showDebugPanel() {
            runOnUiThread(MainActivity.this::showDebugPanel);
        }
    }

    /**
     * Verifie si une nouvelle version est disponible sur le serveur.
     * Exige un champ apk_sha256 valide (64 hex) pour démarrer la mise à jour.
     */
    private void checkBackendVersion() {
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
                    backendVersion = json.optString("backend_version", "unknown");
                    backendRevision = json.optString("cloud_run_revision", "unknown");
                    backendEnvironment = json.optString("environment", "unknown");
                    backendMinVersionCode = json.optInt("minimum_apk_version_code", 0);
                    backendRecommendedVersionCode = json.optInt("recommended_apk_version_code", 0);
                    backendForceUpdate = json.optBoolean("force_update", false);
                    int currentServerApkCode = json.optInt("current_apk_version_code", 0);
                    String apkDownloadUrl = json.optString("apk_download_url", "");

                    backendVersionChecked = true;
                    backendVersionOk = getCurrentVersionCode() >= backendMinVersionCode;

                    android.util.Log.i("LUNA_VERSION",
                        "[APK_VERSION_CHECK] apk_version_code=" + getCurrentVersionCode() +
                        " apk_version_name=" + getCurrentVersionName() +
                        " backend_url=" + LUNA_URL +
                        " backend_version=" + backendVersion +
                        " backend_revision=" + backendRevision +
                        " environment=" + backendEnvironment +
                        " min_apk_version_code=" + backendMinVersionCode +
                        " recommended_apk_version_code=" + backendRecommendedVersionCode +
                        " compatible=" + backendVersionOk);

                    if (backendForceUpdate || !backendVersionOk) {
                        runOnUiThread(() -> showUpdateRequiredDialog(apkDownloadUrl));
                        return;
                    }

                    String apkSha256 = json.optString("apk_sha256", "");
                    if (currentServerApkCode > getCurrentVersionCode()
                            && !apkDownloadUrl.isEmpty()
                            && apkSha256.matches("[0-9a-fA-F]{64}")) {
                        runOnUiThread(() -> showUpdateAvailableDialog(apkDownloadUrl, apkSha256));
                    }
                }
                conn.disconnect();
            } catch (Exception e) {
                android.util.Log.w("LUNA_VERSION", "[APK_VERSION_CHECK] failed: " + e.getMessage());
            }
        }).start();
    }

    private void showUpdateRequiredDialog(final String apkUrl) {
        if (isFinishing()) return;
        new android.app.AlertDialog.Builder(this)
            .setTitle("Mise a jour obligatoire")
            .setMessage("Votre version de Guardian n'est pas compatible avec le serveur actuel.\n\n" +
                        "APK : " + getCurrentVersionName() + " (" + getCurrentVersionCode() + ")\n" +
                        "Serveur : " + backendVersion + " [" + backendEnvironment + "]\n" +
                        "Revision : " + backendRevision + "\n\n" +
                        "Mise a jour obligatoire.")
            .setCancelable(false)
            .setPositiveButton("Telecharger la derniere APK", (dialog, which) -> {
                try {
                    Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(apkUrl));
                    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    startActivity(intent);
                } catch (Exception e) {
                    Toast.makeText(MainActivity.this, "Impossible d'ouvrir le lien", Toast.LENGTH_LONG).show();
                }
            })
            .show();
    }

    private void showUpdateAvailableDialog(final String apkUrl, final String expectedSha256) {
        if (isFinishing()) return;
        new android.app.AlertDialog.Builder(this)
            .setTitle("Mise a jour disponible")
            .setMessage("Une nouvelle version de Luna est disponible.\n\n" +
                        "Revision serveur : " + backendRevision)
            .setPositiveButton("Telecharger", (dialog, which) -> downloadAndVerifyUpdate(apkUrl, expectedSha256))
            .setNegativeButton("Plus tard", null)
            .show();
    }

    /**
     * Panneau debug accessible par long-press sur le WebView.
     * Affiche les infos APK/backend utiles pour les tests Guardian.
     */
    private void showDebugPanel() {
        if (isFinishing()) return;
        StringBuilder sb = new StringBuilder();
        sb.append("APK version: ").append(getCurrentVersionName()).append(" (").append(getCurrentVersionCode()).append(")\n");
        sb.append("Backend URL: ").append(LUNA_URL).append("\n");
        sb.append("Backend version: ").append(backendVersion).append("\n");
        sb.append("Cloud Run revision: ").append(backendRevision).append("\n");
        sb.append("Environment: ").append(backendEnvironment).append("\n");
        sb.append("Compatible: ").append(backendVersionOk).append("\n");
        sb.append("Min APK version: ").append(backendMinVersionCode).append("\n");
        sb.append("Dry-run (Cloud Run): ").append(backendEnvironment.contains("test") ? "true" : "unknown").append("\n");
        sb.append("Last /trigger status: ").append(lastTriggerStatus).append("\n");
        sb.append("Last guardian_session_id: ").append(lastGuardianSessionId).append("\n");

        new android.app.AlertDialog.Builder(this)
            .setTitle("Debug Guardian")
            .setMessage(sb.toString())
            .setPositiveButton("OK", null)
            .show();
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
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
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
    }

    @Override
    protected void onPause() {
        super.onPause();
        isInForeground = false;
        webView.onPause();
    }
}
