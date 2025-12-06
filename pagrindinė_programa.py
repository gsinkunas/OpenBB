"""Paprastesnė programa fundamentaliems rodikliams gauti su yfinance.

Struktūra:
- Dictonaries.py: žodynas su visais palaikomais rodikliais.
- sarasai.py: sąrašai su numatytaisias ticker'iais ir grafiko argumentais.
- pagrindinė_programa.py: vartotojo sąsaja (meniu) ir logika.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf

from Dictonaries import YFINANCE_SERIJOS
import sarasai

plt.switch_backend("Agg")
plt.style.use("seaborn-v0_8")

EXPORT_DIR = Path("eksportai")
PLOTS_DIR = Path("grafikai")


# ---------------------------------------------------------------------------
# Pagalbinės funkcijos
# ---------------------------------------------------------------------------

def ensure_dir(path: Path) -> None:
    """Sukuria katalogą, jei jo dar nėra."""

    path.mkdir(parents=True, exist_ok=True)


def download_company_data(ticker: str) -> Dict[str, pd.DataFrame | dict]:
    """Vienoje vietoje atsisiunčiame visus yfinance duomenis."""

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
    """Ima naujausią konkretos eilutės reikšmę iš finansinės ataskaitos."""

    if statement is None or statement.empty or row_name not in statement.index:
        return None

    values = statement.loc[row_name].dropna()
    return float(values.iloc[0]) if not values.empty else None


def raw_metric_value(meta: dict, datasets: Dict[str, pd.DataFrame | dict]) -> Optional[float]:
    """Grąžina tiesioginę reikšmę iš pasirinkto šaltinio."""

    source = meta.get("source")
    field = meta.get("field")

    if source in {"fast_info", "info"}:
        return datasets.get(source, {}).get(field)

    statement = datasets.get(source)
    if isinstance(statement, pd.DataFrame):
        return newest_statement_value(statement, field)

    return None


def formula_metric_value(meta: dict, datasets: Dict[str, pd.DataFrame | dict], cache: dict) -> Optional[float]:
    """Apskaičiuoja santykius arba sumas pagal aprašą žodyne."""

    method = meta.get("method")

    if method == "divide":
        num = get_metric_value(meta.get("numerator"), datasets, cache)
        den = get_metric_value(meta.get("denominator"), datasets, cache)
        if num is None or den in (None, 0):
            return None
        multiplier = meta.get("multiplier", 1)
        return float(num) / float(den) * multiplier

    if method == "sum":
        operands = meta.get("operands", [])
        values = [get_metric_value(code, datasets, cache) for code in operands]
        if any(value is None for value in values):
            return None
        return float(sum(values))

    return None


def get_metric_value(code: Optional[str], datasets: Dict[str, pd.DataFrame | dict], cache: dict) -> Optional[float]:
    """Pagal kodą grąžina rodiklio reikšmę (iš žodyno)."""

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
    """Gražiai suformatuoja skaičių spausdinimui."""

    if value is None:
        return "N/A"

    fmt = meta.get("format", "number")
    precision = meta.get("precision", 2)

    if fmt == "usd":
        return f"{value:,.{precision}f}"
    if fmt == "percent":
        return f"{value:,.{precision}f}%"
    return f"{value:,.{precision}f}"


# ---------------------------------------------------------------------------
# Suvestinės ir eksportas
# ---------------------------------------------------------------------------

def build_summary_dataframe(
    ticker: str, metrics: Optional[Sequence[str]] = None
) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame | dict]]:
    """Grąžina suvestinę (DataFrame) ir visus atsisiųstus duomenis."""

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
                "Reikšmė": format_metric(value, meta),
            }
        )

    df = pd.DataFrame(rows)
    return df, datasets


def export_to_excel(df: pd.DataFrame, ticker: str, filename: Optional[str] = None) -> Path:
    """Išsaugo lentelę Excel formatu."""

    ensure_dir(EXPORT_DIR)
    output = EXPORT_DIR / (filename or f"{ticker}_santrauka.xlsx")
    df.to_excel(output, index=False)
    return output


def print_summary(df: pd.DataFrame, ticker: str) -> None:
    """Aiškiai atspausdina lentelę konsolėje."""

    separator = "=" * 70
    print(f"\n{separator}\n📊 {ticker} SANTRAUKA\n{separator}")
    print(df.to_string(index=False))


# ---------------------------------------------------------------------------
# Grafikai
# ---------------------------------------------------------------------------

def statement_series_for_plot(
    metric_code: str, datasets: Dict[str, pd.DataFrame | dict]
) -> Optional[pd.Series]:
    """Paverčia pasirinktą metriką į laiko eilutę grafikui."""

    meta = YFINANCE_SERIJOS.get(metric_code)
    if not meta or not meta.get("plot"):
        return None

    statement = datasets.get(meta.get("source"))
    if not isinstance(statement, pd.DataFrame):
        return None

    field = meta.get("field")
    if field not in statement.index:
        return None

    series = statement.loc[field].dropna()
    if series.empty:
        return None

    series.index = pd.to_datetime(series.index)
    return series.sort_index()


def plot_metrics(
    ticker: str,
    metrics: Sequence[str],
    years: Tuple[int, int],
    datasets: Optional[Dict[str, pd.DataFrame | dict]] = None,
) -> Optional[Path]:
    """Braižo iki dviejų rodiklių grafiką ir grąžina failo kelią."""

    datasets = datasets or download_company_data(ticker)
    prepared = []

    for code in metrics[:2]:
        series = statement_series_for_plot(code, datasets)
        if series is None:
            print(f"❌ {code} neturi pakankamai duomenų grafiko braižymui.")
            continue
        mask = (series.index.year >= years[0]) & (series.index.year <= years[1])
        filtered = series[mask]
        if filtered.empty:
            print(f"❌ {code} neturi duomenų tarp {years[0]}–{years[1]} m.")
            continue
        prepared.append((code, filtered))

    if not prepared:
        return None

    ensure_dir(PLOTS_DIR)
    fig, ax = plt.subplots(figsize=(10, 5))
    secondary_ax = None

    for idx, (code, series) in enumerate(prepared):
        label = YFINANCE_SERIJOS[code]["label"]
        axis = ax if idx == 0 else ax.twinx()
        axis.plot(series.index.year, series.values, label=label)
        axis.set_ylabel(label)
        secondary_ax = axis if idx == 1 else secondary_ax

    ax.set_xlabel("Metai")
    title = " ir ".join(YFINANCE_SERIJOS[c]["label"] for c, _ in prepared)
    ax.set_title(f"{ticker}: {title}")

    handles, labels = ax.get_legend_handles_labels()
    if secondary_ax and secondary_ax is not ax:
        h2, l2 = secondary_ax.get_legend_handles_labels()
        handles += h2
        labels += l2
    ax.legend(handles, labels, loc="best")

    filename = f"{ticker}_{'_'.join(code for code, _ in prepared)}_{years[0]}_{years[1]}.png"
    output = PLOTS_DIR / filename
    fig.tight_layout()
    fig.savefig(output, dpi=300)
    plt.close(fig)

    return output


def read_plot_arguments(args: Sequence[str]) -> Tuple[List[str], List[str], List[int]]:
    """Atskiriame ticker'ius, metrikas ir metus."""

    tickers: List[str] = []
    metrics: List[str] = []
    years: List[int] = []

    for arg in args:
        cleaned = arg.strip()
        if not cleaned:
            continue
        if cleaned.isdigit():
            years.append(int(cleaned))
            continue
        upper = cleaned.upper()
        if upper in sarasai.PLOT_METRIC_CHOICES:
            metrics.append(upper)
        else:
            tickers.append(upper)

    return tickers, metrics, years


