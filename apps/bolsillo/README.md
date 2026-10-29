# CORT · bolsillo (Android)

Dos cosas en un mismo APK: **una ventana al HUD que corre en la PC** y, desde 3.1.0,
**un lector en voz alta** que funciona sin la PC ni la red.

Aquí no hay cerebro — el núcleo (router en español, memoria SQLite, Ollama, voz) vive en
la PC y se alcanza por la red local. Lo único que guarda esta app es la dirección de esa
PC y el trozo por el que iba la lectura.

Por qué así y no un CORT completo dentro del teléfono: el portátil de Sandra tiene el
cerebro y los modelos; el teléfono tiene la pantalla y el micrófono. Repetir el núcleo
en el APK significaba mantener dos CORT. Con este diseño, lo que se arregla en la PC se
arregla en el teléfono el mismo día.

## Qué hace

* Abre la URL del HUD en un `WebView` a pantalla completa.
* Recuerda la dirección en `SharedPreferences` (`cort-bolsillo` ▸ `url`); sobrevive a las
  actualizaciones porque la firma no cambia.
* Pide el **micrófono** la primera vez que la página lo pide (`getUserMedia` desde el
  HUD → permiso del sistema). Sin él, la escucha no funciona dentro de la app.
* Si la PC no está, muestra un aviso honesto con dos botones: *Reintentar* y *Cambiar
  dirección*. Nunca finge que hay conexión.
* Volver: atrás en el historial de la página; con el historial vacío, sale de la app.
* Menú del sistema (o *Cambiar dirección* en el aviso) abre de nuevo el cuadro de
  dirección.
* **«Leer con CORT»**: lee en voz alta un texto seleccionado en cualquier app (ver abajo).

No usa AndroidX ni Kotlin ni Gradle: `Activity`, `Service` y `TextToSpeech` de la
plataforma, `javac` y `d8`.

## Leer con CORT (2.0.1)

Es el primer incremento del plan [`docs/ARQUITECTURA-2.0.md`](../../docs/ARQUITECTURA-2.0.md):
el modo estudio. No necesita la PC, ni Tailscale, ni Ollama — habla el teléfono.

Cómo se usa, en el teléfono:

1. En cualquier app (navegador, PDF, WhatsApp), mantener pulsado hasta **seleccionar un
   párrafo**.
2. En el menú de selección (los tres puntos) elegir **«Leer con CORT»**. También aparece
   en *Compartir* como destino de texto.
3. CORT empieza a leer. La notificación trae **anterior · pausa · siguiente · detener**, y
   los mismos botones responden desde los audífonos.

Lo que hay dentro:

* `LeerActivity` — la puerta. Toma el texto de `ACTION_PROCESS_TEXT` (menú de selección) o
  de `ACTION_SEND` (compartir), pide `POST_NOTIFICATIONS` en Android 13+ y arranca el
  servicio. No dibuja pantalla: se cierra para no tapar lo que se estaba leyendo.
* `LectorService` — servicio en primer plano de tipo `mediaPlayback`. Trocea el texto por
  frase (máx. 320 caracteres, sin partir palabras), habla un trozo con `QUEUE_FLUSH` y
  arranca el siguiente en `onDone`, que es lo que hace exacta la pausa. Guarda el índice y
  un hash del texto en `SharedPreferences` (`cort-lector`): si se vuelve a pedir el mismo
  texto, **retoma donde iba**; si es otro, empieza de cero.
* `MediaSession` + `Notification.MediaStyle` — que los controles existan en la pantalla
  bloqueada, en los audífonos y en la notificación. Se usa la de la plataforma, no
  AndroidX.
* Voz: `TextToSpeech` del sistema en `es_ES`, con `es_MX` de reserva y un mensaje claro
  que dice dónde instalar la voz si no hay ninguna. **Piper/sherpa entra después**, cuando
  esta tubería esté probada en el teléfono: primero se valida lo difícil (que la lectura
  sobreviva a la pantalla apagada y a otra app por delante) y después se cambia el motor,
  para no depurar dos cosas a la vez.

Un detalle que cuesta un crash si se ignora: un servicio arrancado con
`startForegroundService` tiene cinco segundos para llamar a `startForeground`, **también
cuando el texto llega vacío**. Por eso el servicio sube la notificación antes de validar
nada y se cierra enseguida si no hay qué leer.


## Antes de abrir la app: la PC

