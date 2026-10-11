#!/usr/bin/env node
// Run one browser flow against an xcdev lab environment (lab-ci-*.tmp1.dev) and print a JSON result.
// For what MCP page_check cannot do: hover, file upload, reading text, more than 20 steps, a video.
//
//   CF_ACCESS_CLIENT_ID=... CF_ACCESS_CLIENT_SECRET=... LAB_PASSWORD=... \
//     node ~/.claude/skills/xcloud-test/scripts/lab-flow.mjs flow.json
//
// Run it from the xCloud checkout (Playwright resolves from ./node_modules).
// Secrets come from the environment only (bot_token for the CF pair, LOGINS.md for the password);
// they are never written to the flow file, the output or a screenshot path.
//
// flow.json:
// {
//   "base": "https://lab-ci-pr-7588.tmp1.dev",
//   "as": "user1@xcdev.test",            // omit to stay signed out
//   "out": "~/.xcloud-qa/pr7588/evidence/C-01",   // screenshots (and video) go here
//   "video": false,
//   "steps": [
//     {"goto": "/server/335000003/sites"},
//     {"click": "role=button[name=/add site/i]"},
//     {"fill": "input[name=title]", "value": "x"},
//     {"press": "input[name=title]", "key": "Enter"},
//     {"hover": "text=Backups"},
//     {"upload": "input[type=file]", "file": "/abs/path.zip"},
//     {"wait_for": "text=Saved", "state": "visible"},
//     {"expect_text": "Saved"},                 // fails the step if the text never shows
//     {"read": ".toast"},                       // returns the element's text
//     {"screenshot": "after-save"},           // whole page by default ("full_page": false = viewport only);
//                                             // fails the step if it captured an error/blank/login page
//     {"screenshot": "denied", "allow_error": true},  // a 403/404 page IS the expected result (IDOR checks)
//     {"wait_ms": 500}
//   ]
// }
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';

const require = createRequire(path.join(process.cwd(), 'noop.js'));
const { chromium } = require('playwright');

const LAB_HOST = /^https:\/\/lab-ci-[a-z0-9-]+\.tmp1\.dev\//;
const TRACKERS = /(redditstatic|reddit\.com\/rp|facebook\.net|facebook\.com\/tr|clarity\.ms|googletagmanager|google-analytics|usermaven|openai\.com|mxpnl\.com|mixpanel\.com|crisp\.chat)/;
const STEP_TIMEOUT = 20000;

const home = p => (typeof p === 'string' && p.startsWith('~/') ? path.join(os.homedir(), p.slice(2)) : p);
const flow = JSON.parse(fs.readFileSync(home(process.argv[2]), 'utf8'));
const { CF_ACCESS_CLIENT_ID, CF_ACCESS_CLIENT_SECRET, LAB_PASSWORD } = process.env;
if (!CF_ACCESS_CLIENT_ID || !CF_ACCESS_CLIENT_SECRET) {
  console.log(JSON.stringify({ ok: false, error: 'CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET not set (MCP bot_token)' }));
  process.exit(2);
}
if (flow.as && !LAB_PASSWORD) {
  console.log(JSON.stringify({ ok: false, error: 'LAB_PASSWORD not set (file_get /workspace/LOGINS.md reveal:true)' }));
  process.exit(2);
}

const out = home(flow.out) || path.join(os.homedir(), '.xcloud-qa', 'evidence');
fs.mkdirSync(out, { recursive: true });
const shortUrl = u => { try { const x = new URL(u); return x.host + x.pathname; } catch { return String(u).slice(0, 120); } };

