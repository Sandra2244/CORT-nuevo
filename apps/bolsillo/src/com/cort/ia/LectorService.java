package com.cort.ia;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.media.MediaMetadata;
import android.media.session.MediaSession;
import android.media.session.PlaybackState;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * CORT · lectura en voz alta.
 *
 * <p>Un servicio en primer plano que lee un texto por trozos y sobrevive a que se apague
 * la pantalla. Es la pieza que Android no trae: {@link TextToSpeech} habla, pero no tiene
 * pausa, ni cola por frases, ni controles en los audífonos. Aquí sí.
 *
 * <p>El troceo es por frase, no por carácter: si se corta a mitad de palabra, la voz suena
 * entrecortada y no se puede pausar en un punto que se entienda. Cada trozo se habla con
 * {@code QUEUE_FLUSH} y el siguiente arranca en {@code onDone}, así la pausa es exacta y el
 * índice sobrevive a la muerte del servicio.
 *
 * <p>Sin AndroidX: {@link MediaSession} y {@code Notification.MediaStyle} son de la
 * plataforma desde Android 5, y la app se compila con {@code javac} + {@code d8}.
 *
 * <p>La voz de este primer paso es la del sistema. Piper entra después de que la tubería
 * completa esté probada en el teléfono, para no depurar dos cosas a la vez.
 */
public class LectorService extends Service {

    // Acciones que llegan por Intent (notificación, audífonos o la actividad).
    public static final String ACCION_LEER = "com.cort.ia.LEER";
    public static final String ACCION_PAUSAR = "com.cort.ia.PAUSAR";
    public static final String ACCION_REANUDAR = "com.cort.ia.REANUDAR";
    public static final String ACCION_ANTERIOR = "com.cort.ia.ANTERIOR";
    public static final String ACCION_SIGUIENTE = "com.cort.ia.SIGUIENTE";
    public static final String ACCION_PARAR = "com.cort.ia.PARAR";
    public static final String EXTRA_TEXTO = "texto";
    public static final String EXTRA_TITULO = "titulo";

    private static final String CANAL = "cort-lector";
    private static final int ID_NOTIFICACION = 4101;
    /** Un trozo largo tarda demasiado en arrancar y la pausa se siente muerta. */
    private static final int TROZO_MAX = 320;
    private static final String PREFS = "cort-lector";
    private static final String CLAVE_HUELLA = "huella";
    private static final String CLAVE_TROZO = "trozo";

    private final List<String> trozos = new ArrayList<>();
    private final Handler principal = new Handler(Looper.getMainLooper());
    private SharedPreferences prefs;
    private MediaSession sesion;
    private TextToSpeech voz;
    private boolean vozLista = false;
    private boolean vozFallida = false;
    private boolean pausado = false;
    private int indice = 0;
    private int huella = 0;
    private String titulo = "Lo que seleccionaste";
    private String idiomaPedido = "es_ES";

    // --- ciclo de vida -----------------------------------------------------

    @Override
    public void onCreate() {
        super.onCreate();
        prefs = getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        crearCanal();
        prepararSesion();
        prepararVoz();
    }

    @Override
    public int onStartCommand(Intent intencion, int banderas, int arranques) {
        String accion = intencion == null ? null : intencion.getAction();
        if (accion == null) {
            // Sin acción no hay nada que reanudar. Igual hay que entrar en primer plano:
            // Android mata el proceso si un servicio arrancado con startForegroundService
            // no llama a startForeground en unos segundos.
            subirANotificacion(true);
            stopSelf();
            return START_NOT_STICKY;
        }
        switch (accion) {
            case ACCION_LEER:
                empezar(intencion.getStringExtra(EXTRA_TEXTO),
                        intencion.getStringExtra(EXTRA_TITULO));
                break;
            case ACCION_PAUSAR:
                pausar();
                break;
            case ACCION_REANUDAR:
                reanudar();
                break;
            case ACCION_ANTERIOR:
                mover(-1);
                break;
            case ACCION_SIGUIENTE:
                mover(1);
                break;
            case ACCION_PARAR:
                parar();
                break;
            default:
                break;
        }
        return START_NOT_STICKY;
    }

    @Override
    public IBinder onBind(Intent intencion) {
        return null;
    }

    @Override
    public void onDestroy() {
        if (voz != null) {
            voz.stop();
            voz.shutdown();
            voz = null;
        }
        if (sesion != null) {
            sesion.setActive(false);
            sesion.release();
            sesion = null;
        }
        super.onDestroy();
    }

    // --- la lectura --------------------------------------------------------