El HUD escucha sólo en `127.0.0.1` por defecto, así que desde el teléfono no se ve. Hay
que abrirlo a la red **con llave**:

```bash
python3 -m cort --hud --host 0.0.0.0 --token tu-llave
```

CORT imprime entonces dos enlaces:

```text
CORT · HUD en http://127.0.0.1:8765/  (Ctrl+C para salir)
CORT · desde el teléfono: http://192.168.1.19:8765/?token=tu-llave
```

El segundo es el que se escribe en la app. Sin `--token`, CORT **se niega** a levantar el
HUD fuera del bucle y lo dice: quedaría abierto a cualquiera con el mismo wifi. PC y
teléfono tienen que estar en la misma red.

## Instalar

1. Bajar `CORT-IA-<versión>-bolsillo.apk` de la [Release](../../releases) más nueva, con
   su `-firma.txt` al lado.
2. Comparar la huella: el renglón `llave sha256:` del `-firma.txt` tiene que coincidir
   con la del APK que ya está instalado. Si coincide, se puede instalar encima; si no,
   Android exigiría desinstalar y se perderían la dirección y los permisos.
3. Abrir el APK desde el archivo ▸ permitir «instalar apps desconocidas» para el
   navegador o el gestor de archivos ▸ *Actualizar* (no *Instalar*).
4. Al abrir, escribir el enlace de arriba. La app guarda la dirección y el token.

Si Play Protect insiste: el APK no está en Play Store ni subido a ningún servicio de
Google, así que la advertencia es la de cualquier app de fuera — *Instalar igualmente*
sobre el archivo firmado por la misma llave de siempre. Lo que hay que comprobar ante
una duda es la huella del paso 2, no la advertencia.

## Cómo se compila

`apps/bolsillo/compilar.sh` — el mismo método del `CORT-IA-2.11.0-nucleo.apk` del
teléfono, a la vista y sin Gradle:

```text
aapt2 compile --dir res        → los iconos
aapt2 link --manifest …        → recursos + manifiesto + versionCode
aapt2 dump xmltree             → comprueba que «Leer con CORT» quedó DENTRO
javac --release 11             → todo src/**/*.java contra android.jar
d8 --release --min-api 26      → classes.dex
zip -j                         → el dex dentro del APK
zipalign -f 4                  → alineado (Android 11 lo exige)
apksigner sign --v1 --v2 --v3  → la llave de siempre
```

La comprobación con `aapt2 dump xmltree` falla el run si faltara `LeerActivity`,
`LectorService`, el filtro `PROCESS_TEXT` o el atributo `foregroundServiceType`: un
manifiesto mal escrito que igual compila se descubriría en el teléfono como «no aparece en
el menú».

Corre en GitHub Actions (`.github/workflows/apk.yml`), no en el portátil: ahí sí hay
JDK y SDK (`ANDROID_HOME`), y el equipo local tiene 2 núcleos y 1,8 GiB de RAM.

`versionCode` se deriva de la versión con `MA*10000 + MI*100 + PA`: **3.1.0 → 30100**
(3.0.1 → 30001, 3.0.0 → 30000), por delante del 2.11.0 (21100) que está instalado. Esa es
la condición para que Android ofrezca *Actualizar*: mismo paquete + misma llave + número
más alto.

### La llave

`apps/bolsillo/llave.sh` resuelve la llave en este orden y deja en `firma.txt` cuál usó:

1. Secretos del repo: `CORT_APK_KEYSTORE_B64` + `CORT_APK_KEYSTORE_PASS`.
2. `CORT_KEYSTORE_FILE` + `CORT_KEYSTORE_PASS`, señaladas a mano.
3. `apps/bolsillo/keystore/cort.keystore` (+ `pass.txt`), la que guardó un run anterior.
4. `~/cort-llave.jks` (+ `~/cort-llave.pass`), la llave del portátil — la que firmó los
   APKs ya instalados, huella `FA:AB:EF:46:8F:3A:E0:4F:DF:AB:96:59:D6:A0:51:C4:53:D6:DE:D7:B9:65:46:8C:9C:3B:85:CA:FF:A3:19:77`.
5. Ninguna: genera una llave nueva y avisa en la cara que esa actualización pide
   desinstalar una vez.

La carpeta `keystore/`, los `*.jks` y `pass.txt` están en `.gitignore`. El repo es
público y con esa llave cualquiera podría firmar actualizaciones que su teléfono acepte
como legítimas.

