#!/usr/bin/env python3
"""
site_crawl.py — opens EVERY page of a Pinnacle UI the way a visitor would, and flags what
we used to find by hand: pages that fail to load, error text, console/network errors,
stale dates, dead or duplicate menu links, and text repeated across pages.

Routes are read from the UI's own src/App.jsx, so a new page is covered automatically.
Menu links are discovered by opening the real (mobile) menu and clicking every entry.

Usage (Mac terminal, from the product folder, with the UI dev server + API running):
    python3 tools/audit/site_crawl.py                      # http://localhost:5174
    SITE_URL=https://veridia.pinnacletranscore.com python3 tools/audit/site_crawl.py
Options (env): SITE_URL, APP_JSX (default ui/src/App.jsx), STALE_DAYS (default 5),
               SKIP_ROUTES (comma list, default /login,/verify), ALLOW_DUP_MENU (default /universe),
               ROUTE_SAMPLES (e.g. symbol=AAPL: crawl pages like /stock/:symbol with that sample value),
               STATIC_DATE_ROUTES / DUP_OK_ROUTES (comma lists; a trailing * matches a prefix, e.g. /flags/*)
Exit code: 1 if any ERROR (so cron / Day Close can alert), else 0.
Requires: pip install playwright && playwright install chromium
"""
import os, re, sys, json, time
from datetime import date, datetime
from pathlib import Path

BASE = os.getenv("SITE_URL", "http://localhost:5174").rstrip("/")
APP_JSX = Path(os.getenv("APP_JSX", "ui/src/App.jsx"))
STALE_DAYS = int(os.getenv("STALE_DAYS", "5"))
ALLOW_DUP = set(filter(None, os.getenv("ALLOW_DUP_MENU", "/universe").split(",")))
STATIC_DATES = set(filter(None, os.getenv("STATIC_DATE_ROUTES", "/,/backtests,/infrastructure").split(",")))  # pages whose dates are deliberate history (a trailing * matches a prefix, e.g. /flags/*)
DUP_OK = set(filter(None, os.getenv("DUP_OK_ROUTES", "/,/veridia-live").split(",")))  # pages that may share text on purpose (templates, walkthroughs); trailing * allowed
PENDING_MENU = set(filter(None, os.getenv("PENDING_MENU", "Register free").split(",")))  # known, planned (auth build)
# per-page allowed age: Cross-Product Correlation trails by design (Quant grades 3-day predictions ~3 market days late)
ROUTE_STALE = {"/cross-product-correlation": 10}
SHORT_PAGES = {"/register", "/login", "/verify"}  # small forms are legitimately short
# SEC (and some other sites) refuse requests without a descriptive User-Agent that names a contact.
EXTERNAL_UA = os.getenv("EXTERNAL_UA", "PinnacleSiteAudit/1.0 (vijay.cloudarchitect@gmail.com)")
EXTERNAL_DELAY = 0.2  # seconds between external requests (SEC fair access allows 10/s; this stays well under)
# Elements that stick out past the right edge of the phone screen. Only the outermost ones are listed:
# an element whose parent also sticks out is a consequence, not the cause.
OVERFLOW_JS = """() => {
  const w = window.innerWidth, out = [];
  const rect = e => e.getBoundingClientRect();
  const sticks = e => rect(e).right > w + 4 && rect(e).width > 0;
  // inside a box that scrolls or clips by itself (overflow-x not visible) that does not stick out: not a cause
  const clipped = e => {
    for (let p = e.parentElement; p && p !== document.documentElement; p = p.parentElement) {
      if (getComputedStyle(p).overflowX !== 'visible' && !sticks(p)) return true;
    }
    return false;
  };
  const name = e => e.tagName.toLowerCase() + ((typeof e.className === 'string' && e.className.trim().split(/\\s+/)[0]) ? '.' + e.className.trim().split(/\\s+/)[0] : '');
  for (const el of document.querySelectorAll('body *')) {
    if (!sticks(el) || clipped(el)) continue;
    if (el.parentElement && el.parentElement !== document.body && sticks(el.parentElement)) continue;
    const r = rect(el);
    out.push({tag: el.tagName.toLowerCase(), id: el.id || '',
              cls: (typeof el.className === 'string' && el.className.trim().split(/\\s+/)[0]) || '',
              text: (el.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 30),
              width: Math.round(r.width), right: Math.round(r.right),
              parent: el.parentElement ? name(el.parentElement) : ''});
  }
  return out.slice(0, 30);
}"""

