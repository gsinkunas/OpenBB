"""Programėlė, kuri naudoja yfinance ir pandas fundamentaliems duomenims rinkti.

Struktūra paremta atskirais žodynų/listų moduliais (Dictonaries, sarasai),
kaip buvo prašyta užduotyje. Programa leidžia:
- saugiai surinkti pagrindinius rodiklius į DataFrame;
- eksportuoti suvestinę į Excel;
- formuoti grafikus pasirinktoms metrikoms;
- peržiūrėti žalius balansų/pajamų/pinigų srautų duomenis.
"""

from __future__ import annotations

import warnings
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf

from Dictonaries import YFINANCE_SERIJOS
import sarasai

warnings.filterwarnings("ignore", category=FutureWarning)
plt.switch_backend("Agg")
plt.style.use("seaborn-v0_8")

EXPORT_DIR = Path("eksportai")
PLOTS_DIR = Path("grafikai")


def ensure_dir(path: Path) -> None:
    """Sukuria direktoriją, jei jos nėra."""

    path.mkdir(parents=True, exist_ok=True)


def fetch_company_datasets(ticker: str) -> Dict[str, pd.DataFrame | dict]:
    """Parsiunčia reikalingus yfinance duomenis vienu kartu."""

    tk = yf.Ticker(ticker)

    try:
        fast_info = tk.fast_info or {}
    except Exception:
        fast_info = {}

    try:
        info = tk.get_info()
    except Exception:
        info = {}

    income_stmt = tk.financials if isinstance(tk.financials, pd.DataFrame) else pd.DataFrame()
    balance_sheet = tk.balance_sheet if isinstance(tk.balance_sheet, pd.DataFrame) else pd.DataFrame()
    cash_flow = tk.cashflow if isinstance(tk.cashflow, pd.DataFrame) else pd.DataFrame()

    history = tk.history(period="max", interval="1mo", auto_adjust=False)

    return {
        "ticker": tk,
        "fast_info": fast_info,
        "info": info,
        "income_stmt": income_stmt,
        "balance_sheet": balance_sheet,
        "cash_flow": cash_flow,
        "history": history,
    }


def extract_statement_value(df: pd.DataFrame, field: str) -> Optional[float]:
    """Grąžina naujausią eilutės reikšmę iš pateiktos finansinės ataskaitos."""

    if df is None or df.empty or field not in df.index:
        return None

    series = df.loc[field].dropna()
    if series.empty:
        return None

    try:
        return float(series.iloc[0])
    except (TypeError, ValueError):
        return None


def compute_derived_value(meta: dict, datasets: Dict[str, pd.DataFrame | dict], cache: dict) -> Optional[float]:
    """Apskaičiuoja išvestines reikšmes (santykius, sumas ir pan.)."""

    formula = meta.get("formula")

    if formula == "divide":
        numerator = resolve_metric_value(meta.get("numerator"), datasets, cache)
        denominator = resolve_metric_value(meta.get("denominator"), datasets, cache)
        if numerator is None or denominator in (None, 0):
            return None
        multiplier = meta.get("multiplier", 1)
        return float(numerator) / float(denominator) * multiplier

    if formula == "add":
        operands = meta.get("operands", [])
        values = [resolve_metric_value(code, datasets, cache) for code in operands]
        if any(value is None for value in values):
            return None
        return float(sum(values))

    return None


def resolve_metric_value(code: str, datasets: Dict[str, pd.DataFrame | dict], cache: dict) -> Optional[float]:
    """Atsineša arba apskaičiuoja rodiklio reikšmę pagal YFINANCE_SERIJOS."""

    if code is None:
        return None

    if code in cache:
        return cache[code]

    meta = YFINANCE_SERIJOS.get(code)
    if not meta:
        cache[code] = None
        return None

    source = meta.get("source")
    value: Optional[float] = None

    if source == "fast_info":
        value = datasets.get("fast_info", {}).get(meta.get("field"))
    elif source == "info":
        value = datasets.get("info", {}).get(meta.get("field"))
    elif source in {"income_stmt", "balance_sheet", "cash_flow"}:
        df = datasets.get(source)
        if isinstance(df, pd.DataFrame):
            value = extract_statement_value(df, meta.get("field"))
    elif source == "derived":
        value = compute_derived_value(meta, datasets, cache)

    if value is not None:
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = None

    cache[code] = value
    return value


def format_metric_value(value: Optional[float], meta: dict) -> str:
    """Gražiai suformatuoja skaičių pagal apibrėžimą žodyne."""

    if value is None:
        return "N/A"

    fmt = meta.get("format", "number")
    precision = meta.get("precision", 2)

    if fmt == "usd":
        return f"{value:,.{precision}f}"
    if fmt == "percent":
        return f"{value:,.{precision}f}%"
    if fmt == "number":
        return f"{value:,.{precision}f}"

    return str(value)


