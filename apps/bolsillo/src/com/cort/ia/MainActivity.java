package com.cort.ia;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.Bundle;
import android.text.InputType;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.InputMethodManager;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;

/**
 * CORT · bolsillo.
 *
 * <p>Una sola pantalla: el HUD que corre en la PC. No hay lógica de CORT aquí — el
 * núcleo (router, memoria, Ollama, voz) vive en la PC y se alcanza por la red local.
 * Lo que sí es de esta app es la <b>dirección</b> (se guarda en SharedPreferences,
 * sobrevive a las actualizaciones), el <b>micrófono</b> (lo pide el HUD por
 * {@code getUserMedia} y sin el permiso del sistema WebView dice que no) y el
 * <b>aviso honesto</b> cuando la PC no está.
 *
 * <p>Escrito contra la plataforma sola, sin AndroidX ni Kotlin: lo mismo que
 * {@code apps/bolsillo/compilar.sh} puede compilar con {@code javac} + {@code d8}.
 */
public class MainActivity extends Activity {

    private static final String PREFS = "cort-bolsillo";
    private static final String CLAVE_URL = "url";
    private static final int PIDEN_MICRO = 41;

    private SharedPreferences prefs;
    private WebView web;
    private LinearLayout aviso;
    private TextView avisoTexto;
    private PermissionRequest microPendiente;
    private String direccionActiva = "";
    // La carga falló *esta* vez: onPageFinished sin bandera borraría el aviso de
    // un error como si la página hubiera vivido.
    private boolean falloEnEstaCarga = false;
    private AlertDialog ventanaDeDireccion;