# What a person looks at when they eyeball a page, measured instead. Thresholds are deliberately forgiving:
# they exist to catch real defects (cut-off text, overlapping text, unusable buttons, unreadable or invisible
# text, broken images), not to impose a design.
LAYOUT_CFG = {"minTap": 32, "minFont": 11, "minContrast": 2.5, "overlap": 0.3}
LAYOUT_LABELS = {
    "clipped": "text cut off by its box",
    "overlap": "text overlapping other text",
    "tap": "buttons/links too small to tap (under 32px)",
    "small": "text too small to read (under 11px)",
    "image": "broken image",
    "contrast": "text nearly invisible against its background (contrast under 2.5)",
}

LAYOUT_JS = """(cfg) => {
  const out = {clipped: [], overlap: [], tap: [], small: [], image: [], contrast: []};
  const rect = e => e.getBoundingClientRect();
  // the body of a closed <details> is not on screen, although the browser may still report a box for it
  const shut = e => { const d = e.closest('details:not([open])'), sm = e.closest('summary'); return !!d && !(sm && sm.parentElement === d); };
  const vis = e => { const r = rect(e), s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && parseFloat(s.opacity) > 0.05 && !shut(e); };
  const label = e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') +
    ((typeof e.className === 'string' && e.className.trim()) ? '.' + e.className.trim().split(/\\s+/)[0] : '') +
    ' “' + (e.innerText || e.alt || e.value || '').trim().replace(/\\s+/g, ' ').slice(0, 24) + '”';
  const own = e => [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length >= 2);
  // scrolled out of view inside a box that scrolls or clips by itself: not a layout defect
  const hiddenByBox = e => { const r = rect(e);
    for (let p = e.parentElement; p && p !== document.documentElement; p = p.parentElement) {
      const s = getComputedStyle(p);
      if (s.overflowX !== 'visible' || s.overflowY !== 'visible') { const pr = rect(p);
        if (r.right > pr.right + 1 || r.left < pr.left - 1 || r.bottom > pr.bottom + 1 || r.top < pr.top - 1) return true; } }
    return false; };
  const parse = c => { const m = (c || '').match(/^rgba?\\(([^)]+)\\)$/); if (!m) return null;
    const p = m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number); return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1}; };
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  // what the text really sits on: translucent layers are blended over whatever is behind them, up to the first solid one
  const bgOf = e => { const layers = [];
    for (let p = e; p && p.nodeType === 1; p = p.parentElement) { const s = getComputedStyle(p);
      if (s.backgroundImage !== 'none') return null;
      const c = parse(s.backgroundColor); if (c && c.a > 0) { layers.push(c); if (c.a > 0.95) break; } }
    let base = {r: 255, g: 255, b: 255};
    for (const c of layers.reverse()) { const a = c.a > 0.95 ? 1 : c.a;
      base = {r: c.r * a + base.r * (1 - a), g: c.g * a + base.g * (1 - a), b: c.b * a + base.b * (1 - a)}; }
    return base; };
  const els = [...document.querySelectorAll('body *')].filter(vis);
  const textEls = els.filter(own);

  for (const e of textEls) { const s = getComputedStyle(e);
    const clipX = (s.overflowX === 'hidden' || s.overflowX === 'clip') && s.textOverflow !== 'ellipsis' && e.scrollWidth > e.clientWidth + 2;
    const clipY = (s.overflowY === 'hidden' || s.overflowY === 'clip') && e.scrollHeight > e.clientHeight + 2;
    if (clipX || clipY) out.clipped.push(label(e));
    const fs = parseFloat(s.fontSize); if (fs < cfg.minFont) out.small.push(label(e) + ' ' + fs + 'px');
    const fg = parse(s.color), bg = bgOf(e);
    if (fg && bg) { const a = fg.a, f = {r: fg.r * a + bg.r * (1 - a), g: fg.g * a + bg.g * (1 - a), b: fg.b * a + bg.b * (1 - a)};
      const l1 = lum(f), l2 = lum(bg), ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
      if (ratio < cfg.minContrast) out.contrast.push(label(e) + ' ratio ' + ratio.toFixed(1)); } }

  for (const e of els) if (e.tagName === 'IMG' && !(e.complete && e.naturalWidth > 0)) out.image.push(label(e));

  if (cfg.phone) for (const e of els) {
    if (!e.matches('a[href], button, select, textarea, [role=button], input:not([type=hidden]):not([type=checkbox]):not([type=radio])')) continue;
    if (e.tagName === 'A' && getComputedStyle(e).display === 'inline') continue;
    if (hiddenByBox(e)) continue;
    const r = rect(e);
    if (r.width < cfg.minTap || r.height < cfg.minTap) out.tap.push(label(e) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height) + 'px'); }

  // text that wraps over several lines is one box per line, not one big box that also covers its neighbours
  const boxes = e => getComputedStyle(e).display === 'inline' ? [...e.getClientRects()].filter(r => r.width > 0 && r.height > 0) : [rect(e)];
  const flow = textEls.filter(e => { const p = getComputedStyle(e).position; return (p === 'static' || p === 'relative') && !hiddenByBox(e); }).slice(0, 300);
  for (let i = 0; i < flow.length; i++) for (let j = i + 1; j < flow.length; j++) {
    const a = flow[i], b = flow[j]; if (a.contains(b) || b.contains(a)) continue;
    let hit = false;
    for (const ra of boxes(a)) { for (const rb of boxes(b)) {
      const ix = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left), iy = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
      if (ix > 2 && iy > 2) { const smaller = Math.min(ra.width * ra.height, rb.width * rb.height);
        if (ix * iy / smaller > cfg.overlap) { hit = true; break; } } } if (hit) break; }
    if (hit) out.overlap.push(label(a) + '  /  ' + label(b)); }

  for (const k of Object.keys(out)) out[k] = [...new Set(out[k])].slice(0, 12);
  return out;
}"""


