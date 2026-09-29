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
| `intercambio.html` | Página privada (no enlazada): herramienta de intercambios (Recibo/Doy, balanza, «Cuadrar», PDF de propuesta). Lee `cartas.json`, `stock.csv` y `suelo.csv`. | Casi nunca |
| `cartas.json` | **Catálogo**: datos fijos de cada carta + lista de cartas **deseadas** (mi colección de Pikachu + candidatas para cambios). | Claude Code al añadir cartas |
| `stock.csv` | **Precio y cantidad** de cada carta (manda sobre `cartas.json`). Cantidad 0 = «Agotada». | Jose o Claude Code |
| `suelo.csv` | Precio más barato de otros vendedores en Cardmarket (idioma de la carta, NM). | Claude Code |
| `suelo_pendiente.csv` | Suelos mirados al listar cartas que aún no tienen id (`url;minimo;ofertas;fecha`). Pasan a `suelo.csv` en el Flujo B. | Claude Code |
| `config.json` | Modo de precios (normal / rebajas). **No lo sobrescribas**: lo gestiona el botón de `informe.html` vía `api/modo.js`. | Botón del informe |
| `img/<id>.webp` | Foto de cada carta. `img/w<num>.webp` = fotos de cartas deseadas. `img/30c/<código>.webp` = resto de la colección 30th Celebration. | Claude Code |
| `data/colecciones/<codigo>.json` | Colecciones completas preparadas (`pgo` Pokémon GO en inglés, `brs` Astros Brillantes en español): `codigo`, `nombre`, `idioma`, `filtro` y `cartas` (`num`, `nombre`, `url`, `img`, `suelo`, `ofertas`, `fecha`). Fotos en `img/<codigo>/`. Las genera `data/colecciones/preparar_colecciones.py` (desatendido; log en `progreso.log`, que no se sube). | Claude Code |
| `ventas_pendientes_cm.csv` | Ventas hechas fuera de Cardmarket («vendí el X», Flujo F) cuya oferta aún hay que quitar o bajar en Cardmarket (`fecha;carta;url;cantidad`). | Claude Code |
| `data/revision/` | Scripts de solo lectura contra Cardmarket: `revisar_suelo.py` (revisión nocturna del suelo) y `comprobar.py` («comprueba», Flujo E). Sus logs y progreso no se suben. | Casi nunca |
| `idiomas.js` | Banderas en SVG, nombres de idioma y la etiqueta «bandera + código» (web y, como imagen, en los PDF). Lo cargan `index.html`, `informe.html` e `intercambio.html`. | Casi nunca |
| `api/modo.js` | Función de Vercel que edita `config.json` en GitHub (variables `GITHUB_TOKEN`, `GITHUB_REPO`). | Nunca |

### `cartas.json`
```json
{
  "cartas": [
    {"id": 1, "name": "Azumarill", "num": 68, "numLabel": "068/128", "set": "30th Celebration", "idioma": "es",
     "url": "https://www.cardmarket.com/es/Pokemon/Products/Singles/30th-Celebration/Azumarill-30C068",
     "price": 0.25, "qty": 2, "type": "psychic", "tag": "", "toploader": false, "img": "img/1.webp"}
  ],
  "deseadas": [
    {"num": "023", "nombre": "Pikachu", "numLabel": "023/128", "set": "30th Celebration",
     "url": "https://www.cardmarket.com/es/Pokemon/Products/Singles/30th-Celebration/Pikachu-30C023",
     "img": "img/w023.webp", "attack": "Thunder Shock", "tag": "", "en_coleccion": true,
     "suelo": 0.54, "ofertas": "50+", "fecha": "27/09/2026"}
  ],
  "coleccion_30c": [
    {"num": "BS 58", "nombre": "Pikachu", "numLabel": "BS 58", "tipo": "classic", "tag": "Classic",
     "url": "https://www.cardmarket.com/es/Pokemon/Products/Singles/30th-Celebration/Pikachu-30CBS-58",
     "img": "img/30c/BS-58.webp", "suelo": 25.0, "ofertas": "12", "fecha": "27/09/2026"}
  ]
}
```
- `id`: entero único. Para cartas nuevas usa `max(id) + 1`. **Nunca reutilices ni cambies un id** (lo usan `stock.csv`, `suelo.csv` y las fotos).
- `name`: nombre en español tal como sale en Cardmarket, sin el código entre paréntesis (`Exeggutor de Alola`, `Cambio`).
- `num`: número para ordenar (999 si no tiene). `numLabel`: lo que se muestra (`068/128`, `VIV 50`, `182`, `Código`).
- `set`: nombre de colección para mostrar. Filtros de la web: `"30th Celebration"`, `"Códigos online"`, cualquier otro = «Otras colecciones».
- `idioma`: `es en fr de it pt ja ko zh` (código de la bandera de la oferta en Cardmarket). Si falta, se entiende `es`.
  La web pone en la esquina de cada foto una etiqueta con la bandera y el código (las que no son `es` salen oscuras con borde dorado),
  hay filtro por idioma, y los PDF y Excel de stock/informe/intercambio también lo muestran.
