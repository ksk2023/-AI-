"""Stock universe for the "big-up day follow-through" study.

A curated, diversified set covering all GICS sectors, market-cap tiers
(mega/large/mid/small), growth vs value, and sector ETFs as sector proxies.
This maximizes signal coverage while staying within free-tier API limits.
"""
from __future__ import annotations

# --- Individual stocks, grouped by Finnhub industry for later aggregation ---
# Tickers chosen for long listing history and high liquidity.
UNIVERSE = {
    # Technology (mega/large cap, growth)
    "Technology": ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "ORCL", "ADBE", "CRM", "INTC", "CSCO"],
    # Communication / Consumer Discretionary
    "Communication": ["NFLX", "DIS", "CMCSA"],
    "Consumer Discretionary": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "LOW"],
    # Consumer Staples (defensive)
    "Consumer Staples": ["WMT", "PG", "KO", "PEP", "COST"],
    # Healthcare
    "Healthcare": ["JNJ", "UNH", "LLY", "PFE", "MRK", "ABBV"],
    # Financials
    "Financials": ["JPM", "BAC", "WFC", "GS", "MS", "V", "BRK-B"],
    # Industrials
    "Industrials": ["CAT", "BA", "GE", "HON", "UPS"],
    # Energy
    "Energy": ["XOM", "CVX", "COP"],
    # Materials
    "Materials": ["LIN", "APD", "FCX"],
    # Utilities (defensive)
    "Utilities": ["NEE", "DUK"],
    # Real Estate
    "Real Estate": ["PLD", "AMT"],
}

# Sector ETFs as clean sector-proxies (less single-name noise)
SECTOR_ETFS = {
    "Tech_XLK": "XLK",
    "Health_XLV": "XLV",
    "Financial_XLF": "XLF",
    "Energy_XLE": "XLE",
    "Discretion_XLY": "XLY",
    "Staples_XLP": "XLP",
    "Industrial_XLI": "XLI",
    "Utilities_XLU": "XLU",
    "RealEstate_XLRE": "XLRE",
    "Materials_XLB": "XLB",
    "Comm_XLC": "XLC",
}

# Broad index ETFs
INDEX_ETFS = {
    "SP500_SPY": "SPY",
    "Nasdaq_QQQ": "QQQ",
    "Dow_DIA": "DIA",
    "Russell2000_IWM": "IWM",
    "Volatility_VIX": "^VIX",
}


def all_individual_tickers() -> list[str]:
    out = []
    for tickers in UNIVERSE.values():
        out.extend(tickers)
    return sorted(set(out))


def all_tickers() -> list[str]:
    """Every ticker we want data for (stocks + ETFs)."""
    out = set(all_individual_tickers())
    out.update(SECTOR_ETFS.values())
    out.update(INDEX_ETFS.values())
    return sorted(out)


if __name__ == "__main__":
    indiv = all_individual_tickers()
    print(f"individual stocks: {len(indiv)}")
    print(f"sector ETFs: {len(SECTOR_ETFS)}")
    print(f"index ETFs: {len(INDEX_ETFS)}")
    print(f"total tickers: {len(all_tickers())}")