GATED = set(filter(None, os.getenv("GATED_ROUTES", "/platform-intelligence").split(",")))  # login-only in production: a redirect to /login is expected
SKIP = set(filter(None, os.getenv("SKIP_ROUTES", "/login,/verify").split(",")))
ROUTE_SAMPLES = dict(kv.split("=", 1) for kv in os.getenv("ROUTE_SAMPLES", "").split(",") if "=" in kv)
OUT = Path(__file__).parent / "site_crawl_report.md"

ERROR_PHRASES = [
    "could not load", "couldn't load", "failed to load", "couldn't reach", "could not reach",
    "is the backend running", "http 5", "internal server error", "something went wrong",
    "undefined", "nan%", "[object object]", "isn't reachable",
]
DATE_RE = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)\b")

errors, warnings, info = [], [], []


def flag(level, where, msg):
    line = f"[{level}] {where}: {msg}"
    {"ERROR": errors, "WARN": warnings, "INFO": info}[level].append(line)
    print(line)


EXTERNAL_CHECK = os.getenv("EXTERNAL_CHECK", "1") != "0"   # set 0 when offline


def duplicate_menu_targets(seen, allow_dup, gated):
    """Menu entries that share a destination. Login-only entries all land on /login for a visitor, so when the site has
    gated routes that shared destination is expected, not a defect."""
    return [(path, labs) for path, labs in seen.items()
            if len(labs) > 1 and path not in allow_dup and not (path == "/login" and gated)]


def route_in(route, entries):
    """True if the route is listed in entries; an entry ending in * matches any route with that prefix."""
    return any(route == e or (e.endswith("*") and route.startswith(e[:-1])) for e in entries)


