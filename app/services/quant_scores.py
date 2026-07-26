"""
Quantitative red-flag scoring service (v1). See decisions.md D-009/D-011.

Computes financial-ratio/composite scores from financial_facts and writes
them into quant_scores, WITH the underlying component variables stored
alongside the final score -- not just the number -- so scores are
auditable the same way the cfo_resignation text classifier was audited
(journal.md, 2026-07-25).

Sloan accruals ratio (simplest, single-period, pipeline smoke test),
then Beneish M-Score (8 variables, year-over-year), then Altman Z-Score
(needs market cap via Pinnacle Quant's market_data.py, D-010).
"""
from collections import defaultdict
from datetime import timedelta

import pandas as pd

from app.db.session import SessionLocal
from app.models.financial_fact import FinancialFact
from app.models.quant_score import QuantScore
from app.services.market_data import get_daily_history


def _facts_by_company_period(db, concept, is_duration):
    """Pull one concept across all companies, keyed by (cik, end_date) --
    NOT by SEC's fy/fp fields, which describe the FILING's fiscal year,
    not the individual fact's actual period (a 10-K reports comparatives
    from prior years, often tagged with the filing's own fy label). This
    caused real corruption: VRT's fiscal_year=2018 bucket contained a
    pre-merger shell-company Assets figure from a genuinely different
    period than its NetIncomeLoss figure -- joining by SEC's fy field
    silently paired mismatched periods. Found via Sloan-ratio spot-check
    2026-07-26 (VRT -11.1, implausible for any real company).

    For duration concepts (income/cash-flow items), only accept facts
    spanning 350-380 days -- excludes quarterly figures SEC sometimes
    mislabels fiscal_period='FY' (seen in CDNS data, same investigation).
    Instant concepts (balance sheet) have no duration to check.

    Prefers form_type='10-K' over '10-Q' when both report the same
    end_date, since 10-Qs occasionally carry stale comparative data."""
    rows = (
        db.query(
            FinancialFact.cik, FinancialFact.ticker, FinancialFact.start_date,
            FinancialFact.end_date, FinancialFact.form_type, FinancialFact.value,
        )
        .filter(FinancialFact.concept == concept, FinancialFact.fiscal_period == "FY")
        .all()
    )
    out = {}
    for cik, ticker, start_date, end_date, form_type, value in rows:
        if end_date is None:
            continue
        if is_duration:
            if start_date is None:
                continue
            span_days = (end_date - start_date).days
            if not (350 <= span_days <= 380):
                continue  # excludes quarterly data mislabeled FY

        key = (cik, end_date)
        if key not in out:
            out[key] = (ticker, value, form_type)
        elif form_type == "10-K" and out[key][2] != "10-K":
            out[key] = (ticker, value, form_type)  # prefer 10-K over 10-Q
    return {k: (v[0], v[1]) for k, v in out.items()}


def _merged_revenue_facts(db):
    """Companies switched from the 'Revenues' tag to
    'RevenueFromContractWithCustomerExcludingAssessedTax' around fiscal
    2018-2019 (ASC 606 adoption) -- confirmed via AAPL spot-check
    2026-07-26: both tags report IDENTICAL values through FY2018 (e.g.
    $265,595,000,000 on 2018-09-29), then 'Revenues' simply stops
    appearing. Querying only 'Revenues' silently truncated score history
    at the transition for every company that switched (358 of 503 per
    the concept-coverage check). Merge both tags into one lookup,
    preferring 'Revenues' where both exist (matches what's already
    computed) and falling back to the newer tag otherwise."""
    legacy = _facts_by_company_period(db, "Revenues", is_duration=True)
    newer = _facts_by_company_period(db, "RevenueFromContractWithCustomerExcludingAssessedTax", is_duration=True)
    merged = dict(newer)
    merged.update(legacy)  # legacy wins on overlapping keys
    return merged


def _prior_year_lookup(facts_dict, cik, end_date):
    """Given a {(cik, end_date): (ticker, value)} dict, find this company's
    fact from ~1 year before end_date (350-380 days prior, same tolerance
    used for duration-span filtering elsewhere in this file). Returns
    (ticker, value) or None if no matching prior-year fact exists."""
    target_start = end_date - timedelta(days=380)
    target_end = end_date - timedelta(days=350)
    for (fcik, fend), (ticker, value) in facts_dict.items():
        if fcik == cik and target_start <= fend <= target_end:
            return (ticker, value)
    return None


