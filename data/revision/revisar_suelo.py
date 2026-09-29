# Revisión nocturna del suelo de todo el stock y subida de precios (nunca bajar). Solo LEE Cardmarket.
#   python -X utf8 data/revision/revisar_suelo.py
# Progreso carta a carta en data/revision/suelo_revision_progreso.csv (reanudable) y log en data/revision/progreso.log.
# Al terminar: copia stock_antes_revision.csv, sube precios en stock.csv y cartas.json, actualiza suelo.csv y deja en Descargas
# el CSV de subidas para Cardmarket (+ pasos .txt) y el informe (HTML con fotos + CSV). No hace commit ni toca config.json.
import base64, csv, html, json, os, random, re, shutil, subprocess, sys, time, traceback, urllib.request
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.join(ROOT, 'data', 'revision')
LOG = os.path.join(HERE, 'progreso.log')
PROG = os.path.join(HERE, 'suelo_revision_progreso.csv')
DESCARGAS = os.path.join(os.path.expanduser('~'), 'Downloads')
CDP, ME = 'http://localhost:9222', 'bepokemon'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PROFILE = r'C:\chrome-cardmarket'
WAIT = (30, 40)
CF_WAIT, CF_TRIES = 600, 12
CF_TITLES = ('Un momento…', 'Just a moment...')
LANG = {'en': 1, 'fr': 2, 'de': 3, 'es': 4, 'it': 5, 'zh': 6, 'ja': 7, 'pt': 8, 'ko': 10}
NOMBRE_IDIOMA = {'es': 'Español', 'en': 'Inglés', 'fr': 'Francés', 'de': 'Alemán', 'it': 'Italiano', 'pt': 'Portugués', 'ja': 'Japonés', 'ko': 'Coreano', 'zh': 'Chino'}
HOY = datetime.now()
FECHA = HOY.strftime('%d/%m/%Y')
AYER = (HOY - timedelta(days=1)).strftime('%d/%m/%Y')
STATS = {'bloqueos': 0, 'pausas': 0}


def log(msg):
    line = f'{datetime.now():%d/%m/%Y %H:%M:%S}  {msg}'
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


# ---------- Navegación con Cloudflare (misma lógica probada que data/colecciones/preparar_colecciones.py) ----------
PW, BROWSER, last_nav = [None], [None], [0.0]

def blocked(pg):
    try: return pg.title().strip() in CF_TITLES or 'challenge' in pg.url
    except Exception: return False

def alive(pg):
    try: return pg is not None and not pg.is_closed() and pg.title() is not None
    except Exception: return False

def live(pg):
    if alive(pg): return pg
    warned = 0.0
    while True:
        try:
            BROWSER[0] = PW[0].chromium.connect_over_cdp(CDP)
            ctx = BROWSER[0].contexts[0]
            good = [x for x in ctx.pages if 'cardmarket.com' in x.url and not blocked(x)]
            pg = good[-1] if good else ctx.pages[0] if ctx.pages else ctx.new_page()
            log('  conectado con el Chrome de Cardmarket'); return pg
        except Exception:
            if time.time() - warned > 1800:
                log('EN PAUSA: el Chrome de Cardmarket está cerrado. Ábrelo con --remote-debugging-port=9222 --user-data-dir="C:\\chrome-cardmarket" y el script seguirá solo.')
                warned = time.time()
            time.sleep(60)

def ok(pg): return alive(pg) and not blocked(pg) and 'cardmarket.com' in pg.url

def tabs():
    try: return json.load(urllib.request.urlopen(CDP + '/json/list', timeout=5))
    except Exception: return None

def pause_for_human(url):
    STATS['pausas'] += 1
    log('EN PAUSA: Cloudflare sigue tras 12 intentos. Me desconecto de Chrome y abro la verificación en una pestaña nueva: resuélvela y seguiré solo.')
    try:
        if BROWSER[0]: BROWSER[0].close()
    except Exception: pass
    BROWSER[0] = None
    try: subprocess.Popen([CHROME, '--remote-debugging-port=9222', f'--user-data-dir={PROFILE}', url])
    except Exception as e: log(f'  no pude abrir la pestaña ({e}); ábrela a mano: {url}')
    while True:
        time.sleep(30)
        t = tabs()
        if t and any(x.get('type') == 'page' and 'cardmarket.com' in x.get('url', '') and x.get('title', '').strip() not in CF_TITLES + ('',) for x in t):
            break
    log('Verificación pasada: me reconecto y sigo.')

