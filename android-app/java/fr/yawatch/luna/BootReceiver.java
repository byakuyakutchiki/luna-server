package fr.yawatch.luna;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;

/**
 * Relance la présence Guardian au redémarrage du téléphone, si l'utilisateur avait
 * activé « Protection permanente ».
 *
 * IMPORTANT : l'écoute micro NE PEUT PAS être redémarrée depuis le boot (contrainte
 * Android : un FGS de type microphone ne démarre pas en arrière-plan). On restaure donc
 * uniquement la notification + la bulle ; l'écoute est réactivée à la prochaine ouverture
 * de l'app (best-effort, jamais bloquant).
 */
public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || !Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) return;
        SharedPreferences sp = context.getSharedPreferences("guardian", Context.MODE_PRIVATE);
        if (!sp.getBoolean("protection_enabled", false)) return;

        Intent svc = new Intent(context, GuardianService.class);
        svc.setAction(GuardianService.ACTION_START);
        svc.putExtra("status", "Protégé");
        svc.putExtra("listen", false); // micro impossible au boot — réactivé à l'ouverture
        svc.putExtra("overlay", sp.getBoolean("overlay_enabled", false));
        try {
            if (Build.VERSION.SDK_INT >= 26) context.startForegroundService(svc);
            else context.startService(svc);
        } catch (Exception ignored) {
            // Android peut refuser un démarrage de FGS au boot : sans gravité, réactivation à l'ouverture.
        }
    }
}
