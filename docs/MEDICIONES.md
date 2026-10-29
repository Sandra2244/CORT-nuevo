# Mediciones

Esta página es la puerta de cada fase de la 2.0: **una fila sin una fecha y una fuente
medida no entra**. Lo que se supone, se escribe en «pendiente», no acá.

Fuentes posibles: la salida de una herramienta (`aapt2 dump badging`, `apksigner verify`,
`sha256sum`), el `-firma.txt` / `-auditoria.txt` de una Release, o un número de run de
GitHub Actions. Las capturas y los videos no cuentan como medición.

## 2.0.1 — «Leer con CORT» (APK 3.1.2, 2026-10-29)

| Qué | Valor medido | De dónde |
|---|---|---|
| Archivo publicado | `CORT-IA-3.1.2-bolsillo.apk` | Release `v3.1.2` |
| Tamaño | 201.965 bytes | listado de assets de la Release |
| sha256 | `cee5d84438a8acea65745006528ecca1adce557e15b63bfcae71e42ec6c4813a` | `-firma.txt` |
| Paquete y versión | `com.cort.ia`, `versionCode 30102`, `versionName 3.1.2` | `aapt2 dump badging` en `-auditoria.txt` |
| SDK | `minSdkVersion 26`, `targetSdkVersion 34` | ídem |
| Permisos | 7: `INTERNET`, `ACCESS_NETWORK_STATE`, `RECORD_AUDIO`, `MODIFY_AUDIO_SETTINGS`, `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_MEDIA_PLAYBACK`, `POST_NOTIFICATIONS` | ídem |
| Componentes del lector dentro del APK | `LeerActivity`, `LectorService`, `android.intent.action.PROCESS_TEXT`, `foregroundServiceType` — los cuatro **presentes**, en la tabla de cadenas del AXML en **UTF-16** | `componentes.txt`, copiado a `-auditoria.txt` |
| Clases compiladas | `Lcom/cort/ia/LectorService;` y `Lcom/cort/ia/LeerActivity;` presentes en `classes.dex` (29.792 bytes), leído del APK descargado | `zipfile` + búsqueda en el dex, sobre el archivo publicado |
| Firma | v2 y v3 `true`; v1 `false`; llave `faabef46…ffa31977` | `apksigner verify` |
| `resources.arsc` | 1544 bytes, sin comprimir | `-auditoria.txt` |
| Alineado | `zipalign -c 4` en verde | ídem |
| Compilación | run `40942914232` en verde: job `pruebas` (158) + job `apk` | GitHub Actions |
| Publicación | Release `v3.1.2` no borrador, no pre-release, marcada como *latest* | `gh api …/releases/latest` |

Desglose por frase: el troceo máximo es 320 caracteres (`TROZO_MAX`), se corta en
`. ! ? ; :` seguido de espacio y nunca a mitad de palabra. No hay medición de velocidad de
voz todavía: depende de la voz que tenga instalada el teléfono.

### Intentos anteriores y por qué fallaron

Dejar el registro evita repetir el mismo error y explica por qué el número no es 3.1.0.

| Tag | Run | Resultado | Causa |
|---|---|---|---|
| `v3.1.0` | `40941520819` | rojo | `aapt2 dump xmltree --file AndroidManifest.xml` devolvía vacío; la comprobación de componentes no encontró `LeerActivity` |
| `v3.1.1` | `40942306988` | rojo | en build-tools 37 `dump xmltree` **exige** `--file`, y sin él no volcaba nada |
| `v3.1.2` | `40942914232` | **verde** | la comprobación lee el AXML del APK con `zipfile` en vez de usar `aapt2 dump` |

## 2.0.1b — voz Piper/sherpa

Sin medir. Se cierra cuando el teléfono pronuncie con Piper un párrafo de 200 palabras y
se anote el tiempo hasta la primera palabra.

## 2.0.2 — «Voz propia» (2026-10-29)

| Qué | Valor medido | De dónde |
|---|---|---|
| Suite completa | **177 pruebas en verde**, 101,756 s | `python3 -m unittest discover -s tests`, 2026-10-29, este portátil |
| Pruebas nuevas de honestidad y persona | 10 (`tests/test_honesto.py`) | ídem |
| Pruebas de huecos en la memoria | 5 (dedupe con `veces`, orden, vacío, borrado) | `tests/test_memory.py` |
| Pruebas de huecos en el flujo | 5 (`tests/test_app.py`: se anota, no se anota si sale bien, se lista, se borra, cancelar no cuenta) | ídem |
| La prueba puede fallar | se mutó el contador `veces` de `anotar_hueco` y la suite dio rojo; archivo restaurado y verificado con `md5sum -c` (`6706e377…6bb699`) | corrida local de mutación |
| Texto de los fallos | todos salen de `cort/brain/honesto.py`; ninguna respuesta de error se arma en otro módulo | lectura de `app.py` y `harness.py` |
| CI en `main` | run `40951410613` en verde: **177 pruebas en 2,970 s** en el runner y `--once` respondiendo la hora; 16 s de job completo | GitHub Actions, `pruebas.yml`, push `38cebe6` |

Lo que **no** está medido todavía: el juicio de Sandra escuchando la voz nueva en conversaciones
reales. Hasta entonces, «suena más cálida» es una intención, no una medición.

## Pendiente de medir en el A16

Estas tres no tienen número todavía y no se anuncian como funcionando:

1. «Leer con CORT» aparece en el menú de selección y lee un párrafo.
2. La lectura sigue con la pantalla apagada y con otra app por delante.
3. Al repetir el mismo texto, retoma desde el trozo donde iba.