def goto(pg, url):
    for attempt in range(CF_TRIES + 1):
        gap = random.uniform(*WAIT) - (time.time() - last_nav[0])
        if gap > 0: time.sleep(gap)
        pg = live(pg)
        try: pg.goto(url, wait_until='domcontentloaded', timeout=90000)
        except Exception as e: log(f'  aviso: error al cargar ({e.__class__.__name__})')
        for _ in range(20):
            time.sleep(1)
            if ok(pg): break
        time.sleep(3); last_nav[0] = time.time()
        if ok(pg): return pg
        STATS['bloqueos'] += 1
        if attempt < CF_TRIES:
            log(f'  Cloudflare en {url} (intento {attempt + 1}/{CF_TRIES}): espero 10 minutos y recargo')
            time.sleep(CF_WAIT)
    pause_for_human(url)
    last_nav[0] = time.time()
    return goto(live(None), url)


# ---------- Lectura del suelo (Flujo C del CLAUDE.md) ----------
def offers(pg):
    res = []
    for r in pg.query_selector_all('div[id^=articleRow]'):
        a = r.query_selector('a[href*="/Users/"]')
        pr = re.search(r'(\d+(?:\.\d{3})*,\d\d) €', r.inner_text())
        res.append((a.get_attribute('href').rsplit('/', 1)[1] if a else None, float(pr.group(1).replace('.', '').replace(',', '.')) if pr else None))
    return res

def floor(pg):
    """Primera oferta que no sea mía en la primera carga; sin «Mostrar más» salvo una vez si todas son mías.
    Ofertas = filas de otros vendedores en la primera carga, con «+» si hay más."""
    rows = offers(pg)
    others = [r for r in rows if r[0] and r[0].lower() != ME and r[1] is not None]
    btn = pg.query_selector('#loadMoreButton'); more = bool(btn and btn.is_visible())
    if rows and not others and more:
        pg.click('#loadMoreButton'); time.sleep(6)
        rows = offers(pg); others = [r for r in rows if r[0] and r[0].lower() != ME and r[1] is not None]
        btn = pg.query_selector('#loadMoreButton'); more = bool(btn and btn.is_visible())
    return (others[0][1] if others else None), f"{len(others)}{'+' if more else ''}"


# ---------- Datos ----------
def read_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return [r for r in csv.reader(f, delimiter=';') if r]

def num(s):
    try: return float(str(s).strip().replace(',', '.'))
    except Exception: return None

def cents(x): return int(round(x * 100))

def load_progress():
    if not os.path.exists(PROG): return {}
    return {r[0]: r for r in read_csv(PROG)[1:]}

def save_progress_row(row):
    new = not os.path.exists(PROG)
    with open(PROG, 'a', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter=';')
        if new: w.writerow(['id', 'url', 'idioma', 'suelo', 'ofertas', 'fecha', 'estado', 'motivo'])
        w.writerow(row)

def recent_floors():
    """Suelos de hoy o de ayer que se pueden reutilizar: suelo.csv (por id) y data/colecciones/*.json (por url + idioma)."""
    by_id, by_url = {}, {}
    for r in read_csv(os.path.join(ROOT, 'suelo.csv'))[1:]:
        if len(r) >= 4 and r[3].strip() in (FECHA, AYER): by_id[r[0]] = (num(r[1]) if r[1].strip() else None, r[2], r[3].strip(), 'suelo.csv')
    cdir = os.path.join(ROOT, 'data', 'colecciones')
    for fn in os.listdir(cdir) if os.path.isdir(cdir) else []:
        if not fn.endswith('.json'): continue
        d = json.load(open(os.path.join(cdir, fn), encoding='utf-8'))
        lang = {v: k for k, v in NOMBRE_IDIOMA.items()}.get(d.get('idioma'), 'es')
        for c in d.get('cartas', []):
            if c.get('fecha') in (FECHA, AYER): by_url[(c['url'], lang)] = (c.get('suelo'), c.get('ofertas', ''), c['fecha'], f'data/colecciones/{fn}')
    return by_id, by_url