- `url`: página del producto en Cardmarket **sin parámetros**. Junto con `idioma` es la clave para cruzar con las ofertas de Jose.
- `type`: `grass fire water lightning psychic fighting darkness metal dragon colorless trainer code` (solo decorativo si falta la foto; mira el símbolo de energía de la carta).
- `tag`: `""`, `"ex"`, `"Ilustración especial"` (número mayor que el total de la colección o arte completo), `"Classic"`.
- `foil` (opcional, solo cartas con efecto fuerte): patrón del foil en la web: `"holo"` (bandas arcoíris verticales),
  `"textura"` (relieve tipo huella dactilar: surcos finos y concéntricos con 3–5 remolinos, generado por código con semilla fija
   por id y en caché; casi invisible de frente, se ve al inclinar; en la ampliada también es el mapa de relieve de la luz), `"cosmos"` (destellos pequeños) u `"oro"` (secretas doradas). Si falta:
  `textura` en `Ilustración especial`, `holo` en el resto. Zona: toda la carta en textura/oro, ilustraciones especiales y
  ex/V/VSTAR/V-ASTRO/VMAX/GX; en las demás solo el recuadro de la ilustración. El brillo sigue la luminosidad de la foto
  (intenso en lo claro, casi nulo en lo oscuro). En la vista ampliada, además: relieve con luz real (filtro SVG), canto brillante
  y sombra al lado contrario. Pregunta a Jose el `foil` de las cartas cosmos u oro al añadirlas.
- `holo` (opcional): `"fuerte"`, `"suave"` o `"ninguno"`. Si existe, manda sobre las reglas del efecto de la web (solo para casos concretos).
  Efecto de las fotos en la web (3D al pasar el ratón, ampliada al pulsar), por orden: agotada → ninguno; campo `holo`; colección en
  `config.json` > `colecciones_holo` (todas sus cartas son holo; se compara con `set` y con la edición de la url, así las Classic
  Collection de `/30th-Celebration/` cuentan) → fuerte; si no, fuerte en `Ilustración especial`, `ex` y nombres que acaban en
  ex/V/VSTAR/V-ASTRO/VMAX/GX, y suave (solo inclinación y reflejo) en el resto. Respeta «reducir movimiento» del sistema.
- `toploader`: `true` si el comentario de la oferta menciona toploader.
- `price` / `qty`: valor inicial; los reales vienen de `stock.csv`.
- `deseadas` (Flujo D): cartas que Jose aceptaría recibir. **`en_coleccion`** lo controla Jose y es independiente de su stock a la venta:
  `true` = ya la tiene en su colección («Ya tengo»), `false` = le falta («Me falta»; son las que salen en la web pública,
  «Busco para intercambio»), `null` = neutra (sin etiqueta), para una candidata que no forme parte de su colección.
  `attack`: ataque(s) de la carta, para distinguir versiones.
  `suelo` / `ofertas` / `fecha`: suelo en español NM (mismas reglas del Flujo C); `suelo` es `null` si no hay ofertas.
  Fotos en `img/w<num>.webp` (380 px, calidad 78); si la carta ya está en el stock, usa su foto `img/<id>.webp`.
- `coleccion_30c`: **todas** las cartas de 30th Celebration (191: 128 normales, 30 ilustraciones especiales `tipo: especial`,
  33 Classic Collection `tipo: classic` con código tipo `BS 58`). Sale del listado masivo de la expansión «Celebración 30.º Aniversario»
  (`idExpansion=6601`, 2 páginas). Foto: la del stock o la de la deseada si existe; si no, `img/30c/<código>.webp` (código sin espacios
  ni barras: `BS-58`, `R-RGB`). `suelo`/`ofertas`/`fecha` con las reglas del Flujo C. Se usa en `intercambio.html` para marcar
  las cartas disponibles de la otra persona.

