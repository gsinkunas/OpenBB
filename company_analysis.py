"""Trumpas pavyzdys, kaip aiškiai pasiimti atskirus rodiklius iš Yahoo Finance."""

from __future__ import annotations

from typing import Dict, Optional

from openbb import obb


# ---------------------------------------------------------------------------
# Pagalbininkai
# ---------------------------------------------------------------------------


def _paskutinis(result_obj) -> Dict:
    return result_obj.results[0].model_dump()


# ---------------------------------------------------------------------------
# Pagrindinės funkcijos (paprastas, vieno tikslo stilius)
# ---------------------------------------------------------------------------


def kainos_duomenys(symbol: str) -> Dict:
    """Gražina dabartinę kainą ir kapitalizaciją."""

    quote = _paskutinis(obb.equity.price.quote(symbol=symbol, provider="yahoo"))
    return {
        "kaina": quote.get("last_price"),
        "kapitalizacija": quote.get("market_cap"),
    }


def finansiniai_santykiai(symbol: str) -> Dict:
    """Gražina svarbiausius finansinius santykius (vieno kvietimo užtenka)."""

    ratios = _paskutinis(
        obb.equity.fundamental.ratios(symbol=symbol, provider="yahoo", limit=1)
    )
    return {
        "pe": ratios.get("price_earnings_ratio"),
        "current_ratio": ratios.get("current_ratio"),
        "debt_to_equity": ratios.get("debt_equity_ratio"),
        "roe": ratios.get("return_on_equity"),
        "roa": ratios.get("return_on_assets"),
        "gross_margin": ratios.get("gross_profit_margin"),
        "net_margin": ratios.get("net_profit_margin"),
    }


def gauti_santyki(symbol: str, pavadinimas: str) -> Optional[float]:
    """Leidžia pasiimti konkretų santykį pagal pavadinimą ar sinonimą."""

    aliasai = {
        "pe": "pe",
        "peratio": "pe",
        "pricetoearnings": "pe",
        "current": "current_ratio",
        "currentratio": "current_ratio",
        "debtequity": "debt_to_equity",
        "debttoequity": "debt_to_equity",
        "roe": "roe",
        "roa": "roa",
        "grossmargin": "gross_margin",
        "netmargin": "net_margin",
    }

    raktas = "".join(ch for ch in pavadinimas.lower() if ch.isalnum())
    normalizuotas = aliasai.get(raktas)
    if not normalizuotas:
        raise KeyError(
            f"Nežinomas rodiklis '{pavadinimas}'. Galimi: {', '.join(sorted(aliasai))}."
        )

    return finansiniai_santykiai(symbol)[normalizuotas]


def finansines_ataskaitos(symbol: str, period: str = "annual") -> Dict:
    """Paima balansą paprastu stiliumi, akcentuojant .get naudojimą."""

    balansas = _paskutinis(
        obb.equity.fundamental.balance(
            symbol=symbol, provider="yahoo", period=period, limit=1
        )
    )
    return {
        "turtas": balansas.get("total_assets"),
        "skolos": balansas.get("total_debt"),
        "nuosavas_kapitalas": balansas.get("total_equity"),
        "grynieji": balansas.get("cash_and_cash_equivalents"),
    }


def pajamu_ataskaita(symbol: str, period: str = "annual") -> Dict:
    """Gražina naujausias pajamų ataskaitos eilutes."""

    income = _paskutinis(
        obb.equity.fundamental.income(
            symbol=symbol, provider="yahoo", period=period, limit=1
        )
    )
    return {
        "pajamos": income.get("revenue"),
        "ebitda": income.get("ebitda"),
        "grynasis_pelnas": income.get("net_income"),
        "eps": income.get("eps"),
    }


def pinigu_srautai(symbol: str, period: str = "annual") -> Dict:
    """Gražina pinigų srautų pagrindus."""

    cash = _paskutinis(
        obb.equity.fundamental.cash(
            symbol=symbol, provider="yahoo", period=period, limit=1
        )
    )
    return {
        "operacinis_cf": cash.get("operating_cash_flow"),
        "laisvas_cf": cash.get("free_cash_flow"),
        "capex": cash.get("capital_expenditure"),
    }


# ---------------------------------------------------------------------------
# Paprastas demonstracinis paleidimas
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    ticker = input("Įveskite ticker (pvz. AAPL): ").strip().upper()

    print("\nKAINA")
    print(kainos_duomenys(ticker))

    print("\nSANTYKIAI")
    print(finansiniai_santykiai(ticker))
    print("PE tiksliai:", gauti_santyki(ticker, "pe"))

    print("\nBALANSAS")
    print(finansines_ataskaitos(ticker))

    print("\nPAJAMOS")
    print(pajamu_ataskaita(ticker))

    print("\nPINIGŲ SRAUTAI")
    print(pinigu_srautai(ticker))
