package fr.yawatch.luna;

/**
 * Etat courant du diagnostic APK.
 *
 * Aucune logique, uniquement du stockage de donnees.
 * Mis a jour par MainActivity et par les rapports JS (LunaBridge.reportJsState).
 */
public class DiagnosticState {

    // --- WebView / page ---
    public String webViewUrl = "-";
    public String webViewPageTitle = "-";
    public boolean webViewCookiesPresent = false;
    public boolean webViewLocalStorageToken = false;

    // --- Auth ---
    public boolean nativeTokenPresent = false;
    public boolean jsTokenPresent = false;

    // --- Audio / speech ---
    public String jsListenState = "inactive";
    public boolean jsSpeechRecognitionAvailable = false;
    public String jsLastError = "-";

    // --- Localisation ---
    public String lastKnownLocation = "-";
    public long lastLocationTime = 0;
    public String locationProvider = "-";

    // --- Permissions (Android) ---
    public boolean permRecordAudio = false;
    public boolean permLocationFine = false;
    public boolean permLocationCoarse = false;
    public boolean permPostNotifications = false;
    public boolean permForegroundService = false;
    public boolean permSystemAlertWindow = false;

    // --- Service & systeme ---
    public boolean guardianServiceRunning = false;
    public boolean batteryOptimizationIgnored = false;
    public boolean isDeviceIdle = false;

    // --- Derniers appels API (codes HTTP ou erreur) ---
    public String lastApiGuardianStart = "-";
    public String lastApiGuardianSos = "-";
    public String lastApiGuardianSessions = "-";
    public String lastApiLocation = "-";

    // --- Dernier session_id ---
    public String lastGuardianSessionId = "-";

    public void resetApiState() {
        lastApiGuardianStart = "-";
        lastApiGuardianSos = "-";
        lastApiGuardianSessions = "-";
        lastApiLocation = "-";
    }
}
