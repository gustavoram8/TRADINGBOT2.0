# -*- coding: utf-8 -*-
"""Genera el icono del sitio en todos los tamaños que el mundo pide.

    venv/bin/python3 tools/gen_favicon.py

Escribe en `scalpel/static/`:
  · favicon.ico          — 16+32+48 en un solo archivo (pestaña + Google)
  · icon-96.png / -192   — el que Google prefiere para resultados de búsqueda
  · icon-512.png         — instalar el sitio como app
  · apple-touch-icon.png — 180×180, iOS "añadir a inicio"
  · og-image.png         — 1200×630, la tarjeta de WhatsApp / X / LinkedIn

🔑 EL ARTE NO SE INVENTA: es la misma "a" del logotipo y el mismo azul que ya
usa el avatar de Instagram, extraídos de `logo_t.png` con el mismo método
(el azul se toma del color MÁS REPETIDO entre píxeles opacos; el primero cae
en el borde suavizado y da #84a9e8 en vez de #004feb). Así el icono de Google,
el de la pestaña y el de Instagram son la MISMA marca, que es justo lo que
Google premia: un icono estable y reconocible.

⚠️ Decisiones que parecen detalles y no lo son:
  · **La "a", no el logotipo.** El logotipo es 6:1; a 16×16 en una pestaña la
    palabra entera es una mancha gris. La letra sola se lee.
  · **Sin transparencia y a sangre.** iOS pinta NEGRO detrás de un icono con
    alfa y le aplica sus propias esquinas redondeadas: un PNG transparente
    queda como un borrón oscuro. Se entrega el cuadrado completo.
  · **Márgenes distintos por tamaño.** A 16px hace falta que la letra ocupe
    más proporción o desaparece; a 512 conviene más aire.
"""
from __future__ import print_function

import os
import sys
from collections import Counter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EST = os.path.join(RAIZ, 'scalpel', 'static')
LOGO = os.path.join(EST, 'logo_t.png')

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit('Hace falta Pillow: venv/bin/pip install Pillow')


def marca(completo=False):
    """(imagen de la "a" en blanco, azul de marca). Mismo método que el kit IG.

    Con `completo=True` devuelve además el LOGOTIPO entero en blanco, que es
    lo que va en la tarjeta social: ahí hay 1200×630 de sitio y un icono solo
    no dice quién eres — el que recibe el enlace por WhatsApp ve un cuadro
    azul y poco más."""
    im = Image.open(LOGO).convert('RGBA')
    im = im.crop(im.getchannel('A').getbbox())
    W, H = im.size
    px = im.load()

    def azulp(p):
        r, g, b, a = p
        return a > 120 and b > 90 and b - r > 45 and b - g > 35

    pts = [(x, y) for y in range(H) for x in range(W) if azulp(px[x, y])]
    azul = Counter(px[x, y][:3] for x, y in pts
                   if px[x, y][3] == 255).most_common(1)[0][0]
    assert azul[2] - azul[0] > 100, 'ese no es el azul de relleno del logo'

    # 🔑 La "a" son EXACTAMENTE los píxeles azules: en `logo_t.png` el resto
    # del logotipo va en otro color, así que `azulp` ya la aísla sola. Mismo
    # método que el kit de Instagram, y por eso el icono y el avatar salen
    # idénticos.
    # ⚠️ Se pintan SOLO esos píxeles, no todo lo opaco dentro del recuadro: la
    # primera versión copiaba el rectángulo entero y se colaba un trozo del
    # glifo vecino (visible como una mancha arriba a la izquierda).
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    letra = Image.new('RGBA', (x1 - x0 + 1, y1 - y0 + 1), (0, 0, 0, 0))
    q = letra.load()
    for x, y in pts:
        q[x - x0, y - y0] = (255, 255, 255, px[x, y][3])
    if not completo:
        return letra, azul
    entero = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    e = entero.load()
    for y in range(H):
        for x in range(W):
            a = px[x, y][3]
            if a:
                e[x, y] = (255, 255, 255, a)
    return letra, azul, entero