    private void empezar(String texto, String tituloPedido) {
        // Antes de cualquier validación: Android da cinco segundos para entrar en primer
        // plano y un texto vacío también tiene que responder con la notificación puesta.
        // Lo viejo se limpia primero para que esa notificación no muestre el texto
        // anterior mientras se valida el nuevo.
        trozos.clear();
        indice = 0;
        pausado = false;
        titulo = (tituloPedido == null || tituloPedido.trim().isEmpty())
                ? "Lo que seleccionaste" : tituloPedido.trim();
        subirANotificacion(true);

        if (texto == null || texto.trim().isEmpty()) {
            avisar("No hay texto para leer.");
            parar();
            return;
        }

        trozos.addAll(trocear(texto));
        if (trozos.isEmpty()) {
            avisar("El texto llegó vacío. Probá seleccionar otra vez.");
            parar();
            return;
        }

        huella = texto.hashCode();
        int guardado = prefs.getInt(CLAVE_TROZO, 0);
        boolean reanuda = prefs.getInt(CLAVE_HUELLA, 0) == huella
                && guardado > 0 && guardado < trozos.size();
        indice = reanuda ? guardado : 0;
        if (!reanuda) {
            prefs.edit().putInt(CLAVE_HUELLA, huella).putInt(CLAVE_TROZO, 0).apply();
        }

        subirANotificacion(true);
        if (reanuda) {
            avisar("Sigo desde el trozo " + (indice + 1) + " de " + trozos.size() + ".");
        }
        hablarActual();
    }

    private void hablarActual() {
        if (indice < 0 || indice >= trozos.size()) {
            terminar();
            return;
        }
        String trozo = trozos.get(indice);
        prefs.edit().putInt(CLAVE_TROZO, indice).apply();
        actualizarEstado(PlaybackState.STATE_PLAYING);
        actualizarNotificacion();
        if (!vozLista) {
            // La voz tarda en inicializar; cuando esté, retoma este mismo trozo.
            return;
        }
        Bundle parametros = new Bundle();
        parametros.putFloat(TextToSpeech.Engine.KEY_PARAM_VOLUME, 1.0f);
        voz.speak(trozo, TextToSpeech.QUEUE_FLUSH, parametros, "trozo-" + indice + "-" + huella);
    }

    private void pausar() {
        if (trozos.isEmpty()) {
            return;
        }
        pausado = true;
        if (voz != null) {
            voz.stop();
        }
        actualizarEstado(PlaybackState.STATE_PAUSED);
        actualizarNotificacion();
    }

    private void reanudar() {
        if (trozos.isEmpty()) {
            return;
        }
        pausado = false;
        hablarActual();
    }

    private void mover(int paso) {
        if (trozos.isEmpty()) {
            return;
        }
        indice = Math.max(0, Math.min(trozos.size() - 1, indice + paso));
        if (voz != null) {
            voz.stop();
        }
        if (pausado) {
            actualizarNotificacion();
            return;
        }
        hablarActual();
    }

    private void terminar() {
        actualizarEstado(PlaybackState.STATE_STOPPED);
        prefs.edit().putInt(CLAVE_TROZO, 0).remove(CLAVE_HUELLA).apply();
        parar();
    }

    private void parar() {
        if (voz != null) {
            voz.stop();
        }
        if (sesion != null) {
            sesion.setActive(false);
        }
        stopForeground(STOP_FOREGROUND_REMOVE);
        stopSelf();
    }

    // --- troceo ------------------------------------------------------------

    /**
     * Parte el texto en trozos legibles: primero por frase, después se juntan las frases
     * cortas hasta {@link #TROZO_MAX}. Un párrafo sin puntuación se corta por palabras,
     * que es lo único honesto que se puede hacer sin partir una palabra al medio.
     */
    static List<String> trocear(String texto) {
        String limpio = texto.replace('\r', ' ').replace('\n', ' ')
                .replaceAll("[ \\t]+", " ").trim();
        List<String> frases = new ArrayList<>();
        StringBuilder actual = new StringBuilder();
        for (int i = 0; i < limpio.length(); i++) {
            char c = limpio.charAt(i);
            actual.append(c);
            boolean fin = c == '.' || c == '!' || c == '?' || c == ';' || c == ':';
            boolean corte = i + 1 >= limpio.length() || limpio.charAt(i + 1) == ' ';
            if (fin && corte) {
                frases.add(actual.toString().trim());
                actual.setLength(0);
            }
        }
        if (actual.toString().trim().length() > 0) {
            frases.add(actual.toString().trim());
        }

        List<String> trozos = new ArrayList<>();
        StringBuilder junto = new StringBuilder();
        for (String frase : frases) {
            if (frase.isEmpty()) {
                continue;
            }
            if (frase.length() > TROZO_MAX) {
                if (junto.length() > 0) {
                    trozos.add(junto.toString());
                    junto.setLength(0);
                }
                trozos.addAll(porPalabras(frase));
                continue;
            }
            if (junto.length() > 0 && junto.length() + 1 + frase.length() > TROZO_MAX) {
                trozos.add(junto.toString());
                junto.setLength(0);
            }
            if (junto.length() > 0) {
                junto.append(' ');
            }
            junto.append(frase);
        }
        if (junto.length() > 0) {
            trozos.add(junto.toString());
        }
        return trozos;
    }

