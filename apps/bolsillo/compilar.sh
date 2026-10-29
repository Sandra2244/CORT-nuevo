#!/usr/bin/env bash
# Compila el APK de bolsillo: aapt2 + javac + d8 + zipalign + apksigner.
# Sin Gradle y sin AndroidX, exactamente por el método con el que está hecho el
# `CORT-IA-2.11.0-nucleo.apk` del teléfono: las mismas cinco herramientas que trae
# el SDK de Android, así que `firma.txt` y `auditoria.txt` responden a preguntas
# reales («¿Play Protect lo deja instalar?», «¿se actualiza encima?») en vez de a
# opiniones.
#
# Corre en el pipeline de GitHub Actions (`ANDROID_HOME` ya viene puesto ahí). En
# el portátil de Sandra no hay JDK ni SDK: aquí falla con ese mensaje, no a medias.
#
#   bash apps/bolsillo/compilar.sh [version]      # por defecto 3.1.2
#
# `versionCode` se deriva de la versión con `MA*10000 + MI*100 + PA`: 3.1.0 → 30100,
# que queda por delante del 2.11.0 (21100) instalado en el teléfono. Con la misma
# llave y ese número por delante, Android ofrece «Actualizar» y no desinstala: se
# quedan la dirección de la PC y los permisos ya concedidos.
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$AQUI"

VERSION="${1:-${APK_VERSION:-3.1.2}}"
PAQUETE="com.cort.ia"
NOMBRE_APK="CORT-IA-${VERSION}-bolsillo.apk"

