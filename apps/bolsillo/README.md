# CORT · bolsillo (Android)

Un cliente ligero: **una ventana al HUD que corre en la PC**. Aquí no hay cerebro — el
núcleo (router en español, memoria SQLite, Ollama, voz) vive en la PC y se alcanza por
la red local. Lo único que guarda esta app es la dirección de esa PC.

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

No usa AndroidX ni Kotlin ni Gradle: un `Activity` de la plataforma, `javac` y `d8`.

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
javac --release 11             → MainActivity.java contra android.jar
d8 --release --min-api 26      → classes.dex
zip -j                         → el dex dentro del APK
zipalign -f 4                  → alineado (Android 11 lo exige)
apksigner sign (v1+v2+v3)      → la llave de siempre
```

Corre en GitHub Actions (`.github/workflows/apk.yml`), no en el portátil: ahí sí hay
JDK y SDK (`ANDROID_HOME`), y el equipo local tiene 2 núcleos y 1,8 GiB de RAM.

`versionCode` se deriva de la versión con `MA*10000 + MI*100 + PA`: **3.0.0 → 30000**,
por delante del 2.11.0 (21100) que está instalado. Esa es la condición para que Android
ofrezca *Actualizar*: mismo paquete + misma llave + número más alto.

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

## Qué está probado y qué no

Probado: la resolución de la llave contra `~/cort-llave.jks` (huella leída con
`keytool`), el guion con `bash -n`, y el camino del HUD por red con token desde la PC
(401 sin llave, 200 con ella, medido entrando por la IP de `wlan0`).

**No probado todavía**: que `javac`/`d8`/`aapt2` compilen este Java (no hay JDK ni SDK en
el portátil: la primera compilación real es la de Actions), que el APK se instale encima
del 2.11.0 en el teléfono, y que el micrófono del HUD funcione dentro del `WebView` en
Android 16. Hasta ver el run verde, esto es código escrito, no software verificado.
