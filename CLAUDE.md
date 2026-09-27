# Carpeta de cartas Pokémon — guía para Claude Code

Este repositorio es la web de venta de cartas de Jose (Pokémon TCG), publicada en Vercel
(rockethouse.vercel.app) desde la rama `main`. Cada push a `main` se publica solo en ~1 minuto.
Jose vende en **Cardmarket** y usa esta web como catálogo para sus grupos.

Habla con Jose en español, con pasos claros. Antes de cualquier acción irreversible
(publicar en Cardmarket, borrar ofertas, hacer push) enséñale un resumen y espera su "sí".

---

## Archivos

| Archivo | Qué es | Quién lo cambia |
|---|---|---|
| `index.html` | Catálogo público. Lee `cartas.json`, `stock.csv`, `config.json` y `suelo.csv` al cargar. | Casi nunca |
| `informe.html` | Página privada (no enlazada): mis precios frente al suelo, exportar PDF/Excel y botón de rebajas. | Casi nunca |
| `cartas.json` | **Catálogo**: datos fijos de cada carta + lista de cartas buscadas. | Claude Code al añadir cartas |
| `stock.csv` | **Precio y cantidad** de cada carta (manda sobre `cartas.json`). Cantidad 0 = «Agotada». | Jose o Claude Code |
| `suelo.csv` | Precio más barato de otros vendedores en Cardmarket (español, NM). | Claude Code |
| `config.json` | Modo de precios (normal / rebajas). **No lo sobrescribas**: lo gestiona el botón de `informe.html` vía `api/modo.js`. | Botón del informe |
| `img/<id>.webp` | Foto de cada carta. `img/w<num>.webp` = fotos de cartas buscadas. | Claude Code |
| `api/modo.js` | Función de Vercel que edita `config.json` en GitHub (variables `GITHUB_TOKEN`, `GITHUB_REPO`). | Nunca |

### `cartas.json`
```json
{
  "cartas": [
    {"id": 1, "name": "Azumarill", "num": 68, "numLabel": "068/128", "set": "30th Celebration",
     "url": "https://www.cardmarket.com/es/Pokemon/Products/Singles/30th-Celebration/Azumarill-30C068",
     "price": 0.25, "qty": 2, "type": "psychic", "tag": "", "toploader": false, "img": "img/1.webp"}
  ],
  "buscadas": [ {"num": "023", "attack": "Thunder Shock", "img": "img/w023.webp"} ]
}
```
- `id`: entero único. Para cartas nuevas usa `max(id) + 1`. **Nunca reutilices ni cambies un id** (lo usan `stock.csv`, `suelo.csv` y las fotos).
- `name`: nombre en español tal como sale en Cardmarket, sin el código entre paréntesis (`Exeggutor de Alola`, `Cambio`).
- `num`: número para ordenar (999 si no tiene). `numLabel`: lo que se muestra (`068/128`, `VIV 50`, `182`, `Código`).
- `set`: nombre de colección para mostrar. Filtros de la web: `"30th Celebration"`, `"Códigos online"`, cualquier otro = «Otras colecciones».
- `url`: página del producto en Cardmarket **sin parámetros** (es la clave para cruzar con las ofertas de Jose).
- `type`: `grass fire water lightning psychic fighting darkness metal dragon colorless trainer code` (solo decorativo si falta la foto; mira el símbolo de energía de la carta).
- `tag`: `""`, `"ex"`, `"Ilustración especial"` (número mayor que el total de la colección o arte completo), `"Classic"`.
- `toploader`: `true` si el comentario de la oferta menciona toploader.
- `price` / `qty`: valor inicial; los reales vienen de `stock.csv`.

### `stock.csv` (separador `;`, decimales con punto o coma)
```
id;carta;precio;cantidad
1;Azumarill 068/128;0.25;2
```

### `suelo.csv`
```
id;minimo;ofertas;fecha
1;0.02;35;25/09/2026
```
`minimo` vacío si no hay ofertas de otros vendedores.

---

## Reglas de Jose (no preguntes esto cada vez)

- Idioma de sus cartas: **Español**. Estado: **NM**.
- Comentario normal: `Fresh pack + sleeve. Añadiré el envío bien protegido.`
- Comentario para cartas caras (con toploader): `Fresh pack + sleeve + toploader. Envío bien protegido.`
- **Regla de precio para bulk**: tendencia × 1,5, redondeado **hacia arriba** a múltiplos de 0,05 €, **mínimo 0,25 €**.
  Quiere estar un poco por encima para no recibir pedidos de céntimos.
- **Cartas buenas (no bulk, tendencia ≳ 1 €)**: la tendencia de la guía de precios mezcla idiomas.
  Mira las ofertas **en español** (`?language=4&minCondition=2`) y propón precio; **Jose decide** (suele poner precios altos a propósito).
- Nunca publiques ni borres nada en Cardmarket por tu cuenta: Jose importa y publica.

## Navegador para Cardmarket (Cloudflare)

Cardmarket tiene Cloudflare y bloquea navegadores automatizados. Método que funciona:
1. Abrir Chrome **normal** con perfil propio y puerto de depuración:
   `chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\chrome-cardmarket"`
2. Jose pasa la verificación y, si hace falta, **inicia sesión en Cardmarket** en esa ventana (la sesión queda guardada en el perfil).
3. Conectar con Playwright: `chromium.connect_over_cdp("http://localhost:9222")` y usar esa pestaña/contexto.
4. **Esperar 15–20 segundos entre páginas.** Con menos, Cloudflare bloquea cada ~20 páginas.
5. Si sale Cloudflare a mitad: parar y pedir a Jose que lo resuelva en esa ventana.

