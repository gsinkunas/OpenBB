"""Sąrašai, kuriais remiamės validuodami vartotojo įvestis."""

# Populiariausi pavyzdiniai ticker'iai
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

# Rodikliai, kurie bus atvaizduoti suvestinėje lentelėje
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

# Tik šie rodikliai turi prasmę grafikams (jie turi kelių metų istoriją)
PLOT_METRIC_CHOICES = [
    "REVENUE",
    "NET_INCOME",
    "OPERATING_CASH_FLOW",
    "FREE_CASH_FLOW",
    "EBITDA",
    "GROSS_PROFIT",
]

# Jei vartotojas neįveda reikšmių, panaudosime ši pavyzdį
ARGUMENTU_PAVYZDYS = [
    "AAPL",
    "MSFT",
    "REVENUE",
    "NET_INCOME",
    "2014",
    "2024",
]
