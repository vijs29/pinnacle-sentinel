import importlib.util
import re
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("site_crawl", Path(__file__).resolve().parents[1] / "tools" / "audit" / "site_crawl.py")
sc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sc)

APP = '''<Route path="/" element={<A/>} />
<Route path="/stock/:symbol" element={<B/>} />
<Route path="/options/:symbol" element={<C/>} />
<Route path="/hit-miss-analysis" element={<D/>} />
<Route path="/login" element={<E/>} />
<Route path="*" element={<Navigate to="/" />} />'''


def app(tmp_path):
    p = tmp_path / "App.jsx"; p.write_text(APP); return p


def test_param_pages_are_skipped_without_a_sample(tmp_path):
    assert sc.routes_from_app(app(tmp_path), samples={}) == ["/", "/hit-miss-analysis"]


def test_param_pages_are_crawled_with_a_sample(tmp_path):
    r = sc.routes_from_app(app(tmp_path), samples={"symbol": "AAPL"})
    assert "/stock/AAPL" in r and "/options/AAPL" in r and "/stock/:symbol" not in r


def test_skip_and_wildcard_routes_are_never_crawled(tmp_path):
    r = sc.routes_from_app(app(tmp_path), samples={"symbol": "AAPL"})
    assert "/login" not in r and "*" not in r


def test_a_link_to_a_param_page_is_known(tmp_path):
    pats = sc.route_patterns(app(tmp_path))
    kind, _ = sc.classify_link("/stock/MSFT", "https://x.com", ["/"], pats)
    assert kind == "internal-ok"


def test_a_link_to_a_missing_page_is_still_bad(tmp_path):
    pats = sc.route_patterns(app(tmp_path))
    assert sc.classify_link("/stocks/MSFT", "https://x.com", ["/"], pats)[0] == "internal-bad"
    assert sc.classify_link("/stock/MSFT/extra", "https://x.com", ["/"], pats)[0] == "internal-bad"


def test_classifier_basics_still_hold():
    assert sc.classify_link("mailto:a@b.c", "https://x.com", ["/"])[0] == "skip"
    assert sc.classify_link("https://other.com/p", "https://x.com", ["/"])[0] == "external"
    assert sc.classify_link("/nope", "https://x.com", ["/"])[0] == "internal-bad"
    assert sc.classify_link("/", "https://x.com", ["/"])[0] == "internal-ok"


def test_route_in_matches_exact_and_prefix_entries():
    assert sc.route_in("/a", ["/a"])
    assert sc.route_in("/flags/late-filing", ["/flags/*"])
    assert not sc.route_in("/flagship", ["/flags/*"])
    assert not sc.route_in("/other", ["/a", "/flags/*"])
    assert not sc.route_in("/a/b", ["/a"])       # an entry without * is exact


def test_wildcard_needs_the_star_to_match_a_prefix():
    assert not sc.route_in("/flags/x", ["/flags/"])


def test_date_and_duplicate_checks_use_the_prefix_aware_helper():
    # the checks run inside the browser loop, which unit tests cannot drive, so pin the wiring in the source
    src = (Path(__file__).resolve().parents[1] / "tools" / "audit" / "site_crawl.py").read_text()
    assert "not route_in(r, STATIC_DATES)" in src
    assert "all(route_in(x, DUP_OK) for x in rs)" in src


# ── external link checks must identify themselves (SEC returns 403 to anonymous bots) ──
def _crawler_source():
    return (Path(__file__).resolve().parents[1] / "tools" / "audit" / "site_crawl.py").read_text()


def test_external_requests_send_descriptive_user_agent_with_contact():
    assert "vijay.cloudarchitect@gmail.com" in sc.EXTERNAL_UA
    assert "rctx = browser.new_context(ignore_https_errors=False, user_agent=EXTERNAL_UA)" in _crawler_source()


def test_external_requests_are_rate_limited_under_sec_fair_access():
    assert 0.1 <= sc.EXTERNAL_DELAY <= 1.0
    assert "time.sleep(EXTERNAL_DELAY)" in _crawler_source()


def test_gated_login_redirect_is_accepted_on_localhost_too():
    assert '"localhost" not in BASE' not in _crawler_source()
