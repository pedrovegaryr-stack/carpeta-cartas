// Función de Vercel: cambia el modo de precios editando config.json en GitHub.
// Variables de entorno en Vercel: GITHUB_TOKEN (obligatoria), GITHUB_REPO = "usuario/repositorio" (obligatoria),
// GITHUB_BRANCH (opcional, por defecto "main"), MODO_PIN (opcional: si la pones, el botón pedirá ese PIN).
const API = 'https://api.github.com';

async function gh(path, opts = {}) {
  const r = await fetch(API + path, {
    ...opts,
    headers: {
      Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
      Accept: 'application/vnd.github+json',
      'User-Agent': 'carpeta-cartas',
      ...(opts.headers || {})
    }
  });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(body.message || `GitHub ${r.status}`), { status: r.status });
  return body;
}

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  const repo = process.env.GITHUB_REPO, branch = process.env.GITHUB_BRANCH || 'main';
  if (!process.env.GITHUB_TOKEN || !repo) {
    return res.status(500).json({ error: 'config', message: 'Faltan GITHUB_TOKEN o GITHUB_REPO en Vercel.' });
  }
  const filePath = `/repos/${repo}/contents/config.json?ref=${encodeURIComponent(branch)}`;
  try {
    const file = await gh(filePath);
    const current = JSON.parse(Buffer.from(file.content, 'base64').toString('utf8'));
    if (req.method === 'GET') return res.status(200).json({ ...current, pin: !!process.env.MODO_PIN });

    if (req.method !== 'POST') return res.status(405).json({ error: 'method' });
    let body = req.body;
    if (typeof body === 'string') { try { body = JSON.parse(body); } catch (e) { body = {}; } }
    body = body || {};
    if (process.env.MODO_PIN && String(body.pin || '') !== String(process.env.MODO_PIN)) {
      return res.status(401).json({ error: 'pin', message: 'PIN incorrecto.' });
    }
    if (!['suelo', 'mis-precios'].includes(body.modo)) return res.status(400).json({ error: 'modo' });

    const next = { ...current, modo: body.modo };
    if (body.ajuste !== undefined && !isNaN(Number(body.ajuste))) next.ajuste = Number(body.ajuste);
    if (body.minimo !== undefined && !isNaN(Number(body.minimo))) next.minimo = Number(body.minimo);

    await gh(`/repos/${repo}/contents/config.json`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: `Modo de precios: ${next.modo}`,
        content: Buffer.from(JSON.stringify(next, null, 2) + '\n').toString('base64'),
        sha: file.sha,
        branch
      })
    });
    return res.status(200).json({ ok: true, ...next });
  } catch (err) {
    return res.status(err.status === 401 || err.status === 403 ? 502 : 500)
      .json({ error: 'github', message: err.message });
  }
};