def filtro(card):
    if '/30th-Celebration-Additionals/' in card['url'] or card['name'].startswith('Código Live'):
        return ''                                    # códigos: sin filtro de idioma
    return f"?language={LANG.get(card.get('idioma', 'es'), 4)}&minCondition=2"


# ---------- Revisión ----------
def revisar(stock, cards):
    prog = load_progress()
    by_id, by_url = recent_floors()
    todo = [r for r in stock if r[0] not in prog or prog[r[0]][6] not in ('ok', 'reutilizado', 'sin competencia')]
    log(f'Cartas con cantidad > 0: {len(stock)} · ya revisadas: {len(stock) - len(todo)} · pendientes: {len(todo)}')
    with sync_playwright() as p:
        PW[0] = p
        pg = None
        for i, r in enumerate(todo, 1):
            cid = r[0]; c = cards[int(cid)]; lang = c.get('idioma', 'es')
            reuse = by_id.get(cid) or by_url.get((c['url'], lang))
            if reuse:
                mn, of, fe, src = reuse
                save_progress_row([cid, c['url'], lang, '' if mn is None else f'{mn:.2f}', of, fe, 'reutilizado', f'suelo del {fe} en {src}'])
                log(f'  {i}/{len(todo)} {c["name"]} {c["numLabel"]}: reutilizo suelo del {fe} ({src})'); continue
            url = c['url'] + filtro(c)
            try:
                pg = goto(pg, url)
                if re.search(r'no encontrad|not found|404', pg.title(), re.I):
                    raise RuntimeError('página no encontrada en Cardmarket')
                mn, of = floor(pg)
                estado = 'ok' if mn is not None else 'sin competencia'
                save_progress_row([cid, c['url'], lang, '' if mn is None else f'{mn:.2f}', of, FECHA, estado, ''])
                log(f'  {i}/{len(todo)} {c["name"]} {c["numLabel"]} [{lang}]: ' + (f'{mn:.2f} € ({of} ofertas)' if mn is not None else 'sin ofertas de otros vendedores'))
            except Exception as e:
                save_progress_row([cid, c['url'], lang, '', '', FECHA, 'error', f'{e.__class__.__name__}: {str(e)[:120]}'])
                log(f'  {i}/{len(todo)} {c["name"]} {c["numLabel"]}: ERROR al leer ({e})')
        try:
            if BROWSER[0]: BROWSER[0].close()   # soltar Chrome (no se cierra)
        except Exception: pass