def _get_unadjusted_history(ticker):
    """Raw (NOT split/dividend-adjusted) daily close prices, for market-cap
    calculations specifically. market_data.py's get_daily_history() uses
    auto_adjust=True (correct for Quant's return-continuity needs), which
    retroactively scales ALL historical prices down to reflect splits that
    happen LATER -- wrong here, since CommonStockSharesOutstanding is the
    actual unadjusted share count reported at each point in time (SEC
    filings never retroactively restate for future splits). Pairing an
    adjusted price with an unadjusted share count understates market value
    of equity for every year before a split, by roughly the split ratio.
    Found via TPL spot-check 2026-07-26 (shares_outstanding nearly tripled
    2023->2024, matching TPL's real 3-for-1 split; back-of-envelope check
    against real historical TPL prices confirmed the understatement)."""
    import yfinance as yf
    try:
        df = yf.Ticker(ticker).history(period="max", auto_adjust=False)
        if df is None or df.empty:
            return None
        df = df[["Close"]].copy()
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        return df
    except Exception:
        return None


def _closest_close(price_history, target_date, max_gap_days=7):
    """Find the closing price on the trading day nearest target_date,
    within max_gap_days -- fiscal year-end often falls on a weekend/
    holiday, so exact-date matches would silently fail most of the time."""
    if price_history is None or price_history.empty:
        return None
    idx = price_history.index
    diffs = abs((idx - pd.Timestamp(target_date)).days)
    closest_pos = diffs.argmin()
    if diffs[closest_pos] > max_gap_days:
        return None
    return float(price_history.iloc[closest_pos]["Close"])


# ---------------------------------------------------------------------------
# Sloan accruals ratio
# ---------------------------------------------------------------------------

def compute_sloan_ratios():
    """Sloan ratio = (NetIncomeLoss - OperatingCashFlow) / Assets, per
    company per fiscal year. Positive and large = earnings running well
    ahead of cash -- the accrual-heavy pattern Sloan (1996) linked to
    weaker future returns."""
    db = SessionLocal()

    net_income = _facts_by_company_period(db, "NetIncomeLoss", is_duration=True)
    ocf = _facts_by_company_period(db, "NetCashProvidedByUsedInOperatingActivities", is_duration=True)
    assets = _facts_by_company_period(db, "Assets", is_duration=False)

    common_keys = set(net_income) & set(ocf) & set(assets)

    computed = 0
    skipped_zero_assets = 0

    for key in common_keys:
        cik, end_date = key
        fiscal_year = end_date.year
        ticker, ni = net_income[key]
        _, cfo = ocf[key]
        _, total_assets = assets[key]

        if not total_assets:
            skipped_zero_assets += 1
            continue

        sloan_ratio = (ni - cfo) / total_assets

        existing = (
            db.query(QuantScore)
            .filter(
                QuantScore.cik == cik,
                QuantScore.fiscal_year == fiscal_year,
                QuantScore.score_type == "sloan_ratio",
            )
            .first()
        )
        if existing:
            continue

        db.add(QuantScore(
            cik=cik,
            ticker=ticker,
            fiscal_year=fiscal_year,
            score_type="sloan_ratio",
            value=sloan_ratio,
            components={
                "net_income": ni,
                "operating_cash_flow": cfo,
                "total_assets": total_assets,
            },
        ))
        computed += 1

    db.commit()
    db.close()

    print(f"Sloan ratios computed: {computed}")
    print(f"Skipped (zero/missing total assets): {skipped_zero_assets}")
    print(f"Companies with all 3 required facts for at least one year: {len(set(k[0] for k in common_keys))}")


# ---------------------------------------------------------------------------
# Beneish M-Score
# ---------------------------------------------------------------------------

