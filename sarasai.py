"""Iš anksto apibrėžti sąrašai, naudojami vartotojo įvestims validuoti."""

DEFAULT_TICKERS = [
    "AAPL",
    "MSFT",
    "GOOGL",
    "NVDA",
    "AMZN",
    "META",
    "TSLA",
    "NFLX",
]

DEFAULT_SUMMARY_METRICS = [
    "PRICE",
    "MARKET_CAP",
    "REVENUE",
    "NET_INCOME",
    "EPS",
    "PE_RATIO",
    "ROE",
    "ROA",
    "NET_MARGIN",
    "EBITDA",
    "GROSS_PROFIT",
    "OPERATING_CASH_FLOW",
    "FREE_CASH_FLOW",
    "FREE_CASH_FLOW_MARGIN",
    "TOTAL_ASSETS",
    "TOTAL_EQUITY",
    "TOTAL_DEBT",
    "DEBT_TO_EBITDA",
    "CURRENT_RATIO",
    "DEBT_TO_EQUITY",
    "CASH_EQUIVALENTS",
]

PLOT_METRIC_CHOICES = [
    "REVENUE",
    "NET_INCOME",
    "OPERATING_CASH_FLOW",
    "FREE_CASH_FLOW",
    "EBITDA",
    "GROSS_PROFIT",
]

ARGUMENTU_PAVYZDYS = [
    "AAPL",
    "MSFT",
    "REVENUE",
    "NET_INCOME",
    "2014",
    "2024",
]
