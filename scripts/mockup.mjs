#!/usr/bin/env node
// Put real captures into a clean device frame on the brand ground, at the slot's size. Layouts:
//   browser  one desktop capture in a browser window
//   phone    one mobile capture in a phone
//   pair     desktop capture + mobile capture of the same site (img1 desktop, img2 mobile)
//   split    before / after, two desktop captures (img1 before, img2 after)
//   element  one UI element (a capture made with --selector) lifted on the ground
//
//   node mockup.mjs <layout> <out.png> --size 1080x1350 --img a.png [--img b.png] [--bg "#0a0908"]
//        [--fg "#f2ece0"] [--ground texture.jpg] [--chrome light|dark] [--url example.com]
//        [--labels "Before,After"] [--margin 0.08]
//   node mockup.mjs --batch <jobs.json>   # [{"layout", "out", "size", "imgs": [...], "bg"?, ...}]
//   node mockup.mjs --self-test
//
// Renders at 2x (out is 2W x 2H) so `finish.py fit` downsizes it cleanly to the delivery size.
// Prints the worst upscale of any capture; above 1.5 the capture is too small for that slot.
// The only text drawn is --url and --labels: pass the site's real domain and plain labels.
import { createRequire } from 'node:module';
import { mkdirSync, readFileSync, existsSync } from 'node:fs';
import { join, dirname, extname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const TEMPLATE = join(HERE, '..', 'templates', 'mockup.html');
const CANDIDATES = [process.env.PLAYWRIGHT_DIR, join(HERE, '..'), join(HERE, '..', '..', 'creator-studio')].filter(Boolean);
const LAYOUTS = { browser: 1, phone: 1, pair: 2, split: 2, element: 1 };
const MIME = { '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.avif': 'image/avif' };

function loadPlaywright() {
  for (const dir of CANDIDATES) {
    try { return createRequire(join(dir, 'package.json'))('playwright'); } catch {}
  }
  throw new Error(`Playwright not found in: ${CANDIDATES.join(', ')}. Run "npm install" in the skill dir, or set PLAYWRIGHT_DIR.`);
}

const dataUri = (file) => `data:${MIME[extname(file).toLowerCase()] || 'image/png'};base64,${readFileSync(file).toString('base64')}`;

function validate(job) {
  const need = LAYOUTS[job.layout];
  if (!need) return `unknown layout "${job.layout}" (${Object.keys(LAYOUTS).join(', ')})`;
  if (!/^\d+x\d+$/.test(job.size || '')) return 'size must be WxH';
  if ((job.imgs || []).length !== need) return `${job.layout} takes ${need} image(s), got ${(job.imgs || []).length}`;
  const missing = [...job.imgs, job.ground].filter(Boolean).find((f) => !existsSync(f));
  if (missing) return `not found: ${missing}`;
  if (job.labels && job.labels.length !== 2) return 'labels takes two comma-separated values';
  return null;
}

async function renderAll(jobs) {
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch();
  const template = readFileSync(TEMPLATE, 'utf8');
  const results = [];
  try {
    for (const job of jobs) {
      const bad = validate(job);
      if (bad) { results.push({ out: job.out, ok: false, error: bad }); continue; }
      const [w, h] = job.size.split('x').map(Number);
      const params = { layout: job.layout, w, h, imgs: job.imgs.map(dataUri), ground: job.ground && dataUri(job.ground),
        bg: job.bg || '#f2ece0', fg: job.fg || '#1d1b18', chrome: job.chrome || 'light', url: job.url || '',
        labels: job.labels || null, margin: job.margin, shadow: job.shadow };
      const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 2 });
      const page = await ctx.newPage();
      try {
        await page.setContent(template.replace('/*PARAMS*/', JSON.stringify(params).replace(/</g, '\\u003c')));
        await page.waitForFunction(() => window.__done, null, { timeout: 60000 });
        const error = await page.evaluate(() => window.__error);
        if (error) throw new Error(error);
        mkdirSync(dirname(job.out), { recursive: true });
        await page.locator('#stage').screenshot({ path: job.out });
        results.push({ out: job.out, ok: true, upscale: +(await page.evaluate(() => window.__upscale)).toFixed(2) });
      } catch (e) {
        results.push({ out: job.out, ok: false, error: String(e.message || e).split('\n')[0].slice(0, 200) });
      } finally {
        await ctx.close();
      }
    }
  } finally {
    await browser.close();
  }
  return results;
}