def create_summary_dataframe(
    ticker: str, metrics: Optional[Sequence[str]] = None
) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame | dict], Dict[str, Optional[float]]]:
    """Sudaro pagrindinę suvestinę DataFrame formatu."""

    datasets = fetch_company_datasets(ticker)
    codes = list(metrics or sarasai.DEFAULT_SUMMARY_METRICS)
    cache: Dict[str, Optional[float]] = {}

    rows = []
    for code in codes:
        meta = YFINANCE_SERIJOS.get(code)
        if not meta:
            continue
        value = resolve_metric_value(code, datasets, cache)
        rows.append(
            {
                "Kategorija": meta.get("category", "Kita"),
                "Rodiklis": meta.get("label", code),
                "Reikšmė": format_metric_value(value, meta),
            }
        )

    df = pd.DataFrame(rows)
    return df, datasets, cache


def export_summary_to_excel(df: pd.DataFrame, ticker: str, filename: Optional[str] = None) -> Path:
    """Išsaugo suvestinę Excel faile."""

    ensure_dir(EXPORT_DIR)
    clean_filename = filename or f"{ticker}_santrauka.xlsx"
    path = EXPORT_DIR / clean_filename
    df.to_excel(path, index=False)
    return path


def statement_to_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Paverčia yfinance transponuotą ataskaitą į patogesnę formą."""

    if df is None or df.empty:
        return pd.DataFrame()
    tidy = df.T.copy()
    tidy.index = pd.to_datetime(tidy.index)
    tidy.index.name = "Periodas"
    return tidy


def get_metric_series_for_plot(
    metric_code: str, datasets: Dict[str, pd.DataFrame | dict]
) -> Optional[pd.Series]:
    """Paruošia metrikos laiko eilutę grafiko braižymui."""

    meta = YFINANCE_SERIJOS.get(metric_code)
    if not meta or not meta.get("plot"):
        return None

    source = meta.get("source")
    df = datasets.get(source)
    if not isinstance(df, pd.DataFrame) or meta.get("field") not in df.index:
        return None

    series = df.loc[meta["field"]].dropna()
    if series.empty:
        return None

    series.index = pd.to_datetime(series.index)
    series = series.sort_index()
    return series


def plot_metrics_for_ticker(
    ticker: str,
    metrics: Sequence[str],
    years: Tuple[int, int],
    datasets: Optional[Dict[str, pd.DataFrame | dict]] = None,
) -> Optional[Path]:
    """Braižo iki dviejų metrikų grafiką ir išsaugo PNG faile."""

    datasets = datasets or fetch_company_datasets(ticker)
    start_year, end_year = years
    prepared_series = []

    for code in metrics[:2]:
        series = get_metric_series_for_plot(code, datasets)
        if series is None:
            print(f"❌ Nepavyko rasti duomenų metrikoje {code}")
            continue
        filtered = series[(series.index.year >= start_year) & (series.index.year <= end_year)]
        if filtered.empty:
            print(f"❌ {code} neturi duomenų nurodytam laikotarpiui")
            continue
        prepared_series.append((code, filtered))

    if not prepared_series:
        return None

    ensure_dir(PLOTS_DIR)
    fig, ax = plt.subplots(figsize=(10, 5))
    secondary_ax = None

    for idx, (code, series) in enumerate(prepared_series):
        meta = YFINANCE_SERIJOS[code]
        if idx == 0:
            ax.plot(series.index.year, series.values, label=meta["label"], color="#2f80ed")
            ax.set_xlabel("Metai")
            ax.set_ylabel(meta["label"])
        else:
            secondary_ax = ax.twinx()
            secondary_ax.plot(
                series.index.year,
                series.values,
                label=meta["label"],
                color="#eb5757",
            )
            secondary_ax.set_ylabel(meta["label"])

    title_metrics = " ir ".join([YFINANCE_SERIJOS[m]["label"] for m, _ in prepared_series])
    ax.set_title(f"{ticker}: {title_metrics}")

    handles, labels = ax.get_legend_handles_labels()
    if secondary_ax:
        h2, l2 = secondary_ax.get_legend_handles_labels()
        handles.extend(h2)
        labels.extend(l2)
    ax.legend(handles, labels, loc="best")

    filename = f"{ticker}_{'_'.join(m for m, _ in prepared_series)}_{start_year}_{end_year}.png"
    output_path = PLOTS_DIR / filename
    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)

    return output_path


def parse_plot_arguments(args: Sequence[str]) -> Tuple[List[str], List[str], List[int]]:
    """Atskiria ticker'ius, metrikas ir metus iš pateikto sąrašo."""

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


