# 12 · IDIOMAS (i18n)

**Cuatro idiomas, siempre a la par:** inglés (EN, base), español (ES), francés
(FR) y portugués de Brasil (PT). Un texto nuevo se sube en los cuatro o no se sube.

## Cómo funciona

- **El servidor siempre sirve inglés** (`<html lang="en">`). La traducción la
  aplica **el navegador** después, con JavaScript.
  - Consecuencia: los buscadores solo ven inglés. Por eso las descripciones
    para Google (`<meta description>`, títulos) van en inglés a propósito.
- **El idioma elegido** se guarda en `localStorage` como `scalpel_lang`.
  Sin preferencia, las páginas sueltas usan `navigator.language`.
- **No hay archivos `.po` ni librería de traducción.** Son diccionarios
  JavaScript con claves tipo `seccion.clave`.
- Los elementos del HTML llevan un atributo con su clave; un "aplicador" recorre
  la página y pone el texto.

## Dónde vive cada diccionario

| Zona del sitio | Dónde están los textos | Atributo en el HTML |
|---|---|---|
| **La app** (`index.html`) | Objeto `I18N` **dentro** de `index.html` (más `MT_I18N`, `RANK_I18N`, `NX_T` de Tessera, `LX` de Synapse, `HELP_CONTENT`) | `data-t` |
| **Portada** (`landing.html`) | Dentro de la propia plantilla | `data-t` |
| **Páginas sueltas** (checkout, ajustes, precios, socials, partner, tienda…) | `static/pages_i18n.js` | `data-i18n`, `data-i18n-html`, `data-i18n-vars` |
| **Login / registro / 2FA** | `static/auth.js` | propio |
| **Términos y privacidad** | Inglés en la plantilla; ES/FR/PT en `static/legal_i18n.js` | propio |
| **Mentorías** | `static/improve_i18n.js` | propio |
| **`/creators`, `/contact`, `/proyecto`** | Diccionario **dentro** de cada plantilla (autocontenidas) | propio |
| **Guía** (`/guide`) | Se **genera** desde `tools/gen_guide/` (no editar a mano) | — |
| **Correos** | `EMAIL_I18N` en `app.py` | — |
| **Synapse (contenido)** | `synapse_library.js` (EN) + `synapse_content_{es,fr,pt}.json` + `synapse_translations.py`; se sirve por `/api/synapse/l10n/<lang>` | — |
| **Quiz y Reto diario** | Cada pregunta trae sus 4 idiomas en el banco | — |
| **Asistente Tessera** | Responde en el idioma de la pregunta | — |
| **Análisis de la IA** | El idioma se le pide al modelo en el mensaje; las siglas de ICT quedan en inglés | — |

## Reglas de estilo por idioma

| Idioma | Trato | Notas |
|---|---|---|
| Español | **tú**, latinoamericano | Que no suene a traducción literal (el dueño lo detecta). |
| Francés | **vous** | Ojo con apóstrofes: su diccionario usa comillas dobles. |
| Portugués | **você** (Brasil) | |
| Todos | — | **La jerga de trading se queda en inglés** (FVG, BOS, order block, kill zone…). El nombre de la pestaña es "Chalkboard" en los 4. |

- Los textos se **redactan por idioma**, no se traducen palabra por palabra.
- La palabra **"socio" está prohibida** en español para los creadores:
  "colaborador".

## Trampas conocidas

- **`data-i18n` usa `textContent`**: si el texto lleva etiquetas (`<b>`), salen
  literales. Para eso está `data-i18n-html`.
- **Texto con un número del servidor** (por ejemplo "pierdes 25 días"): se usa
  `data-i18n-vars` con JSON, porque el orden de la frase cambia entre idiomas.
- **Mensajes armados en tiempo de ejecución fuera del bloque principal** de
  `index.html` necesitan **`window.T`**: `I18N` es una constante del bloque y
  otros bloques no la ven (sale la clave cruda en pantalla).
- **Al cambiar de idioma en vivo**, cada módulo se engancha a
  `window.applyLanguage`. Uno que no lo haga se queda en el idioma anterior
  (le pasó a la burbuja de Tessera).
- **Claves parejas:** antes de subir, comprobar que las 4 lenguas tienen las
  mismas claves y que ninguna clave usada en el HTML falta en el diccionario.
- **Google Fonts no bloqueante** en páginas a las que se llega desde Instagram:
  una hoja pendiente en el `<head>` retrasa los scripts y la página se queda en
  inglés unos segundos.

## Comprobaciones

```bash
python3 tools/audit_legal_translations.py     # legales: cláusula por cláusula
python3 tools/validate_synapse_content.py     # Synapse: paridad y longitudes
node tools/validate_daily_bank.js             # Reto diario: 4 idiomas, 1 correcta, longitudes parejas
node --check <archivo.js>                     # cualquier JS tocado
```
No hay una herramienta única que verifique la paridad de claves de
`index.html` y `pages_i18n.js`: se hace con un guion puntual en cada cambio.
⚠️ Buen candidato a automatizar.
