/* Idioma de las cartas: banderas en SVG, nombres y etiqueta «bandera + código».
   Lo usan index.html, informe.html e intercambio.html (web y PDF). El idioma por defecto es «es». */
(function(){
  const NAMES = {es:'Español', en:'Inglés', fr:'Francés', de:'Alemán', it:'Italiano', pt:'Portugués', ja:'Japonés', ko:'Coreano', zh:'Chino'};
  // Banderas en un lienzo de 30×20 (se recortan con esquinas redondeadas donde se usan)
  const FLAGS = {
    es: '<rect width="30" height="20" fill="#c60b1e"/><rect y="5" width="30" height="10" fill="#ffc400"/>',
    en: '<rect width="30" height="20" fill="#012169"/>' +
        '<path d="M0,0L30,20M30,0L0,20" stroke="#fff" stroke-width="4"/>' +
        '<path d="M0,0L30,20M30,0L0,20" stroke="#c8102e" stroke-width="1.6"/>' +
        '<path d="M15,0V20M0,10H30" stroke="#fff" stroke-width="6"/>' +
        '<path d="M15,0V20M0,10H30" stroke="#c8102e" stroke-width="3.4"/>',
    fr: '<rect width="30" height="20" fill="#fff"/><rect width="10" height="20" fill="#002395"/><rect x="20" width="10" height="20" fill="#ed2939"/>',
    de: '<rect width="30" height="20" fill="#ffce00"/><rect width="30" height="13.34" fill="#dd0000"/><rect width="30" height="6.67" fill="#000"/>',
    it: '<rect width="30" height="20" fill="#fff"/><rect width="10" height="20" fill="#009246"/><rect x="20" width="10" height="20" fill="#ce2b37"/>',
    pt: '<rect width="30" height="20" fill="#ff0000"/><rect width="12" height="20" fill="#006600"/><circle cx="12" cy="10" r="4" fill="#ffcc00" stroke="#fff" stroke-width=".8"/>',
    ja: '<rect width="30" height="20" fill="#fff"/><circle cx="15" cy="10" r="6" fill="#bc002d"/>',
    ko: '<rect width="30" height="20" fill="#fff"/><path d="M9,10a6,6 0 0 1 12,0z" fill="#cd2e3a"/><path d="M9,10a6,6 0 0 0 12,0z" fill="#0047a0"/>',
    zh: '<rect width="30" height="20" fill="#de2910"/><path d="M6,3l1.1,3.4h3.6l-2.9,2.1 1.1,3.4-2.9-2.1-2.9,2.1 1.1-3.4-2.9-2.1h3.6z" fill="#ffde00"/>'
  };
  const OTHER = '<rect width="30" height="20" fill="#8a979b"/>';
  const code = l => (l || 'es').toLowerCase();
  const flagSVG = (l, w = 16, h = 11) =>
    `<svg class="lang-flag" viewBox="0 0 30 20" width="${w}" height="${h}" preserveAspectRatio="xMidYMid slice" aria-hidden="true">${FLAGS[code(l)] || OTHER}</svg>`;

  // Estilo de la etiqueta en la web: pastilla blanca con sombra suave; si no es español, oscura con borde dorado para que destaque.
  const css = `.lang{position:absolute;top:6px;left:6px;z-index:3;display:inline-flex;align-items:center;gap:4px;padding:2px 6px 2px 3px;
    border-radius:999px;background:rgba(255,255,255,.95);color:#10202a;font:800 10.5px/1 "Manrope","Segoe UI",system-ui,sans-serif;letter-spacing:.04em;
    box-shadow:0 1px 3px rgba(0,0,0,.35),0 0 0 .5px rgba(0,0,0,.12);pointer-events:none}
  .lang .lang-flag{display:block;width:16px;height:11px;border-radius:2.5px;box-shadow:0 0 0 .5px rgba(0,0,0,.25)}
  .lang.lang-other{background:#10202a;color:#fff;box-shadow:0 1px 4px rgba(0,0,0,.45),0 0 0 1.5px #e8ba5e}`;
  const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  // Etiqueta HTML para poner dentro de un contenedor con position:relative (la foto)
  const badgeHTML = l => `<span class="lang ${code(l) === 'es' ? '' : 'lang-other'}" title="${NAMES[code(l)] || code(l).toUpperCase()}">${flagSVG(l)}${code(l).toUpperCase()}</span>`;

  // Etiqueta como imagen PNG (para los PDF): {data, ratio}. Se dibuja un SVG en un canvas a 4×.
  const cache = {};
  function badgePNG(l){
    const c = code(l);
    if (cache[c]) return cache[c];
    const other = c !== 'es', label = c.toUpperCase();
    const W = 30 + label.length * 9.5 + 10, H = 24;           // unidades SVG
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${(W+6)*4}" height="${(H+6)*4}" viewBox="-3 -2 ${W+6} ${H+6}">
      <defs><filter id="s" x="-20%" y="-30%" width="140%" height="170%"><feDropShadow dx="0" dy="1" stdDeviation="1.2" flood-opacity=".45"/></filter>
      <clipPath id="c"><rect x="4" y="4" width="24" height="16" rx="3"/></clipPath></defs>
      <rect width="${W}" height="${H}" rx="${H/2}" fill="${other ? '#10202a' : '#ffffff'}" ${other ? 'stroke="#e8ba5e" stroke-width="1.6"' : ''} filter="url(#s)"/>
      <g clip-path="url(#c)"><svg x="4" y="4" width="24" height="16" viewBox="0 0 30 20" preserveAspectRatio="xMidYMid slice">${FLAGS[c] || OTHER}</svg></g>
      <rect x="4" y="4" width="24" height="16" rx="3" fill="none" stroke="rgba(0,0,0,.25)" stroke-width=".6"/>
      <text x="32" y="16.6" font-family="Helvetica,Arial,sans-serif" font-weight="800" font-size="13" letter-spacing=".4" fill="${other ? '#ffffff' : '#10202a'}">${label}</text></svg>`;
    cache[c] = new Promise(res => {
      const img = new Image();
      img.onload = () => {
        const cv = document.createElement('canvas'); cv.width = img.width; cv.height = img.height;
        cv.getContext('2d').drawImage(img, 0, 0);
        res({data: cv.toDataURL('image/png'), ratio: img.width / img.height});
      };
      img.onerror = () => res(null);
      img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
    });
    return cache[c];
  }
  // Pone la etiqueta en la esquina superior izquierda de una foto del PDF (x, y, ancho de la foto en mm)
  async function pdfBadge(doc, l, x, y, photoW){
    const b = await badgePNG(l); if (!b) return;
    const h = Math.max(2.6, Math.min(4.6, photoW * 0.16)), w = h * b.ratio;
    doc.addImage(b.data, 'PNG', x + h*0.18, y + h*0.18, w, h);
  }

  // Número de idioma en Cardmarket (?language=N) y filtro de ofertas del suelo: idioma de la carta + Near Mint o mejor
  const CM = {en:1, fr:2, de:3, es:4, it:5, zh:6, ja:7, pt:8, ko:10};
  const filtro = l => `?language=${CM[code(l)] || 4}&minCondition=2`;

  window.IDIOMAS = {NAMES, code, name: l => NAMES[code(l)] || code(l).toUpperCase(), flagSVG, badgeHTML, badgePNG, pdfBadge, CM, filtro};
})();