### `stock.csv` (separador `;`, decimales con punto o coma)
```
id;carta;precio;cantidad;agotada_desde
1;Azumarill 068/128;0.25;2;
62;Raikou VIV 50;20.00;0;28/09/2026
```
`agotada_desde` (dd/mm/aaaa): fecha en que la carta pasó a cantidad 0; vacía si hay stock. Durante `dias_agotada` días (en `config.json`,
14 por defecto) la carta agotada sigue en su sitio en la web (también en Destacadas si lo era), en gris y con el sello «Agotada»;
después pasa al final de la lista y sale de Destacadas. Los totales, PDF y Excel nunca cuentan las agotadas.

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

## Precios web frente a Cardmarket (regla fija)

- **La web es para gente de confianza y SIEMPRE es igual o más barata que Cardmarket.**
- **El precio de Cardmarket es el de `stock.csv`**: el de Jose, alto a propósito. **Nunca se toca en automático** (ni scripts ni
  revisiones de suelo); solo cambia si Jose lo pide o al sincronizar con sus ofertas reales (Flujo B).
- **Cómo sale el precio web** (lógica de `applyMode()` en `index.html`, comprobada el 29/09/2026): se parte del precio de `stock.csv`.
  Si `config.json` tiene `"modo": "suelo"` y la carta tiene un suelo numérico en `suelo.csv` (y no se pasa del `tope`, cuando
  `tope` > 0), se calcula `objetivo = max(minimo, redondeo_a_céntimos(suelo × (1 + porcentaje/100) + ajuste))`; si
  `objetivo` < precio de `stock.csv`, la web muestra `objetivo` (tachando el de stock); si no, muestra el de stock.
  Con `modo` distinto de `suelo`, la web muestra el precio de `stock.csv`. Con la configuración actual (0 %, mínimo 0,02 €, sin
  ajuste ni tope) el precio web es **el menor entre el precio de `stock.csv` y el suelo**, así que nunca supera a Cardmarket.
  `informe.html` calcula su columna «Precio web ahora» con la misma regla.
- **Revisiones de suelo**: comparan **suelo NUEVO frente a suelo ANTERIOR** (`git show HEAD:suelo.csv`) y calculan el precio web
  antes y después con la lógica de arriba (leyendo `index.html`, no de memoria). **No comparan con `stock.csv`.**
- **Por defecto, «solo subidas»** (opción b): las cartas cuyo precio web sube (o se queda igual) toman el suelo nuevo; en las que
  bajarían se deja la fila anterior de `suelo.csv` tal cual (suelo, ofertas y fecha). **Solo se aplican bajadas si Jose lo pide
  expresamente** («aplica todo»).
- En el informe de cambio de suelo, marca con **⚠ «tope»** las cartas cuyo **suelo nuevo ≥ su precio de `stock.csv`**: ahí la web ya
  está igual que Cardmarket y quizá a Jose le interese subir el precio en Cardmarket (él decide; no se toca `stock.csv`).

## Navegador para Cardmarket (Cloudflare)

Cardmarket tiene Cloudflare y bloquea navegadores automatizados. Método que funciona:
1. Abrir Chrome **normal** con perfil propio y puerto de depuración:
   `chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\chrome-cardmarket"`
2. Jose pasa la verificación y, si hace falta, **inicia sesión en Cardmarket** en esa ventana (la sesión queda guardada en el perfil).
3. Conectar con Playwright: `chromium.connect_over_cdp("http://localhost:9222")` y usar esa pestaña/contexto.
4. **Esperar 15–20 segundos entre páginas.** Con menos, Cloudflare bloquea cada ~20 páginas.
5. Si sale Cloudflare a mitad: parar y pedir a Jose que lo resuelva en esa ventana.
6. **Scripts desatendidos** (p. ej. `data/colecciones/preparar_colecciones.py`): ante Cloudflare esperan 10 min y recargan, hasta 12 veces.
   Si sigue, quedan **en pausa** así: **cierran la conexión CDP** (Chrome sigue abierto; con la automatización enganchada el
   «no soy un robot» a veces ni carga), **abren la verificación en una pestaña nueva** lanzando `chrome.exe` con el mismo perfil
   (`--remote-debugging-port=9222 --user-data-dir="C:\chrome-cardmarket"`) y comprueban cada 30 s, **sin conectarse**, la lista
   de pestañas en `http://localhost:9222/json/list`. Cuando una pestaña de Cardmarket ya no está en «Un momento…», se reconectan solas
   y siguen. Si Chrome se cierra, esperan a que se vuelva a abrir con ese comando. Todo queda en el log.

Imágenes: la imagen principal está en `og:image` de la página del producto. La URL acaba en `.jpg` pero los bytes son **PNG**.
Convertir a WebP de 380 px de ancho, calidad 78 (Pillow) y guardar como `img/<id>.webp`.

