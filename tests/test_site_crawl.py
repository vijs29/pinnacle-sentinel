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


# ── a sideways-scroll warning must name what is too wide, not just by how much ──
def test_culprits_are_named_widest_first_and_limited():
    items = [
        {"tag": "div", "id": "", "cls": "box", "text": "small", "width": 420, "right": 420},
        {"tag": "table", "id": "ledger", "cls": "data", "text": "Date Ticker", "width": 700, "right": 700},
        {"tag": "pre", "id": "", "cls": "", "text": "", "width": 500, "right": 500},
        {"tag": "p", "id": "", "cls": "", "text": "x", "width": 410, "right": 410},
    ]
    out = sc.format_culprits(items)
    assert out.startswith("table#ledger.data “Date Ticker” width 700px")
    assert out.index("700px") < out.index("500px") < out.index("420px")
    assert "410px" not in out                      # only the three widest
    assert "pre width 500px" in out                # no id/class/text: just the tag


def test_culprits_of_nothing_is_empty():
    assert sc.format_culprits([]) == ""


def test_overflow_warning_uses_the_culprit_report():
    src = _crawler_source()
    assert "culprits = pg.evaluate(OVERFLOW_JS)" in src
    assert "widest: {format_culprits(culprits)}" in src


def test_overflow_script_lists_only_outermost_elements():
    assert "sticks(el.parentElement)" in sc.OVERFLOW_JS
    assert "rect(e).right > w + 4" in sc.OVERFLOW_JS


def test_culprit_report_includes_right_edge_and_the_container():
    out = sc.format_culprits([{"tag": "span", "id": "", "cls": "more", "text": "x", "width": 248, "right": 600, "parent": "div.row"}])
    assert "right edge 600px" in out
    assert out.endswith("in div.row")


def test_culprit_without_a_parent_has_no_in_clause():
    out = sc.format_culprits([{"tag": "pre", "width": 5, "right": 9}])
    assert " in " not in out


def test_elements_inside_a_scrolling_box_are_not_blamed():
    js = sc.OVERFLOW_JS
    assert "getComputedStyle(p).overflowX !== 'visible' && !sticks(p)" in js
    assert "if (!sticks(el) || clipped(el)) continue;" in js


def test_overflow_script_reports_the_parent_container():
    assert "parent: el.parentElement ? name(el.parentElement) : ''" in sc.OVERFLOW_JS


# ── layout quality: the checks that replace a person looking at the page ──────────────────────
import pytest

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "layout.html"


def test_layout_thresholds_are_pinned():
    assert sc.LAYOUT_CFG == {"minTap": 32, "minFont": 11, "minContrast": 2.5, "overlap": 0.3}


def test_layout_has_a_label_for_every_category():
    assert set(sc.LAYOUT_LABELS) == {"clipped", "overlap", "tap", "small", "image", "contrast"}


def test_broken_image_is_an_error_and_the_rest_are_warnings():
    issues = {k: ["x"] for k in sc.LAYOUT_LABELS}
    levels = {msg.split(" on ")[0]: lvl for lvl, msg in sc.format_layout(issues, "a phone")}
    assert levels[sc.LAYOUT_LABELS["image"]] == "ERROR"
    assert all(lvl == "WARN" for label, lvl in levels.items() if label != sc.LAYOUT_LABELS["image"])


def test_layout_message_names_where_counts_and_limits_examples():
    msgs = sc.format_layout({"small": ["a 9px", "b 8px", "c 7px", "d 6px"]}, "a phone", limit=3)
    assert len(msgs) == 1
    text = msgs[0][1]
    assert "on a phone (4)" in text and "a 9px; b 8px; c 7px" in text and "d 6px" not in text


def test_layout_with_no_issues_reports_nothing():
    assert sc.format_layout({k: [] for k in sc.LAYOUT_LABELS}, "desktop") == []
    assert sc.format_layout({}, "desktop") == []


def test_layout_checks_run_in_both_the_desktop_and_phone_pass():
    src = _crawler_source()
    assert 'dict(LAYOUT_CFG, phone=False)), "desktop")' in src
    assert 'dict(LAYOUT_CFG, phone=True)), "a phone")' in src


@pytest.fixture(scope="module")
def _browser():
    pw = pytest.importorskip("playwright.sync_api")
    ctx = pw.sync_playwright().start()
    try:
        b = ctx.chromium.launch()
    except Exception as e:  # browser not installed on this machine
        ctx.stop()
        pytest.skip(f"no browser available: {e}")
    yield b
    b.close()
    ctx.stop()


def _layout(browser, phone):
    vp = {"width": 390, "height": 800} if phone else {"width": 1280, "height": 900}
    pg = browser.new_context(viewport=vp).new_page()
    pg.goto(FIXTURE.as_uri())
    pg.wait_for_timeout(200)
    return pg.evaluate(sc.LAYOUT_JS, dict(sc.LAYOUT_CFG, phone=phone))