const report = (r) => (r.ok ? `${r.upscale > 1.5 ? 'WARN' : 'ok  '} ${r.out} (upscale ${r.upscale}x${r.upscale > 1.5 ? ': capture too small for this slot' : ''})`
  : `FAIL ${r.out}: ${r.error}`);

async function selfTest() {
  const dir = join(process.env.TEMP || '/tmp', 'image-studio-mockup-selftest');
  mkdirSync(dir, { recursive: true });
  // Fake captures: a desktop page and a tall mobile page, made with the same browser.
  const { chromium } = loadPlaywright();
  const b = await chromium.launch();
  const page = (bg) => `<body style="margin:0;font:40px sans-serif;background:linear-gradient(${bg},#fff)"><h1 style="margin:40px">Site</h1></body>`;
  const shoot = async (vw, vh, dpr, file, bg) => {
    const c = await b.newContext({ viewport: { width: vw, height: vh }, deviceScaleFactor: dpr });
    const p = await c.newPage(); await p.setContent(page(bg)); await p.screenshot({ path: join(dir, file) }); await c.close();
  };
  await shoot(1440, 900, 2, 'desk.png', '#2a6f4e');
  await shoot(390, 844, 3, 'mob.png', '#8f6b24');
  await shoot(900, 540, 2, 'el.png', '#655f5a');
  await b.close();
  const D = join(dir, 'desk.png'), Mo = join(dir, 'mob.png');
  const jobs = [
    { layout: 'browser', size: '1080x1350', imgs: [D], url: 'example.com' },
    { layout: 'phone', size: '1080x1920', imgs: [Mo], bg: '#0a0908' },
    { layout: 'pair', size: '1080x1350', imgs: [D, Mo], url: 'example.com' },
    { layout: 'pair', size: '1920x1080', imgs: [D, Mo], chrome: 'dark', bg: '#0a0908' },
    { layout: 'split', size: '1920x1080', imgs: [D, D], labels: ['Before', 'After'] },
    { layout: 'split', size: '1080x1350', imgs: [D, D], labels: ['Before', 'After'] },
    { layout: 'element', size: '1080x1080', imgs: [join(dir, 'el.png')] },
    { layout: 'pair', size: '1080x1080', imgs: [D] }, // wrong image count: must fail cleanly
  ].map((j, k) => ({ ...j, out: join(dir, `out-${k}-${j.layout}.png`) }));
  const res = await renderAll(jobs);
  const sizeOk = res.slice(0, 7).every((r, k) => {
    const buf = readFileSync(r.out); const [w, h] = jobs[k].size.split('x').map(Number);
    return buf.readUInt32BE(16) === 2 * w && buf.readUInt32BE(20) === 2 * h;
  });
  const ok = res.slice(0, 7).every((r) => r.ok && r.upscale > 0 && r.upscale <= 1.5) && !res[7].ok && sizeOk;
  res.forEach((r) => console.log(report(r)));
  console.log(ok ? `self-test OK (7 layouts rendered at 2x into ${dir}, bad job rejected)` : 'self-test FAILED');
  if (!ok) process.exit(1);
}

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(`--${k}`); return i >= 0 ? args[i + 1] : d; };
if (args[0] === '--self-test') {
  await selfTest();
} else if (args[0] === '--batch' && args[1]) {
  const res = await renderAll(JSON.parse(readFileSync(args[1], 'utf8')));
  res.forEach((r) => console.log(report(r)));
  if (res.some((r) => !r.ok)) process.exitCode = 1;
} else {
  const [layout, out] = args;
  if (!layout || !out || layout.startsWith('--')) {
    console.error('usage: mockup.mjs <browser|phone|pair|split|element> <out.png> --size WxH --img a.png [--img b.png]\n'
      + '       [--bg #hex] [--fg #hex] [--ground img] [--chrome light|dark] [--url domain] [--labels "Before,After"] [--margin 0.08]\n'
      + '       mockup.mjs --batch <jobs.json> | --self-test');
    process.exit(2);
  }
  const imgs = args.flatMap((a, i) => (a === '--img' ? [args[i + 1]] : []));
  const [r] = await renderAll([{ layout, out, size: opt('size'), imgs, bg: opt('bg'), fg: opt('fg'), ground: opt('ground'),
    chrome: opt('chrome'), url: opt('url'), labels: opt('labels')?.split(',').map((s) => s.trim()),
    margin: opt('margin') && +opt('margin') }]);
  console.log(report(r));
  if (!r.ok) process.exitCode = 1;
}