---

## Flujo A — Listar una colección nueva en Cardmarket

1. Jose dice la colección (ej. «Mega Evolución 3»). **Pregúntale si todas sus cartas son holo**: si dice que sí, añade su nombre
   (como se escribe en `set`) a `colecciones_holo` de `config.json` para que la web les ponga el efecto fuerte.
   Localiza su página de listado masivo:
   `https://www.cardmarket.com/es/Pokemon/Stock/ListingMethods/BulkListing` (elegir la expansión).
2. **Dictado**: Jose dicta con el dictado de Windows (Win+H), p. ej. «carta 012 tengo dos, carta 047 tengo una reverse».
   Acepta números con o sin ceros, en cifra o en palabra, en varios mensajes, hasta que diga «ya está».
   Si aparece un número suelto o raro, pregunta.
3. Lee **todas las páginas del listado masivo** de esa colección (texto de la tabla). Cada fila tiene el nombre exacto con código y número,
   p. ej. `Exeggutor de Alola (30C 002)`, y a veces el nombre en inglés debajo. Apunta en qué página está cada número.
   Las ilustraciones especiales y promos tienen el mismo nombre con otro número: **el número es lo único que las distingue**.
4. **Modo de precio**: pregúntalo **siempre** al empezar una colección nueva (no lo des por supuesto):
   - **«regla»**: tendencia × 1,5 redondeado hacia arriba a múltiplos de 0,05 €, mínimo 0,25 € (la regla de bulk de siempre).
   - **«suelo»**: para cada carta abre su `url` + `?language=4&minCondition=2`, coge la oferta más barata de **otros** vendedores
     (ignorando las de `USUARIO_CM`) y pon ese precio **+ el % que diga Jose** (0 % si no dice nada), redondeado hacia arriba al céntimo,
     con el **mínimo que diga Jose** (0,25 € por defecto). Si no hay ofertas en español, usa la «regla» para esa carta y avísale.
     **15–20 s entre cartas.** Cómo leer el suelo: ver «Cómo leer el suelo de una carta» en el Flujo C.
     **Si la colección ya está en `data/colecciones/`** (mismo idioma): mira la `fecha` de sus suelos. Si tienen **menos de 7 días**,
     úsalos directamente (cruza por `url`, y por número si hace falta) **sin volver a consultar Cardmarket**, y díselo a Jose en la tabla
     de verificación («suelo del dd/mm»). Si son **más antiguos**, pregúntale si los actualiza antes (lo hace el script con
     `--actualizar <codigo>`, ver Flujo C) o si usa los que hay.
   - **«manual»**: propón precio para cada carta y Jose decide carta a carta.

   Se pueden mezclar, p. ej. «suelo +10 %, mínimo 0,25, pero las de más de 5 € enséñamelas antes»: aplica el modo y separa las excepciones
   para que Jose las decida. La tendencia sale de la tabla del listado masivo (campo oculto `trendPrice` de cada fila) o de la página del producto.
5. Enseña a Jose una tabla de verificación: número → carta → cantidad → **tendencia** → **suelo en español** (y nº de ofertas, si lo has mirado)
   → **precio propuesto**. Espera su OK.
   Los suelos que mires guárdalos en `suelo_pendiente.csv` (`url;minimo;ofertas;fecha`, url sin parámetros): las cartas aún no tienen id,
   así que pasan a `suelo.csv` en el Flujo B cuando se les asigna. Así el informe queda actualizado sin volver a consultarlos.
6. Genera **un CSV por página** del listado masivo (solo con las cartas de esa página), separador `,`, y guárdalo en **Descargas**
   (`C:\Users\Jose\Downloads\<coleccion>-pagina<N>.csv`):
   `Name,Quantity,Price,Condition,Language,Comment` con `Name` = nombre **exacto** de la tabla incluido el código
   (`Lapras (30C 017)`), `Condition` = `NM`, `Language` = `Spanish`.
   Motivo: la extensión «Cardmarket Bulk Import» empareja por nombre **solo en la página abierta**; si la carta no está en esa página
   coge la más parecida (p. ej. la versión especial) y la lista a precio de bulk. Ya pasó una vez.
7. Instrucciones para Jose, por cada página: abrir esa página → importar su CSV → comprobar en la vista previa que los números coinciden →
   rellenar → revisar → **publicar antes de cambiar de página**.
8. Cuando haya publicado, sigue con el Flujo B.

## Flujo B — Sincronizar la web con Cardmarket («sincroniza»)