## Lo que dicen los tres esquemas de firma

`apksigner verify --verbose` del APK publicado (`build-tools 37.0.0`) deja:

```text
Verified using v1 scheme (JAR signing):                    false
Verified using v2 scheme (APK Signature Scheme v2):        true
Verified using v3 scheme (APK Signature Scheme v3):        true
```

y `-firma.txt` copia esas tres líneas tal cual. Que v1 salga `false` **no** significa que
el bloque JAR no esté: el APK trae `META-INF/MANIFEST.MF`, `META-INF/CORT.SF` y
`META-INF/CORT.RSA`, los 13 `SHA-256-Digest` del manifiesto coinciden con los archivos
recalculados, y `keytool -printcert -jarfile` lee el firmante `CN=CORT` con huella
`FA:AB:EF:46:…:A3:19:77` — la misma del `CORT-IA-2.11.0-nucleo.apk`. El `.SF` además
declara `X-Android-APK-Signed: 2, 3`, que es la marca que `apksigner` pone cuando firma
también con v2/v3.

Por qué da igual para instalar: con `minSdkVersion` 26 (Android 8.0) cualquier equipo que
acepte este APK entiende el esquema v2, y ése está verificado. Android valida la firma por
v2 y ni mira el bloque JAR. Lo que **sí** importa para que se instale encima es que la llave
sea la misma, y esa huella está medida en los dos APK, no supuesta.

Un detalle de la auditoría: en `v3.0.0` el `-auditoria.txt` mostraba
`targetSdkVersion:'34'` pero **no** la línea del mínimo, porque el `grep` que arma ese archivo
buscaba `sdkVersion` en minúsculas y `aapt2` la escribe como `minSdkVersion`. El mínimo sí estaba
declarado (`AndroidManifest.xml` ▸ `android:minSdkVersion="26"`, `aapt2 link --min-sdk-version 26`,
`d8 --min-api 26`); lo que faltaba era verlo impreso en la evidencia. Se corrigió el `grep` y
`v3.0.1` sale con `minSdkVersion:'26'` en su auditoría. Lección: la evidencia se lee, no se supone.

## Qué está probado y qué no

Probado, con el archivo ya publicado — hoy, la Release [`v3.0.1`](https://github.com/Sandra2244/CORT-nuevo/releases/latest):

* GitHub Actions compila de verdad: `javac`, `d8`, `aapt2`, `zipalign` y `apksigner`
  salieron verdes en el run `40875001609` (`v3.0.0`) y otra vez en `40878467846` (`v3.0.1`),
  cada uno después de las 158 pruebas del job previo.
* El APK resultante pesa 193.773 bytes y su sha256 está en `-firma.txt`
  (`4e54f7c9…418a87` en 3.0.1), con `package: name='com.cort.ia' versionCode='30001'
  versionName='3.0.1'` leído con `aapt2 dump badging`.
* La llave usada es la de siempre: `-firma.txt` dice `origen llave: el secreto
  CORT_APK_KEYSTORE_B64 del repo` y `keytool -printcert -jarfile` lee en el APK nuevo
  `CN=CORT` con huella `FA:AB:EF:46:…:A3:19:77` — idéntica a la del `2.11.0-nucleo`.
* Lo que mira Android 11+: `minSdkVersion:'26'`, `targetSdkVersion:'34'`, 4 permisos justos,
  `resources.arsc` de 1544 bytes sin comprimir y `zipalign -c 4` en verde (`-auditoria.txt`).
* El camino del HUD por red con token desde la PC: 401 sin llave, 200 con ella, 401 con
  llave falsa, medido entrando por la IP de `wlan0`, y también en el navegador.

**No probado todavía**: que el APK se instale encima del 2.11.0 en el teléfono sin perder
la dirección guardada, y que el micrófono del HUD funcione dentro del `WebView` en
Android 16. Las dos se comprueban en cinco minutos con el móvil en la mano; hasta entonces
esta sección es la única promesa que hay que leer.

Con el lector (3.1.0) hay tres comprobaciones que sólo puede hacer el teléfono, y no se
dan por hechas:

1. Que **«Leer con CORT»** aparezca en el menú de selección y lea un párrafo.
2. Que la lectura **siga con la pantalla apagada** y con otra app delante.
3. Que al repetir el mismo texto **retome desde el trozo donde iba**.
