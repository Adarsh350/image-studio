#!/usr/bin/env node
// Read a business website for image work: every usable image on the homepage and a few internal
// pages (largest srcset candidate, CSS backgrounds, og:image), plus the brand signals a prompt needs
// (palette, fonts, headings, nav, meta) and a homepage screenshot for the visual vibe.
//
//   node harvest.mjs <url> <out-dir> [--pages 6] [--min 400]
//   node harvest.mjs --self-test
//
// Writes <out-dir>/site.json, <out-dir>/home.png and <out-dir>/images/NNN.<ext>.
// site.json.images[]: { file, url, width, height, alt, page, role: photo|logo|graphic, bytes }.
// site.json.pages[]: also outbound (client sites, case studies) and ui (elements that look like product
// UI or work samples: { selector, w, h, hint, text }) for capture.mjs.
// Images whose short side is under --min px (default 400) are dropped, except logos.
import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
// This skill's own node_modules, else creator-studio's (same Playwright version, shared browser cache).
const CANDIDATES = [process.env.PLAYWRIGHT_DIR, join(HERE, '..'), join(HERE, '..', '..', 'creator-studio')].filter(Boolean);

function loadPlaywright() {
  for (const dir of CANDIDATES) {
    try { return createRequire(join(dir, 'package.json'))('playwright'); } catch {}
  }
  throw new Error(`Playwright not found in: ${CANDIDATES.join(', ')}. Run "npm install" in the skill dir, or set PLAYWRIGHT_DIR.`);
}

const HIDE_CSS = `
  [class*="cookie" i], [id*="cookie" i], [class*="consent" i], [id*="consent" i],
  [class*="gdpr" i], [id*="onetrust" i], [class*="cc-window" i], [id*="CybotCookiebot" i],
  [class*="intercom" i], [id*="intercom" i], [class*="crisp" i], iframe[src*="chat" i] { display: none !important; }`;

const EXT = { 'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp', 'image/avif': 'avif', 'image/gif': 'gif', 'image/svg+xml': 'svg' };