case "$VERSION" in
    [0-9]*.[0-9]*.[0-9]*)
        IFS=. read -r MA MI PA <<<"$VERSION"
        CODE=$(( 10#$MA * 10000 + 10#$MI * 100 + 10#$PA ))
        ;;
    *)
        echo "versión mal formada: $VERSION (se esperaba X.Y.Z)" >&2
        exit 1
        ;;
esac

SDK="${ANDROID_HOME:-}"
[ -n "$SDK" ] || SDK="${ANDROID_SDK_ROOT:-}"
if [ -z "$SDK" ] && [ -d /usr/local/lib/android/sdk ]; then
    SDK=/usr/local/lib/android/sdk
fi
if [ -z "$SDK" ]; then
    echo "falta ANDROID_HOME: este script corre en el pipeline, no en el portátil" >&2
    exit 1
fi

BT="$( { ls -d "$SDK"/build-tools/*/ 2>/dev/null || true; } | sort -V | tail -1)"
PLAT="$( { ls -d "$SDK"/platforms/*/ 2>/dev/null || true; } | sort -V | tail -1)"
if [ -z "$BT" ] || [ -z "$PLAT" ]; then
    CMDL="$( { ls -d "$SDK"/cmdline-tools/*/bin 2>/dev/null || true; } | head -1)"
    [ -n "$CMDL" ] || { echo "ni SDK ni sdkmanager: el runner cambió de imagen" >&2; exit 1; }
    yes | "$CMDL/sdkmanager" --licenses >/dev/null 2>&1 || true
    "$CMDL/sdkmanager" "platforms;android-34" "build-tools;34.0.0"
    BT="$( { ls -d "$SDK"/build-tools/*/ 2>/dev/null || true; } | sort -V | tail -1)"
    PLAT="$( { ls -d "$SDK"/platforms/*/ 2>/dev/null || true; } | sort -V | tail -1)"
fi
echo "build-tools: $(basename "$BT") · platform: $(basename "$PLAT") · APK $VERSION (código $CODE)"

rm -rf build
mkdir -p build/obj build/apk

# -- Recursos y manifiesto ---------------------------------------------------
"$BT/aapt2" compile --dir res -o build/obj/res.zip
"$BT/aapt2" link -o build/apk/sin-alinear.apk \
    -I "$PLAT/android.jar" \
    --manifest AndroidManifest.xml \
    --min-sdk-version 26 --target-sdk-version 34 \
    --version-code "$CODE" --version-name "$VERSION" \
    build/obj/res.zip --auto-add-overlay

# -- Que las piezas nuevas estén DENTRO del APK ------------------------------
# El manifiesto se puede escribir bien y aun así no llegar al APK (un `aapt2 link`
# que se lleva el viejo, un filtro con la categoría mal puesta). Sin esta prueba el
# fallo aparecería en el teléfono como «Leer con CORT no está en el menú».
#
# Se lee el `AndroidManifest.xml` binario que quedó DENTRO del APK y se buscan los
# nombres en su tabla de cadenas (`aapt2 dump xmltree` cambió de sintaxis entre
# build-tools y devolvía vacío; esto no depende de la versión).
python3 - build/apk/sin-alinear.apk <<'PY'
import sys, zipfile

piezas = ["LeerActivity", "LectorService",
          "android.intent.action.PROCESS_TEXT", "foregroundServiceType"]
with zipfile.ZipFile(sys.argv[1]) as apk:
    manifiesto = apk.read("AndroidManifest.xml")

# La tabla de cadenas de AXML puede ir en UTF-8 o en UTF-16: se acepta cualquiera.
lineas, falta = [], []
for pieza in piezas:
    if pieza.encode("utf-8") in manifiesto:
        lineas.append(f"{pieza}: presente (utf-8)")
    elif pieza.encode("utf-16-le") in manifiesto:
        lineas.append(f"{pieza}: presente (utf-16)")
    else:
        lineas.append(f"{pieza}: FALTA")
        falta.append(pieza)

texto = "\n".join(lineas) + "\n"
with open("build/componentes.txt", "w", encoding="utf-8") as salida:
    salida.write(texto)
if falta:
    print(texto, end="", file=sys.stderr)
    sys.exit(1)
print(texto, end="")
PY

# -- El Java -----------------------------------------------------------------
# `--release 11` con `android.jar` en el classpath: es la única prueba que existe
# de que los `@Override` de `WebChromeClient.onPermissionRequest` y compañía tienen
# la firma de la plataforma real. `-encoding UTF-8` porque los mensajes están en
# español con tildes.
javac --release 11 -encoding UTF-8 -classpath "$PLAT/android.jar" \
    -d build/obj $(find src -name '*.java')

# -- El dex ------------------------------------------------------------------
"$BT/d8" --release --min-api 26 --lib "$PLAT/android.jar" --output build/apk \
    $(find build/obj -name '*.class')

# `aapt2 link` ya armó el APK con los recursos; el dex entra dentro, que es lo que
# Gradle hace por detrás y aquí se hace a la vista.
(cd build/apk && zip -q -j sin-alinear.apk classes.dex)

# -- Alinear -----------------------------------------------------------------
"$BT/zipalign" -f 4 build/apk/sin-alinear.apk build/apk/alineado.apk

# -- La llave de siempre -----------------------------------------------------
# shellcheck source=apps/bolsillo/llave.sh
source llave.sh
preparar_llave || { echo "no se pudo preparar la llave de firma" >&2; exit 1; }
echo "firmando con $LLAVE_ORIGEN — instalar encima: $LLAVE_ACTUALIZA"

# Los tres esquemas, pedidos a la fuerza: con `minSdkVersion 26` `apksigner` deja
# la v1 desactivada por defecto, y la v1 es la única que puede leer una herramienta
# corriente (`keytool -printcert -jarfile`) — con ella se comparó la llave del
# 2.11.0 que ya está instalado. La sonda existe porque estas banderas dependen de
# la versión de las build-tools: si el runner cambiara, un argumento desconocido
# pondría el run rojo en vez de avisar.
ESQUEMAS=""
for bander in --v1-signing-enabled --v2-signing-enabled --v3-signing-enabled; do
    if "$BT/apksigner" sign --help 2>&1 | grep -q -- "$bander"; then
        ESQUEMAS="$ESQUEMAS $bander true"
    else
        echo "aviso: este apksigner no conoce $bander; se firma con sus defaults"
    fi
done
echo "esquemas pedidos:${ESQUEMAS:- (ninguno explícito)}"

# shellcheck disable=SC2086
"$BT/apksigner" sign $ESQUEMAS --ks "$LLAVE" \
    --ks-pass pass:"$LLAVE_PASS" --key-pass pass:"$LLAVE_PASS" \
    --out "build/$NOMBRE_APK" build/apk/alineado.apk

# Sin `|| true`: si la firma no cuadra, el run se pone rojo antes de publicar nada.
"$BT/apksigner" verify --verbose build/"$NOMBRE_APK" | tee build/verificacion.txt

# -- Lo que se lee del archivo final ----------------------------------------
# `firma.txt` y `auditoria.txt` viajan pegados al APK en la Release: sin sesión en
# GitHub los logs de Actions dan 403, y estas son las dos preguntas que la dueña ya
# hizo con números delante («¿Play Protect lo deja instalar?», «¿se actualiza
# encima?»).
HUELLA="$("$BT/apksigner" verify --print-certs build/"$NOMBRE_APK" 2>/dev/null \
    | grep -m1 'SHA-256 digest' | awk '{print $NF}' || true)"
[ -n "$HUELLA" ] || HUELLA="(no se pudo leer)"
SHA_APK="$(sha256sum build/"$NOMBRE_APK" | awk '{print $1}')"
MB="$(du -m build/"$NOMBRE_APK" | cut -f1)"

cat > "build/${NOMBRE_APK%.apk}-firma.txt" <<EOF
paquete:        $PAQUETE
versión:        $VERSION (versionCode $CODE)
archivo:        $NOMBRE_APK ($MB MB)
sha256:         $SHA_APK
llave sha256:   $HUELLA
origen llave:   $LLAVE_ORIGEN
actualizar:     $LLAVE_ACTUALIZA
esquemas:       $(grep -E '^Verified using' build/verificacion.txt | tr '\n' ';' || true)
EOF

# La auditoría de instalabilidad: lo que Android 11+ y Play Protect miran de
# verdad, leído del APK ya firmado.
{
    echo "== badging =="
    # `minSdkVersion` va en la lista a propósito: aapt2 escribe la línea con la «S»
    # mayúscula, así que un `grep sdkVersion` a secas nunca la atrapa y la auditoría
    # sale sin el mínimo del APK.
    "$BT/aapt2" dump badging build/"$NOMBRE_APK" 2>/dev/null \
        | grep -E "^package|versionCode|versionName|^sdkVersion|^minSdkVersion|^targetSdkVersion|uses-permission|^application-label"
    echo
    echo "== componentes del lector (dentro del APK) =="
    cat build/componentes.txt 2>/dev/null || echo "(no se generó)"
    echo
    echo "== resources.arsc (Android 11 exige: sin comprimir y alineado a 4) =="
    python3 - "build/$NOMBRE_APK" <<'PY'
import sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
    info = z.getinfo("resources.arsc")
    modo = "SIN COMPRIMIR (ok)" if info.compress_type == zipfile.ZIP_STORED else "COMPRIMIDO (mal)"
    print(f"resources.arsc: {info.file_size} bytes · {modo}")
PY
    echo
    echo "== zipalign =="
    "$BT/zipalign" -c 4 build/"$NOMBRE_APK" && echo "alineado de a 4: ok"
    echo
    echo "== contenido =="
    unzip -l build/"$NOMBRE_APK" | tail -3
    echo
    echo "== verificación de firma =="
    cat build/verificacion.txt
} > "build/${NOMBRE_APK%.apk}-auditoria.txt" 2>&1 || true

echo
echo "APK:    build/$NOMBRE_APK ($MB MB)"
echo "firma:  build/${NOMBRE_APK%.apk}-firma.txt"
echo "audio:  build/${NOMBRE_APK%.apk}-auditoria.txt"
anotar_llave build/"$NOMBRE_APK" "$BT/apksigner"
