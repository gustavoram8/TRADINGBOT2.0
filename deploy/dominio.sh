#!/usr/bin/env bash
# Abrir y cerrar tradeable.academy con UN comando. Se corre EN EL VPS, como root.
#
#   bash deploy/dominio.sh cerrar    → "en construcción" para todos menos tú
#   bash deploy/dominio.sh abrir     → la app para todo el mundo (sin indexar)
#   bash deploy/dominio.sh estado    → qué está puesto ahora mismo
#
# POR QUÉ EXISTE
# -------------
# Cerrar el dominio eran seis pasos con un `sed`, un pase que inventar y un
# certificado que no perder. A las dos de la mañana eso no se hace: se pospone.
# Aquí está todo junto, y el pase lo GUARDA él (/etc/nginx/.ta_pase), así que
# cerrar dos veces no te cambia la dirección secreta ni te obliga a recordarla.
#
# ⚠️ No toca los certificados: los deja exactamente donde estaban. Las líneas
# `ssl_certificate` las escribe certbot en el archivo instalado, así que al
# reemplazarlo hay que volver a ponerlas — eso lo hace este script solo,
# copiándolas del archivo que estaba en uso (o del propio Let's Encrypt).
set -euo pipefail

REPO="${REPO:-/var/www/TRADINGBOT2.0}"
DESTINO=/etc/nginx/sites-available/tradeable.academy
ENLACE=/etc/nginx/sites-enabled/tradeable.academy
GUARDA=/etc/nginx/.ta_pase
DOMINIO=tradeable.academy

rojo()  { printf '\033[31m%s\033[0m\n' "$*"; }
verde() { printf '\033[32m%s\033[0m\n' "$*"; }

[ "$(id -u)" = 0 ] || { rojo "Hay que correrlo como root (sudo)."; exit 1; }

lineas_ssl() {
  # Las que ya estaban puestas; si no hay, las del certificado de Let's Encrypt.
  if [ -f "$DESTINO" ] && grep -q '^\s*ssl_certificate ' "$DESTINO"; then
    grep -E '^\s*ssl_certificate(_key)? ' "$DESTINO" | sed 's/^\s*/    /'
    return
  fi
  local dir
  dir=$(ls -d /etc/letsencrypt/live/*/ 2>/dev/null | head -1 || true)
  if [ -n "$dir" ]; then
    printf '    ssl_certificate %sfullchain.pem;\n' "$dir"
    printf '    ssl_certificate_key %sprivkey.pem;\n' "$dir"
  fi
}

instalar() {                     # $1 = plantilla, $2 = pase (opcional)
  local plantilla="$1" pase="${2:-}" tmp
  tmp=$(mktemp)
  if [ -n "$pase" ]; then
    sed "s/PASE-CAMBIAME/$pase/g" "$plantilla" > "$tmp"
  else
    cp "$plantilla" "$tmp"
  fi
  # Reponer el certificado donde la plantilla lo deja anotado como comentario.
  local ssl
  ssl=$(lineas_ssl)
  if [ -n "$ssl" ]; then
    awk -v ssl="$ssl" '
      /# ssl_certificate/ && !hecho { print ssl; hecho=1; next } { print }
    ' "$tmp" > "$tmp.2" && mv "$tmp.2" "$tmp"
  else
    rojo "No encontré ningún certificado. Se instala igual, pero revisá HTTPS."
  fi
  cp -a "$DESTINO" "$DESTINO.bak.$(date +%s)" 2>/dev/null || true
  mv "$tmp" "$DESTINO"
  ln -sfn "$DESTINO" "$ENLACE"
  nginx -t
  systemctl reload nginx
  # ⚠️ `nginx -t` dice que el ARCHIVO es válido, no que esté activo. Esto sí:
  local puesto
  puesto=$(nginx -T 2>/dev/null | grep -c 'ta_pase' || true)
  echo "   (marcas de pase cargadas en nginx: $puesto)"
}

case "${1:-}" in
  cerrar)
    if [ -s "$GUARDA" ]; then
      PASE=$(cat "$GUARDA")
      echo "Reuso el pase que ya tenías guardado."
    else
      PASE=$(openssl rand -hex 16)
      umask 077; printf '%s' "$PASE" > "$GUARDA"
    fi
    instalar "$REPO/deploy/nginx/$DOMINIO.preview.conf" "$PASE"
    verde "✅ CERRADO. Los demás ven la página de en construcción."
    echo
    echo "   Tu puerta (ábrela una vez en cada navegador y teléfono):"
    echo "   https://$DOMINIO/pase/$PASE"
    echo
    echo "   Guardada en $GUARDA por si la pierdes."
    echo "   Si el navegador te sigue mostrando la página de espera, es la"
    echo "   caché de Cloudflare: abre la dirección en una ventana nueva."
    ;;
  abrir)
    instalar "$REPO/deploy/nginx/$DOMINIO.abierto.conf"
    verde "✅ ABIERTO a todo el mundo (con robots.txt en Disallow: no se indexa)."
    echo "   Para volver a cerrarlo: bash deploy/dominio.sh cerrar"
    ;;
  estado)
    if nginx -T 2>/dev/null | grep -q 'ta_pase'; then
      verde "CERRADO — solo entra quien traiga el pase."
      [ -s "$GUARDA" ] && echo "   https://$DOMINIO/pase/$(cat "$GUARDA")"
    elif nginx -T 2>/dev/null | grep -q 'proxy_pass http://127.0.0.1:5001'; then
      rojo "ABIERTO — cualquiera que entre al dominio ve la aplicación."
    else
      echo "Solo la página de 'en construcción' (nadie ve la app, ni tú)."
    fi
    ;;
  *)
    sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'
    exit 1
    ;;
esac
