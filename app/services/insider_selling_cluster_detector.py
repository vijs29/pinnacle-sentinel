"""
Accelerated insider selling cluster detection. See strategy.md and
decisions.md D-016 for the original design, D-019 for the real Form 4
data-quality investigation this detector's input table went through.

Flags when multiple DISTINCT insiders (by insider_cik) execute
open-market sales (transaction_code='S') on the same ticker within a
rolling 30-day window. A single insider selling is common and often
meaningless; multiple distinct insiders selling in a short window is a
much rarer, harder-to-explain-away pattern.

Runs entirely against the already-ingested insider_transactions table
(see form4_ingest.py) -- no network calls, no SEC fetching. Reuses the
same dedup pattern as other detectors: (filing_id, flag_type), keyed
on the SPECIFIC transaction/filing that crosses the 2-distinct-insider
threshold (the "trigger"), not every transaction in an already-flagged
cluster.
"""
from collections import defaultdict
from datetime import timedelta

from app.db.session import SessionLocal
from app.models.filing import Filing, FlagEvent
from app.models.insider_transaction import InsiderTransaction
from app.models.quant_score import QuantScore  # noqa: F401 -- registers
# quant_scores in shared metadata so FlagEvent.quant_score_id's FK
# resolves at flush time (same fix as other detectors)

FLAG_TYPE = "accelerated_insider_selling"
WINDOW_DAYS = 30
MIN_DISTINCT_INSIDERS = 2


def detect_clusters(transactions):
    """transactions: list of (insider_cik, txn_date, filing_id), already
    sorted by txn_date ascending, for ONE ticker.

    Returns a list of (trigger_filing_id, cluster_date, involved_insider_ciks)
    -- one entry per NEWLY-formed cluster (the first transaction where the
    distinct-insider count in the trailing 30-day window reaches the
    threshold). Does not re-trigger for every subsequent transaction
    within an already-active cluster; re-triggers only after the window
    genuinely drops back below threshold and rises again (a new,
    distinct cluster).
    """
    clusters = []
    active = False
    for i, (insider_cik, txn_date, filing_id) in enumerate(transactions):
        window_start = txn_date - timedelta(days=WINDOW_DAYS)
        window_insiders = {
            t[0] for t in transactions[: i + 1] if window_start <= t[1] <= txn_date
        }
        if len(window_insiders) >= MIN_DISTINCT_INSIDERS:
            if not active:
                clusters.append((filing_id, txn_date, window_insiders))
                active = True
        else:
            active = False
    return clusters


def run(rescan_all=False):
    db = SessionLocal()

    existing_flag_keys = {
        (fe.filing_id, fe.flag_type)
        for fe in db.query(FlagEvent.filing_id, FlagEvent.flag_type)
        .filter(FlagEvent.flag_type == FLAG_TYPE).all()
    }

    # Only real open-market sales -- NOT gifts (G), awards (A), option
    # exercises (M), tax withholding (F), etc. Confirmed real transaction
    # codes during Form 4 schema verification (see D-016/D-019).
    rows = (
        db.query(
            InsiderTransaction.ticker,
            InsiderTransaction.insider_cik,
            InsiderTransaction.transaction_date,
            InsiderTransaction.filing_id,
            InsiderTransaction.issuer_cik,
        )
        .filter(InsiderTransaction.transaction_code == "S")
        .filter(InsiderTransaction.ticker.isnot(None))
        .order_by(InsiderTransaction.ticker, InsiderTransaction.transaction_date)
        .all()
    )

    by_ticker = defaultdict(list)
    issuer_cik_by_ticker = {}
    for ticker, insider_cik, txn_date, filing_id, issuer_cik in rows:
        by_ticker[ticker].append((insider_cik, txn_date, filing_id))
        issuer_cik_by_ticker[ticker] = issuer_cik

    flags_created = 0
    tickers_with_clusters = 0

    for ticker, txns in by_ticker.items():
        clusters = detect_clusters(txns)
        if not clusters:
            continue
        tickers_with_clusters += 1

        for trigger_filing_id, cluster_date, involved_insiders in clusters:
            key = (trigger_filing_id, FLAG_TYPE)
            if key in existing_flag_keys and not rescan_all:
                continue

            db.add(FlagEvent(
                filing_id=trigger_filing_id,
                source_type="insider_transaction",
                cik=issuer_cik_by_ticker[ticker],
                ticker=ticker,
                flag_type=FLAG_TYPE,
                flag_tier=1,
                filing_date=cluster_date,
                details={
                    "distinct_insiders": len(involved_insiders),
                    "insider_ciks": sorted(involved_insiders),
                    "window_days": WINDOW_DAYS,
                },
            ))
            existing_flag_keys.add(key)
            flags_created += 1

    db.commit()
    db.close()

    print(f"Tickers with any sale transaction: {len(by_ticker)}")
    print(f"Tickers with at least one cluster: {tickers_with_clusters}")
    print(f"Flags created: {flags_created}")


if __name__ == "__main__":
    import sys
    rescan_all = "--rescan-all" in sys.argv
    run(rescan_all=rescan_all)