def compute_beneish_m_scores():
    """Beneish M-Score (8 variables, all year-over-year). See journal.md
    2026-07-26 -- reuses the end_date-join fix from the Sloan ratio build;
    do NOT join on SEC's fy/fp fields, they describe the filing's fiscal
    year, not each fact's actual period."""
    db = SessionLocal()

    revenues = _merged_revenue_facts(db)
    receivables = _facts_by_company_period(db, "AccountsReceivableNetCurrent", is_duration=False)
    cogs = _facts_by_company_period(db, "CostOfGoodsAndServicesSold", is_duration=True)
    current_assets = _facts_by_company_period(db, "AssetsCurrent", is_duration=False)
    ppe = _facts_by_company_period(db, "PropertyPlantAndEquipmentNet", is_duration=False)
    total_assets = _facts_by_company_period(db, "Assets", is_duration=False)
    depreciation = _facts_by_company_period(db, "DepreciationDepletionAndAmortization", is_duration=True)
    sga = _facts_by_company_period(db, "SellingGeneralAndAdministrativeExpense", is_duration=True)
    liabilities = _facts_by_company_period(db, "Liabilities", is_duration=False)
    net_income = _facts_by_company_period(db, "NetIncomeLoss", is_duration=True)
    ocf = _facts_by_company_period(db, "NetCashProvidedByUsedInOperatingActivities", is_duration=True)

    computed = 0
    skipped_missing_data = 0
    skipped_div_zero = 0

    for key in list(revenues.keys()):
        cik, end_date = key
        ticker, sales_t = revenues[key]

        prior_sales = _prior_year_lookup(revenues, cik, end_date)
        if prior_sales is None:
            skipped_missing_data += 1
            continue
        _, sales_t1 = prior_sales

        try:
            rec_t = receivables[key][1]
            rec_t1 = _prior_year_lookup(receivables, cik, end_date)[1]
            cogs_t = cogs[key][1]
            cogs_t1 = _prior_year_lookup(cogs, cik, end_date)[1]
            ca_t = current_assets[key][1]
            ca_t1 = _prior_year_lookup(current_assets, cik, end_date)[1]
            ppe_t = ppe[key][1]
            ppe_t1 = _prior_year_lookup(ppe, cik, end_date)[1]
            assets_t = total_assets[key][1]
            assets_t1 = _prior_year_lookup(total_assets, cik, end_date)[1]
            dep_t = depreciation[key][1]
            dep_t1 = _prior_year_lookup(depreciation, cik, end_date)[1]
            sga_t = sga[key][1]
            sga_t1 = _prior_year_lookup(sga, cik, end_date)[1]
            liab_t = liabilities[key][1]
            liab_t1 = _prior_year_lookup(liabilities, cik, end_date)[1]
            ni_t = net_income[key][1]
            ocf_t = ocf[key][1]
        except (KeyError, TypeError):
            skipped_missing_data += 1
            continue

        try:
            dsri = (rec_t / sales_t) / (rec_t1 / sales_t1)
            gm_t = (sales_t - cogs_t) / sales_t
            gm_t1 = (sales_t1 - cogs_t1) / sales_t1
            gmi = gm_t1 / gm_t
            aqi_t = 1 - (ca_t + ppe_t) / assets_t
            aqi_t1 = 1 - (ca_t1 + ppe_t1) / assets_t1
            aqi = aqi_t / aqi_t1
            sgi = sales_t / sales_t1
            deprate_t = dep_t / (dep_t + ppe_t)
            deprate_t1 = dep_t1 / (dep_t1 + ppe_t1)
            depi = deprate_t1 / deprate_t
            sgai = (sga_t / sales_t) / (sga_t1 / sales_t1)
            lvgi = (liab_t / assets_t) / (liab_t1 / assets_t1)
            tata = (ni_t - ocf_t) / assets_t
        except ZeroDivisionError:
            skipped_div_zero += 1
            continue

        m_score = (
            -4.84 + 0.92 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi
            + 0.115 * depi - 0.172 * sgai + 4.679 * tata - 0.327 * lvgi
        )

        # AQI is a ratio-of-ratios that can blow up when a company's
        # "other assets" (non-current, non-PPE) is near zero in either
        # year -- common in asset-heavy industries like oil & gas E&P.
        # Found via EQT 2024 spot-check (2026-07-26): AQI=12.56 from a
        # real but numerically unstable balance-sheet composition, not
        # manipulation -- inflated M-Score to +2.33 on its own. Flag
        # rather than silently trust when any component variable is
        # implausibly large.
        unstable_component = any(
            abs(v) > 10 for v in [dsri, gmi, aqi, sgi, depi, sgai, lvgi]
        )

        fiscal_year = end_date.year
        existing = (
            db.query(QuantScore)
            .filter(QuantScore.cik == cik, QuantScore.fiscal_year == fiscal_year, QuantScore.score_type == "beneish_m_score")
            .first()
        )
        if existing:
            continue

        db.add(QuantScore(
            cik=cik, ticker=ticker, fiscal_year=fiscal_year, score_type="beneish_m_score",
            value=m_score,
            components={
                "DSRI": dsri, "GMI": gmi, "AQI": aqi, "SGI": sgi, "DEPI": depi,
                "SGAI": sgai, "LVGI": lvgi, "TATA": tata,
                "unstable_component": unstable_component,
            },
        ))
        computed += 1

    db.commit()
    db.close()

    print(f"Beneish M-Scores computed: {computed}")
    print(f"Skipped (missing current/prior-year data for some concept): {skipped_missing_data}")
    print(f"Skipped (division by zero in a ratio): {skipped_div_zero}")