Imágenes: la imagen principal está en `og:image` de la página del producto. La URL acaba en `.jpg` pero los bytes son **PNG**.
Convertir a WebP de 380 px de ancho, calidad 78 (Pillow) y guardar como `img/<id>.webp`.

---

## Flujo A — Listar una colección nueva en Cardmarket

1. Jose dice la colección (ej. «Mega Evolución 3»). Localiza su página de listado masivo:
   `https://www.cardmarket.com/es/Pokemon/Stock/ListingMethods/BulkListing` (elegir la expansión).
2. **Dictado**: Jose dicta con el dictado de Windows (Win+H), p. ej. «carta 012 tengo dos, carta 047 tengo una reverse».
   Acepta números con o sin ceros, en cifra o en palabra, en varios mensajes, hasta que diga «ya está».
   Si aparece un número suelto o raro, pregunta.
3. Lee **todas las páginas del listado masivo** de esa colección (texto de la tabla). Cada fila tiene el nombre exacto con código y número,
   p. ej. `Exeggutor de Alola (30C 002)`, y a veces el nombre en inglés debajo. Apunta en qué página está cada número.
   Las ilustraciones especiales y promos tienen el mismo nombre con otro número: **el número es lo único que las distingue**.
4. Enseña a Jose una tabla de verificación: número → carta → cantidad → precio propuesto. Espera su OK.
5. Precios: descarga la guía de precios de `https://www.cardmarket.com/es/Pokemon/Data/Price-Guide` (y el catálogo en `Data/Product-List`)
   o lee la tendencia en la página de cada producto. Aplica la regla de bulk; las cartas buenas, propón y que decida Jose.
6. Genera **un CSV por página** del listado masivo (solo con las cartas de esa página), separador `,`:
   `Name,Quantity,Price,Condition,Language,Comment` con `Name` = nombre **exacto** de la tabla incluido el código
   (`Lapras (30C 017)`), `Condition` = `NM`, `Language` = `Spanish`.
   Motivo: la extensión «Cardmarket Bulk Import» empareja por nombre **solo en la página abierta**; si la carta no está en esa página
   coge la más parecida (p. ej. la versión especial) y la lista a precio de bulk. Ya pasó una vez.
7. Instrucciones para Jose, por cada página: abrir esa página → importar su CSV → comprobar en la vista previa que los números coinciden →
   rellenar → revisar → **publicar antes de cambiar de página**.
8. Cuando haya publicado, sigue con el Flujo B.

## Flujo B — Sincronizar la web con Cardmarket («sincroniza»)

1. Con la sesión de Jose iniciada en el Chrome del puerto 9222, lee **todas las páginas** de *Vender → Mis ofertas*
   (la página de stock propio de Cardmarket; compruébala navegando desde el menú Vender la primera vez y apunta aquí la URL: `URL_MIS_OFERTAS = ____`): nombre, url del producto, precio, cantidad y comentario de cada oferta.
   Si una carta tiene varias ofertas (mismo url), suma cantidades y usa el precio más bajo.
2. Cruza por `url` (sin parámetros) con `cartas.json`:
   - **Nueva** → añade entrada a `cartas.json` (ver formato), descarga su foto a `img/<id>.webp`, añádela a `stock.csv`.
   - **Existente** → actualiza precio y cantidad en `stock.csv` (y en `cartas.json`).
   - **Está en la web pero ya no en Cardmarket** → cantidad **0** en `stock.csv` (sale como «Agotada»). No la borres.
3. Si ha cambiado el stock, ofrece regenerar el suelo (Flujo C).
4. Resumen para Jose: cartas nuevas, precios cambiados, agotadas, total del stock. Tras su OK: `git add -A && git commit && git push`.
5. Comprueba la web en local antes del push si ha habido cambios grandes: `python -m http.server` y abrir `http://localhost:8000`.

## Flujo C — Suelo («actualiza el suelo»)

Para cada carta con cantidad > 0 en `stock.csv`: abre su `url` + `?language=4&minCondition=2`
(los «Código Live» sin filtro de idioma), coge la oferta más barata **ignorando las del propio Jose**
(pregúntale su usuario de Cardmarket la primera vez y apúntalo aquí: `USUARIO_CM = ____`), cuenta las ofertas de otros vendedores
y escribe `suelo.csv`. 15–20 s entre cartas. Comprueba 2–3 a mano antes de hacerlas todas. Después commit + push.

## Flujo D — Cartas buscadas para intercambio

Lista `buscadas` de `cartas.json`: `num`, `attack` (texto pequeño bajo el nombre) e `img` (`img/w<num>.webp`, foto descargada de su página de Cardmarket).
Si Jose consigue una, quítala de la lista.

---

## Cosas que ya se aprendieron (evita repetir errores)

- El archivo de productos de Cardmarket **no trae el número de carta**; no deduzcas el número por el orden de `idProduct` sin comprobar.
- La tendencia de la guía de precios mezcla todos los idiomas: en español suele ser distinta.
- Ofertas en el carrito de un comprador no se pueden borrar hasta que se liberan.
- Si Cloudflare bloquea, no reintentes en bucle: para y avisa a Jose.
- No toques `config.json` a mano ni lo sobrescribas al subir archivos.
