# Prepara los datos de dos colecciones para listados e intercambios:
#   Pokémon GO (cartas en INGLÉS)  -> data/colecciones/pgo.json, fotos en img/pgo/
#   Astros Brillantes (ESPAÑOL)    -> data/colecciones/brs.json, fotos en img/brs/
# Pasos: 1) listado de cartas de cada colección, 2) todas las fotos (servidor de imágenes, sin Cloudflare),
# 3) suelos (primera oferta de otro vendedor que no sea BePokemon, reglas del CLAUDE.md).
# Guarda el progreso después de cada carta: si se corta, al relanzarlo sigue donde se quedó.
# Uso: python data/colecciones/preparar_colecciones.py   (log en data/colecciones/progreso.log)
#      python data/colecciones/preparar_colecciones.py --actualizar pgo brs   (vuelve a consultar el suelo de esas colecciones)
import html, io, json, os, random, re, sys, time, traceback, urllib.request
from datetime import datetime
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'data', 'colecciones')
LOG = os.path.join(OUT, 'progreso.log')
CDP = 'http://localhost:9222'          # Chrome de Cardmarket abierto con --remote-debugging-port=9222
ME = 'bepokemon'                       # USUARIO_CM: sus ofertas no cuentan para el suelo
WAIT = (30, 40)                        # segundos entre páginas de Cardmarket
CF_WAIT, CF_TRIES = 600, 12            # Cloudflare: esperar 10 min y reintentar, hasta 12 veces
COLS = [
    {'codigo': 'pgo', 'nombre': 'Pokémon GO', 'idExpansion': 5051, 'slug': 'Pokemon-GO',
     'idioma': 'Inglés', 'filtro': '?language=1&minCondition=2'},
    {'codigo': 'brs', 'nombre': 'Astros Brillantes', 'idExpansion': 4434, 'slug': 'Brilliant-Stars',
     'idioma': 'Español', 'filtro': '?language=4&minCondition=2'},
]


def log(msg):
    line = f'{datetime.now():%d/%m/%Y %H:%M:%S}  {msg}'
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def path_json(col):
    return os.path.join(OUT, col['codigo'] + '.json')


def load(col):
    p = path_json(col)
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None


def save(data):
    data['actualizado'] = datetime.now().strftime('%d/%m/%Y %H:%M')
    p = os.path.join(OUT, data['codigo'] + '.json')
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)                  # escritura atómica: nunca queda un JSON a medias


# ---------- Navegación con pausas y Cloudflare ----------
last_nav = [0.0]


def blocked(pg):
    try:
        return pg.title().strip() in ('Un momento…', 'Just a moment...') or 'challenge' in pg.url
    except Exception:
        return False


PW = [None]                            # Playwright, para reconectar si se cierra Chrome o la pestaña
BROWSER = [None]                       # conexión CDP actual (se cierra durante la pausa por Cloudflare)
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PROFILE = r'C:\chrome-cardmarket'
CF_TITLES = ('Un momento…', 'Just a moment...')


def tabs():
    """Lista de pestañas por HTTP (/json/list): no se engancha a ninguna, así Cloudflare no ve automatización."""
    try:
        return json.load(urllib.request.urlopen(CDP + '/json/list', timeout=5))
    except Exception:
        return None


def pause_for_human(url):
    """Pausa por Cloudflare: cierra la conexión CDP (Chrome sigue abierto), abre la verificación en una pestaña
    nueva y espera, sin conectarse, a que alguna pestaña de Cardmarket haya pasado la verificación."""
    log('EN PAUSA: Cloudflare sigue tras 12 intentos. Me desconecto de Chrome y abro la verificación en una pestaña '
        'nueva: resuélvela y me reconectaré solo.')
    try:
        if BROWSER[0]:
            BROWSER[0].close()         # con connect_over_cdp solo cierra la conexión, no Chrome
    except Exception:
        pass
    BROWSER[0] = None
    try:
        import subprocess
        subprocess.Popen([CHROME, '--remote-debugging-port=9222', f'--user-data-dir={PROFILE}', url])
    except Exception as e:
        log(f'  no pude abrir la pestaña nueva ({e}); ábrela a mano: {url}')
    while True:
        time.sleep(30)
        t = tabs()
        if t and any(x.get('type') == 'page' and 'cardmarket.com' in x.get('url', '')
                     and x.get('title', '').strip() not in CF_TITLES + ('',) for x in t):
            break
    log('Verificación pasada: me reconecto a Chrome y sigo.')


