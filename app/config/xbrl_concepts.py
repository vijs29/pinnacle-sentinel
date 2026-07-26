"""
Whitelist of us-gaap XBRL concepts to ingest from SEC's companyfacts API.

Structure: each entry maps a concept tag to the score(s)/ratio(s) that
consume it, purely for documentation/traceability -- the ingestion script
only cares about the CONCEPTS set below.

TO EXPAND: add the us-gaap tag to CONCEPTS. If it's an instant-in-time
fact (balance sheet items), add it to INSTANT_CONCEPTS too, so the parser
knows to key it by end-date only rather than start+end date. Everything
not in INSTANT_CONCEPTS is treated as a duration fact (income statement /
cash flow items, which cover a start-to-end period).
"""

# -- Income statement / cash flow (duration facts: cover a period) --
DURATION_CONCEPTS = {
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "CostOfGoodsAndServicesSold",
    "CostOfRevenue",
    "GrossProfit",
    "SellingGeneralAndAdministrativeExpense",
    "OperatingIncomeLoss",
    "NetIncomeLoss",
    "NetCashProvidedByUsedInOperatingActivities",
    "DepreciationDepletionAndAmortization",
    "DepreciationAmortizationAndAccretionNet",
    "IncomeTaxExpenseBenefit",
    "InterestExpense",
}

# -- Balance sheet (instant facts: a snapshot as of one date) --
INSTANT_CONCEPTS = {
    "Assets",
    "AssetsCurrent",
    "LiabilitiesCurrent",
    "Liabilities",
    "StockholdersEquity",
    "RetainedEarningsAccumulatedDeficit",
    "PropertyPlantAndEquipmentNet",
    "AccountsReceivableNetCurrent",
    "InventoryNet",
    "LongTermDebtNoncurrent",
    "LongTermDebtCurrent",
    "CommonStockSharesOutstanding",
    "IntangibleAssetsNetExcludingGoodwill",
    "Goodwill",
    "AllowanceForDoubtfulAccountsReceivableCurrent",
    "DeferredRevenueCurrent",
    "CashAndCashEquivalentsAtCarryingValue",
}

CONCEPTS = DURATION_CONCEPTS | INSTANT_CONCEPTS  # 30 concepts total

assert len(CONCEPTS) == 30, f"Expected 30 whitelisted concepts, got {len(CONCEPTS)} -- update this assertion if intentionally expanding"
