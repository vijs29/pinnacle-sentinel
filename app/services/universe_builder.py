"""
Builds the Sentinel scan universe (ticker, CIK, company_name) from
Wikipedia's "List of S&P 500 companies" page - static HTML table,
includes CIK directly, no anti-bot friction.

Output: app/config/universe.csv
"""
import pandas as pd
import io
from pathlib import Path

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Sentinel/1.0 (vijay.cloudarchitect@gmail.com)"}

OUTPUT_PATH = Path(__file__).resolve().parents[2] / "app" / "config" / "universe.csv"


def fetch_sp500_table() -> pd.DataFrame:
    import requests
    resp = requests.get(WIKI_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    tables = pd.read_html(io.StringIO(resp.text))
    df = tables[0]  # first table on the page is the constituents table
    return df


def build_universe() -> list[dict]:
    df = fetch_sp500_table()

    # Wikipedia columns: Symbol, Security, GICS Sector, GICS Sub-Industry,
    # Headquarters Location, Date added, CIK, Founded
    universe = []
    for _, row in df.iterrows():
        ticker = str(row["Symbol"]).strip().upper().replace(".", "-")  # BRK.B -> BRK-B style
        cik = str(row["CIK"]).strip().zfill(10)
        company_name = str(row["Security"]).strip()
        universe.append({"ticker": ticker, "cik": cik, "company_name": company_name})

    print(f"S&P 500 constituents parsed: {len(universe)}")
    return universe


def write_universe_csv(universe: list[dict]):
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    import csv
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ticker", "cik", "company_name"])
        writer.writeheader()
        writer.writerows(universe)
    print(f"Written: {OUTPUT_PATH} ({len(universe)} rows)")


if __name__ == "__main__":
    universe = build_universe()
    write_universe_csv(universe)