const result = { ok: true, base: flow.base, as: flow.as || null, steps: [], console_errors: [], page_errors: [], failed_requests: [], screenshots: [], video: null };

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  ...(flow.video ? { recordVideo: { dir: out, size: { width: 1280, height: 800 } } } : {}),
});
// Access headers on the lab hosts only (never extraHTTPHeaders: that leaks them to every origin).
await context.route(LAB_HOST, r => r.continue({ headers: { ...r.request().headers(), 'cf-access-client-id': CF_ACCESS_CLIENT_ID, 'cf-access-client-secret': CF_ACCESS_CLIENT_SECRET } }));
await context.route(TRACKERS, r => r.abort());
const page = await context.newPage();
page.setDefaultTimeout(STEP_TIMEOUT);
page.on('console', m => { if (m.type() === 'error') result.console_errors.push(m.text().slice(0, 300)); });
page.on('pageerror', e => result.page_errors.push(String(e.message).slice(0, 300)));
// Status of the last page load: the document, or an Inertia visit (XHR with X-Inertia).
let lastPageStatus = null;
page.on('response', r => {
  const req = r.request();
  if ((req.isNavigationRequest() && r.frame() === page.mainFrame()) || req.headers()['x-inertia']) lastPageStatus = r.status();
});
page.on('response', r => { if (r.status() >= 400) result.failed_requests.push({ status: r.status(), method: r.request().method(), url: shortUrl(r.url()) }); });
// ERR_ABORTED is Inertia cancelling in-flight requests on navigation: noise, not a failure.
page.on('requestfailed', r => { const err = r.failure()?.errorText || ''; if (!TRACKERS.test(r.url()) && !err.includes('ERR_ABORTED')) result.failed_requests.push({ status: 'network', method: r.method(), url: shortUrl(r.url()), error: r.failure()?.errorText }); });

async function dismissCookieBanner() {
  // Customize -> Save My Preferences keeps necessary cookies only. Never "Accept All".
  const customize = page.getByRole('button', { name: /^customize$/i }).first();
  if (!(await customize.waitFor({ state: 'visible', timeout: 3000 }).then(() => true, () => false))) return;
  await customize.click();
  const save = page.getByRole('button', { name: /save my preferences/i }).first();
  if (await save.waitFor({ state: 'visible', timeout: 3000 }).then(() => true, () => false)) await save.click();
}

async function login(email) {
  // xCloud's login is email-first: email -> "Continue with Email" -> password.
  await page.goto(new URL('/login', flow.base).href, { waitUntil: 'domcontentloaded' });
  await dismissCookieBanner();
  await page.getByRole('textbox', { name: /email/i }).first().fill(email);
  await page.getByRole('button', { name: /continue with email/i }).click();
  const pw = page.locator('input[type="password"]').first();
  await pw.waitFor({ state: 'visible' });
  await pw.fill(LAB_PASSWORD);
  await pw.press('Enter');
  await page.waitForURL(u => !u.toString().includes('/login'), { timeout: 30000 });
  await page.evaluate(() => localStorage.setItem('new_ui_banner_seen', 'true'));
}

const ERROR_TEXT = /^\s*(400|401|403|404|405|419|429|500|502|503)\s*(\||\n|\s)\s*(BAD REQUEST|UNAUTHORIZED|FORBIDDEN|NOT FOUND|METHOD NOT ALLOWED|PAGE EXPIRED|TOO MANY REQUESTS|SERVER ERROR|BAD GATEWAY|SERVICE UNAVAILABLE)/i;
const lastHashes = [];

// What a screenshot would show, so an error page is never filed as evidence of success.
async function pageProblems() {
  const problems = [];
  if (lastPageStatus && lastPageStatus >= 400) problems.push(`HTTP ${lastPageStatus}`);
  const info = await page.evaluate(() => {
    const app = document.querySelector('#app');
    return {
      text: (document.body?.innerText || '').trim().slice(0, 400),
      blankInertia: !!(app && app.hasAttribute('data-page') && app.children.length === 0),
      laravelError: !!document.querySelector('.exception-message, [class*="ignition"], #sf-resetcontent'),
    };
  }).catch(() => ({ text: '', blankInertia: false, laravelError: false }));
  const m = info.text.match(ERROR_TEXT);
  if (m) problems.push(`error page "${m[1]} ${m[3]}"`);
  if (/Whoops|Server Error|Something went wrong/i.test(info.text.slice(0, 200))) problems.push('error text at top of page');
  if (info.laravelError) problems.push('Laravel exception page');
  if (info.blankInertia) problems.push('blank page: Inertia app did not mount');
  if (!info.text) problems.push('empty page body');
  if (flow.as && /\/login(\b|$)/.test(page.url())) problems.push('signed out: redirected to /login');
  return [...new Set(problems)];
}