1. Con la sesión de Jose iniciada en el Chrome del puerto 9222, lee **todas las páginas** de *Vender → Mis ofertas*
   (la página de stock propio de Cardmarket; compruébala navegando desde el menú Vender la primera vez y apunta aquí la URL: `URL_MIS_OFERTAS = https://www.cardmarket.com/es/Pokemon/Stock/Offers/Singles` (20 ofertas por página, `?site=N`)): nombre, url del producto, precio, cantidad y comentario de cada oferta.
   Lee también el **idioma** de cada oferta (su bandera: `aria-label` «Español», «Inglés»…).
   Si una carta tiene varias ofertas (mismo url **y mismo idioma**), suma cantidades y usa el precio más bajo.
   **La misma carta en otro idioma es otra entrada** de `cartas.json` (id nuevo, mismo url, otro `idioma`).
2. Cruza por `url` (sin parámetros) **+ `idioma`** con `cartas.json`:
   - **Nueva** → añade entrada a `cartas.json` (ver formato), descarga su foto a `img/<id>.webp`, añádela a `stock.csv`.
     Si su url está en `suelo_pendiente.csv`, pasa esa fila a `suelo.csv` con el id nuevo y quítala de `suelo_pendiente.csv`.
   - **Existente** → actualiza precio y cantidad en `stock.csv` (y en `cartas.json`).
   - **Está en la web pero ya no en Cardmarket** → cantidad **0** en `stock.csv` (sale como «Agotada») y `agotada_desde` = fecha de hoy
     (solo si estaba vacía: no la cambies si ya estaba agotada). No la borres.
   - **Vuelve a tener stock** una agotada → cantidad nueva y `agotada_desde` vacía.
   - **Está en `ventas_pendientes_cm.csv`** y sigue en Cardmarket → **no** le vuelvas a poner stock en la web (resta lo vendido a la
     cantidad de Cardmarket) y avisa a Jose de que aún tiene que quitarla o bajarla allí. Cuando ya no esté en Cardmarket (o la
     cantidad ya refleje la venta), quítala de `ventas_pendientes_cm.csv`.
   - Lo mismo si Jose dice que ha vendido una carta fuera de Cardmarket («X vendida»): cantidad 0 y `agotada_desde` = hoy.
3. Si ha cambiado el stock, ofrece regenerar el suelo (Flujo C).
4. Resumen para Jose: cartas nuevas, precios cambiados, agotadas, total del stock. Tras su OK: `git add -A && git commit && git push`.
5. Comprueba la web en local antes del push si ha habido cambios grandes: `python -m http.server` y abrir `http://localhost:8000`.

## Flujo C — Suelo («actualiza el suelo»)

**Pregunta siempre primero qué quiere actualizar**, con lo que tarda cada opción (páginas de Cardmarket que hay que abrir;
~25 s por página y Cloudflare cada ~20 páginas: si Jose lo resuelve al momento son 1–2 min; desatendido, 10 min o más cada vez).
Recalcula las páginas con los datos del momento; a 28/09/2026 eran:

| Opción | Dónde se guarda | Páginas | Con Jose delante | Desatendido |
|---|---|---|---|---|
| Mi stock (cantidad > 0) | `suelo.csv` | 92 | ~45 min | ~1 h 20 min |
| Deseadas | `cartas.json` > `deseadas` | 30 | ~15 min | ~30 min |
| 30th Celebration completa | `cartas.json` > `coleccion_30c` | 191 | ~1 h 30 min | ~2 h 45 min |
| Pokémon GO (inglés) | `data/colecciones/pgo.json` | 109 | ~50 min | ~1 h 40 min |
| Astros Brillantes (español) | `data/colecciones/brs.json` | 245 | ~1 h 55 min | ~3 h 45 min |
| Todo (cada carta una sola vez) | todos los anteriores | 549 | ~4 h 30 min | ~8 h |

Una carta que esté en varias listas se consulta una sola vez y se escribe en todas. Para Pokémon GO y Astros Brillantes (o varias a la vez
y desatendido) usa el script: `python -X utf8 data/colecciones/preparar_colecciones.py --actualizar pgo brs` lanzado en segundo plano
con el Python real (`C:\Users\Jose\AppData\Local\Programs\Python\Python313\python.exe`, no el acceso directo de WindowsApps).

