#!/usr/bin/env node
// Screenshot real proof of what a business does: a client site it built, its product UI, a demo
// element on its own site. These are real pixels, so they may carry text and UI (the no-text rule is
// for generated images only).
//
//   node capture.mjs <url> <out.png> [--device desktop|mobile] [--selector "<css>"] [--full] [--wait 1500]
//   node capture.mjs --batch <jobs.json>      # [{"url", "out", "device"?, "selector"?, "full"?, "wait"?}]
//   node capture.mjs --self-test
//
// desktop = 1440x900 at 2x (2880px wide), mobile = 390x844 at 3x (1170px wide), so a capture survives
// a full-size crop. --selector screenshots one element (selectors come from site.json pages[].ui);
// --full takes the whole page; otherwise the first viewport. Cookie banners and chat widgets are hidden.
import { createRequire } from 'node:module';
import { mkdirSync, readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
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
  [class*="intercom" i], [id*="intercom" i], [class*="crisp" i], iframe[src*="chat" i],
  [class*="tidio" i], [id*="hubspot-messages" i], [class*="drift-" i] { display: none !important; }`;

const DEVICES = {
  desktop: { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 },
  mobile: {
    viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true,
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1',
  },
};

async function settle(page) {
  // Scroll through once so lazy images and scroll-triggered reveals load, then return to the top.
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  for (let y = 0; y < Math.min(height, 20000); y += 700) {
    await page.evaluate((top) => window.scrollTo(0, top), y);
    await page.waitForTimeout(80);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {});
}

async function captureAll(jobs) {
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch();
  const results = [];
  try {
    for (const job of jobs) {
      const ctx = await browser.newContext({ ...DEVICES[job.device || 'desktop'], reducedMotion: 'reduce' });
      const page = await ctx.newPage();
      try {
        await page.goto(job.url, { waitUntil: 'domcontentloaded', timeout: 45000 });
        await page.addStyleTag({ content: HIDE_CSS });
        await settle(page);
        await page.waitForTimeout(job.wait ?? 1500);
        mkdirSync(dirname(job.out), { recursive: true });
        if (job.selector) {
          const el = page.locator(job.selector).first();
          await el.scrollIntoViewIfNeeded({ timeout: 10000 });
          await page.waitForTimeout(600);
          await el.screenshot({ path: job.out, animations: 'disabled' });
        } else {
          await page.screenshot({ path: job.out, fullPage: !!job.full, animations: 'disabled' });
        }
        results.push({ out: job.out, ok: true });
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

function pngSize(file) {
  const b = readFileSync(file);
  return [b.readUInt32BE(16), b.readUInt32BE(20)];
}

async function selfTest() {
  const { createServer } = await import('node:http');
  const dir = join(process.env.TEMP || '/tmp', 'image-studio-capture-selftest');
  const html = `<html><body style="margin:0;background:#f4efe6">
    <div class="cookie-banner" style="position:fixed;top:0;left:0;width:100%;height:200px;background:red">cookies</div>
    <h1>Client site</h1><div id="demo" style="width:500px;height:250px;background:#2a6f4e">Demo</div>
    <div style="height:2000px"></div></body></html>`;
  const server = createServer((req, res) => { res.writeHead(200, { 'content-type': 'text/html' }); res.end(html); });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const url = `http://127.0.0.1:${server.address().port}/`;
  let res;
  try {
    res = await captureAll([
      { url, out: join(dir, 'desktop.png'), wait: 0 },
      { url, out: join(dir, 'mobile.png'), device: 'mobile', wait: 0 },
      { url, out: join(dir, 'el.png'), selector: '#demo', wait: 0 },
      // The banner is hidden, so screenshotting it fails: proves HIDE_CSS and the error report at once.
      { url, out: join(dir, 'bad.png'), selector: '.cookie-banner', wait: 0 },
    ]);
  } finally {
    server.close();
  }
  const [d, m, e] = ['desktop', 'mobile', 'el'].map((n) => pngSize(join(dir, `${n}.png`)));
  const near = (a, b) => Math.abs(a[0] - b[0]) <= 3 && Math.abs(a[1] - b[1]) <= 3; // subpixel rounding
  const ok = res.slice(0, 3).every((r) => r.ok) && !res[3].ok
    && near(d, [2880, 1800]) && near(m, [1170, 2532]) && near(e, [1000, 500])
    && existsSync(join(dir, 'el.png'));
  console.log(ok ? `self-test OK (desktop ${d.join('x')}, mobile ${m.join('x')}, element ${e.join('x')}, hidden banner reported)`
    : `self-test FAILED: ${JSON.stringify({ res, d, m, e })}`);
  if (!ok) process.exit(1);
}

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(`--${k}`); return i >= 0 ? args[i + 1] : d; };
if (args[0] === '--self-test') {
  await selfTest();
} else if (args[0] === '--batch' && args[1]) {
  const res = await captureAll(JSON.parse(readFileSync(args[1], 'utf8')));
  for (const r of res) console.log(r.ok ? `ok   ${r.out}` : `FAIL ${r.out}: ${r.error}`);
  if (res.some((r) => !r.ok)) process.exitCode = 1;
} else {
  const [url, out] = args;
  if (!url || !out || url.startsWith('--') || (opt('device') && !DEVICES[opt('device')])) {
    console.error('usage: capture.mjs <url> <out.png> [--device desktop|mobile] [--selector "<css>"] [--full] [--wait 1500]\n'
      + '       capture.mjs --batch <jobs.json> | --self-test');
    process.exit(2);
  }
  const [r] = await captureAll([{ url, out, device: opt('device', 'desktop'), selector: opt('selector'),
    full: args.includes('--full'), wait: +opt('wait', 1500) }]);
  console.log(r.ok ? `ok   ${r.out}` : `FAIL ${r.out}: ${r.error}`);
  if (!r.ok) process.exitCode = 1;
}
