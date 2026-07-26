"""
Converts quant_scores into flag_events (source_type='quantitative'). See
decisions.md D-009/D-011, journal.md 2026-07-26 for how each score was
built and verified.

Thresholds:
- Beneish M-Score > -1.78 (published manipulation-probability cutoff).
  Scores with unstable_component=true (see journal.md, EQT 2024 AQI
  case) are explicitly SKIPPED -- a numerically unstable ratio-of-ratios
  should not masquerade as a fraud signal.
- Altman Z-Score < 1.81 (published distress-zone cutoff). Known
  limitation (decisions.md D-013): understated for companies with stock-
  split history, so a borderline score here could be a false negative,
  not a false positive -- treat non-flags with caution for split-history
  companies, not flags.
- Sloan ratio > +0.10 -- no single published hard cutoff exists in the
  literature (academic practice ranks by decile within a sample rather
  than a fixed threshold); this is a judgment-call starting point, not
  a citation, and may need revisiting once enough data exists to look
  at decile behavior within this universe specifically.
"""
from datetime import date

from app.db.session import SessionLocal
from app.models.quant_score import QuantScore
from app.models.filing import FlagEvent

BENEISH_THRESHOLD = -1.78
ALTMAN_THRESHOLD = 1.81
SLOAN_THRESHOLD = 0.10


def _fiscal_year_end_date(fiscal_year, cik, db):
    """Approximate fiscal year-end as a real date for flag_events.filing_date
    (NOT NULL). Pulls the actual end_date from financial_facts.Assets for
    this cik/fiscal_year if available (correct even for non-calendar fiscal
    years, e.g. AAPL's September year-end) -- falls back to Dec 31 only if
    no matching fact exists."""
    from app.models.financial_fact import FinancialFact
    row = (
        db.query(FinancialFact.end_date)
        .filter(
            FinancialFact.cik == cik,
            FinancialFact.concept == "Assets",
            FinancialFact.fiscal_period == "FY",
        )
        .all()
    )
    for (end_date,) in row:
        if end_date and end_date.year == fiscal_year:
            return end_date
    return date(fiscal_year, 12, 31)


def generate_quant_flags():
    db = SessionLocal()

    existing_quant_score_ids = {
        row[0] for row in db.query(FlagEvent.quant_score_id).filter(FlagEvent.quant_score_id.isnot(None)).all()
    }

    beneish_flagged = 0
    beneish_skipped_unstable = 0
    altman_flagged = 0
    sloan_flagged = 0

    scores = db.query(QuantScore).all()
    for score in scores:
        if score.id in existing_quant_score_ids:
            continue  # already flagged (or evaluated and not flagged -- see note below)

        flag_type = None
        flag_tier = 1

        if score.score_type == "beneish_m_score":
            if score.components and score.components.get("unstable_component"):
                beneish_skipped_unstable += 1
                continue
            if score.value > BENEISH_THRESHOLD:
                flag_type = "beneish_manipulation_risk"
                beneish_flagged += 1

        elif score.score_type == "altman_z_score":
            if score.value < ALTMAN_THRESHOLD:
                flag_type = "altman_distress"
                altman_flagged += 1

        elif score.score_type == "sloan_ratio":
            if score.value > SLOAN_THRESHOLD:
                flag_type = "sloan_ratio_high"
                sloan_flagged += 1

        if flag_type is None:
            continue  # score computed, but didn't cross the threshold -- no flag_event row

        filing_date = _fiscal_year_end_date(score.fiscal_year, score.cik, db)

        db.add(FlagEvent(
            filing_id=None,
            quant_score_id=score.id,
            source_type="quantitative",
            cik=score.cik,
            ticker=score.ticker,
            flag_type=flag_type,
            flag_tier=flag_tier,
            filing_date=filing_date,
            details={
                "score_type": score.score_type,
                "value": score.value,
                "components": score.components,
                "threshold_used": (
                    BENEISH_THRESHOLD if score.score_type == "beneish_m_score"
                    else ALTMAN_THRESHOLD if score.score_type == "altman_z_score"
                    else SLOAN_THRESHOLD
                ),
            },
        ))

    db.commit()
    db.close()

    print(f"Beneish flags created: {beneish_flagged}")
    print(f"Beneish skipped (unstable_component): {beneish_skipped_unstable}")
    print(f"Altman flags created: {altman_flagged}")
    print(f"Sloan flags created: {sloan_flagged}")


if __name__ == "__main__":
    generate_quant_flags()