# ---------------------------------------------------------------------------
# Altman Z-Score
# ---------------------------------------------------------------------------

def compute_altman_z_scores():
    """Altman Z-Score = 1.2*(WC/TA) + 1.4*(RE/TA) + 3.3*(EBIT/TA)
    + 0.6*(MVE/TL) + 1.0*(Sales/TA). Reuses Pinnacle Quant's market_data.py
    (D-010 -- reuse, don't rebuild a second price feed) for MVE.
    Same end_date-join discipline as Sloan/Beneish."""
    db = SessionLocal()

    current_assets = _facts_by_company_period(db, "AssetsCurrent", is_duration=False)
    current_liabilities = _facts_by_company_period(db, "LiabilitiesCurrent", is_duration=False)
    retained_earnings = _facts_by_company_period(db, "RetainedEarningsAccumulatedDeficit", is_duration=False)
    op_income = _facts_by_company_period(db, "OperatingIncomeLoss", is_duration=True)
    liabilities = _facts_by_company_period(db, "Liabilities", is_duration=False)
    revenues = _merged_revenue_facts(db)
    total_assets = _facts_by_company_period(db, "Assets", is_duration=False)
    shares_out = _facts_by_company_period(db, "CommonStockSharesOutstanding", is_duration=False)

    keys_by_cik = defaultdict(list)
    for (cik, end_date) in total_assets.keys():
        keys_by_cik[cik].append(end_date)

    computed = 0
    skipped_missing_data = 0
    skipped_no_price = 0

    price_cache = {}

    for cik, end_dates in keys_by_cik.items():
        ticker = total_assets[(cik, end_dates[0])][0]

        if ticker not in price_cache:
            price_cache[ticker] = _get_unadjusted_history(ticker)
        price_history = price_cache[ticker]

        for end_date in end_dates:
            key = (cik, end_date)
            try:
                ca = current_assets[key][1]
                cl = current_liabilities[key][1]
                re = retained_earnings[key][1]
                ebit = op_income[key][1]
                liab = liabilities[key][1]
                sales = revenues[key][1]
                assets = total_assets[key][1]
                shares = shares_out[key][1]
            except KeyError:
                skipped_missing_data += 1
                continue

            close_price = _closest_close(price_history, end_date)
            if close_price is None:
                skipped_no_price += 1
                continue

            mve = close_price * shares
            wc = ca - cl

            try:
                z_score = (
                    1.2 * (wc / assets) + 1.4 * (re / assets) + 3.3 * (ebit / assets)
                    + 0.6 * (mve / liab) + 1.0 * (sales / assets)
                )
            except ZeroDivisionError:
                skipped_missing_data += 1
                continue

            fiscal_year = end_date.year
            existing = (
                db.query(QuantScore)
                .filter(QuantScore.cik == cik, QuantScore.fiscal_year == fiscal_year, QuantScore.score_type == "altman_z_score")
                .first()
            )
            if existing:
                continue

            db.add(QuantScore(
                cik=cik, ticker=ticker, fiscal_year=fiscal_year, score_type="altman_z_score",
                value=z_score,
                components={
                    "working_capital": wc, "retained_earnings": re, "ebit": ebit,
                    "market_value_equity": mve, "total_liabilities": liab,
                    "sales": sales, "total_assets": assets,
                    "close_price_used": close_price, "shares_outstanding": shares,
                },
            ))
            computed += 1

    db.commit()
    db.close()

    print(f"Altman Z-Scores computed: {computed}")
    print(f"Skipped (missing financial data): {skipped_missing_data}")
    print(f"Skipped (no matching price within 7 days): {skipped_no_price}")


if __name__ == "__main__":
    compute_sloan_ratios()
    compute_beneish_m_scores()
    compute_altman_z_scores()