def prompt_plot_flow() -> None:
    """Surinka argumentus grafiko generavimui, primindama apie sąrašus."""

    print("\n📈 Galimi grafiko rodikliai:")
    print(", ".join(sarasai.PLOT_METRIC_CHOICES))
    user_input = input(
        "\nĮveskite ticker'ius, metrikas ir (nebūtinai) metus, pvz. AAPL,MSFT,REVENUE,NET_INCOME,2015,2024: "
    )

    if not user_input.strip():
        print("Naudojamas pavyzdinis argumentų sąrašas.")
        args = sarasai.ARGUMENTU_PAVYZDYS
    else:
        args = [item.strip() for item in user_input.split(",") if item.strip()]

    tickers, metrics, years = parse_plot_arguments(args)

    if not metrics:
        print("❌ Nenurodėte nė vieno rodiklio.")
        return

    if len(metrics) > 2:
        print("⚠️ Naudosime tik pirmus du rodiklius grafike.")
        metrics = metrics[:2]

    if not tickers:
        print("❌ Nenurodėte nė vieno ticker.")
        return

    if len(years) == 0:
        years = [2000, date.today().year]
    elif len(years) == 1:
        years.append(date.today().year)

    start_year, end_year = min(years), max(years)

    for ticker in tickers[:2]:
        print(f"\n🎯 Generuojamas grafikas {ticker}...")
        datasets = fetch_company_datasets(ticker)
        output = plot_metrics_for_ticker(ticker, metrics, (start_year, end_year), datasets)
        if output:
            print(f"💾 Grafikas išsaugotas: {output}")
        else:
            print("❌ Nepavyko suformuoti grafiko.")


def show_raw_statements(ticker: str) -> None:
    """Atspausdina pagrindinius finansinius DataFrame'us."""

    datasets = fetch_company_datasets(ticker)
    income = statement_to_dataframe(datasets.get("income_stmt"))
    balance = statement_to_dataframe(datasets.get("balance_sheet"))
    cash = statement_to_dataframe(datasets.get("cash_flow"))

    print(f"\n{'=' * 70}\n💵 PAJAMŲ ATASKAITA\n{'=' * 70}")
    print(income.head() if not income.empty else "Nėra duomenų")

    print(f"\n{'=' * 70}\n💼 BALANSAS\n{'=' * 70}")
    print(balance.head() if not balance.empty else "Nėra duomenų")

    print(f"\n{'=' * 70}\n💸 PINIGŲ SRAUTAI\n{'=' * 70}")
    print(cash.head() if not cash.empty else "Nėra duomenų")


def summary_flow(to_excel: bool = False) -> None:
    """Apdoroja vartotojo įvestį su santrauka ir (jei reikia) eksportu."""

    ticker = input("\nĮveskite ticker (pvz. AAPL): ").strip().upper()
    if not ticker:
        print("❌ Ticker privalomas.")
        return

    summary_df, _, _ = create_summary_dataframe(ticker)

    print(f"\n{'=' * 70}\n📊 {ticker} SANTRAUKA\n{'=' * 70}")
    print(summary_df.to_string(index=False))

    if to_excel:
        filename = input("Failo pavadinimas (palikite tuščią numatytajam): ").strip()
        path = export_summary_to_excel(summary_df, ticker, filename or None)
        print(f"\n💾 Suvestinė išsaugota faile: {path}")


def main() -> None:
    print("\n" + "=" * 70)
    print("📊 ĮMONIŲ ANALIZĖ SU YFINANCE")
    print("=" * 70)
    print("✅ Duomenys konvertuojami į pandas DataFrame")
    print("✅ Įmanoma eksportuoti į Excel")
    print("✅ Galima generuoti grafikus")

    menu = (
        "\n1 - Įmonės santrauka",
        "2 - Santrauką eksportuoti į Excel",
        "3 - Suformuoti grafikus",
        "4 - Peržiūrėti žalius finansinius duomenis",
        "0 - Išeiti",
    )

    while True:
        print("\n" + "=" * 70)
        print("MENIU")
        print("=" * 70)
        for line in menu:
            print(line)

        choice = input("\nPasirinkimas: ").strip()

        if choice == "0":
            print("\n👋 Iki!")
            break
        if choice == "1":
            summary_flow(to_excel=False)
        elif choice == "2":
            summary_flow(to_excel=True)
        elif choice == "3":
            prompt_plot_flow()
        elif choice == "4":
            ticker = input("\nĮveskite ticker, kurio ataskaitas rodyti: ").strip().upper()
            if ticker:
                show_raw_statements(ticker)
            else:
                print("❌ Ticker privalomas.")
        else:
            print("❌ Neteisingas pasirinkimas.")


if __name__ == "__main__":
    main()