    // --- ciclo de vida -----------------------------------------------------
    @Override
    protected void onCreate(Bundle guardado) {
        super.onCreate(guardado);
        prefs = getSharedPreferences(PREFS, Context.MODE_PRIVATE);

        web = new WebView(this);
        WebSettings ajuste = web.getSettings();
        ajuste.setJavaScriptEnabled(true);
        // El HUD guarda estado del chat y del token en sessionStorage / localStorage.
        ajuste.setDomStorageEnabled(true);
        // CORT habla solo (TTS del navegador). Con la bandera en true el sonido no
        // arranca hasta que alguien toque la pantalla, y el aviso saldría mudo.
        ajuste.setMediaPlaybackRequiresUserGesture(false);
        ajuste.setCacheMode(WebSettings.LOAD_DEFAULT);
        // No hace falta, y un WebView con acceso a archivos es superficie de ataque.
        ajuste.setAllowFileAccess(false);
        ajuste.setAllowContentAccess(false);
        web.setBackgroundColor(Color.parseColor("#04090f"));
        web.setWebViewClient(new ClienteDeNavegacion());
        web.setWebChromeClient(new ClienteDeCara());

        aviso = construirAviso();

        FrameLayout raiz = new FrameLayout(this);
        raiz.addView(web, nuevosParametros());
        raiz.addView(aviso, nuevosParametros());
        setContentView(raiz);

        String guardada = prefs.getString(CLAVE_URL, "");
        if (guardada == null || guardada.trim().isEmpty()) {
            pedirDireccion();
        } else {
            cargar(guardada);
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        // `pauseTimers` congela el reloj del WebView para todo el proceso: si no se
        // reanuda, el HUD deja de sondear /api/estado y la cara se queda quieta.
        web.resumeTimers();
        web.onResume();
    }

    @Override
    protected void onPause() {
        // Si la app se va a segundo plano con CORT hablando, el audio se corta aquí
        // en vez de seguir parloteando desde el bolsillo.
        web.pauseTimers();
        web.onPause();
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        ViewGroup padre = (ViewGroup) web.getParent();
        if (padre != null) {
            padre.removeView(web);
        }
        web.destroy();
        super.onDestroy();
    }

    // --- navegación --------------------------------------------------------
    @Override
    public void onBackPressed() {
        if (web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    public boolean onKeyDown(int codigo, KeyEvent evento) {
        if (codigo == KeyEvent.KEYCODE_MENU) {
            pedirDireccion();
            return true;
        }
        return super.onKeyDown(codigo, evento);
    }

    private FrameLayout.LayoutParams nuevosParametros() {
        return new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
    }

    private void cargar(String texto) {
        String direccion = normalizar(texto);
        if (direccion.isEmpty()) {
            mostrarAviso("Esa dirección no vale. Escribí la que imprime CORT en la PC, "
                    + "con http:// y el ?token= si lo abriste a la red.");
            return;
        }
        prefs.edit().putString(CLAVE_URL, direccion).apply();
        direccionActiva = direccion;
        falloEnEstaCarga = false;
        ocultarAviso();
        web.loadUrl(direccion);
    }

    /**
     * Acepta {@code 192.168.1.19:8765}, {@code http://x/?token=y} y {@code https://x}.
     * Sin esquema se asume http: el HUD de CORT es http en la red local.
     */
    private static String normalizar(String texto) {
        if (texto == null) {
            return "";
        }
        String limpio = texto.trim();
        if (limpio.isEmpty()) {
            return "";
        }
        if (!limpio.regionMatches(true, 0, "http://", 0, 7)
                && !limpio.regionMatches(true, 0, "https://", 0, 8)) {
            limpio = "http://" + limpio;
        }
        String minusculas = limpio.toLowerCase();
        return minusculas.startsWith("http://") || minusculas.startsWith("https://") ? limpio : "";
    }

    // --- la dirección, una sola vez y a pedido -----------------------------
    private void pedirDireccion() {
        if (ventanaDeDireccion != null && ventanaDeDireccion.isShowing()) {
            return;  // con el botón Menú apretado dos veces no se apilan dos cuadros
        }
        final EditText campo = new EditText(this);
        String actual = prefs.getString(CLAVE_URL, "");
        campo.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        campo.setText(actual == null ? "" : actual);
        campo.setHint("http://192.168.1.19:8765/?token=…");
        campo.setSelection(campo.getText().length());

        ventanaDeDireccion = new AlertDialog.Builder(this)
                .setTitle("¿Dónde está CORT?")
                .setMessage("En la PC:\n\npython3 -m cort --hud --host 0.0.0.0 --token tu-llave\n\n"
                        + "CORT imprime un enlace «desde el teléfono». Copialo acá. "
                        + "PC y teléfono tienen que estar en la misma red.")
                .setView(campo)
                .setPositiveButton("Abrir", (dialogo, cual) -> {
                    ocultarTeclado(campo);
                    cargar(campo.getText().toString());
                })
                .setNegativeButton("Cerrar", (dialogo, cual) -> {
                    if (direccionActiva.isEmpty()) {
                        finish();
                    }
                })
                .setNeutralButton("Reintentar", (dialogo, cual) -> {
                    if (!direccionActiva.isEmpty()) {
                        cargar(direccionActiva);
                    }
                })
                .setOnCancelListener(dialogo -> {
                    if (direccionActiva.isEmpty()) {
                        finish();
                    }
                })
                .show();
    }

    private void ocultarTeclado(View vista) {
        InputMethodManager sistema = (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
        if (sistema != null) {
            sistema.hideSoftInputFromWindow(vista.getWindowToken(), 0);
        }
    }

    // --- el aviso, cuando la PC no responde --------------------------------
    private LinearLayout construirAviso() {
        LinearLayout caja = new LinearLayout(this);
        caja.setOrientation(LinearLayout.VERTICAL);
        caja.setBackgroundColor(Color.parseColor("#061019"));
        int margen = (int) (28 * getResources().getDisplayMetrics().density);
        caja.setPadding(margen, margen, margen, margen);
        caja.setVisibility(View.GONE);
        caja.setClickable(true);

        avisoTexto = new TextView(this);
        avisoTexto.setTextColor(Color.parseColor("#d7f3fb"));
        avisoTexto.setTextSize(15f);
        avisoTexto.setLineSpacing(0f, 1.35f);
        caja.addView(avisoTexto, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        Button reintentar = new Button(this);
        reintentar.setText("Reintentar");
        reintentar.setOnClickListener(v -> {
            if (direccionActiva.isEmpty()) {
                pedirDireccion();
            } else {
                cargar(direccionActiva);
            }
        });
        caja.addView(reintentar, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        Button cambiar = new Button(this);
        cambiar.setText("Cambiar dirección");
        cambiar.setOnClickListener(v -> pedirDireccion());
        caja.addView(cambiar, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        TextView version = new TextView(this);
        version.setTextColor(Color.parseColor("#5c8496"));
        version.setTextSize(11f);
        version.setText("CORT · bolsillo " + versionDeLaApp());
        LinearLayout.LayoutParams parametrosVersion = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        parametrosVersion.topMargin = margen / 2;
        caja.addView(version, parametrosVersion);
        return caja;
    }

    /** La versión real del APK, leída del paquete: no la que alguien escribió a mano. */
    private String versionDeLaApp() {
        try {
            String nombre = getPackageManager().getPackageInfo(getPackageName(), 0).versionName;
            return nombre == null ? "" : nombre;
        } catch (Exception e) {
            return "";
        }
    }

    private void mostrarAviso(String texto) {
        if (avisoTexto != null) {
            avisoTexto.setText(texto);
        }
        aviso.setVisibility(View.VISIBLE);
        aviso.bringToFront();
    }

    private void ocultarAviso() {
        aviso.setVisibility(View.GONE);
    }

    // --- el WebView escucha, y pide el micrófono si hace falta -------------
    private class ClienteDeCara extends WebChromeClient {
        @Override
        public void onPermissionRequest(final PermissionRequest solicitud) {
            boolean quiereMicro = false;
            for (String recurso : solicitud.getResources()) {
                if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(recurso)) {
                    quiereMicro = true;
                }
            }
            if (quiereMicro && chequeoPermiso() != PackageManager.PERMISSION_GRANTED) {
                // Android no deja conceder el micrófono del sistema desde acá: se lo
                // pregunta al usuario y la solicitud queda en espera.
                microPendiente = solicitud;
                requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, PIDEN_MICRO);
                return;
            }
            solicitud.grant(solicitud.getResources());
        }
    }

    private int chequeoPermiso() {
        return checkSelfPermission(Manifest.permission.RECORD_AUDIO);
    }

    @Override
    public void onRequestPermissionsResult(int peticion, String[] permisos, int[] resultados) {
        super.onRequestPermissionsResult(peticion, permisos, resultados);
        if (peticion != PIDEN_MICRO || microPendiente == null) {
            return;
        }
        boolean concedido = resultados.length > 0 && resultados[0] == PackageManager.PERMISSION_GRANTED;
        if (concedido) {
            microPendiente.grant(microPendiente.getResources());
        } else {
            microPendiente.deny();
            mostrarAviso("Sin permiso de micrófono CORT te oye poco. Concedelo en "
                    + "Ajustes ▸ Apps ▸ CORT ▸ Permisos, o escribí en el chat.");
        }
        microPendiente = null;
    }

    // --- cuándo la PC no está ---------------------------------------------
    private class ClienteDeNavegacion extends WebViewClient {
        @Override
        public void onPageFinished(WebView vista, String url) {
            // El WebView normaliza la URL (le agrega la barra final), así que no se
            // compara contra `direccionActiva`: se mira si *esta* carga dio error.
            if (!falloEnEstaCarga) {
                ocultarAviso();
            }
        }

        @Override
        public void onReceivedError(WebView vista, WebResourceRequest peticion, WebResourceError error) {
            if (peticion.isForMainFrame()) {
                mostrarError(peticion.getUrl().toString(), error.getDescription().toString());
            }
        }

        @Override
        @SuppressWarnings("deprecation")
        public void onReceivedError(WebView vista, int codigo, String descripcion, String url) {
            if (url != null && url.equals(direccionActiva)) {
                mostrarError(url, descripcion);
            }
        }

        private void mostrarError(String url, String descripcion) {
            falloEnEstaCarga = true;
            mostrarAviso("No encuentro CORT en " + url + ".\n\n"
                    + (descripcion == null || descripcion.isEmpty() ? "" : descripcion + "\n\n")
                    + "Mirá que la PC esté despierta, que el HUD esté corriendo con "
                    + "--host 0.0.0.0, y que el teléfono esté en la misma red.");
        }
    }
}