Para cada carta con cantidad > 0 en `stock.csv`: abre su `url` + `?language=N&minCondition=2` con **el idioma de la carta**
(`N`: en 1, fr 2, de 3, es 4, it 5, zh 6, ja 7, pt 8, ko 10; está en `IDIOMAS.CM` de `idiomas.js`; los «Código Live» sin filtro de idioma), coge la oferta más barata **ignorando las del propio Jose**
(su nombre de vendedor en Cardmarket: `USUARIO_CM = BePokemon`)
y apunta el suelo nuevo. **Haz lo mismo con todas las `deseadas` y toda la `coleccion_30c` de `cartas.json`** (campos `suelo`, `ofertas`, `fecha`),
para que `intercambio.html` tenga los valores al día (una carta que esté en varias listas se consulta una sola vez; son unas 190 páginas,
más de una hora: avisa a Jose antes y guarda el progreso para poder seguir si salta Cloudflare). 15–20 s entre cartas. Comprueba 2–3 a mano antes de hacerlas todas.

**Revisión de suelo de mi stock** (también «revisión de suelo»; sigue la sección «Precios web frente a Cardmarket»):
1. Lee los suelos: desatendido con `python -X utf8 data/revision/revisar_suelo.py` (Python real, en segundo plano; reanudable, 30–40 s
   entre páginas, reutiliza suelos de hoy o ayer en el mismo idioma, pausa por Cloudflare como en «Navegador»). **Sin `--subir-stock`**:
   así solo escribe `suelo.csv` y su informe; `stock.csv` y `cartas.json` no se tocan. `--subir-stock` solo si Jose lo pide expresamente.
2. Compara `git show HEAD:suelo.csv` (anterior) con el `suelo.csv` nuevo y calcula para cada carta con stock el precio web antes y
   después con la lógica de `applyMode()` de `index.html` (léela) y `config.json`.
3. Informe en el chat y en `Descargas\cambio_suelo_AAAA-MM-DD.html` (fotos incrustadas): 🟢 SUBE (suelo anterior con su fecha, suelo
   nuevo, precio web antes → después, diferencia en € y × cantidad; arriba el total que gana la web), 🟡 IGUAL (cuántas),
   🔴 BAJA (lo mismo que SUBE). Marca con ⚠ «tope» las que tienen suelo nuevo ≥ precio de `stock.csv`.
4. Aplica por defecto **solo subidas**: en las 🔴 restaura en `suelo.csv` su fila de `HEAD`. Comprueba después con la misma lógica que
   no baja ningún precio web. Bajadas, solo si Jose lo pide.
5. Resumen para Jose y **commit + push solo tras su «sí»**. Nunca se toca `stock.csv`, `config.json` ni Cardmarket.

**Cómo leer el suelo de una carta** (también para el modo «suelo» del Flujo A):
- **No pulses «Mostrar más resultados».** Las ofertas vienen ordenadas de más barata a más cara: el suelo es la **primera oferta
  que no sea de Jose** en la primera carga de la página.
- Solo si **todas** las ofertas de la primera carga son de Jose, pulsa «Mostrar más» **una vez**.
- Número de ofertas (`ofertas`): cuenta las **filas de otros vendedores en la primera carga** (ya filtrada en español NM).
  Si hay botón «Mostrar más», escribe ese número seguido de `+` (p. ej. `25+`). Es solo orientativo.
  **No uses «Artículos disponibles»** de la ficha: cuenta todos los idiomas y estados.

## Flujo D — Intercambios (deseadas + `intercambio.html`)

- Lista `deseadas` de `cartas.json` (formato arriba): **los Pikachu 023–052 de 30th Celebration**, que son la colección de Jose.
  Los Pikachu ex 053–054 **no** están en `deseadas` (no forman parte de su colección; siguen en `coleccion_30c`). A 28/09/2026 le faltan
  **046, 047 y 050** (`en_coleccion: false`); el resto de 023–052 los tiene (`true`). Para añadir una deseada: url del producto,
  foto a `img/w<num>.webp` (imagen de `og:image` o del listado masivo), su suelo (reglas del Flujo C) y `en_coleccion` según diga Jose.
- **Cuando Jose diga «ya tengo el X»** → pon `en_coleccion: true` en la deseada X; **«me falta el X»** → `en_coleccion: false`.
  Después **commit y push** sin esperar más confirmación (es su propia lista; cambia la sección pública «Busco para intercambio»).
  Si X no está en `deseadas` o es ambiguo (varias versiones), pregunta antes.
