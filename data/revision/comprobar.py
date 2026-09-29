# «comprueba» (Flujo E del CLAUDE.md): web frente a Cardmarket. SOLO LECTURA: no cambia nada en la web ni en Cardmarket.
#   python -X utf8 data/revision/comprobar.py
# Lee todas las ofertas de Mis ofertas (30–40 s entre páginas, misma gestión de Cloudflare que revisar_suelo.py), las cruza por url
# con cartas.json + stock.csv (+ suelo.csv/config.json para el precio web, con la lógica de applyMode() de index.html) y deja:
#   data/revision/comprobacion.json   (resultado para el chat)
#   Descargas\comprobacion_AAAA-MM-DD.html (con enlaces a cada oferta)
import csv, html, json, math, os, re, sys, time
from datetime import datetime
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
import revisar_suelo as nav                      # goto(), live(), Cloudflare y pausa ya probados

ROOT = nav.ROOT
nav.LOG = os.path.join(nav.HERE, 'comprobacion.log')
OFERTAS = 'https://www.cardmarket.com/es/Pokemon/Stock/Offers/Singles'
LANG_NOMBRE = {'Español': 'es', 'Inglés': 'en', 'Francés': 'fr', 'Alemán': 'de', 'Italiano': 'it', 'Portugués': 'pt', 'Japonés': 'ja', 'Coreano': 'ko',
               'Chino simplificado': 'zh', 'Chino tradicional': 'zh'}
NOMBRE = {v: k for k, v in LANG_NOMBRE.items()}; NOMBRE['zh'] = 'Chino'
log = lambda m: nav.log(m)


def sesion(pg):
    """True = sesión iniciada (la página tiene «Cerrar sesión»), False = sin sesión (formulario de login),
    None = no se puede saber (Cloudflare u otra página)."""
    try:
        if nav.blocked(pg) or 'cardmarket.com' not in pg.url: return None
        h = pg.content()
        if 'User_Logout' in h: return True
        if 'Iniciar sesión' in pg.title() or '/Login' in pg.url or 'User_Login' in h: return False
    except Exception:
        return None
    return None

def sin_sesion():
    log('SIN SESIÓN: la sesión de Cardmarket no está iniciada. Inicia sesión en el Chrome de depuración y vuelve a lanzar «comprueba».')
    sys.exit(3)

def leer_ofertas():
    ofertas, site, total = [], 1, 1
    with sync_playwright() as p:
        nav.PW[0] = p
        # Antes de nada: ¿hay sesión? Primero en la pestaña actual (sin recargar); si no se sabe, se abre Mis ofertas una vez.
        # Así, sin sesión se para al momento en vez de esperar como si fuera Cloudflare.
        pg = nav.live(None)
        estado = sesion(pg)
        if estado is None:
            pg = nav.goto(pg, f'{OFERTAS}?site=1'); estado = sesion(pg)
        if estado is False: sin_sesion()
        log('  sesión de Cardmarket iniciada' if estado else '  aviso: no se ha podido confirmar la sesión; sigo y lo vuelvo a mirar en cada página')
        while site <= total:
            pg = nav.goto(pg, f'{OFERTAS}?site={site}')
            if sesion(pg) is False: sin_sesion()
            h = pg.content()
            m = re.search(r'Página \d+ de (\d+)', h); total = int(m.group(1)) if m else 1
            for r in re.findall(r'<div id="stockRow\d+".*?(?=<div id="stockRow|<div class="table-footer|\Z)', h, re.S):
                a = re.search(r'col-seller[^>]*><a href="([^"]+)">([^<]+)</a>', r)
                if not a: continue
                pr = re.search(r'(\d+(?:\.\d{3})*,\d\d) €', r); q = re.search(r'item-count[^>]*>(\d+)<', r)
                lang = re.search(r'aria-label="(' + '|'.join(LANG_NOMBRE) + r')"', r)
                cond = re.search(r'badge[^"]*">(\w+)<', r)
                com = re.search(r'product-comments.*?data-bs-original-title="([^"]*)"', r, re.S)
                art = re.search(r'idArticle=(\d+)', r)
                ofertas.append({'url': 'https://www.cardmarket.com' + a.group(1).split('?')[0], 'nombre': html.unescape(' '.join(a.group(2).split())),
                                'precio': float(pr.group(1).replace('.', '').replace(',', '.')) if pr else None, 'cantidad': int(q.group(1)) if q else 0,
                                'idioma': LANG_NOMBRE.get(lang.group(1), '?') if lang else '?', 'estado': cond.group(1) if cond else '?',
                                'comentario': html.unescape(com.group(1)) if com else '', 'articulo': art.group(1) if art else '', 'pagina': site})
            log(f'  Mis ofertas: página {site} de {total} ({len(ofertas)} ofertas)')
            site += 1
        try:
            if nav.BROWSER[0]: nav.BROWSER[0].close()
        except Exception: pass
    return ofertas