def alive(pg):
    try:
        return pg is not None and not pg.is_closed() and pg.title() is not None
    except Exception:
        return False


def live(pg):
    """Devuelve una pestaña viva del Chrome de Cardmarket. Si Chrome o la pestaña se han cerrado, espera
    (comprobando cada minuto) a que vuelva a estar abierto y se reconecta solo."""
    if alive(pg):
        return pg
    warned = 0.0
    while True:
        try:
            BROWSER[0] = PW[0].chromium.connect_over_cdp(CDP)
            ctx = BROWSER[0].contexts[0]
            # Preferir una pestaña de Cardmarket que ya haya pasado la verificación
            good = [x for x in ctx.pages if 'cardmarket.com' in x.url and not blocked(x)]
            pg = good[-1] if good else ctx.pages[0] if ctx.pages else ctx.new_page()
            log('  conectado con el Chrome de Cardmarket')
            return pg
        except Exception:
            if time.time() - warned > 1800:
                log('EN PAUSA: el Chrome de Cardmarket está cerrado. Ábrelo con --remote-debugging-port=9222 '
                    '--user-data-dir="C:\\chrome-cardmarket" y el script seguirá solo.')
                warned = time.time()
            time.sleep(60)


def ok(pg):
    return alive(pg) and not blocked(pg) and 'cardmarket.com' in pg.url


def goto(pg, url):
    """Abre url respetando 30-40 s entre páginas y devuelve la pestaña (puede ser otra si Chrome se reabrió).
    Si sale Cloudflare: 10 min de espera y recarga, hasta 12 veces; después queda en pausa (comprobando cada
    minuto) hasta que Jose lo resuelva en la ventana de Chrome."""
    for attempt in range(CF_TRIES + 1):
        gap = random.uniform(*WAIT) - (time.time() - last_nav[0])
        if gap > 0:
            time.sleep(gap)
        pg = live(pg)
        try:
            pg.goto(url, wait_until='domcontentloaded', timeout=90000)
        except Exception as e:
            log(f'  aviso: error al cargar ({e.__class__.__name__}); lo trato como bloqueo')
        for _ in range(20):
            time.sleep(1)
            if ok(pg):
                break
        time.sleep(3)
        last_nav[0] = time.time()
        if ok(pg):
            return pg
        if attempt < CF_TRIES:
            log(f'  Cloudflare en {url} (intento {attempt + 1}/{CF_TRIES}): espero 10 minutos y recargo')
            time.sleep(CF_WAIT)
    pause_for_human(url)
    last_nav[0] = time.time()
    return goto(live(None), url)


