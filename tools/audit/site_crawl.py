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


def route_in(route, entries):
    """True if the route is listed in entries; an entry ending in * matches any route with that prefix."""
    return any(route == e or (e.endswith("*") and route.startswith(e[:-1])) for e in entries)


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
                over = pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
                if over > 4:
                    flag("WARN", r, f"scrolls sideways on a phone (content is {over}px wider than the screen)")
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
        for path, labs in seen.items():
            if len(labs) > 1 and path not in ALLOW_DUP:
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