async function loadLazy(page) {
  const step = 700;
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  for (let y = 0; y < Math.min(height, 30000); y += step) {
    await page.evaluate((top) => window.scrollTo(0, top), y);
    await page.waitForTimeout(100);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(800);
}

// Runs in the page: image candidates with their natural size, and the page's brand signals.
function collect() {
  const abs = (u) => { try { return new URL(u, location.href).href; } catch { return null; } };
  const largestFromSrcset = (srcset) => {
    let best = null, bestW = 0;
    for (const part of (srcset || '').split(',')) {
      const [u, d] = part.trim().split(/\s+/);
      const w = d ? parseFloat(d) * (d.endsWith('x') ? 1000 : 1) : 1;
      if (u && w >= bestW) { best = u; bestW = w; }
    }
    return best;
  };
  const isLogo = (el, url, alt) =>
    /logo|brand|wordmark/i.test(`${url} ${alt} ${el.className || ''} ${el.id || ''}`) || !!el.closest('header, nav, footer');
  const found = [];
  for (const img of document.querySelectorAll('img')) {
    const pic = img.closest('picture');
    const srcset = [...(pic ? pic.querySelectorAll('source') : []), img].map((s) => s.getAttribute('srcset') || s.getAttribute('data-srcset')).find(Boolean);
    const url = abs(largestFromSrcset(srcset) || img.currentSrc || img.src || img.dataset.src);
    if (url) found.push({ url, alt: img.alt || '', logo: isLogo(img, url, img.alt || '') });
  }
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width < 200 || r.height < 150) continue;
    const bg = getComputedStyle(el).backgroundImage;
    for (const m of bg.matchAll(/url\(["']?([^"')]+)["']?\)/g)) {
      const url = abs(m[1]);
      if (url) found.push({ url, alt: (el.innerText || '').trim().slice(0, 80), logo: false });
    }
  }
  for (const sel of ['meta[property="og:image"]', 'meta[name="twitter:image"]']) {
    const url = abs(document.querySelector(sel)?.content || '');
    if (url) found.push({ url, alt: 'og:image', logo: false });
  }
  // Palette: background and text colors weighted by painted area; skips pure white/black-ish noise later.
  const colors = {};
  const toHex = (c) => {
    const m = c.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?/);
    if (!m || (m[4] !== undefined && parseFloat(m[4]) < 0.5)) return null;
    return '#' + [m[1], m[2], m[3]].map((n) => (+n).toString(16).padStart(2, '0')).join('');
  };
  for (const el of document.querySelectorAll('body, body *')) {
    const r = el.getBoundingClientRect();
    const area = Math.min(r.width * r.height, 2e6);
    if (area < 400) continue;
    const s = getComputedStyle(el);
    const bg = toHex(s.backgroundColor);
    if (bg) colors[bg] = (colors[bg] || 0) + area;
    if (el.childNodes.length && [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) {
      const fg = toHex(s.color);
      if (fg) colors[fg] = (colors[fg] || 0) + area * 0.3;
    }
  }
  const font = (sel) => { const el = document.querySelector(sel); return el ? getComputedStyle(el).fontFamily : null; };
  const texts = (sel, n) => [...document.querySelectorAll(sel)].map((e) => e.innerText.replace(/\s+/g, ' ').trim()).filter(Boolean).slice(0, n);
  const links = [...document.querySelectorAll('a[href]')]
    .map((a) => { try { return new URL(a.getAttribute('href'), location.href); } catch { return null; } })
    .filter((u) => u && u.origin === location.origin && !/\.(pdf|zip|jpe?g|png|webp)$/i.test(u.pathname))
    .map((u) => u.origin + u.pathname);
  // Proof a showcase slot can use: links to client sites and case studies, and on-page elements that
  // look like product UI or work samples (capture.mjs screenshots them by selector).
  const SOCIAL = /(^|\.)(linkedin|instagram|facebook|twitter|x|tiktok|youtube|pinterest|wa|whatsapp|t|threads|google|apple|calendly)\.(com|me|co)$/i;
  const outbound = [...new Map([...document.querySelectorAll('a[href]')].map((a) => {
    let u; try { u = new URL(a.getAttribute('href'), location.href); } catch { return null; }
    if (!/^https?:$/.test(u.protocol) || u.origin === location.origin || SOCIAL.test(u.hostname)) return null;
    return [u.origin + u.pathname, (a.innerText || a.getAttribute('aria-label') || '').replace(/\s+/g, ' ').trim().slice(0, 80)];
  }).filter(Boolean)).entries()].map(([href, text]) => ({ url: href, text })).slice(0, 40);
  const cssPath = (el) => {
    const parts = [];
    for (let e = el; e && e !== document.body; e = e.parentElement) {
      if (e.id) { parts.unshift('#' + CSS.escape(e.id)); return parts.join(' > '); }
      const same = [...e.parentElement.children].filter((s) => s.tagName === e.tagName);
      parts.unshift(e.tagName.toLowerCase() + (same.length > 1 ? `:nth-of-type(${same.indexOf(e) + 1})` : ''));
    }
    return ['body', ...parts].join(' > ');
  };
  const UI_HINT = /mock|demo|preview|dashboard|chat|answer|screen|device|browser|widget|showcase|case|portfolio|work|project|result|report|score|audit|app/i;
  const ui = [];
  for (const el of document.querySelectorAll('main *, section *, body > div *')) {
    const hint = `${el.getAttribute('class') || ''} ${el.id} ${el.getAttribute('aria-label') || ''}`;
    if (!UI_HINT.test(hint) || el.closest('header, nav, footer')) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 280 || r.height < 180 || r.height > 1800) continue;
    if (ui.some((u) => u.el.contains(el))) continue; // keep the outermost match
    ui.push({ el, selector: cssPath(el), w: Math.round(r.width), h: Math.round(r.height),
      hint: hint.trim().slice(0, 80), text: (el.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 120) });
    if (ui.length >= 15) break;
  }
  return {
    found, colors, links, outbound, ui: ui.map(({ el, ...u }) => u),
    title: document.title,
    description: document.querySelector('meta[name="description"]')?.content || '',
    lang: document.documentElement.lang || '',
    headings: texts('h1, h2', 20),
    nav: texts('header a, nav a', 20),
    fonts: { heading: font('h1, h2'), body: font('p, body') },
  };
}

