"""Automatinis skriptas, kuris naudoja yfinance fundamentiniams duomenims
surinkti ir viską tiesiogiai išsaugo į Excel failus (be jokio meniu).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Sequence

import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# Konfigūracija (koreguokite pagal poreikį)
# ---------------------------------------------------------------------------

DEFAULT_TICKERS = ["AAPL", "MSFT", "GOOGL"]
EXPORT_DIR = Path("eksportai")
SUMMARY_METRICS = [
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
    "OPERATING_CASH_FLOW",
    "FREE_CASH_FLOW",
    "TOTAL_ASSETS",
    "TOTAL_EQUITY",
    "TOTAL_DEBT",
    "CURRENT_RATIO",
    "DEBT_TO_EQUITY",
]

YFINANCE_SERIES = {
    "PRICE": {
        "label": "Dabartinė kaina ($)",
        "group": "Kaina",
        "type": "raw",
        "source": "fast_info",
        "field": "lastPrice",
        "format": "usd",
        "precision": 2,
    },
    "MARKET_CAP": {
        "label": "Kapitalizacija ($)",
        "group": "Kaina",
        "type": "raw",
        "source": "fast_info",
        "field": "marketCap",
        "format": "usd",
        "precision": 0,
    },
    "EPS": {
        "label": "EPS",
        "group": "Pelningumas",
        "type": "raw",
        "source": "info",
        "field": "trailingEps",
        "format": "number",
        "precision": 2,
    },
    "REVENUE": {
        "label": "Pajamos ($)",
        "group": "Augimas",
        "type": "raw",
        "source": "income_stmt",
        "field": "Total Revenue",
        "format": "usd",
        "precision": 0,
    },
    "NET_INCOME": {
        "label": "Grynasis pelnas ($)",
        "group": "Augimas",
        "type": "raw",
        "source": "income_stmt",
        "field": "Net Income",
        "format": "usd",
        "precision": 0,
    },
    "EBITDA": {
        "label": "EBITDA ($)",
        "group": "Pelningumas",
        "type": "raw",
        "source": "income_stmt",
        "field": "Ebitda",
        "format": "usd",
        "precision": 0,
    },
    "OPERATING_CASH_FLOW": {
        "label": "Operacinis pinigų srautas ($)",
        "group": "Pinigų srautai",
        "type": "raw",
        "source": "cash_flow",
        "field": "Total Cash From Operating Activities",
        "format": "usd",
        "precision": 0,
    },
    "TOTAL_ASSETS": {
        "label": "Turtas ($)",
        "group": "Balansas",
        "type": "raw",
        "source": "balance_sheet",
        "field": "Total Assets",
        "format": "usd",
        "precision": 0,
    },
    "TOTAL_DEBT": {
        "label": "Visos skolos ($)",
        "group": "Balansas",
        "type": "raw",
        "source": "balance_sheet",
        "field": "Total Debt",
        "format": "usd",
        "precision": 0,
    },
    "TOTAL_EQUITY": {
        "label": "Nuosavas kapitalas ($)",
        "group": "Balansas",
        "type": "raw",
        "source": "balance_sheet",
        "field": "Total Stockholder Equity",
        "format": "usd",
        "precision": 0,
    },
    "FREE_CASH_FLOW": {
        "label": "Laisvas pinigų srautas ($)",
        "group": "Pinigų srautai",
        "type": "formula",
        "method": "sum",
        "operands": ["OPERATING_CASH_FLOW"],
        "format": "usd",
        "precision": 0,
    },
    "PE_RATIO": {
        "label": "P/E",
        "group": "Vertinimas",
        "type": "formula",
        "method": "divide",
        "numerator": "PRICE",
        "denominator": "EPS",
        "format": "number",
        "precision": 2,
    },
    "ROE": {
        "label": "ROE (%)",
        "group": "Pelningumas",
        "type": "formula",
        "method": "divide",
        "numerator": "NET_INCOME",
        "denominator": "TOTAL_EQUITY",
        "multiplier": 100,
        "format": "percent",
        "precision": 2,
    },
    "ROA": {
        "label": "ROA (%)",
        "group": "Pelningumas",
        "type": "formula",
        "method": "divide",
        "numerator": "NET_INCOME",
        "denominator": "TOTAL_ASSETS",
        "multiplier": 100,
        "format": "percent",
        "precision": 2,
    },
    "NET_MARGIN": {
        "label": "Grynojo pelno marža (%)",
        "group": "Pelningumas",
        "type": "formula",
        "method": "divide",
        "numerator": "NET_INCOME",
        "denominator": "REVENUE",
        "multiplier": 100,
        "format": "percent",
        "precision": 2,
    },
    "CURRENT_RATIO": {
        "label": "Current Ratio",
        "group": "Likvidumas",
        "type": "formula",
        "method": "divide",
        "numerator": "TOTAL_ASSETS",
        "denominator": "TOTAL_DEBT",
        "format": "number",
        "precision": 2,
    },
    "DEBT_TO_EQUITY": {
        "label": "Debt/Equity",
        "group": "Skolos",
        "type": "formula",
        "method": "divide",
        "numerator": "TOTAL_DEBT",
        "denominator": "TOTAL_EQUITY",
        "format": "number",
        "precision": 2,
    },
}


# ---------------------------------------------------------------------------
# Pagalbinės funkcijos
# ---------------------------------------------------------------------------

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def download_company_data(ticker: str) -> Dict[str, pd.DataFrame | dict]:
    ticker_obj = yf.Ticker(ticker)
    fast_info = getattr(ticker_obj, "fast_info", {}) or {}
    try:
        info = ticker_obj.get_info()
    except Exception:
        info = {}

    def to_df(data: object) -> pd.DataFrame:
        return data if isinstance(data, pd.DataFrame) else pd.DataFrame()

    return {
        "fast_info": fast_info,
        "info": info,
        "income_stmt": to_df(ticker_obj.financials),
        "balance_sheet": to_df(ticker_obj.balance_sheet),
        "cash_flow": to_df(ticker_obj.cashflow),
    }


def newest_statement_value(statement: pd.DataFrame, field: str) -> Optional[float]:
    if statement is None or statement.empty or field not in statement.index:
        return None
    series = statement.loc[field].dropna()
    return float(series.iloc[0]) if not series.empty else None


def raw_metric_value(meta: dict, datasets: Dict[str, pd.DataFrame | dict]) -> Optional[float]:
    source = meta.get("source")
    field = meta.get("field")

    if source in {"fast_info", "info"}:
        return datasets.get(source, {}).get(field)

    statement = datasets.get(source)
    if isinstance(statement, pd.DataFrame):
        return newest_statement_value(statement, field)

    return None


def formula_metric_value(meta: dict, datasets: Dict[str, pd.DataFrame | dict], cache: dict) -> Optional[float]:
    method = meta.get("method")

    if method == "divide":
        numerator = get_metric_value(meta.get("numerator"), datasets, cache)
        denominator = get_metric_value(meta.get("denominator"), datasets, cache)
        if numerator is None or denominator in (None, 0):
            return None
        multiplier = meta.get("multiplier", 1)
        return float(numerator) / float(denominator) * multiplier

    if method == "sum":
        operands = meta.get("operands", [])
        values = [get_metric_value(code, datasets, cache) for code in operands]
        if any(value is None for value in values):
            return None
        return float(sum(values))

    return None


def get_metric_value(code: Optional[str], datasets: Dict[str, pd.DataFrame | dict], cache: dict) -> Optional[float]:
    if not code:
        return None
    if code in cache:
        return cache[code]

    meta = YFINANCE_SERIES.get(code)
    if not meta:
        cache[code] = None
        return None

    if meta.get("type") == "raw":
        value = raw_metric_value(meta, datasets)
    else:
        value = formula_metric_value(meta, datasets, cache)

    if value is not None:
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = None

    cache[code] = value
    return value


def format_metric(value: Optional[float], meta: dict) -> str:
    if value is None:
        return "N/A"
    fmt = meta.get("format", "number")
    precision = meta.get("precision", 2)

    if fmt == "usd":
        return f"{value:,.{precision}f}"
    if fmt == "percent":
        return f"{value:,.{precision}f}%"
    return f"{value:,.{precision}f}"


def tidy_statement(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    tidy = df.T.copy()
    tidy.index = pd.to_datetime(tidy.index)
    tidy.index.name = "Periodas"
    return tidy.sort_index()


# ---------------------------------------------------------------------------
# Eksportas
# ---------------------------------------------------------------------------

def build_summary_dataframe(ticker: str) -> tuple[pd.DataFrame, Dict[str, pd.DataFrame | dict]]:
    datasets = download_company_data(ticker)
    cache: Dict[str, Optional[float]] = {}

    rows = []
    for code in SUMMARY_METRICS:
        meta = YFINANCE_SERIES.get(code)
        if not meta:
            continue
        value = get_metric_value(code, datasets, cache)
        rows.append(
            {
                "Kategorija": meta.get("group", "Kita"),
                "Rodiklis": meta.get("label", code),
                "Reikšmė": value,
                "Formatuota": format_metric(value, meta),
            }
        )

    df = pd.DataFrame(rows)
    return df, datasets


def export_company_workbook(
    ticker: str,
    summary_df: pd.DataFrame,
    datasets: Dict[str, pd.DataFrame | dict],
    filename: Optional[str] = None,
) -> Path:
    ensure_dir(EXPORT_DIR)
    output = EXPORT_DIR / (filename or f"{ticker}_fundamentalai.xlsx")

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Santrauka", index=False)
        tidy_statement(datasets.get("income_stmt")).to_excel(writer, sheet_name="Pajamos")
        tidy_statement(datasets.get("balance_sheet")).to_excel(writer, sheet_name="Balansas")
        tidy_statement(datasets.get("cash_flow")).to_excel(writer, sheet_name="Pinigų srautai")

    return output


def process_ticker(ticker: str) -> None:
    print(f"\n🔄 Apdorojama {ticker}...")
    summary_df, datasets = build_summary_dataframe(ticker)
    if summary_df.empty:
        print("❌ Nepavyko gauti duomenų.")
        return
    path = export_company_workbook(ticker, summary_df, datasets)
    print(f"✅ Išsaugota: {path}")


def export_all(tickers: Sequence[str]) -> None:
    tickers = [t.strip().upper() for t in tickers if t.strip()]
    if not tickers:
        print("⚠️ Tuščias sąrašas – nieko neeksportuota.")
        return

    for ticker in tickers:
        process_ticker(ticker)

    print("\n🎉 Baigta! Failų ieškokite kataloge 'eksportai'.")


if __name__ == "__main__":
    export_all(DEFAULT_TICKERS)
