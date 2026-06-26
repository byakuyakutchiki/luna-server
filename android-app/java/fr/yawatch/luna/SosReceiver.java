package fr.yawatch.luna;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/**
 * SosReceiver — reçoit le broadcast du bouton "🆘 Urgence SOS" de la notification Guardian.
 *
 * Amène MainActivity au premier plan avec un flag guardian_sos=true.
 * MainActivity.onNewIntent() détecte ce flag et déclenche triggerSOS() côté JS.
 */
public class SosReceiver extends BroadcastReceiver {

    @Override
    public void onReceive(Context context, Intent intent) {
        Intent launchIntent = new Intent(context, MainActivity.class);
        launchIntent.setFlags(
            Intent.FLAG_ACTIVITY_NEW_TASK      |
            Intent.FLAG_ACTIVITY_SINGLE_TOP    |
            Intent.FLAG_ACTIVITY_CLEAR_TOP
        );
        launchIntent.putExtra("guardian_sos", true);
        context.startActivity(launchIntent);
    }
}