def test_browser_finds_each_planted_defect_once_on_a_phone(_browser):
    got = _layout(_browser, phone=True)
    assert len(got["clipped"]) == 1 and "div.cut" in got["clipped"][0]
    assert len(got["overlap"]) == 1 and "div.top" in got["overlap"][0] and "div.over" in got["overlap"][0]
    assert len(got["tap"]) == 1 and "button.tiny" in got["tap"][0]
    assert len(got["small"]) == 1 and "p.small" in got["small"][0]
    assert len(got["image"]) == 1 and "img.broken" in got["image"][0]
    assert len(got["contrast"]) == 1 and "div.ghost" in got["contrast"][0]


def test_browser_does_not_flag_the_clean_section(_browser):
    for phone in (True, False):
        flagged = " ".join(sum(_layout(_browser, phone).values(), []))
        for innocent in ("Big button", "Link", "scrolls inside", "second cell", "badge", "normal paragraph", "ellipsis by design", "inline link", "bold words", "white on gradient", "wide cell", "neighbour of scroller", "hidden", "dark on translucent green", "closed body tiny", "zero box tiny", "alpha beta", "zeta", "white on faint layer"):
            assert innocent not in flagged, f"{innocent!r} wrongly flagged (phone={phone})"


def test_browser_tap_size_is_checked_on_phones_only(_browser):
    assert _layout(_browser, phone=True)["tap"] != []
    assert _layout(_browser, phone=False)["tap"] == []


def test_layout_default_limit_shows_three_examples():
    text = sc.format_layout({"small": ["a", "b", "c", "d"]}, "desktop")[0][1]
    assert "(4)" in text and "a; b; c" in text and "d" not in text.split("e.g.")[1]


def test_browser_sees_text_that_is_nearly_transparent(_browser):
    pg = _browser.new_context(viewport={"width": 390, "height": 800}).new_page()
    pg.set_content('<body style="background:#fff"><p class="faint" style="color:rgba(0,0,0,0.12)">faint words</p></body>')
    got = pg.evaluate(sc.LAYOUT_JS, dict(sc.LAYOUT_CFG, phone=True))
    assert len(got["contrast"]) == 1 and "p.faint" in got["contrast"][0]


def _on_phone(browser, html):
    pg = browser.new_context(viewport={"width": 390, "height": 800}).new_page()
    pg.set_content(html)
    return pg.evaluate(sc.LAYOUT_JS, dict(sc.LAYOUT_CFG, phone=True))


def test_browser_closed_details_hide_their_body_but_open_ones_do_not(_browser):
    closed = _on_phone(_browser, '<details><summary>More</summary><p style="font-size:8px">shut tiny</p></details>')
    opened = _on_phone(_browser, '<details open><summary>More</summary><p style="font-size:8px">open tiny</p></details>')
    assert closed["small"] == []
    assert len(opened["small"]) == 1 and "open tiny" in opened["small"][0]


def test_browser_summary_of_a_closed_details_is_still_checked(_browser):
    got = _on_phone(_browser, '<details><summary style="font-size:8px">tiny summary</summary><p>body</p></details>')
    assert len(got["small"]) == 1 and "tiny summary" in got["small"][0]


def test_browser_overlap_on_a_later_line_of_wrapped_text_is_found(_browser):
    got = _on_phone(_browser, '<body style="margin:0"><p style="width:100px;margin:0"><span>aaaa bbbb cccc dddd eeee ffff</span></p>'
                              '<div style="margin-top:-18px;width:60px;height:18px">covering block</div></body>')
    assert len(got["overlap"]) == 1 and "covering block" in got["overlap"][0]


# ── login-only menu entries all land on /login for a visitor: expected, not a duplicate ──
def test_gated_menu_entries_sharing_the_login_page_are_not_flagged():
    seen = {"/login": ["My Signals", "My Trades"]}
    assert sc.duplicate_menu_targets(seen, set(), {"/my-signals", "/my-trades"}) == []


def test_login_duplicates_are_flagged_when_the_site_has_no_gated_routes():
    seen = {"/login": ["A", "B"]}
    assert sc.duplicate_menu_targets(seen, set(), set()) == [("/login", ["A", "B"])]


def test_other_duplicate_menu_targets_are_still_flagged_and_allowed_ones_are_not():
    seen = {"/scan": ["Scan", "Scanner"], "/universe": ["A", "B"], "/x": ["Only"]}
    assert sc.duplicate_menu_targets(seen, {"/universe"}, {"/g"}) == [("/scan", ["Scan", "Scanner"])]


def test_menu_check_uses_the_duplicate_helper():
    assert "duplicate_menu_targets(seen, ALLOW_DUP, GATED)" in _crawler_source()
