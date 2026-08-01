package fr.yawatch.luna;

import android.content.Context;
import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.MediaRecorder;
import android.util.Log;

import org.json.JSONObject;

import java.io.File;
import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

/**
 * Optional Guardian VOSK POC engine.
 *
 * This class intentionally uses reflection: the app still compiles and runs when
 * vosk-android.aar and the model are absent. GuardianService only starts it when
 * both are present, otherwise it falls back to Android SpeechRecognizer.
 */
final class VoskKeywordSpotter {
    interface Listener {
        void onReady(String modelPath);
        void onPartial(String text);
        void onFinal(String text);
        void onKeyword(String text, float confidence);
        void onError(String message);
        void onStopped();
    }

    private static final String TAG = "LunaVoskSpotter";
    private static final int SAMPLE_RATE = 16000;
    private static final String[] KEYWORDS = new String[]{
        "au secours", "a l aide", "à l aide", "aide moi", "aidez moi",
        "je peux pas respirer", "je ne peux pas respirer", "j ai du mal a respirer",
        "urgence", "appelle les secours"
    };

    private final Context context;
    private final Listener listener;
    private volatile boolean running;
    private Thread worker;
    private AudioRecord recorder;

    VoskKeywordSpotter(Context context, Listener listener) {
        this.context = context.getApplicationContext();
        this.listener = listener;
    }

    static boolean isRuntimeAvailable(Context context) {
        return findModelDir(context) != null && hasVoskClasses();
    }

    static String availabilityReason(Context context) {
        if (!hasVoskClasses()) return "vosk_classes_missing";
        File model = findModelDir(context);
        if (model == null) return "vosk_model_missing";
        return "available:" + model.getAbsolutePath();
    }

    private static boolean hasVoskClasses() {
        try {
            Class.forName("org.vosk.Model");
            Class.forName("org.vosk.Recognizer");
            return true;
        } catch (Throwable ignored) {
            return false;
        }
    }

    private static File findModelDir(Context context) {
        File[] candidates = new File[]{
            new File(context.getFilesDir(), "vosk-model-small-fr"),
            new File(context.getFilesDir(), "model-fr"),
            new File(context.getExternalFilesDir(null), "vosk-model-small-fr"),
            new File(context.getExternalFilesDir(null), "model-fr")
        };
        for (File f : candidates) {
            if (f != null && f.isDirectory()) {
                File conf = new File(f, "conf");
                File am = new File(f, "am");
                if (conf.exists() || am.exists()) return f;
            }
        }
        return null;
    }

    synchronized void start() {
        if (running) return;
        File modelDir = findModelDir(context);
        if (modelDir == null) {
            listener.onError("vosk_model_missing");
            return;
        }
        if (!hasVoskClasses()) {
            listener.onError("vosk_classes_missing");
            return;
        }
        running = true;
        worker = new Thread(() -> runLoop(modelDir), "LunaVoskSpotter");
        worker.start();
    }

    synchronized void stop() {
        running = false;
        if (recorder != null) {
            try { recorder.stop(); } catch (Exception ignored) {}
            try { recorder.release(); } catch (Exception ignored) {}
            recorder = null;
        }
        if (worker != null) {
            try { worker.interrupt(); } catch (Exception ignored) {}
            worker = null;
        }
    }

    private Object newRecognizer(Class<?> recCls, Class<?> modelCls, Object model) throws Exception {
        String grammar = "[\"au secours\",\"à l'aide\",\"a l'aide\",\"aide moi\",\"aidez moi\",\"j'ai du mal à respirer\",\"je peux pas respirer\",\"je ne peux pas respirer\",\"appelle les secours\",\"urgence\",\"[unk]\"]";
        try {
            Constructor<?> grammarCtor = recCls.getConstructor(modelCls, float.class, String.class);
            listener.onPartial("grammar_enabled");
            return grammarCtor.newInstance(model, (float) SAMPLE_RATE, grammar);
        } catch (NoSuchMethodException ignored) {
            Constructor<?> recCtor = recCls.getConstructor(modelCls, float.class);
            listener.onPartial("grammar_unavailable");
            return recCtor.newInstance(model, (float) SAMPLE_RATE);
        }
    }

    private void runLoop(File modelDir) {
        Object model = null;
        Object recognizer = null;
        try {
            Class<?> modelCls = Class.forName("org.vosk.Model");
            Class<?> recCls = Class.forName("org.vosk.Recognizer");
            Constructor<?> modelCtor = modelCls.getConstructor(String.class);
            model = modelCtor.newInstance(modelDir.getAbsolutePath());
            recognizer = newRecognizer(recCls, modelCls, model);
            Method acceptWaveForm = recCls.getMethod("acceptWaveForm", byte[].class, int.class);
            Method getResult = recCls.getMethod("getResult");
            Method getPartialResult = recCls.getMethod("getPartialResult");
            Method closeRecognizer = recCls.getMethod("close");
            Method closeModel = modelCls.getMethod("close");

            int min = AudioRecord.getMinBufferSize(
                SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT
            );
            int bufferSize = Math.max(min, SAMPLE_RATE);
            recorder = new AudioRecord(
                MediaRecorder.AudioSource.VOICE_RECOGNITION,
                SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                bufferSize
            );
            byte[] buffer = new byte[Math.max(4096, bufferSize / 2)];
            recorder.startRecording();
            listener.onReady(modelDir.getAbsolutePath());

            while (running && !Thread.currentThread().isInterrupted()) {
                int read = recorder.read(buffer, 0, buffer.length);
                if (read <= 0) continue;
                boolean isFinal = (Boolean) acceptWaveForm.invoke(recognizer, buffer, read);
                String json = String.valueOf((isFinal ? getResult : getPartialResult).invoke(recognizer));
                String text = extractText(json, isFinal ? "text" : "partial");
                if (text.isEmpty()) continue;
                if (isFinal) listener.onFinal(text); else listener.onPartial(text);
                if (matchesKeyword(text)) {
                    listener.onKeyword(text, 0.9f);
                }
            }

            try { closeRecognizer.invoke(recognizer); } catch (Exception ignored) {}
            try { closeModel.invoke(model); } catch (Exception ignored) {}
        } catch (Throwable t) {
            Log.e(TAG, "VOSK runtime failed", t);
            listener.onError(t.getClass().getSimpleName() + ": " + t.getMessage());
        } finally {
            stop();
            listener.onStopped();
        }
    }

    private static String extractText(String json, String key) {
        try {
            return new JSONObject(json).optString(key, "").trim();
        } catch (Exception ignored) {
            return "";
        }
    }

    private static boolean matchesKeyword(String text) {
        String n = normalize(text);
        for (String kw : KEYWORDS) {
            if (n.contains(normalize(kw))) return true;
        }
        return false;
    }

    private static String normalize(String text) {
        if (text == null) return "";
        String s = java.text.Normalizer.normalize(text, java.text.Normalizer.Form.NFD)
            .replaceAll("\\p{InCombiningDiacriticalMarks}+", "")
            .toLowerCase(Locale.FRANCE)
            .replaceAll("['‘’]", " ")
            .replaceAll("[^a-z ]", " ")
            .replaceAll("\\s+", " ")
            .trim();
        return s;
    }
}