// Natural size of each candidate, measured in the page so CSS backgrounds and lazy srcsets work too.
async function measure(page, urls) {
  return page.evaluate(async (list) => Promise.all(list.map((u) => new Promise((res) => {
    const im = new Image();
    const done = () => res({ url: u, width: im.naturalWidth, height: im.naturalHeight });
    im.onload = done; im.onerror = done; im.src = u;
    setTimeout(done, 10000);
  }))), urls);
}

async function harvest(url, outDir, { pages = 6, min = 400 } = {}) {
  mkdirSync(join(outDir, 'images'), { recursive: true });
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const site = { url, pages: [], images: [] };
  const seen = new Map(); // url -> { alt, page, logo }
  const colors = {};
  try {
    const queue = [url];
    const visited = new Set();
    while (queue.length && visited.size < pages) {
      const next = new URL(queue.shift());
      const target = next.origin + next.pathname; // "site.com" and "site.com/" are one page
      if (visited.has(target)) continue;
      visited.add(target);
      try {
        await page.goto(target, { waitUntil: 'domcontentloaded', timeout: 45000 });
      } catch (e) {
        site.pages.push({ url: target, error: String(e.message || e).slice(0, 200) });
        continue;
      }
      await page.evaluate((css) => document.head.append(Object.assign(document.createElement('style'), { textContent: css })), HIDE_CSS);
      await loadLazy(page);
      if (visited.size === 1) await page.screenshot({ path: join(outDir, 'home.png') });
      const info = await page.evaluate(collect);
      const { found, colors: c, links, ...meta } = info;
      site.pages.push({ url: target, ...meta });
      for (const [k, v] of Object.entries(c)) colors[k] = (colors[k] || 0) + v;
      for (const f of found) if (!seen.has(f.url) && !f.url.startsWith('data:')) seen.set(f.url, { alt: f.alt, page: target, logo: f.logo });
      // Shallow pages first (/about, /services) — they carry the most representative imagery.
      for (const l of links.sort((a, b) => a.split('/').length - b.split('/').length)) if (!visited.has(l) && !queue.includes(l)) queue.push(l);
    }

    const sizes = await measure(page, [...seen.keys()]);
    let n = 0;
    for (const { url: u, width, height } of sizes) {
      const meta = seen.get(u);
      const svg = /\.svg(\?|$)/i.test(u);
      if (!meta.logo && !svg && Math.min(width, height) < min) continue;
      if (!svg && !width) continue;
      let res;
      try { res = await ctx.request.get(u, { timeout: 30000 }); } catch { continue; }
      if (!res.ok()) continue;
      const type = (res.headers()['content-type'] || '').split(';')[0].trim();
      const ext = EXT[type] || (svg ? 'svg' : null);
      if (!ext) continue;
      const body = await res.body();
      if (body.length > 25e6) continue;
      const file = join('images', `${String(++n).padStart(3, '0')}.${ext}`);
      writeFileSync(join(outDir, file), body);
      const role = meta.logo || svg ? 'logo' : ext === 'png' && Math.min(width, height) < 700 ? 'graphic' : 'photo';
      site.images.push({ file, url: u, width, height, alt: meta.alt, page: meta.page, role, bytes: body.length });
    }
  } finally {
    await browser.close();
  }
  site.palette = Object.entries(colors).sort((a, b) => b[1] - a[1]).slice(0, 10).map(([hex]) => hex);
  site.images.sort((a, b) => (a.role === 'photo' ? 0 : 1) - (b.role === 'photo' ? 0 : 1) || b.width * b.height - a.width * a.height);
  writeFileSync(join(outDir, 'site.json'), JSON.stringify(site, null, 2));
  return site;
}