    private static List<String> porPalabras(String frase) {
        List<String> partes = new ArrayList<>();
        StringBuilder actual = new StringBuilder();
        for (String palabra : frase.split(" ")) {
            if (actual.length() > 0 && actual.length() + 1 + palabra.length() > TROZO_MAX) {
                partes.add(actual.toString());
                actual.setLength(0);
            }
            if (actual.length() > 0) {
                actual.append(' ');
            }
            actual.append(palabra);
        }
        if (actual.length() > 0) {
            partes.add(actual.toString());
        }
        return partes;
    }

    // --- voz ---------------------------------------------------------------

    private void prepararVoz() {
        voz = new TextToSpeech(this, estado -> principal.post(() -> {
            // El servicio pudo morir con la voz todavía arrancando: `onDestroy` ya la
            // soltó y este callback llegaría a un campo nulo.
            if (voz == null) {
                return;
            }
            if (estado != TextToSpeech.SUCCESS) {
                vozFallida = true;
                avisar("Este teléfono no tiene una voz en español instalada.");
                actualizarNotificacion();
                return;
            }
            int resultado = voz.setLanguage(new Locale("es", "ES"));
            if (resultado == TextToSpeech.LANG_MISSING_DATA
                    || resultado == TextToSpeech.LANG_NOT_SUPPORTED) {
                resultado = voz.setLanguage(new Locale("es", "MX"));
                idiomaPedido = "es_MX";
            }
            if (resultado == TextToSpeech.LANG_MISSING_DATA
                    || resultado == TextToSpeech.LANG_NOT_SUPPORTED) {
                vozFallida = true;
                avisar("Falta la voz en español. Ajustes ▸ Administración general ▸ "
                        + "Salida de texto a voz ▸ instalar español.");
                actualizarNotificacion();
                return;
            }
            voz.setSpeechRate(0.98f);
            voz.setOnUtteranceProgressListener(new Progreso());
            vozLista = true;
            // Si el texto llegó antes que la voz, arranca ahora.
            if (!trozos.isEmpty() && !pausado) {
                hablarActual();
            }
        }));
    }

    private class Progreso extends UtteranceProgressListener {
        @Override
        public void onStart(String id) {
            // Nada: el estado ya se marcó al hablar.
        }

        @Override
        public void onDone(String id) {
            principal.post(() -> {
                if (pausado) {
                    return;
                }
                indice++;
                if (indice >= trozos.size()) {
                    terminar();
                } else {
                    hablarActual();
                }
            });
        }

        @Override
        public void onError(String id) {
            principal.post(() -> {
                // Un trozo que falla no puede colgar la lectura: se salta y se sigue.
                indice++;
                if (indice >= trozos.size()) {
                    avisar("La voz se detuvo: no pudo leer el final del texto.");
                    terminar();
                } else {
                    hablarActual();
                }
            });
        }
    }

    // --- notificación y sesión --------------------------------------------

    private void crearCanal() {
        NotificationManager gestor = getSystemService(NotificationManager.class);
        if (gestor == null) {
            return;
        }
        NotificationChannel canal = new NotificationChannel(
                CANAL, "CORT · lectura en voz alta", NotificationManager.IMPORTANCE_LOW);
        canal.setDescription("Controles de la lectura mientras CORT te lee.");
        canal.setShowBadge(false);
        gestor.createNotificationChannel(canal);
    }

    private void subirANotificacion(boolean arrancarEnPrimerPlano) {
        Notification notificacion = construirNotificacion();
        if (arrancarEnPrimerPlano) {
            startForeground(ID_NOTIFICACION, notificacion);
        } else {
            NotificationManager gestor = getSystemService(NotificationManager.class);
            if (gestor != null) {
                gestor.notify(ID_NOTIFICACION, notificacion);
            }
        }
    }

