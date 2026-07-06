package fr.yawatch.luna;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONObject;

/**
 * Stockage local des tokens d'authentification Luna.
 *
 * Responsabilités strictes : stocker, lire, effacer.
 * Aucune logique réseau, aucune logique métier.
 *
 * Note : le projet est construit sans Gradle. Nous utilisons SharedPreferences
 * standard. Une migration vers EncryptedSharedPreferences sera envisagée lorsque
 * le build supportera AndroidX Security.
 */
public class AuthStorage {
    private static final String PREFS_NAME = "luna_auth";
    private static final String KEY_ACCESS = "access_token";
    private static final String KEY_REFRESH = "refresh_token";

    private final SharedPreferences prefs;

    public AuthStorage(Context context) {
        this.prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
    }

    /** Stocke les tokens d'accès et de refresh. */
    public void storeTokens(String accessToken, String refreshToken) {
        SharedPreferences.Editor editor = prefs.edit();
        editor.putString(KEY_ACCESS, accessToken);
        editor.putString(KEY_REFRESH, refreshToken);
        editor.apply();
    }

    /**
     * Retourne les tokens sous forme de JSON.
     * Format : {"access":"...","refresh":"..."}
     */
    public JSONObject getTokens() {
        JSONObject tokens = new JSONObject();
        try {
            tokens.put("access", prefs.getString(KEY_ACCESS, ""));
            tokens.put("refresh", prefs.getString(KEY_REFRESH, ""));
        } catch (Exception e) {
            // En cas d'erreur JSON improbable, retourner un objet vide.
        }
        return tokens;
    }

    /** Efface les tokens stockés. */
    public void clearTokens() {
        SharedPreferences.Editor editor = prefs.edit();
        editor.remove(KEY_ACCESS);
        editor.remove(KEY_REFRESH);
        editor.apply();
    }
}