def format_culprits(items, limit=3):
    """Short description of the outermost elements that stick out past the phone screen.
    `items` are dicts from the page: {tag, id, cls, text, width, right}. Pure, so it can be tested."""
    out = []
    for it in sorted(items, key=lambda i: -i.get("right", 0))[:limit]:
        name = it.get("tag", "?") + (f"#{it['id']}" if it.get("id") else "") + (f".{it['cls']}" if it.get("cls") else "")
        label = f" “{it['text']}”" if it.get("text") else ""
        where = f" in {it['parent']}" if it.get("parent") else ""
        out.append(f"{name}{label} width {it.get('width', '?')}px, right edge {it.get('right', '?')}px{where}")
    return "; ".join(out)


def format_layout(issues, where, limit=3):
    """[(level, message)] for the layout problems found on one page. Pure, so it can be tested.
    A broken image is an error; the rest are warnings."""
    out = []
    for cat in ("image", "clipped", "overlap", "contrast", "small", "tap"):
        found = issues.get(cat) or []
        if not found:
            continue
        level = "ERROR" if cat == "image" else "WARN"
        out.append((level, f"{LAYOUT_LABELS[cat]} on {where} ({len(found)}): e.g. {'; '.join(found[:limit])}"))
    return out


def classify_link(href, base, routes, patterns=()):
    """What kind of link is this? Returns (kind, target):
       ("internal-ok", path) | ("internal-bad", path) | ("external", url) | ("skip", href).
       Pure and network-free so it can be tested."""
    from urllib.parse import urlparse, urljoin
    if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
        return "skip", href
    full = urljoin(base + "/", href)
    u, b = urlparse(full), urlparse(base)
    if u.scheme not in ("http", "https"):
        return "skip", href
    if u.netloc != b.netloc:
        return "external", full.split("#")[0]
    path = u.path or "/"
    known = path in routes or path in SKIP or any(p.fullmatch(path) for p in patterns)
    return ("internal-ok" if known else "internal-bad"), path


def _all_route_paths(src):
    return [r for r in re.findall(r'<Route\s+path="([^"]+)"', src) if r != "*"]


def routes_from_app(path, samples=None):
    """Pages to crawl. A page with a :param is crawled only when a sample value is given for it."""
    samples = ROUTE_SAMPLES if samples is None else samples
    out = []
    for r in _all_route_paths(path.read_text(encoding="utf-8")):
        if ":" in r:
            names = re.findall(r":(\w+)", r)
            if not all(n in samples for n in names):
                continue
            for n in names:
                r = r.replace(f":{n}", samples[n])
        if r not in SKIP:
            out.append(r)
    return out


def route_patterns(path):
    """Regexes for every route in App.jsx, a :param matching one path segment (so /stock/AAPL is a known page)."""
    return [re.compile(re.sub(r":\w+", "[^/]+", re.escape(r)))
            for r in _all_route_paths(path.read_text(encoding="utf-8"))]


def newest_date(text, today):
    best = None
    for y, m, d in DATE_RE.findall(text):
        try:
            dt = date(int(y), int(m), int(d))
        except ValueError:
            continue
        if dt <= today and (best is None or dt > best):
            best = dt
    return best


def paragraphs(text):
    out = []
    for p in re.split(r"\n{1,}", text):
        p = " ".join(p.split())
        if len(p) >= 90:  # long enough to be real copy, not a label
            out.append(p)
    return out


