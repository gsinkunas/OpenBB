"""Automatinis skriptas, kuris su yfinance surenka fundamentalius duomenis
ir perkelia juos į Excel failus.

Kiekvienam pasirinktam ticker'iui sugeneruojame vieną Excel dokumentą su:
- pagrindine santrauka (rodikliai ir apskaičiuoti santykiai);
- žaliomis pajamas, balanso ir pinigų srautų ataskaitomis (jei prieinamos).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

import pandas as pd
import yfinance as yf

from Dictonaries import YFINANCE_SERIJOS
import sarasai

EXPORT_DIR = Path("eksportai")
DEFAULT_TICKERS = sarasai.DEFAULT_TICKERS[:3]


# ---------------------------------------------------------------------------
# Pagalbinės funkcijos
# ---------------------------------------------------------------------------

def ensure_dir(path: Path) -> None:
    """Sukuria katalogą, jeigu reikia."""

    path.mkdir(parents=True, exist_ok=True)


def download_company_data(ticker: str) -> Dict[str, pd.DataFrame | dict]:
    """Vienoje vietoje atsisiunčia reikalingus yfinance duomenis."""

    tk = yf.Ticker(ticker)

    fast_info = getattr(tk, "fast_info", {}) or {}
    try:
        info = tk.get_info()
    except Exception:
        info = {}

    def to_df(value: object) -> pd.DataFrame:
        return value if isinstance(value, pd.DataFrame) else pd.DataFrame()

    return {
        "fast_info": fast_info,
        "info": info,
        "income_stmt": to_df(tk.financials),
        "balance_sheet": to_df(tk.balance_sheet),
        "cash_flow": to_df(tk.cashflow),
    }


def newest_statement_value(statement: pd.DataFrame, row_name: str) -> Optional[float]:
    """Paimame naujausią reikšmę iš finansinės ataskaitos eilutės."""

    if statement is None or statement.empty or row_name not in statement.index:
        return None

    values = statement.loc[row_name].dropna()
    return float(values.iloc[0]) if not values.empty else None


def raw_metric_value(meta: dict, datasets: Dict[str, pd.DataFrame | dict]) -> Optional[float]:
    """Gražina tiesioginę reikšmę iš fast_info/info ar ataskaitų."""

    source = meta.get("source")
    field = meta.get("field")

    if source in {"fast_info", "info"}:
        return datasets.get(source, {}).get(field)

    statement = datasets.get(source)
    if isinstance(statement, pd.DataFrame):
        return newest_statement_value(statement, field)

    return None


def formula_metric_value(meta: dict, datasets: Dict[str, pd.DataFrame | dict], cache: dict) -> Optional[float]:
    """Suskaičiuoja išvestinius rodiklius pagal nurodytą metodą."""

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
    """Pagal kodą gražina (arba suskaičiuoja) rodiklio reikšmę."""

    if code is None:
        return None
    if code in cache:
        return cache[code]

    meta = YFINANCE_SERIJOS.get(code)
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
    """Sukuria draugišką formatą, kurį parodysime Excel'e."""

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
    """Paverčia yfinance formatą į "viena eilutė = metai" variantą."""

    if df is None or df.empty:
        return pd.DataFrame()
    tidy = df.T.copy()
    tidy.index = pd.to_datetime(tidy.index)
    tidy.index.name = "Periodas"
    return tidy.sort_index()


# ---------------------------------------------------------------------------
# Excel eksportas
# ---------------------------------------------------------------------------

def build_summary_dataframe(
    ticker: str, metrics: Optional[Sequence[str]] = None
) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame | dict]]:
    """Sugeneruoja vienos įmonės rodiklių santrauką."""

    datasets = download_company_data(ticker)
    codes = list(metrics or sarasai.DEFAULT_SUMMARY_METRICS)
    cache: Dict[str, Optional[float]] = {}

    rows = []
    for code in codes:
        meta = YFINANCE_SERIJOS.get(code)
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
    """Sukuria Excel failą su santrauka ir žaliomis ataskaitomis."""

    ensure_dir(EXPORT_DIR)
    output = EXPORT_DIR / (filename or f"{ticker}_fundamentalai.xlsx")

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Santrauka", index=False)
        tidy_statement(datasets.get("income_stmt")).to_excel(writer, sheet_name="Pajamos")
        tidy_statement(datasets.get("balance_sheet")).to_excel(writer, sheet_name="Balansas")
        tidy_statement(datasets.get("cash_flow")).to_excel(writer, sheet_name="Pinigų srautai")

    return output


def process_ticker(ticker: str) -> Optional[Path]:
    """Sukuria santrauką ir ją įrašo į Excel. Grąžina failo kelią."""

    print(f"\n🔄 Apdorojama {ticker}...")
    summary_df, datasets = build_summary_dataframe(ticker)
    if summary_df.empty:
        print("❌ Nepavyko gauti duomenų.")
        return None

    output = export_company_workbook(ticker, summary_df, datasets)
    print(f"✅ {ticker} išsaugotas: {output}")
    return output


def export_all(tickers: Sequence[str]) -> None:
    """Per visus ticker'ius prasukame automatiškai."""

    if not tickers:
        print("⚠️ Sąrašas tuščias, nėra ko eksportuoti.")
        return

    for ticker in tickers:
        process_ticker(ticker.strip().upper())

    print("\n🎉 Darbas baigtas! Failai yra kataloge 'eksportai'.")


if __name__ == "__main__":
    export_all(DEFAULT_TICKERS)