def plot_flow() -> None:
    """Vartotojo sąsaja grafikams generuoti."""

    print("\n📈 Galimi rodikliai grafikams:")
    print(", ".join(sarasai.PLOT_METRIC_CHOICES))
    user_input = input(
        "Įveskite argumentus (pvz. AAPL,MSFT,REVENUE,NET_INCOME,2015,2024): "
    )

    args = (
        [chunk.strip() for chunk in user_input.split(",") if chunk.strip()]
        if user_input.strip()
        else sarasai.ARGUMENTU_PAVYZDYS
    )

    tickers, metrics, years = read_plot_arguments(args)

    if not metrics:
        print("❌ Nenurodėte rodiklių.")
        return
    if len(metrics) > 2:
        print("⚠️ Naudosime tik pirmus du rodiklius.")
        metrics = metrics[:2]
    if not tickers:
        print("❌ Nenurodėte nė vieno ticker.")
        return

    if len(years) == 0:
        years = [2000, date.today().year]
    elif len(years) == 1:
        years.append(date.today().year)

    year_range = (min(years), max(years))

    for ticker in tickers[:2]:
        print(f"\n🎯 Generuojamas grafikas {ticker}...")
        datasets = download_company_data(ticker)
        output = plot_metrics(ticker, metrics, year_range, datasets)
        if output:
            print(f"💾 Grafikas išsaugotas: {output}")
        else:
            print("❌ Nepavyko suformuoti grafiko.")