// xCloud's layout scrolls an inner container, not the document, so Playwright's fullPage stops at the
// viewport. Grow the viewport to the tallest scroller's content for the shot, then put it back.
async function fullScreenshot(file, full) {
  if (!full) return page.screenshot({ path: file });
  const size = page.viewportSize();
  const needed = await page.evaluate(() => {
    let extra = 0;
    for (const el of document.querySelectorAll('*')) {
      const style = getComputedStyle(el);
      if (/(auto|scroll)/.test(style.overflowY) && el.scrollHeight > el.clientHeight + 10) {
        extra = Math.max(extra, el.scrollHeight - el.clientHeight);
      }
    }
    return Math.max(document.documentElement.scrollHeight, window.innerHeight + extra);
  }).catch(() => size.height);
  const height = Math.min(Math.max(needed, size.height), 8000);
  if (height > size.height) {
    await page.setViewportSize({ width: size.width, height });
    await page.waitForTimeout(400);
  }
  try {
    return await page.screenshot({ path: file, fullPage: true });
  } finally {
    if (height > size.height) await page.setViewportSize(size);
  }
}

async function runStep(s) {
  if (s.goto) return void (await page.goto(new URL(s.goto, flow.base).href, { waitUntil: 'domcontentloaded' }));
  if (s.click) return void (await page.locator(s.click).first().click());
  if (s.fill) return void (await page.locator(s.fill).first().fill(String(s.value ?? '')));
  if (s.press) return void (await page.locator(s.press).first().press(s.key));
  if (s.hover) return void (await page.locator(s.hover).first().hover());
  if (s.upload) return void (await page.locator(s.upload).first().setInputFiles(home(s.file)));
  if (s.wait_for) return void (await page.locator(s.wait_for).first().waitFor({ state: s.state || 'visible' }));
  if (s.expect_text) return void (await page.getByText(s.expect_text).first().waitFor({ state: 'visible' }));
  if (s.read) return (await page.locator(s.read).first().innerText()).slice(0, 2000);
  if (s.wait_ms) return void (await page.waitForTimeout(s.wait_ms));
  if (s.screenshot) {
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    const file = path.join(out, `${String(s.screenshot).replace(/[^a-z0-9._-]/gi, '-')}.png`);
    const buffer = await fullScreenshot(file, s.full_page !== false);
    const hash = crypto.createHash('sha1').update(buffer).digest('hex');
    const problems = await pageProblems();
    const shot = { file, url: shortUrl(page.url()), status: lastPageStatus, problems };
    const same = lastHashes.find(h => h.hash === hash);
    if (same) shot.identical_to = same.file;   // the action may have changed nothing on screen
    lastHashes.push({ hash, file });
    result.screenshots.push(shot);
    if (problems.length && !s.allow_error) {
      throw new Error(`screenshot shows a problem page (${problems.join('; ')}): not evidence of success`);
    }
    return file;
  }
  throw new Error(`unknown step ${JSON.stringify(s)}`);
}

try {
  if (flow.as) await login(flow.as);
  for (const [i, s] of (flow.steps || []).entries()) {
    const entry = { i, step: s.fill ? { ...s, value: '[set]' } : s };
    try {
      const value = await runStep(s);
      if (value !== undefined) entry.value = value;
      entry.ok = true;
    } catch (e) {
      entry.ok = false;
      entry.error = String(e.message).split('\n')[0].slice(0, 300);
      result.ok = false;
      const file = path.join(out, `fail-step-${i}.png`);
      if (!s.screenshot) {
        await page.screenshot({ path: file, fullPage: true }).catch(() => {});
        result.screenshots.push({ file, url: shortUrl(page.url()), status: lastPageStatus, problems: ['failure screenshot'] });
      }
      result.steps.push(entry);
      break;
    }
    entry.url = shortUrl(page.url());
    result.steps.push(entry);
  }
} catch (e) {
  result.ok = false;
  result.error = String(e.message).split('\n')[0].slice(0, 300);
} finally {
  result.final_url = shortUrl(page.url());
  const video = page.video();
  await context.close();
  if (video) result.video = await video.path().catch(() => null);
  await browser.close();
}
if (result.page_errors.length) result.ok = false;
console.log(JSON.stringify(result, null, 2));
process.exit(result.ok ? 0 : 1);
