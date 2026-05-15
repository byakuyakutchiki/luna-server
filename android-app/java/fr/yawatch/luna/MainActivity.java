package fr.yawatch.luna;

import android.Manifest;
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
import android.webkit.ValueCallback;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.DownloadListener;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.URLUtil;
import android.widget.Toast;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class MainActivity extends Activity {

    private static final String LUNA_URL = "https://luna-beta-674304336025.europe-west1.run.app";
    private static final int PERMISSION_REQUEST_CODE = 100;
    private static final int NOTIFICATION_PERMISSION_CODE = 101;
    private static final int FILE_CHOOSER_REQUEST_CODE = 102;
    private static final String CURRENT_VERSION = "2.7";
    private static final int CURRENT_VERSION_CODE = 18;
    private static final int CAMERA_PERMISSION_FOR_FILE = 103;
    private static final int CAMERA_CAPTURE_REQUEST_CODE = 104;
    private static final String CHANNEL_ID = "luna_messages";
    private WebView webView;
    private PermissionRequest pendingPermissionRequest;
    private ValueCallback<Uri[]> fileUploadCallback;
    private Uri cameraOutputUri;
    private boolean isInForeground = true;
    private int notificationId = 1000;

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

        // WebView
        webView = new WebView(this);
        setContentView(webView);

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

        // Geolocation support
        settings.setGeolocationEnabled(true);

        // Version dans le User-Agent pour auto-update
        settings.setUserAgentString(settings.getUserAgentString() + " LunaApp/" + CURRENT_VERSION);

        // Cookies (pour la session JWT)
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true);

        // WebChromeClient: gere les permissions camera/micro/geoloc
        webView.setWebChromeClient(new WebChromeClient() {
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
            public void onPermissionRequest(final PermissionRequest request) {
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

        // Garde la navigation dans le WebView
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                return false;
            }
        });

        // Vider le cache avant de charger (force la mise a jour)
        webView.clearCache(true);

        // Charge Luna
        webView.loadUrl(LUNA_URL);

        // Verification auto-update en arriere-plan
        checkForUpdate();
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
    }

    /**
     * Verifie si une nouvelle version est disponible sur le serveur.
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

                    if (serverVersionCode > CURRENT_VERSION_CODE && !apkUrl.isEmpty()) {
                        String fullApkUrl = LUNA_URL + apkUrl;
                        runOnUiThread(() -> triggerUpdate(fullApkUrl));
                    }
                }
                conn.disconnect();
            } catch (Exception e) {
                // Silencieux
            }
        }).start();
    }

    private void triggerUpdate(String apkUrl) {
        try {
            DownloadManager.Request request = new DownloadManager.Request(Uri.parse(apkUrl));
            request.setTitle("Luna - Mise a jour");
            request.setDescription("Nouvelle version disponible !");
            request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, "Luna-Proprio.apk");
            request.setMimeType("application/vnd.android.package-archive");

            DownloadManager dm = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
            if (dm != null) {
                dm.enqueue(request);
                Toast.makeText(this, "Mise a jour Luna disponible ! Ouvre la notification pour installer.", Toast.LENGTH_LONG).show();
            }
        } catch (Exception e) {
            // Silencieux
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
