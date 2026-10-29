#!/usr/bin/env bash
# La llave con la que se firma el APK de bolsillo — la misma de siempre.
#
# Por qué importa: para Android una firma distinta es OTRA aplicación. Si este APK
# se firmara con una llave nueva, instalarlo exigiría desinstalar el CORT-IA del
# teléfono, y al desinstalar se va el permiso del micrófono y la dirección de la PC
# que la dueña escribió a mano. Con la llave de `FA:AB:EF:46:…:19:77` se instala
# ENCIMA y no se pierde nada.
#
# Orden de resolución (manda el primero que exista):
#   1. `CORT_APK_KEYSTORE_B64` + `CORT_APK_KEYSTORE_PASS` — los secretos del repo.
#      Es la vía permanente: sobrevive aunque se borre la caché de Actions.
#   2. `CORT_KEYSTORE_FILE` + `CORT_KEYSTORE_PASS` — una llave señalada a mano.
#   3. `apps/bolsillo/keystore/cort.keystore` (+ `pass.txt`) — la que guardó un run
#      anterior en la caché del workflow.
#   4. `~/cort-llave.jks` (+ `~/cort-llave.pass`) — la llave del portátil, la que
#      firmó los APKs ya instalados en el teléfono.
#   5. Ninguna: se genera una llave nueva y se deja en (3) para la próxima vez.
#      Este caso avisa en la cara: la actualización de ahora pide desinstalar una vez.
#
# La llave NUNCA se sube al repo (`keystore/` está en .gitignore): el repo es público
# y con esa llave cualquiera podría firmar actualizaciones de su CORT.
#
# Uso (desde la raíz del repo o desde `apps/bolsillo/`):
#   source apps/bolsillo/llave.sh && preparar_llave
#
# Deja definidas: `LLAVE`, `LLAVE_PASS`, `LLAVE_ORIGEN`, `LLAVE_ACTUALIZA`.

_AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORT_KEYSTORE_DIR="${CORT_KEYSTORE_DIR:-$_AQUI/keystore}"

preparar_llave() {
    if [ -n "${CORT_APK_KEYSTORE_B64:-}" ]; then
        LLAVE="${TMPDIR:-/tmp}/cort-firma.keystore"
        printf '%s' "$CORT_APK_KEYSTORE_B64" | base64 -d > "$LLAVE" || return 1
        if [ -z "${CORT_APK_KEYSTORE_PASS:-}" ]; then
            echo "falta CORT_APK_KEYSTORE_PASS: hay keystore pero no su contraseña"
            return 1
        fi
        LLAVE_PASS="$CORT_APK_KEYSTORE_PASS"
        LLAVE_ORIGEN="el secreto CORT_APK_KEYSTORE_B64 del repo"
        LLAVE_ACTUALIZA="sí: se instala encima del anterior"
        return 0
    fi

    if [ -n "${CORT_KEYSTORE_FILE:-}" ]; then
        if [ ! -f "$CORT_KEYSTORE_FILE" ]; then
            echo "CORT_KEYSTORE_FILE apunta a $CORT_KEYSTORE_FILE y ese archivo no existe"
            return 1
        fi
        if [ -z "${CORT_KEYSTORE_PASS:-}" ]; then
            echo "falta CORT_KEYSTORE_PASS para $CORT_KEYSTORE_FILE"
            return 1
        fi
        LLAVE="$CORT_KEYSTORE_FILE"
        LLAVE_PASS="$CORT_KEYSTORE_PASS"
        LLAVE_ORIGEN="la llave señalada con CORT_KEYSTORE_FILE"
        LLAVE_ACTUALIZA="sí si es la misma llave de antes"
        return 0
    fi

    if [ -f "$CORT_KEYSTORE_DIR/cort.keystore" ]; then
        if [ -n "${CORT_APK_KEYSTORE_PASS:-}" ]; then
            LLAVE_PASS="$CORT_APK_KEYSTORE_PASS"
        elif [ -f "$CORT_KEYSTORE_DIR/pass.txt" ]; then
            LLAVE_PASS="$(cat "$CORT_KEYSTORE_DIR/pass.txt")"
        else
            echo "la caché trajo el keystore pero no su contraseña: se regenera"
            rm -f "$CORT_KEYSTORE_DIR/cort.keystore"
            preparar_llave
            return $?
        fi
        LLAVE="$CORT_KEYSTORE_DIR/cort.keystore"
        LLAVE_ORIGEN="la llave fija de $CORT_KEYSTORE_DIR (caché del workflow)"
        LLAVE_ACTUALIZA="sí: se instala encima del anterior"
        return 0
    fi

    if [ -f "$HOME/cort-llave.jks" ] && [ -f "$HOME/cort-llave.pass" ]; then
        LLAVE="$HOME/cort-llave.jks"
        LLAVE_PASS="$(cat "$HOME/cort-llave.pass")"
        LLAVE_ORIGEN="la llave del portátil ($HOME/cort-llave.jks), la que firmó los APKs instalados"
        LLAVE_ACTUALIZA="sí: se instala encima del anterior"
        return 0
    fi

    mkdir -p "$CORT_KEYSTORE_DIR" || { echo "no se puede crear $CORT_KEYSTORE_DIR"; return 1; }
    chmod 700 "$CORT_KEYSTORE_DIR" 2>/dev/null || true
    LLAVE="$CORT_KEYSTORE_DIR/cort.keystore"
    LLAVE_PASS="$( (openssl rand -hex 8 2>/dev/null || echo "cort$(date +%s)") | cut -c1-16)"
    printf '%s' "$LLAVE_PASS" > "$CORT_KEYSTORE_DIR/pass.txt"
    chmod 600 "$CORT_KEYSTORE_DIR/pass.txt" 2>/dev/null || true
    keytool -genkeypair -keystore "$LLAVE" -alias CORT \
        -keyalg RSA -keysize 2048 -validity 10950 \
        -storepass "$LLAVE_PASS" -keypass "$LLAVE_PASS" \
        -dname "CN=CORT, OU=asistente local, O=local" >/dev/null || return 1
    LLAVE_ORIGEN="una llave NUEVA generada en este run y guardada en $CORT_KEYSTORE_DIR"
    LLAVE_ACTUALIZA="no esta vez: pide desinstalar una vez, y de ahí en adelante sí"
    return 0
}

# La huella viaja como anotación del check-run: sin sesión en GitHub los registros
# de Actions dan 403, así que lo que no sale anotado o en `firma.txt` no existe.
#   anotar_llave <apk> [ruta-de-apksigner]
anotar_llave() {
    local apk="$1" signer="${2:-apksigner}" dig
    [ -x "$signer" ] || signer=apksigner
    dig="$("$signer" verify --print-certs "$apk" 2>/dev/null \
            | grep -m1 'SHA-256 digest' | awk '{print $NF}' || true)"
    [ -n "$dig" ] || dig="(no se pudo leer la huella)"
    echo "::notice::llave del APK $dig · $LLAVE_ORIGEN · instalar encima: $LLAVE_ACTUALIZA"
}