    private void actualizarNotificacion() {
        if (trozos.isEmpty()) {
            return;
        }
        subirANotificacion(false);
    }

    private Notification construirNotificacion() {
        String detalle;
        if (vozFallida) {
            detalle = "Sin voz en español instalada";
        } else if (trozos.isEmpty()) {
            detalle = "Preparando la lectura…";
        } else {
            String vista = trozos.get(Math.min(indice, trozos.size() - 1));
            if (vista.length() > 90) {
                vista = vista.substring(0, 90) + "…";
            }
            detalle = (indice + 1) + " de " + trozos.size() + " · " + vista;
        }

        Notification.Builder constructor = new Notification.Builder(this, CANAL)
                .setSmallIcon(getApplicationInfo().icon)
                .setContentTitle(titulo)
                .setContentText(detalle)
                .setStyle(new Notification.BigTextStyle().bigText(detalle))
                .setOngoing(!trozos.isEmpty())
                .setShowWhen(false)
                .setOnlyAlertOnce(true)
                .setVisibility(Notification.VISIBILITY_PUBLIC);

        if (!trozos.isEmpty()) {
            constructor.addAction(accion(android.R.drawable.ic_media_previous,
                    "Anterior", ACCION_ANTERIOR, 11));
            if (pausado) {
                constructor.addAction(accion(android.R.drawable.ic_media_play,
                        "Reanudar", ACCION_REANUDAR, 12));
            } else {
                constructor.addAction(accion(android.R.drawable.ic_media_pause,
                        "Pausar", ACCION_PAUSAR, 13));
            }
            constructor.addAction(accion(android.R.drawable.ic_media_next,
                    "Siguiente", ACCION_SIGUIENTE, 14));
            constructor.addAction(accion(android.R.drawable.ic_delete,
                    "Detener", ACCION_PARAR, 15));
            Notification.MediaStyle estilo = new Notification.MediaStyle()
                    .setShowActionsInCompactView(0, 1, 2);
            if (sesion != null) {
                estilo.setMediaSession(sesion.getSessionToken());
            }
            constructor.setStyle(estilo);
        }
        return constructor.build();
    }

    private Notification.Action accion(int icono, String tituloAccion, String accion, int codigo) {
        Intent intencion = new Intent(this, LectorService.class).setAction(accion);
        PendingIntent pendiente = PendingIntent.getService(this, codigo, intencion,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        return new Notification.Action.Builder(icono, tituloAccion, pendiente).build();
    }

    private void prepararSesion() {
        sesion = new MediaSession(this, "CORT-lectura");
        sesion.setFlags(MediaSession.FLAG_HANDLES_MEDIA_BUTTONS
                | MediaSession.FLAG_HANDLES_TRANSPORT_CONTROLS);
        sesion.setCallback(new MediaSession.Callback() {
            @Override
            public void onPlay() {
                reanudar();
            }

            @Override
            public void onPause() {
                pausar();
            }

            @Override
            public void onStop() {
                parar();
            }

            @Override
            public void onSkipToNext() {
                mover(1);
            }

            @Override
            public void onSkipToPrevious() {
                mover(-1);
            }
        });
        actualizarEstado(PlaybackState.STATE_NONE);
        sesion.setActive(true);
    }

    private void actualizarEstado(int estado) {
        if (sesion == null) {
            return;
        }
        PlaybackState.Builder constructor = new PlaybackState.Builder()
                .setActions(PlaybackState.ACTION_PLAY | PlaybackState.ACTION_PAUSE
                        | PlaybackState.ACTION_PLAY_PAUSE | PlaybackState.ACTION_STOP
                        | PlaybackState.ACTION_SKIP_TO_NEXT
                        | PlaybackState.ACTION_SKIP_TO_PREVIOUS)
                .setState(estado, indice, 1.0f);
        sesion.setPlaybackState(constructor.build());
        MediaMetadata.Builder datos = new MediaMetadata.Builder()
                .putString(MediaMetadata.METADATA_KEY_TITLE, titulo)
                .putString(MediaMetadata.METADATA_KEY_ARTIST, "CORT · lectura");
        if (!trozos.isEmpty()) {
            datos.putLong(MediaMetadata.METADATA_KEY_TRACK_NUMBER, indice + 1);
            datos.putLong(MediaMetadata.METADATA_KEY_NUM_TRACKS, trozos.size());
        }
        sesion.setMetadata(datos.build());
    }

    private void avisar(String texto) {
        android.widget.Toast.makeText(this, texto, android.widget.Toast.LENGTH_LONG).show();
    }
}