- `intercambio.html` (privada, sin enlace desde la web; mismo estilo que `informe.html`):
  - «Recibo» = deseadas, «Doy» = stock con cantidad > 0. Valor de cada carta = su suelo en español (si una carta del stock no tiene suelo,
    su precio de venta; si una deseada no tiene suelo, 0). Cualquier valor se puede cambiar a mano (sale con `*` en el PDF).
  - Balanza: totales y diferencia en € y en % sobre lo que doy.
  - «Cuadrar»: busca combinaciones de 1–3 cartas que acerquen la diferencia a 0 (de las deseadas si recibo menos; del stock si doy menos)
    y enseña las 3 mejores (distintas entre sí) con botón «Añadir». Orden: **primero la que más se acerca a 0** (al céntimo);
    si empatan, la que tenga más cartas «me falta» (en Recibo; **solo las de `en_coleccion: false`**, las demás son moneda de cambio
    igual que el resto) o más bulk < 1 € (en Doy); luego la de menos cartas.
    Ej.: si faltan 1,40 € y un Pikachu que ya tengo vale 1,40 €, sale el primero.
  - Opción «Cuadrar usando mis cartas de hasta X €» (2 € por defecto; vacío o 0 = sin límite): en el lado «Doy» no propone cartas más caras.
  - Campo «Nombre de la otra persona»: las columnas pasan a «Recibo de [nombre]» / «Doy a [nombre]».
  - «Descargar propuesta en PDF»: `propuesta-intercambio_[nombre]_AAAA-MM-DD_HH-MM.pdf` (nombre sin tildes ni espacios).
    **Lo lee la otra persona**: texto neutro, desde fuera. Columnas «[nombre] da» / «BePokemon da» (Jose firma como BePokemon); nada de «doy/recibo» ni negativos en rojo.
    Título «Propuesta de intercambio con [nombre]», franja «[nombre] da N cartas · X € | BePokemon da N cartas · Y € | Diferencia Z €»
    y debajo (solo ahí, no se repite en las opciones) la frase «Para igualar, faltarían Z € por parte de [nombre]» (o «por mi parte»). Cartas en cuadrícula (3 por fila, o 4 si no cabe),
    con nombre, número y valor debajo. «Opciones para cuadrar»: las 3 combinaciones en fila (Opción 1-3, fotos grandes, quién las
    añadiría y cómo quedaría); si Jose añadió una con «Cuadrar», sale como Opción 1 con la marca ELEGIDA y las otras son alternativas
    calculadas sin ella. Las opciones nunca se parten: si no caben en la primera página, van enteras a la segunda.
    Pie: «Enviado por BePokemon · Responde con el número de opción que prefieras (o propón otra)».
  - «Cuadrar» nunca sugiere una carta que ya esté en Recibo o en Doy (se compara por url).
  - «Cartas disponibles de [nombre]» (en la columna Recibo): **selector de colección** (30th Celebration de `coleccion_30c`, y las de
    `data/colecciones/`: Pokémon GO en inglés y Astros Brillantes en español), cada una con su rejilla (foto con la bandera de su idioma,
    número y suelo), buscador y «Pegar números» (acepta `012, 047, 88 131` y códigos como `BS 58` o `TG16`; si un número tiene varias
    versiones en Cardmarket marca la primera y lo avisa). Las marcadas de todas las colecciones se suman; contador «X cartas disponibles · Y €».
    Se guardan **por persona** (al volver a escribir su nombre se recuperan). Para añadir otra colección: su JSON en `data/colecciones/`
    y una línea en la lista de `intercambio.html` (buscar `data/colecciones/pgo.json`).
  - Cartas **sin suelo**: salen como «sin precio» y «Cuadrar» no las usa hasta que Jose les pone un valor a mano (campo € en la propia
    carta marcada, o en la lista de Recibo).
  - Si la otra persona tiene disponibles marcadas, «Cuadrar» saca sus opciones **solo de esas** (cualquier carta, no solo Pikachu);
    usa **todas las marcadas de todas las colecciones**; en empate, primero las que me faltan y los Pikachu. Si no hay ninguna marcada,
    usa las deseadas como siempre.
    El PDF no enseña la lista de disponibles, solo las opciones.
  - **«Cómo se compensa la diferencia»**: «Con cartas» (Cuadrar, como siempre) o «Con dinero». En modo dinero no hay «Cuadrar» y sale un
    recuadro «[nombre] paga a BePokemon X €» (o al revés) con: redondeo (sin / 0,10 / 0,50 / euro entero, con el exacto al lado), importe
    a mano (sustituye al calculado, sale con *), envío opcional (importe y quién lo paga; se suma o resta) y método de pago (texto libre).
    El desglose va siempre en el mismo sentido: + paga la otra persona, − paga BePokemon.
  - En «Con cartas», si tras añadir una opción queda una diferencia pequeña (≤ 1 € o ≤ 10 % del lado mayor), sale «Diferencia restante:
    X € → la paga Y» con botón para pagarla en dinero; el PDF lo indica bajo la franja y en la opción elegida.
  - PDF en modo dinero: `resumen-intercambio_[nombre]_AAAA-MM-DD_HH-MM.pdf`, título «Resumen de intercambio con [nombre]», columnas y
    franja como siempre y, en lugar de las opciones, el bloque «Compensación en dinero» (quién paga, importe grande, desglose, método).
    Pie: «Enviado por BePokemon · Valores según el precio más bajo en Cardmarket (idioma de cada carta, NM) a fecha X». Una página.
  - La selección, el nombre, el límite, la opción elegida, las disponibles de cada persona y las opciones de dinero se guardan en el navegador (localStorage).