def icono(letra, azul, lado, prop, redondeado=0):
    """Cuadrado azul a sangre con la "a" blanca centrada ocupando `prop`."""
    im = Image.new('RGB', (lado, lado), azul)
    w = max(1, int(lado * prop))
    h = max(1, int(letra.size[1] * w / float(letra.size[0])))
    cap = letra.resize((w, h), Image.LANCZOS)
    im.paste(cap, ((lado - w) // 2, (lado - h) // 2), cap)
    if redondeado:
        # solo para la tarjeta social; los iconos van a sangre a propósito
        mask = Image.new('L', (lado, lado), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, lado - 1, lado - 1], redondeado, fill=255)
        fondo = Image.new('RGB', (lado, lado), (255, 255, 255))
        fondo.paste(im, (0, 0), mask)
        im = fondo
    return im


def tarjeta_social(entero, azul, w=1200, h=630):
    """La imagen que sale al pegar el enlace en WhatsApp / X / LinkedIn.

    NO es el icono estirado: lleva el LOGOTIPO completo, porque aquí hay sitio
    y lo que importa es que quien recibe el enlace sepa de quién es. Esas
    plataformas recortan a 1.91:1, así que todo lo legible vive en el centro.
    """
    im = Image.new('RGB', (w, h), azul)
    d = ImageDraw.Draw(im)
    # rejilla tenue, el mismo lenguaje visual del kit de Instagram
    tenue = tuple(min(255, c + 16) for c in azul)
    for x in range(0, w, 48):
        d.line([(x, 0), (x, h)], fill=tenue)
    for y in range(0, h, 48):
        d.line([(0, y), (w, y)], fill=tenue)
    # logotipo centrado, ocupando ~62% del ancho: legible incluso en la
    # miniatura pequeña que pinta WhatsApp en el hilo de un chat
    ancho = int(w * 0.62)
    alto = max(1, int(entero.size[1] * ancho / float(entero.size[0])))
    cap = entero.resize((ancho, alto), Image.LANCZOS)
    im.paste(cap, ((w - ancho) // 2, (h - alto) // 2), cap)
    return im


def main():
    if not os.path.exists(LOGO):
        sys.exit('no encuentro %s' % LOGO)
    letra, azul, entero = marca(completo=True)
    print('azul de marca medido: #%02x%02x%02x   "a": %dx%d px'
          % (azul + letra.size))

    salidas = []
    # ⚠️ Proporciones distintas a propósito: a 16 px la letra necesita ocupar
    # más para no desaparecer; a 512 conviene más aire.
    for lado, prop, nombre in ((96, 0.58, 'icon-96.png'),
                               (192, 0.55, 'icon-192.png'),
                               (512, 0.52, 'icon-512.png'),
                               (180, 0.56, 'apple-touch-icon.png')):
        p = os.path.join(EST, nombre)
        icono(letra, azul, lado, prop).save(p)
        salidas.append(p)

    # el .ico con las tres resoluciones dentro: el navegador elige
    # ⚠️ 0.74 y no 0.58 como los PNG: el .ico se reduce hasta 16 px y ahí los
    # trazos finos de la "a" se lavan hasta desaparecer. Comparadas 0.66 /
    # 0.74 / 0.82 / 0.90 ampliando el resultado real a 16 px: por debajo la
    # letra se deshace, por encima toca los bordes y se cierra su ojo.
    ico = os.path.join(EST, 'favicon.ico')
    icono(letra, azul, 48, 0.74).save(
        ico, sizes=[(16, 16), (32, 32), (48, 48)])
    salidas.append(ico)

    og = os.path.join(EST, 'og-image.png')
    tarjeta_social(entero, azul).save(og)
    salidas.append(og)

    for p in salidas:
        print('  %-24s %6.1f KB' % (os.path.basename(p),
                                    os.path.getsize(p) / 1024.0))
    return 0


if __name__ == '__main__':
    sys.exit(main())