# ---------- 1) Listado de cartas ----------
def split_name(text):
    """'Exeggcute (BRS 001)' -> ('Exeggcute', '001'); 'Charizard (BRS TG03)' -> ('Charizard', 'TG03')."""
    m = re.match(r'(.*?)\s*\((?:[A-Z0-9-]+)\s+([^)]+)\)\s*$', text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return re.sub(r'\s*\([A-Z0-9-]+\)\s*$', '', text).strip(), ''      # «Marcador V-ASTRO (BRS)», códigos online


def listing_bulk(pg, col):
    base = f"https://www.cardmarket.com/es/Pokemon/Stock/ListingMethods/BulkListing?idExpansion={col['idExpansion']}"
    rows, site, total = {}, 1, 1
    while site <= total:
        pg = goto(pg, f'{base}&site={site}')
        if 'Iniciar sesión' in pg.title() or 'Login' in pg.url:
            return None                 # el listado masivo necesita la sesión iniciada
        h = pg.content()
        m = re.search(r'Página \d+ de (\d+)', h)
        total = int(m.group(1)) if m else 1
        for r in re.findall(r'<tr id="BulkListingRow\d+".*?</tr>', h, re.S):
            a = re.search(r'col-product[^>]*><a href="([^"]+)">([^<]*)</a>', r)
            if not a:
                continue
            url = 'https://www.cardmarket.com' + a.group(1).split('?')[0]
            if url in rows:
                continue
            nombre, num = split_name(' '.join(html.unescape(a.group(2)).split()))
            img = re.search(r'(https://product-images[^&"]+?\.jpg)', r)
            rar = re.search(r'rarity-symbol[^>]*aria-label="([^"]+)"', r) or re.search(r'aria-label="([^"]+)" data-bs-original-title', r)
            rows[url] = {'num': num, 'nombre': nombre, 'url': url, 'img_origen': img and img.group(1),
                         'rareza': rar and html.unescape(rar.group(1))}
        log(f"  listado {col['codigo']}: página {site} de {total} ({len(rows)} cartas)")
        site += 1
    return list(rows.values())


def listing_public(pg, col):
    """Plan B sin sesión: páginas públicas de la expansión. La foto se saca luego de og:image."""
    base = f"https://www.cardmarket.com/es/Pokemon/Products/Singles/{col['slug']}"
    # Vista de cuadrícula: <a href="…/Pikachu-V1-PGO027" class="card … galleryBox"><img src="…jpg"> … <h2>Pikachu (PGO 027)</h2>
    # Cada recuadro se trata por separado (de un galleryBox al siguiente) para no mezclar datos de dos cartas.
    rows, site, total = {}, 1, 1
    start = re.compile(r'<a href="(/es/Pokemon/Products/Singles/' + re.escape(col['slug']) + r'/[^"?#]+)"[^>]*galleryBox')
    while site <= total:
        pg = goto(pg, f'{base}?site={site}')
        h = pg.content()
        m = re.search(r'Página \d+ de (\d+)', h)
        total = int(m.group(1)) if m else 1
        marks = list(start.finditer(h))
        for i, m in enumerate(marks):
            block = h[m.start(): marks[i+1].start() if i + 1 < len(marks) else m.start() + 6000]
            url = 'https://www.cardmarket.com' + m.group(1)
            t = re.search(r'<h2[^>]*>(.*?)</h2>', block, re.S)
            if url in rows or not t:
                continue
            text = ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', t.group(1))).replace('\xa0', ' ').split())
            nombre, num = split_name(text)
            img = re.search(r'(https://product-images[^"\s]+?\.(?:jpg|png))', block)   # src o data-src
            rows[url] = {'num': num, 'nombre': nombre, 'url': url, 'img_origen': img and img.group(1), 'rareza': None}
        log(f"  listado público {col['codigo']}: página {site} de {total} ({len(rows)} cartas)")
        site += 1
    return list(rows.values())


def assign_files(col, cards):
    used = set()
    for c in cards:
        base = re.sub(r'[^A-Za-z0-9]+', '-', c['num'] or c['url'].rsplit('/', 1)[1]).strip('-') or 'carta'
        name, i = base, 2
        while name in used:
            name, i = f'{base}-{i}', i + 1
        used.add(name)
        c['img'] = f"img/{col['codigo']}/{name}.webp"


def sort_key(c):
    n = c['num']
    m = re.match(r'([A-Z]*)(\d+)', n)
    return (m.group(1), int(m.group(2))) if m else ('~', 0) if not n else (n, 0)


# ---------- 2) Fotos ----------
def download_photo(src, dest):
    req = urllib.request.Request(src, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.cardmarket.com/'})
    data = urllib.request.urlopen(req, timeout=30).read()
    im = Image.open(io.BytesIO(data))           # la url acaba en .jpg pero puede ser PNG: Pillow lo detecta
    im = im.convert('RGBA').convert('RGB') if im.mode in ('P', 'LA', 'RGBA') else im.convert('RGB')
    im = im.resize((380, round(im.height * 380 / im.width)), Image.LANCZOS)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    im.save(dest, 'WEBP', quality=78)


# ---------- 3) Suelos ----------
def offers(pg):
    res = []
    for r in pg.query_selector_all('div[id^=articleRow]'):
        a = r.query_selector('a[href*="/Users/"]')
        pr = re.search(r'(\d+(?:\.\d{3})*,\d\d) €', r.inner_text())
        res.append((a.get_attribute('href').rsplit('/', 1)[1] if a else None,
                    float(pr.group(1).replace('.', '').replace(',', '.')) if pr else None))
    return res


def floor(pg):
    """Primera oferta que no sea mía en la primera carga (vienen de más barata a más cara). Sin «Mostrar más»,
    salvo una vez si todas las de la primera carga son mías. Ofertas = filas de otros vendedores (+ si hay más)."""
    rows = offers(pg)
    others = [r for r in rows if r[0] and r[0].lower() != ME and r[1] is not None]
    btn = pg.query_selector('#loadMoreButton')
    more = bool(btn and btn.is_visible())
    if rows and not others and more:
        pg.click('#loadMoreButton')
        time.sleep(6)
        rows = offers(pg)
        others = [r for r in rows if r[0] and r[0].lower() != ME and r[1] is not None]
        btn = pg.query_selector('#loadMoreButton')
        more = bool(btn and btn.is_visible())
    return (others[0][1] if others else None), f"{len(others)}{'+' if more else ''}"


def main():
    os.makedirs(OUT, exist_ok=True)
    log('=== Inicio ===')
    with sync_playwright() as p:
        PW[0] = p
        pg = live(None)

        # 1) Listados
        datas = {}
        for col in COLS:
            data = load(col)
            if data and data.get('cartas'):
                log(f"{col['nombre']}: listado ya guardado ({len(data['cartas'])} cartas)")
            else:
                log(f"{col['nombre']}: leyendo el listado de cartas")
                cards = listing_bulk(pg, col)
                if cards is None:
                    log('  el listado masivo pide iniciar sesión: uso las páginas públicas de la expansión')
                    cards = listing_public(pg, col)
                cards.sort(key=sort_key)
                assign_files(col, cards)
                data = {k: col[k] for k in ('codigo', 'nombre', 'idExpansion', 'idioma', 'filtro')}
                data['cartas'] = [{**c, 'suelo': None, 'ofertas': '', 'fecha': ''} for c in cards]
                save(data)
                log(f"{col['nombre']}: {len(cards)} cartas")
            datas[col['codigo']] = data

        # 2) Fotos de las dos colecciones
        for col in COLS:
            data, n = datas[col['codigo']], 0
            for c in data['cartas']:
                dest = os.path.join(ROOT, c['img'])
                if os.path.exists(dest) or not c.get('img_origen'):
                    continue
                try:
                    download_photo(c['img_origen'], dest)
                    n += 1
                except Exception as e:
                    log(f"  foto no descargada {c['num']} {c['nombre']}: {e}")
            falta = sum(1 for c in data['cartas'] if not os.path.exists(os.path.join(ROOT, c['img'])))
            log(f"{col['nombre']}: {n} fotos nuevas" + (f"; {falta} sin foto (se sacarán de su página al mirar el suelo)" if falta else ''))

        # 3) Suelos. Con «--actualizar pgo brs» se vuelven a consultar todos los de esas colecciones.
        if '--actualizar' in sys.argv:
            quiero = sys.argv[sys.argv.index('--actualizar') + 1:] or [c['codigo'] for c in COLS]
            for col in COLS:
                if col['codigo'] in quiero and not datas[col['codigo']].get('_actualizando'):
                    for c in datas[col['codigo']]['cartas']:
                        c['fecha'] = ''
                    datas[col['codigo']]['_actualizando'] = True   # si se corta, al relanzar sigue sin volver a empezar
                    save(datas[col['codigo']])
                    log(f"{col['nombre']}: se vuelven a consultar todos los suelos")
        for col in COLS:
            data = datas[col['codigo']]
            todo = [c for c in data['cartas'] if not c.get('fecha')]
            log(f"{col['nombre']} ({col['idioma']}): suelos pendientes {len(todo)} de {len(data['cartas'])}")
            for i, c in enumerate(todo, 1):
                pg = goto(pg, c['url'] + col['filtro'])
                dest = os.path.join(ROOT, c['img'])
                if not os.path.exists(dest):
                    m = re.search(r'<meta property="og:image" content="([^"]+)"', pg.content())
                    if m:
                        try:
                            download_photo(m.group(1), dest)
                            c['img_origen'] = m.group(1)
                        except Exception as e:
                            log(f"  foto no descargada {c['num']}: {e}")
                mn, of = floor(pg)
                c.update({'suelo': mn, 'ofertas': of, 'fecha': datetime.now().strftime('%d/%m/%Y')})
                save(data)
                log(f"  {col['codigo']} {i}/{len(todo)}  {c['num']} {c['nombre']}: "
                    + (f"{mn:.2f} € ({of} ofertas)" if mn is not None else 'sin ofertas de otros vendedores'))
    for data in datas.values():
        if data.pop('_actualizando', None):
            save(data)
    log('=== TERMINADO: las dos colecciones tienen listado, fotos y suelo ===')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        log('ERROR: el script se ha parado. Al relanzarlo seguirá donde se quedó.\n' + traceback.format_exc())
        sys.exit(1)