# ---------- Aplicar precios, suelo.csv y salidas ----------
def aplicar_y_generar(stock_rows, header, cards):
    prog = load_progress()
    stock_path = os.path.join(ROOT, 'stock.csv')
    backup = os.path.join(ROOT, 'stock_antes_revision.csv')
    if not os.path.exists(backup):              # si se relanza, la copia sigue siendo la del stock original
        shutil.copyfile(stock_path, backup); log('Copia de seguridad: stock_antes_revision.csv')
    filas = []                                   # una por carta revisada, con su clasificación
    nuevos = {}                                  # id -> precio nuevo
    for r in stock_rows:
        cid = r[0]; c = cards[int(cid)]; qty = int(r[3]); precio = num(r[2]); pr = prog.get(cid)
        f = {'id': cid, 'carta': c['name'], 'numero': c['numLabel'], 'coleccion': c['set'], 'idioma': NOMBRE_IDIOMA.get(c.get('idioma', 'es'), 'Español'),
             'url': c['url'], 'img': c.get('img', ''), 'cantidad': qty, 'precio': precio, 'suelo': None, 'ofertas': '', 'nuevo': precio,
             'grupo': 'ilegible', 'motivo': '', 'raro': '', 'fuente': ''}
        if not pr or pr[6] == 'error':
            f['motivo'] = pr[7] if pr else 'no se llegó a revisar'
        else:
            f['ofertas'] = pr[4]; f['fuente'] = 'reutilizado: ' + pr[7] if pr[6] == 'reutilizado' else 'leído hoy'
            if not pr[3]:
                f['grupo'] = 'sin competencia'; f['motivo'] = 'no hay ofertas de otros vendedores'
            else:
                s = num(pr[3]); f['suelo'] = s
                raro = bool(precio) and (s >= 3 * precio or s <= precio / 3)
                if cents(s) > cents(precio):
                    f['grupo'] = 'encima'
                    nuevo_c = (cents(s) // 5) * 5                                 # hacia abajo a 0,05 €
                    if raro:                                                      # prudencia: puede ser otra versión de la carta
                        f['motivo'] = 'no se sube sola: suelo 3 veces mayor o más, revisa a mano que sea la misma versión'
                    elif nuevo_c > cents(precio):
                        f['nuevo'] = nuevo_c / 100; nuevos[cid] = f['nuevo']
                    else:
                        f['motivo'] = 'al redondear a 0,05 € no supera mi precio: no se cambia'
                elif cents(s) == cents(precio): f['grupo'] = 'igual'
                else: f['grupo'] = 'debajo'
                if raro:
                    f['raro'] = f'suelo {eur(s)} frente a mi precio {eur(precio)} (x{s / precio:.1f}): ¿otra versión de la carta?'.replace('x', '×', 1)
        filas.append(f)

    # stock.csv: solo cambia el precio de las que suben (mismo formato y saltos de línea)
    raw = open(stock_path, encoding='utf-8', newline='').read(); nl = '\r\n' if '\r\n' in raw else '\n'
    out = []
    for line in raw.split(nl):
        p = line.split(';')
        if p and p[0] in nuevos: p[2] = f'{nuevos[p[0]]:.2f}'; line = ';'.join(p)
        out.append(line)
    open(stock_path, 'w', encoding='utf-8', newline='').write(nl.join(out))
    # cartas.json: price de las que suben
    cj = os.path.join(ROOT, 'cartas.json'); raw = open(cj, encoding='utf-8', newline='').read(); crlf = '\r\n' in raw
    d = json.loads(raw)
    for c in d['cartas']:
        if str(c['id']) in nuevos: c['price'] = nuevos[str(c['id'])]
    txt = json.dumps(d, ensure_ascii=False, indent=1)
    open(cj, 'w', encoding='utf-8', newline='').write(txt.replace('\n', '\r\n') if crlf else txt)
    log(f'Precios subidos en stock.csv y cartas.json: {len(nuevos)} cartas')
    # suelo.csv: todos los suelos revisados (fecha de la lectura)
    sp = os.path.join(ROOT, 'suelo.csv'); raw = open(sp, encoding='utf-8', newline='').read(); nl = '\r\n' if '\r\n' in raw else '\n'
    lines = [l for l in raw.split(nl) if l.strip()]; idx = {l.split(';')[0]: i for i, l in enumerate(lines)}
    for cid, pr in prog.items():
        if pr[6] in ('ok', 'sin competencia', 'reutilizado'):
            row = f'{cid};{pr[3]};{pr[4]};{pr[5]}'
            if cid in idx: lines[idx[cid]] = row
            else: lines.append(row)
    open(sp, 'w', encoding='utf-8', newline='').write(nl.join(lines) + nl)
    log('suelo.csv actualizado')
    return filas


def eur(x): return '' if x is None else f'{x:.2f} €'.replace('.', ',')

def salidas(filas, inicio, fin):
    tag = HOY.strftime('%Y-%m-%d')
    sube = [f for f in filas if f['nuevo'] != f['precio']]
    enc = sorted([f for f in filas if f['grupo'] == 'encima'], key=lambda f: -((f['nuevo'] - f['precio']) * f['cantidad']))
    igual = [f for f in filas if f['grupo'] == 'igual']
    deb = sorted([f for f in filas if f['grupo'] == 'debajo'], key=lambda f: -(f['precio'] - f['suelo']))
    otras = [f for f in filas if f['grupo'] in ('sin competencia', 'ilegible')]
    raros = [f for f in filas if f['raro']]
    ganancia = sum((f['nuevo'] - f['precio']) * f['cantidad'] for f in sube)

    # 1) CSV de subidas para Cardmarket
    with open(os.path.join(DESCARGAS, f'subidas_cardmarket_{tag}.csv'), 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh, delimiter=';')
        w.writerow(['nombre', 'numero', 'coleccion', 'idioma', 'url', 'precio_anterior', 'precio_nuevo', 'cantidad'])
        for f in sube: w.writerow([f['carta'], f['numero'], f['coleccion'], f['idioma'], f['url'], f"{f['precio']:.2f}".replace('.', ','), f"{f['nuevo']:.2f}".replace('.', ','), f['cantidad']])
    with open(os.path.join(DESCARGAS, f'subidas_cardmarket_{tag}_pasos.txt'), 'w', encoding='utf-8') as fh:
        fh.write(f"""CÓMO APLICAR LAS SUBIDAS EN CARDMARKET ({len(sube)} cartas) — subidas_cardmarket_{tag}.csv

La web (rockethouse.vercel.app) ya tendrá los precios nuevos cuando hagas commit y push. En Cardmarket hay que cambiarlos aparte:
el script NO ha tocado nada allí.

Opción A — a mano (recomendada si son pocas):
  1. Abre Cardmarket > Vender > Mis ofertas > Cartas sueltas.
  2. Busca cada carta del CSV por su nombre (o abre su url y baja a tus ofertas).
  3. Pulsa editar en tu oferta (idioma y estado deben coincidir: {', '.join(sorted({f['idioma'] for f in sube})) or 'Español'}, NM)
     y cambia el precio a «precio_nuevo». Guarda.
  4. Marca la fila en el CSV cuando la tengas hecha.

Opción B — con la extensión «Stock Exporter» (o similar):
  1. Exporta tu stock actual de Cardmarket a CSV con la extensión.
  2. En ese CSV, cambia la columna de precio de las cartas que aparecen en subidas_cardmarket_{tag}.csv
     (crúzalas por nombre + número, o por la url del producto) al valor de «precio_nuevo».
  3. Vuelve a importar el CSV con la función de actualización de precios de la extensión y revisa la vista previa
     antes de confirmar: comprueba que solo cambian estas {len(sube)} cartas y que ninguna baja de precio.

En ambos casos: si una carta está en el carrito de un comprador, Cardmarket puede no dejar editarla hasta que se libere.
""")
    # 2) CSV del informe
    with open(os.path.join(DESCARGAS, f'informe_suelo_{tag}.csv'), 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh, delimiter=';')
        w.writerow(['seccion', 'id', 'carta', 'numero', 'coleccion', 'idioma', 'cantidad', 'mi_precio', 'suelo', 'ofertas', 'precio_nuevo', 'diferencia_eur', 'diferencia_pct', 'ganancia', 'motivo', 'aviso', 'fuente'])
        nombre = {'encima': 'Suelo por encima', 'igual': 'Suelo igual', 'debajo': 'Suelo por debajo', 'sin competencia': 'Sin competencia', 'ilegible': 'No se pudo leer'}
        for f in enc + igual + deb + otras:
            dif = (f['suelo'] - f['precio']) if f['suelo'] is not None else None
            w.writerow([nombre[f['grupo']], f['id'], f['carta'], f['numero'], f['coleccion'], f['idioma'], f['cantidad'], f"{f['precio']:.2f}".replace('.', ','),
                        '' if f['suelo'] is None else f"{f['suelo']:.2f}".replace('.', ','), f['ofertas'], f"{f['nuevo']:.2f}".replace('.', ','),
                        '' if dif is None else f'{dif:.2f}'.replace('.', ','), '' if dif is None or not f['precio'] else f"{dif / f['precio'] * 100:.0f}",
                        f"{(f['nuevo'] - f['precio']) * f['cantidad']:.2f}".replace('.', ','), f['motivo'], f['raro'], f['fuente']])
    # 3) Informe HTML (fotos incrustadas: se abre con doble clic sin conexión)
    def foto(f):
        p = os.path.join(ROOT, f['img'])
        if not f['img'] or not os.path.exists(p): return ''
        return f'<img src="data:image/webp;base64,{base64.b64encode(open(p, "rb").read()).decode()}" alt="">'
    def card(f): return f'<td class="ph">{foto(f)}</td><td><b>{html.escape(f["carta"])}</b><br><small>{html.escape(f["numero"])} · {html.escape(f["coleccion"])} · {f["idioma"]}</small>{"<br><span class=raro>⚠ " + html.escape(f["raro"]) + "</span>" if f["raro"] else ""}</td>'
    pct = lambda a, b: f'{(a - b) / b * 100:+.0f} %' if b else ''
    t_enc = ''.join(f'<tr>{card(f)}<td>{f["cantidad"]}</td><td>{eur(f["precio"])}</td><td>{eur(f["suelo"])}<br><small>{f["ofertas"]} ofertas</small></td>'
                    f'<td class="{"up" if f["nuevo"] != f["precio"] else ""}">{eur(f["nuevo"])}{"<br><small>" + html.escape(f["motivo"]) + "</small>" if f["motivo"] else ""}</td>'
                    f'<td>{eur(f["nuevo"] - f["precio"])}<br><small>{pct(f["nuevo"], f["precio"])}</small></td><td>{eur((f["nuevo"] - f["precio"]) * f["cantidad"])}</td></tr>' for f in enc)
    t_ig = ''.join(f'<tr>{card(f)}<td>{f["cantidad"]}</td><td>{eur(f["precio"])}</td><td>{eur(f["suelo"])}<br><small>{f["ofertas"]} ofertas</small></td></tr>' for f in igual)
    t_deb = ''.join(f'<tr>{card(f)}<td>{f["cantidad"]}</td><td>{eur(f["precio"])}</td><td>{eur(f["suelo"])}<br><small>{f["ofertas"]} ofertas</small></td>'
                    f'<td>{eur(f["precio"] - f["suelo"])}<br><small>{pct(f["precio"], f["suelo"])}</small></td></tr>' for f in deb)
    t_otr = ''.join(f'<tr>{card(f)}<td>{f["cantidad"]}</td><td>{eur(f["precio"])}</td><td>{"Sin competencia" if f["grupo"] == "sin competencia" else "No se pudo leer"}</td><td>{html.escape(f["motivo"])}</td></tr>' for f in otras)
    reu = [f for f in filas if f['fuente'].startswith('reutilizado')]
    doc = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Revisión del suelo · {FECHA}</title><style>
body{{font:15px/1.45 "Segoe UI",system-ui,sans-serif;margin:0;background:#0f1f28;color:#eee8dc}} .w{{max-width:1100px;margin:0 auto;padding:24px 16px 60px}}
h1{{font-size:28px;margin:0 0 6px}} h2{{margin:34px 0 10px;font-size:20px}} small{{color:#9db0b4}} .muted{{color:#9db0b4}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin:18px 0}} .k{{background:#132732;border:1px solid #24404d;border-radius:12px;padding:12px 14px}}
.k b{{display:block;font-size:24px}} .k.g b{{color:#6fc28a}} .big{{background:#16331f;border:1px solid #2e6b42;border-radius:14px;padding:16px 18px;margin:16px 0;font-size:18px}}
.big b{{font-size:30px;color:#6fc28a}} table{{width:100%;border-collapse:collapse;background:#132732;border-radius:12px;overflow:hidden}}
th,td{{padding:8px 10px;border-bottom:1px solid #24404d;text-align:left;vertical-align:middle}} th{{background:#10202a;font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:#9db0b4}}
td.ph img{{width:46px;border-radius:4px;display:block}} td.up{{color:#6fc28a;font-weight:700}} .raro{{color:#e8ba5e;font-size:12.5px}}
.avisos{{background:#2a2410;border:1px solid #6b5a1e;border-radius:12px;padding:12px 16px;margin:14px 0}} .avisos li{{margin:4px 0}}
</style></head><body><div class="w">
<h1>Revisión del suelo de mi stock</h1>
<div class="muted">Empezó {inicio:%d/%m/%Y %H:%M} · terminó {fin:%d/%m/%Y %H:%M} · suelo = primera oferta de otro vendedor en el idioma de cada carta y NM (códigos sin filtro de idioma)</div>
<div class="kpis"><div class="k"><small>Cartas revisadas</small><b>{len(filas)}</b></div><div class="k g"><small>🟢 Suben de precio</small><b>{len(sube)}</b></div>
<div class="k"><small>🟢 Suelo por encima</small><b>{len(enc)}</b></div><div class="k"><small>🟡 Suelo igual</small><b>{len(igual)}</b></div><div class="k"><small>🔴 Suelo por debajo</small><b>{len(deb)}</b></div>
<div class="k"><small>⚪ Sin competencia / sin leer</small><b>{len(otras)}</b></div><div class="k"><small>Bloqueos de Cloudflare</small><b>{STATS['bloqueos']}</b><small>{STATS['pausas']} pausa(s) para resolver a mano</small></div></div>
{"<div class=avisos><b>Para mirar:</b><ul>" + "".join(f"<li>{html.escape(f['carta'])} {html.escape(f['numero'])}: {html.escape(f['raro'])}</li>" for f in raros) + "</ul></div>" if raros else ""}
<p class="muted">Suelos reutilizados sin visitar Cardmarket (de hoy o de ayer, mismo idioma): {len(reu)}{" — " + ", ".join(html.escape(f['carta'] + ' ' + f['numero']) for f in reu) if reu else ""}.</p>
<h2>🟢 Suelo por encima de mi precio (subidas)</h2>
<div class="big">Ganancia potencial total: <b>{eur(ganancia)}</b> <small>(diferencia × cantidad de las {len(sube)} cartas que suben; precio nuevo = suelo redondeado hacia abajo a 0,05 €, nunca por debajo del actual)</small></div>
<table><tr><th></th><th>Carta</th><th>Cant.</th><th>Precio anterior</th><th>Suelo</th><th>Precio nuevo</th><th>Diferencia</th><th>Ganancia</th></tr>{t_enc or '<tr><td colspan=8>Ninguna</td></tr>'}</table>
<h2>🟡 Suelo igual a mi precio</h2>
<table><tr><th></th><th>Carta</th><th>Cant.</th><th>Mi precio</th><th>Suelo</th></tr>{t_ig or '<tr><td colspan=5>Ninguna</td></tr>'}</table>
<h2>🔴 Suelo por debajo de mi precio <small>(solo informativo, no se ha tocado)</small></h2>
<table><tr><th></th><th>Carta</th><th>Cant.</th><th>Mi precio</th><th>Suelo</th><th>Estoy por encima</th></tr>{t_deb or '<tr><td colspan=6>Ninguna</td></tr>'}</table>
<h2>⚪ Sin competencia y cartas que no se pudieron leer</h2>
<table><tr><th></th><th>Carta</th><th>Cant.</th><th>Mi precio</th><th>Estado</th><th>Motivo</th></tr>{t_otr or '<tr><td colspan=6>Ninguna</td></tr>'}</table>
</div></body></html>"""
    open(os.path.join(DESCARGAS, f'informe_suelo_{tag}.html'), 'w', encoding='utf-8').write(doc)
    log(f'Informe y CSV en Descargas (informe_suelo_{tag}.html/.csv, subidas_cardmarket_{tag}.csv y pasos .txt)')
    return {'sube': len(sube), 'encima': len(enc), 'igual': len(igual), 'debajo': len(deb), 'otras': len(otras), 'ganancia': round(ganancia, 2), 'raros': len(raros)}


def main():
    os.makedirs(HERE, exist_ok=True)
    inicio = datetime.now()
    log('=== Inicio de la revisión del suelo ===')
    rows = read_csv(os.path.join(ROOT, 'stock.csv')); header, rows = rows[0], rows[1:]
    stock = [r for r in rows if len(r) >= 4 and (num(r[3]) or 0) > 0]
    cards = {c['id']: c for c in json.load(open(os.path.join(ROOT, 'cartas.json'), encoding='utf-8'))['cartas']}
    revisar(stock, cards)
    filas = aplicar_y_generar(stock, header, cards)
    res = salidas(filas, inicio, datetime.now())
    log('=== TERMINADO === ' + json.dumps(res, ensure_ascii=False))

if __name__ == '__main__':
    try: main()
    except Exception:
        log('ERROR: el script se ha parado. Al relanzarlo seguirá donde se quedó.\n' + traceback.format_exc()); sys.exit(1)