def precio_web(stock, suelo_rows, cfg):
    """Misma lógica que applyMode() de index.html (agotadas incluidas: no se rebajan)."""
    price = {cid: v['precio'] for cid, v in stock.items()}
    if cfg.get('modo') != 'suelo': return price
    adj, mn, pct, tope = float(cfg.get('ajuste') or 0), float(cfg.get('minimo') or 0), float(cfg.get('porcentaje') or 0), float(cfg.get('tope') or 0)
    for r in suelo_rows:
        cid = r[0].strip()
        if cid not in price or stock[cid]['cantidad'] <= 0 or len(r) < 2 or not r[1].strip(): continue
        f = float(r[1].replace(',', '.'))
        if tope > 0 and price[cid] > tope: continue
        t = max(mn, math.floor((f * (1 + pct / 100) + adj) * 100 + 0.5) / 100)
        if t < price[cid]: price[cid] = t
    return price


def cruzar(ofertas):
    cards = {str(c['id']): c for c in json.load(open(os.path.join(ROOT, 'cartas.json'), encoding='utf-8'))['cartas']}
    stock = {r[0]: {'precio': float(r[2].replace(',', '.')), 'cantidad': int(r[3])} for r in nav.read_csv(os.path.join(ROOT, 'stock.csv'))[1:] if len(r) >= 4 and r[0] in cards}
    suelo = nav.read_csv(os.path.join(ROOT, 'suelo.csv'))[1:]
    cfg = json.load(open(os.path.join(ROOT, 'config.json'), encoding='utf-8'))
    web = precio_web(stock, suelo, cfg)
    pend_path = os.path.join(ROOT, 'ventas_pendientes_cm.csv')
    pendientes = nav.read_csv(pend_path)[1:] if os.path.exists(pend_path) else []
    # ofertas agrupadas por url + idioma (la misma carta en otro idioma es otra entrada de cartas.json)
    grupos = {}
    for o in ofertas: grupos.setdefault((o['url'], o['idioma']), []).append(o)
    por_url = {}
    for c in cards.values(): por_url.setdefault(c['url'], []).append(c)
    P = {k: [] for k in ('pendientes', 'urgente', 'cantidad', 'precio_stock', 'web_mayor', 'sin_publicar', 'no_en_web', 'raras')}
    vistos = set()
    def enlace(o): return {'mis_ofertas': f"{OFERTAS}?site={o['pagina']}", 'ficha': o['url'] + f"?language={nav.LANG.get(o['idioma'], 4)}", 'articulo': o['articulo']}
    for (url, lang), os_ in grupos.items():
        cand = por_url.get(url, [])
        c = next((x for x in cand if x.get('idioma', 'es') == lang), None) or (cand[0] if len(cand) == 1 else None)
        qty_cm = sum(o['cantidad'] for o in os_); precio_cm = min(o['precio'] for o in os_ if o['precio'] is not None)
        base = {'nombre': os_[0]['nombre'], 'idioma': NOMBRE.get(lang, lang), 'cm_cantidad': qty_cm, 'cm_precio': precio_cm, 'enlaces': [enlace(o) for o in os_]}
        if not c:
            P['no_en_web'].append(base); continue
        cid = str(c['id']); vistos.add(cid); s = stock.get(cid, {'precio': c['price'], 'cantidad': 0})
        info = {**base, 'id': cid, 'carta': f"{c['name']} {c['numLabel']}", 'web_cantidad': s['cantidad'], 'stock_precio': s['precio'], 'web_precio': web.get(cid, s['precio'])}
        if any(p[2] == url for p in pendientes):
            P['pendientes'].append(info); continue      # venta pendiente de quitar: solo sale en su sección, no se repite
        if s['cantidad'] == 0: P['urgente'].append(info)
        elif s['cantidad'] != qty_cm: P['cantidad'].append(info)
        if nav.cents(s['precio']) != nav.cents(precio_cm): P['precio_stock'].append(info)
        if s['cantidad'] > 0 and nav.cents(info['web_precio']) > nav.cents(precio_cm): P['web_mayor'].append(info)
        motivos = []
        if lang != c.get('idioma', 'es'): motivos.append(f"idioma de la oferta {NOMBRE.get(lang, lang)} ≠ {NOMBRE.get(c.get('idioma', 'es'), 'Español')} en cartas.json")
        for o in os_:
            if o['estado'] != 'NM': motivos.append(f"estado {o['estado']} (no NM)")
            if o['precio'] and o['precio'] > 5 and 'toploader' not in o['comentario'].lower(): motivos.append(f"{o['precio']:.2f} € sin «toploader» en el comentario".replace('.', ','))
        if len(os_) > 1: motivos.append(f'la misma carta en {len(os_)} ofertas')
        if motivos: P['raras'].append({**info, 'motivos': sorted(set(motivos))})
    for cid, s in stock.items():
        if s['cantidad'] > 0 and cid not in vistos:
            c = cards[cid]; P['sin_publicar'].append({'id': cid, 'carta': f"{c['name']} {c['numLabel']}", 'idioma': NOMBRE.get(c.get('idioma', 'es')), 'web_cantidad': s['cantidad'],
                                                       'stock_precio': s['precio'], 'web_precio': web[cid], 'enlaces': [{'ficha': c['url'], 'mis_ofertas': '', 'articulo': ''}]})
    return P, len(ofertas), sum(1 for s in stock.values() if s['cantidad'] > 0)


