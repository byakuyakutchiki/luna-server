package fr.yawatch.luna;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

/**
 * Journal chronologique des evenements diagnostiques.
 *
 * Conserve les N derniers evenements avec horodatage.
 * Thread-safe par synchronisation simple.
 */
public class DiagnosticLogger {
    private static final int MAX_EVENTS = 200;
    private final List<String> events = new ArrayList<>();
    private final SimpleDateFormat sdf = new SimpleDateFormat("HH:mm:ss.SSS", Locale.getDefault());

    public synchronized void log(String category, String message) {
        String line = sdf.format(new Date()) + " [" + category + "] " + message;
        events.add(line);
        if (events.size() > MAX_EVENTS) {
            events.remove(0);
        }
    }

    public synchronized String getLogText() {
        StringBuilder sb = new StringBuilder();
        for (String line : events) {
            sb.append(line).append("\n");
        }
        return sb.toString();
    }

    public synchronized void clear() {
        events.clear();
    }
}
