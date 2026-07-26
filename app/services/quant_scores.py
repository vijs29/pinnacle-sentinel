"""
Quantitative red-flag scoring service (v1). See decisions.md D-009/D-011.

Computes financial-ratio/composite scores from financial_facts and writes
them into quant_scores, WITH the underlying component variables stored
alongside the final score -- not just the number -- so scores are
auditable the same way the cfo_resignation text classifier was audited
(journal.md, 2026-07-25).

Started with the Sloan accruals ratio (simplest, single-period, good
pipeline smoke test). Beneish M-Score and Altman Z-Score follow once this
is verified against real filings.
"""
from collections import defaultdict

from app.db.session import SessionLocal
from app.models.financial_fact import FinancialFact
from app.models.quant_score import QuantScore


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
            continue  # already computed, don't recompute/duplicate

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


if __name__ == "__main__":
    compute_sloan_ratios()