# ---------------------------------------------------------------------------
# Papildomi veiksmai (raw statement'ai)
# ---------------------------------------------------------------------------

def print_statements(ticker: str) -> None:
    """Parodo pagrindines finansines ataskaitas."""

    datasets = download_company_data(ticker)

    def show(title: str, df: pd.DataFrame) -> None:
        separator = "=" * 70
        print(f"\n{separator}\n{title}\n{separator}")
        print(df.T.head() if not df.empty else "Nėra duomenų")

    show("💵 PAJAMŲ ATASKAITA", datasets.get("income_stmt", pd.DataFrame()))
    show("💼 BALANSAS", datasets.get("balance_sheet", pd.DataFrame()))
    show("💸 PINIGŲ SRAUTAI", datasets.get("cash_flow", pd.DataFrame()))


# ---------------------------------------------------------------------------
# Vartotojo meniu
# ---------------------------------------------------------------------------

def handle_summary_flow(export: bool) -> None:
    """Klausiam ticker ir parodome suvestinę, optional eksportas."""

    ticker = input("\nĮveskite ticker (pvz. AAPL): ").strip().upper()
    if not ticker:
        print("❌ Ticker privalomas.")
        return

    summary_df, _ = build_summary_dataframe(ticker)
    print_summary(summary_df, ticker)

    if export:
        filename = input("Failo pavadinimas (palikite tuščią, jei tinka numatytasis): ").strip()
        path = export_to_excel(summary_df, ticker, filename or None)
        print(f"💾 Suvestinė įrašyta: {path}")


def main() -> None:
    separator = "=" * 70
    print("\n" + separator)
    print("📊 ĮMONIŲ ANALIZĖ SU YFINANCE")
    print(separator)
    print("✅ Duomenis pateikiame pandas DataFrame formatu")
    print("✅ Galima eksportuoti į Excel failą")
    print("✅ Galima sugeneruoti grafikus")

    menu = (
        "\n1 - Įmonės santrauka",
        "2 - Įmonės santrauka + eksportas",
        "3 - Suformuoti grafikus",
        "4 - Parodyti žalius finansinius duomenis",
        "0 - Išeiti",
    )

    while True:
        print("\n" + separator)
        print("MENIU")
        print(separator)
        for line in menu:
            print(line)

        choice = input("\nPasirinkimas: ").strip()

        if choice == "0":
            print("\n👋 Iki!")
            break
        if choice == "1":
            handle_summary_flow(export=False)
        elif choice == "2":
            handle_summary_flow(export=True)
        elif choice == "3":
            plot_flow()
        elif choice == "4":
            ticker = input("Įveskite ticker: ").strip().upper()
            if ticker:
                print_statements(ticker)
            else:
                print("❌ Ticker privalomas.")
        else:
            print("❌ Neteisingas pasirinkimas.")


if __name__ == "__main__":
    main()