## Flujo E — «comprueba» (web frente a Cardmarket)

**Solo lectura**: no cambies nada en la web ni en Cardmarket.
1. Lanza `python -X utf8 data/revision/comprobar.py` (Python real). Lee **todas** las páginas de `URL_MIS_OFERTAS` (como en
   «sincroniza», 30–40 s entre páginas, misma gestión de Cloudflare que los scripts desatendidos; si pide iniciar sesión, para y
   pídeselo a Jose). Cruza por `url` (+ idioma) con `cartas.json` y `stock.csv`, y calcula el precio web con la lógica de `applyMode()`.
   Deja `data/revision/comprobacion.json` y `Descargas\comprobacion_AAAA-MM-DD.html` (con enlaces a la página de Mis ofertas
   donde está cada oferta, para pulsar «Editar», y a la ficha del producto en su idioma).
2. Enseña en el chat una tabla por cada tipo de problema, en este orden:
   - 🔴 Vendidas fuera de Cardmarket (`ventas_pendientes_cm.csv`) que **siguen publicadas**: las primeras.
   - 🔴 **URGENTE**: cantidad 0 en la web pero publicada en Cardmarket (me la pueden comprar y ya no la tengo).
   - 🟠 Cantidad distinta entre la web y Cardmarket.
   - 🟠 Precio de `stock.csv` distinto del precio real de la oferta en Cardmarket.
   - 🟠 Precio que se ve en la web **mayor** que el de Cardmarket (rompe la regla fija; menor es lo normal).
   - 🟡 Con stock en la web pero no publicada en Cardmarket.
   - 🟡 Publicada en Cardmarket pero no está en la web.
   - 🟡 Ofertas raras: idioma distinto del de `cartas.json`, estado distinto de NM, carta de más de 5 € sin «toploader» en el
     comentario, o la misma carta en dos ofertas.
3. Si todo cuadra, dilo en una línea.
4. Pregunta a Jose qué quiere arreglar. **Nunca borres ni cambies nada en Cardmarket** (lo hace él); en la web, solo lo que confirme.

## Flujo F — «vendí el X» (venta fuera de Cardmarket, por sus grupos)

1. Busca la carta por nombre o número. Si hay varias posibles (versiones, idiomas, colecciones), pregunta cuál.
2. Resta la cantidad vendida en `stock.csv` (1 si no dice nada). Si queda en 0, pon `agotada_desde` = hoy.
3. Apúntala en `ventas_pendientes_cm.csv` (`fecha;carta;url;cantidad`) y dale el enlace de su oferta en Cardmarket
   (página de `URL_MIS_OFERTAS` donde está, o la ficha del producto) para quitarla o bajar la cantidad.
4. **Commit y push sin preguntar** (como «ya tengo el X»).
5. En «sincroniza» (Flujo B) y en «comprueba» (Flujo E) se tienen en cuenta las pendientes (ver esos flujos).

---

## Cosas que ya se aprendieron (evita repetir errores)

- El archivo de productos de Cardmarket **no trae el número de carta**; no deduzcas el número por el orden de `idProduct` sin comprobar.
- La tendencia de la guía de precios mezcla todos los idiomas: en español suele ser distinta.
- Ofertas en el carrito de un comprador no se pueden borrar hasta que se liberan.
- Si Cloudflare bloquea, no reintentes en bucle: para y avisa a Jose.
- El precio de `stock.csv` (Cardmarket) nunca se sube ni se baja en automático: las revisiones de suelo solo cambian `suelo.csv`
  (precio web) y por defecto solo hacia arriba. Ver «Precios web frente a Cardmarket».
- No toques `config.json` a mano ni lo sobrescribas al subir archivos. Excepción: `dias_agotada` (días que una agotada se queda en su sitio)
  y `colecciones_holo` (colecciones en las que todas las cartas son holo; ahora `["30th Celebration"]`)
  se pueden cambiar a mano; `api/modo.js` conserva los campos que no gestiona. Haz `git pull` antes, por si el botón lo acaba de cambiar.