def informe(P, n_ofertas, n_stock):
    e = lambda x: '' if x is None else f'{x:.2f} €'.replace('.', ',')
    def link(l):
        mis = f'<a href="{html.escape(l["mis_ofertas"])}">Mis ofertas (pág. {l["mis_ofertas"].rsplit("=", 1)[1]})</a>' if l.get('mis_ofertas') else ''
        return ' · '.join(filter(None, [mis, f'<a href="{html.escape(l["ficha"])}">ficha</a>']))
    def links(o): return '<br>'.join(link(l) for l in o['enlaces'])
    SEC = [('pendientes', '🔴 Vendidas fuera de Cardmarket y aún publicadas (ventas_pendientes_cm.csv)', 'bad'),
           ('urgente', '🔴 URGENTE: cantidad 0 en la web pero publicada en Cardmarket', 'bad'),
           ('cantidad', '🟠 Cantidad distinta entre la web y Cardmarket', 'warn'),
           ('precio_stock', '🟠 Precio de stock.csv distinto del de mi oferta en Cardmarket', 'warn'),
           ('web_mayor', '🟠 Precio web MAYOR que el de Cardmarket (rompe la regla fija)', 'warn'),
           ('sin_publicar', '🟡 Con stock en la web pero no publicada en Cardmarket', 'info'),
           ('no_en_web', '🟡 Publicada en Cardmarket pero no está en la web', 'info'),
           ('raras', '🟡 Ofertas raras', 'info')]
    cuerpo = ''
    for k, t, cls in SEC:
        L = P[k]
        filas = ''.join(f"<tr><td><b>{html.escape(o.get('carta') or o['nombre'])}</b><br><small>{o.get('idioma','')}</small></td>"
                        f"<td>{o.get('web_cantidad','—')}</td><td>{o.get('cm_cantidad','—')}</td><td>{e(o.get('stock_precio'))}</td><td>{e(o.get('web_precio'))}</td><td>{e(o.get('cm_precio'))}</td>"
                        f"<td>{html.escape('; '.join(o.get('motivos', [])))}</td><td>{links(o)}</td></tr>" for o in L)
        cuerpo += (f"<h2 class={cls}>{t} <small>({len(L)})</small></h2>" + (f"<table><tr><th>Carta</th><th>Cant. web</th><th>Cant. CM</th><th>Precio stock.csv</th><th>Precio web</th><th>Precio CM</th><th>Detalle</th><th>Arreglar</th></tr>{filas}</table>" if L else '<p class=ok>Nada.</p>'))
    doc = f"""<!doctype html><html lang=es><head><meta charset=utf-8><meta name=viewport content="width=device-width, initial-scale=1"><title>Comprobación web frente a Cardmarket · {datetime.now():%d/%m/%Y}</title><style>
body{{font:15px/1.45 "Segoe UI",system-ui,sans-serif;margin:0;background:#0f1f28;color:#eee8dc}}.w{{max-width:1150px;margin:0 auto;padding:24px 16px 60px}}small{{color:#9db0b4}}a{{color:#e8ba5e}}
h2{{margin:28px 0 8px;font-size:18px}}h2.bad{{color:#ff9b85}}h2.warn{{color:#f0c060}}h2.info{{color:#e8e0a0}}.ok{{color:#6fc28a}}
table{{width:100%;border-collapse:collapse;background:#132732}}th,td{{padding:7px 9px;border-bottom:1px solid #24404d;text-align:left;vertical-align:top}}th{{background:#10202a;font-size:12px;text-transform:uppercase;color:#9db0b4}}</style></head>
<body><div class=w><h1>Comprobación: web frente a Cardmarket</h1><small>{datetime.now():%d/%m/%Y %H:%M} · {n_ofertas} ofertas leídas en Mis ofertas · {n_stock} cartas con stock en la web · solo lectura, no se ha cambiado nada</small>
{cuerpo}</div></body></html>"""
    path = os.path.join(nav.DESCARGAS, f'comprobacion_{datetime.now():%Y-%m-%d}.html')
    open(path, 'w', encoding='utf-8').write(doc)
    return path


if __name__ == '__main__':
    log('=== «comprueba»: web frente a Cardmarket (solo lectura) ===')
    ofertas = leer_ofertas()
    P, n, ns = cruzar(ofertas)
    path = informe(P, n, ns)
    json.dump({'ofertas': n, 'con_stock': ns, **P}, open(os.path.join(nav.HERE, 'comprobacion.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    log(f'=== TERMINADO === {path} · ' + ', '.join(f'{k}: {len(v)}' for k, v in P.items()))
