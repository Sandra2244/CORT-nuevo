package com.cort.ia;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.widget.Toast;

/**
 * CORT · «Leer con CORT».
 *
 * <p>La puerta que usa Android para meter texto de otras apps: aparece en el menú de
 * selección ({@code ACTION_PROCESS_TEXT}) y en «Compartir» ({@code ACTION_SEND}). No
 * dibuja nada: toma el texto, lo entrega al {@link LectorService} y se cierra, para no
 * tapar la app donde Sandra estaba leyendo.
 *
 * <p>En Android 13+ la notificación del lector solo se ve si se concede
 * {@code POST_NOTIFICATIONS}. Ese diálogo necesita una actividad viva delante, así que el
 * arranque del servicio se hace <em>después</em> de responder: si se arrancara antes y esta
 * pantalla se cerrara, el diálogo se iría con ella y los controles de pausa nunca
 * aparecerían.
 *
 * <p>Si el texto llega vacío lo dice en vez de abrir un servicio mudo. Ese caso existe de
 * verdad: algunas apps mandan el intent sin el extra.
 */
public class LeerActivity extends Activity {

    private static final int PIDEN_NOTIFICACIONES = 52;

    private String texto;
    private String titulo;

    @Override
    protected void onCreate(Bundle guardado) {
        super.onCreate(guardado);

        Intent origen = getIntent();
        texto = textoDe(origen);
        if (texto.trim().isEmpty()) {
            Toast.makeText(this, "No llegó texto. Seleccioná un párrafo y elegí "
                    + "«Leer con CORT», o compartilo desde la app.", Toast.LENGTH_LONG).show();
            cerrar();
            return;
        }
        titulo = tituloDe(origen);

        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},
                    PIDEN_NOTIFICACIONES);
            return;
        }
        leer();
    }

    @Override
    public void onRequestPermissionsResult(int codigo, String[] permisos, int[] resultados) {
        super.onRequestPermissionsResult(codigo, permisos, resultados);
        if (codigo == PIDEN_NOTIFICACIONES) {
            // Se lea como se lea la respuesta, se lee: negar solo quita los botones de la
            // notificación, no la voz.
            leer();
        }
    }

    private void leer() {
        Intent servicio = new Intent(this, LectorService.class)
                .setAction(LectorService.ACCION_LEER)
                .putExtra(LectorService.EXTRA_TEXTO, texto)
                .putExtra(LectorService.EXTRA_TITULO, titulo);
        startForegroundService(servicio);
        Toast.makeText(this, "CORT leyendo…", Toast.LENGTH_SHORT).show();
        cerrar();
    }

    private void cerrar() {
        finishAndRemoveTask();
    }

    private String textoDe(Intent intencion) {
        if (intencion == null) {
            return "";
        }
        CharSequence elegido = null;
        String accion = intencion.getAction();
        if (Intent.ACTION_PROCESS_TEXT.equals(accion)) {
            elegido = intencion.getCharSequenceExtra(Intent.EXTRA_PROCESS_TEXT);
        } else if (Intent.ACTION_SEND.equals(accion)) {
            elegido = intencion.getCharSequenceExtra(Intent.EXTRA_TEXT);
        }
        if (elegido == null) {
            elegido = intencion.getCharSequenceExtra(LectorService.EXTRA_TEXTO);
        }
        return elegido == null ? "" : elegido.toString();
    }

    private String tituloDe(Intent intencion) {
        if (intencion == null) {
            return "Lo que seleccionaste";
        }
        String asunto = intencion.getStringExtra(Intent.EXTRA_SUBJECT);
        if (asunto != null && asunto.trim().length() > 0) {
            return asunto.trim();
        }
        // Hasta 60 caracteres del texto sirven de título reconocible; más largo se corta
        // en la notificación y no aporta.
        String base = texto.trim().replaceAll("\\s+", " ");
        if (base.isEmpty()) {
            return "Lo que seleccionaste";
        }
        return base.length() > 60 ? base.substring(0, 60) + "…" : base;
    }
}