async function selfTest() {
  const { createServer } = await import('node:http');
  const dir = join(process.env.TEMP || '/tmp', 'image-studio-harvest-selftest');
  // A tiny site: a large photo via srcset, the same photo as a CSS background (deduped), a small
  // icon (dropped), a header logo, and a second page reached from the nav.
  const box = (w, h, fill) => `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}"><rect width="${w}" height="${h}" fill="${fill}"/></svg>`;
  const files = {
    '/': ['text/html', `<html><head><title>Test Co</title><meta name="description" content="We test things"></head>
      <body style="background:#f4efe6;color:#1d2b24;margin:0">
      <header><img src="/logo.svg" alt="Test Co logo" width="120" height="40"><a href="/about">About</a></header>
      <h1>Hello</h1><div style="width:800px;height:400px;background-image:url('/hero.svg')">bg</div>
      <img srcset="/hero.svg 1600w" width="800" alt="hero"><img src="/icon.svg" width="32" alt="icon">
      <main><div class="demo-preview" style="width:600px;height:300px">Live demo</div></main>
      <a href="https://client-site.example/">Client site</a><a href="https://www.linkedin.com/company/x">in</a>
      <p>Body copy</p></body></html>`],
    '/about': ['text/html', `<html><body style="background:#f4efe6"><h1>About us</h1></body></html>`],
    '/hero.svg': ['image/svg+xml', box(1600, 1000, '#2a6f4e')],
    '/logo.svg': ['image/svg+xml', box(120, 40, '#000')],
    '/icon.svg': ['image/svg+xml', box(32, 32, '#f00')],
  };
  const server = createServer((req, res) => {
    const f = files[req.url];
    res.writeHead(f ? 200 : 404, { 'content-type': f ? f[0] : 'text/plain' });
    res.end(f ? f[1] : '');
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const base = `http://127.0.0.1:${server.address().port}`;
  let site;
  try {
    site = await harvest(`${base}/`, dir, { pages: 3 });
  } finally {
    server.close();
  }
  const urls = site.images.map((i) => i.url.replace(base, ''));
  const home = site.pages[0];
  const ok = home.outbound?.length === 1 && home.outbound[0].text === 'Client site' && home.ui?.length === 1
    && home.ui[0].hint.includes('demo-preview')
    && site.pages.length === 2 && site.pages[0].title === 'Test Co' && site.palette.includes('#f4efe6')
    && urls.includes('/hero.svg') && urls.includes('/logo.svg') && urls.length === 3 /* svg icon kept as logo-ish */
    && existsSync(join(dir, 'home.png')) && existsSync(join(dir, site.images[0].file));
  console.log(ok ? `self-test OK (${site.pages.length} pages, ${urls.length} images, palette ${site.palette.slice(0, 3).join(' ')})`
    : `self-test FAILED: ${JSON.stringify({ pages: site.pages.length, urls, palette: site.palette })}`);
  if (!ok) process.exit(1);
}

const args = process.argv.slice(2);
if (args[0] === '--self-test') {
  await selfTest();
} else {
  const opt = (k, d) => { const i = args.indexOf(`--${k}`); return i >= 0 ? args[i + 1] : d; };
  const [url, outDir] = args;
  if (!url || !outDir || url.startsWith('--')) {
    console.error('usage: harvest.mjs <url> <out-dir> [--pages 6] [--min 400]');
    process.exit(2);
  }
  const site = await harvest(url, outDir, { pages: +opt('pages', 6), min: +opt('min', 400) });
  const roles = site.images.reduce((m, i) => ({ ...m, [i.role]: (m[i.role] || 0) + 1 }), {});
  console.log(`${site.pages.length} pages, ${site.images.length} images ${JSON.stringify(roles)}, palette ${site.palette.slice(0, 6).join(' ')}`);
  console.log(`-> ${join(outDir, 'site.json')}`);
}