def main():
    from playwright.sync_api import sync_playwright

    routes = routes_from_app(APP_JSX)
    patterns = route_patterns(APP_JSX)
    today = date.today()
    page_text = {}
    page_links = {}
    print(f"Crawling {BASE} — {len(routes)} routes from {APP_JSX}\n")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        # ── 1. every route renders cleanly ───────────────────────────────────
        ctx = browser.new_context(viewport={"width": 1280, "height": 900}, ignore_https_errors=True)
        for r in routes:
            pg = ctx.new_page()
            cons, js, bad_api = [], [], []
            pg.on("console", lambda m, c=cons: c.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e, j=js: j.append(str(e)))
            pg.on("response", lambda resp, b=bad_api:
                  b.append(f"{resp.status} {resp.url.split(BASE)[-1][:80]}")
                  if resp.status >= 400 and "/api/" in resp.url else None)
            try:
                pg.goto(BASE + r, wait_until="networkidle", timeout=30000)
                pg.wait_for_timeout(1500)
                final = pg.evaluate("location.pathname")
                text = pg.evaluate("document.body.innerText")
                page_text[r] = text
                page_links[r] = pg.eval_on_selector_all("a[href]", "els => els.map(e => e.getAttribute('href'))")
                if final == r:
                    for lvl, msg in format_layout(pg.evaluate(LAYOUT_JS, dict(LAYOUT_CFG, phone=False)), "desktop"):
                        flag(lvl, r, msg)
                low = text.lower()
                if final != r and r in GATED and final == "/login":
                    flag("INFO", r, "requires login in production — redirect to /login is expected")
                    continue
                if final != r:
                    flag("ERROR", r, f"redirected to {final} (page does not exist or is gated)")
                if len(text.strip()) < (60 if r in SHORT_PAGES else 200):
                    flag("ERROR", r, f"page is nearly empty ({len(text.strip())} chars)")
                for ph in ERROR_PHRASES:
                    if ph in low:
                        flag("ERROR", r, f"error text on page: '{ph}'")
                if bad_api:
                    flag("ERROR", r, f"API calls failed: {sorted(set(bad_api))[:3]}")
                real = [e for e in cons if not any(s in e.lower() for s in ("favicon", "robots", "analytics"))
                        and "failed to load resource" not in e.lower()
                        and "status of 4" not in e.lower() and "status of 5" not in e.lower()]
                if real:
                    flag("WARN", r, f"console errors: {real[:2]}")
                if js:
                    flag("ERROR", r, f"JS exception: {js[0][:140]}")
                nd = newest_date(text, today)
                if nd and not route_in(r, STATIC_DATES) and (today - nd).days > ROUTE_STALE.get(r, STALE_DAYS):
                    flag("WARN", r, f"newest date on page is {nd} ({(today - nd).days} days old)")
                if not any(x.startswith(f"[ERROR] {r}:") or x.startswith(f"[WARN] {r}:")
                           for x in errors + warnings):
                    flag("INFO", r, "renders cleanly" + (f", newest date {nd}" if nd else ""))
            except Exception as e:
                flag("ERROR", r, f"did not load: {str(e)[:120]}")
            finally:
                pg.close()
        ctx.close()

        # ── 2. every menu entry goes somewhere real, and nowhere twice ───────
        mctx = browser.new_context(viewport={"width": 390, "height": 800}, ignore_https_errors=True)
        pg = mctx.new_page()
        # every page must fit a phone screen without sideways scrolling
        for r in routes:
            try:
                pg.goto(BASE + r, wait_until="networkidle", timeout=30000)
                pg.wait_for_timeout(600)
                if pg.evaluate("location.pathname") != r:
                    continue
                for lvl, msg in format_layout(pg.evaluate(LAYOUT_JS, dict(LAYOUT_CFG, phone=True)), "a phone"):
                    flag(lvl, r, msg)
                over = pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
                if over > 4:
                    culprits = pg.evaluate(OVERFLOW_JS)
                    flag("WARN", r, f"scrolls sideways on a phone (content is {over}px wider than the screen); widest: {format_culprits(culprits)}")
            except Exception as e:
                flag("WARN", r, f"phone-width check failed: {str(e)[:80]}")
        pg.goto(BASE + "/track-record" if "/track-record" in routes else BASE + "/", wait_until="networkidle")
        overlay = "div[style*='position: fixed'][style*='z-index: 999']"

        def open_menu():
            pg.get_by_role("button", name="☰").click()
            pg.wait_for_selector(overlay)

        if pg.get_by_role("button", name="☰").count() == 0:
            flag("INFO", "menu", "no mobile menu overlay on this site; links are checked from each page's anchors")
            labels = []
        else:
            open_menu()
            labels = [t.strip() for t in pg.locator(f"{overlay} button").all_inner_texts()]
        labels = [l for l in labels if l and l not in ("✕", "Logout", "Login")]
        landed = {}
        for label in labels:
            pg.goto(BASE + "/track-record" if "/track-record" in routes else BASE + "/", wait_until="networkidle")
            open_menu()
            pg.locator(f"{overlay} button", has_text=label).first.click()
            pg.wait_for_timeout(700)
            landed[label] = pg.evaluate("location.pathname + location.search + location.hash")
        seen = {}
        for label, path in landed.items():
            base_path = path.split("#")[0].split("?")[0]
            if path == "/" and any(p.lower() in label.lower() for p in PENDING_MENU):
                flag("INFO", f"menu '{label}'", "no page yet — known, planned")
            elif path == "/" and label.lower() not in ("home",):
                flag("ERROR", f"menu '{label}'", "dead link — bounces to the home page")
            elif base_path not in routes and base_path not in SKIP and not any(p.fullmatch(base_path) for p in patterns):
                flag("ERROR", f"menu '{label}'", f"goes to {path}, which is not a known page")
            seen.setdefault(path, []).append(label)
        for path, labs in duplicate_menu_targets(seen, ALLOW_DUP, GATED):
            flag("WARN", f"menu → {path}", f"{len(labs)} entries go to the same page: {labs}")
        if labels:
            flag("INFO", "menu", f"{len(labels)} entries checked")
        mctx.close()

        # ── 3. every link on every page leads somewhere real ─────────────────
        bad_internal, externals = {}, {}
        for r, hrefs in page_links.items():
            for h in hrefs:
                kind, target = classify_link(h, BASE, routes, patterns)
                if kind == "internal-bad":
                    bad_internal.setdefault(target, set()).add(r)
                elif kind == "external":
                    externals.setdefault(target, set()).add(r)
        for target, where in sorted(bad_internal.items()):
            flag("ERROR", f"link {target}", f"not a page; linked from {sorted(where)}")
        if EXTERNAL_CHECK:
            rctx = browser.new_context(ignore_https_errors=False, user_agent=EXTERNAL_UA)
            for url, where in sorted(externals.items()):
                time.sleep(EXTERNAL_DELAY)
                try:
                    resp = rctx.request.get(url, timeout=20000)
                    if resp.status >= 400:
                        flag("ERROR", f"link {url}", f"returns HTTP {resp.status}; linked from {sorted(where)}")
                except Exception as e:
                    flag("ERROR", f"link {url}", f"cannot be reached ({str(e)[:90]}); linked from {sorted(where)}")
            rctx.close()
        flag("INFO", "links", f"{sum(len(v) for v in page_links.values())} anchors on {len(page_links)} pages; "
                              f"{len(externals)} external link(s){'' if EXTERNAL_CHECK else ' (not fetched)'}")
        browser.close()

    # ── 3. text repeated across pages ────────────────────────────────────────
    owners = {}
    for r, t in page_text.items():
        for p in set(paragraphs(t)):
            owners.setdefault(p, []).append(r)
    for p, rs in owners.items():
        if len(rs) > 1 and not all(route_in(x, DUP_OK) for x in rs):
            flag("WARN", "duplicate text", f"on {rs}: “{p[:90]}…”")

    # ── report ───────────────────────────────────────────────────────────────
    lines = [f"# Site crawl report", f"Generated: {datetime.now():%Y-%m-%d %H:%M}  Target: {BASE}",
             f"\n- Errors: {len(errors)}\n- Warnings: {len(warnings)}\n- Info: {len(info)}\n",
             "## Errors", *(errors or ["none"]), "\n## Warnings", *(warnings or ["none"]),
             "\n## Info", *info]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{len(errors)} errors, {len(warnings)} warnings → {OUT}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
