from openbb import obb
import pandas as pd


def gauti_imones_duomenis(ticker):
    """
    Gauna visus svarbiausius įmonės duomenis ir grąžina kaip pandas DataFrame
    """

    print(f"\nGaunami duomenys apie {ticker}")

    # === 1. KAINA IR RINKA ===
    quote = obb.equity.price.quote(symbol=ticker, provider="yfinance")
    quote_df = quote.to_dataframe()

    # === 2. BALANSAS ===
    balance = obb.equity.fundamental.balance(symbol=ticker, provider="yfinance", period="annual", limit=1)
    balance_df = balance.to_dataframe()

    # === 3. PAJAMŲ ATASKAITA ===
    income = obb.equity.fundamental.income(symbol=ticker, provider="yfinance", period="annual", limit=2)
    income_df = income.to_dataframe()

    # === 4. PINIGŲ SRAUTAI ===
    cashflow = obb.equity.fundamental.cash(symbol=ticker, provider="yfinance", period="annual", limit=1)
    cashflow_df = cashflow.to_dataframe()

    print("Duomenys gauti!")

    return {
        'kaina': quote_df,
        'balansas': balance_df,
        'pajamos': income_df,
        'cf': cashflow_df
    }


def sukurti_santrauka(ticker):
    """
    Sukuria vieną DataFrame su svarbiausiais rodikliais
    """

    duomenys = gauti_imones_duomenis(ticker)

    # Ištraukiame duomenis
    kaina_df = duomenys['kaina']
    balance_df = duomenys['balansas']
    income_df = duomenys['pajamos']
    cf_df = duomenys['cf']

    # Imame naujausius duomenis - SAUGIAI
    dabartine_kaina = kaina_df['last_price'].iloc[0] if 'last_price' in kaina_df.columns else None
    market_cap = kaina_df['market_cap'].iloc[0] if 'market_cap' in kaina_df.columns else None

    # Jei nėra market_cap, bandome apskaičiuoti
    if market_cap is None:
        print("Market cap nerastas, bandome apskaičiuoti")
        # market_cap = kaina * akcijų skaičius (jei turime)

    # Balansas
    turtas = balance_df['total_assets'].iloc[0] if 'total_assets' in balance_df.columns else 0
    skolos = balance_df['total_debt'].iloc[0] if 'total_debt' in balance_df.columns else 0
    nuosavas_kapitalas = balance_df['total_equity'].iloc[0] if 'total_equity' in balance_df.columns else 0
    grynieji = balance_df['cash_and_cash_equivalents'].iloc[
        0] if 'cash_and_cash_equivalents' in balance_df.columns else 0
    trumpalaikis_turtas = balance_df['total_current_assets'].iloc[
        0] if 'total_current_assets' in balance_df.columns else 0
    trumpalaikes_skolos = balance_df['total_current_liabilities'].iloc[
        0] if 'total_current_liabilities' in balance_df.columns else 0

    # Pajamos (dabartinės ir praėjusių metų)
    pajamos_dabar = income_df['revenue'].iloc[0] if 'revenue' in income_df.columns else 0
    pajamos_praeita = income_df['revenue'].iloc[1] if len(income_df) > 1 and 'revenue' in income_df.columns else 0
    ebitda = income_df['ebitda'].iloc[0] if 'ebitda' in income_df.columns else 0
    grynasis_pelnas = income_df['net_income'].iloc[0] if 'net_income' in income_df.columns else 0
    bendrasis_pelnas = income_df['gross_profit'].iloc[0] if 'gross_profit' in income_df.columns else 0
    eps = income_df['eps'].iloc[0] if 'eps' in income_df.columns else 0

    # Cash Flow
    operacinis_cf = cf_df['operating_cash_flow'].iloc[0] if 'operating_cash_flow' in cf_df.columns else 0
    laisvas_cf = cf_df['free_cash_flow'].iloc[0] if 'free_cash_flow' in cf_df.columns else 0

    # === SKAIČIUOJAME SANTYKIUS ===
    pe_ratio = dabartine_kaina / eps if eps else None
    revenue_growth = ((pajamos_dabar / pajamos_praeita) - 1) * 100 if pajamos_praeita else None
    current_ratio = trumpalaikis_turtas / trumpalaikes_skolos if trumpalaikes_skolos else None
    debt_to_equity = skolos / nuosavas_kapitalas if nuosavas_kapitalas else None
    roe = (grynasis_pelnas / nuosavas_kapitalas) * 100 if nuosavas_kapitalas else None
    roa = (grynasis_pelnas / turtas) * 100 if turtas else None
    gross_margin = (bendrasis_pelnas / pajamos_dabar) * 100 if pajamos_dabar else None
    net_margin = (grynasis_pelnas / pajamos_dabar) * 100 if pajamos_dabar else None
    debt_to_ebitda = skolos / ebitda if ebitda else None

    # === KURIAME DATAFRAME ===
    santrauka = pd.DataFrame({
        'Rodiklis': [
            '=== KAINA ===',
            'Dabartinė kaina ($)',
            'Kapitalizacija ($)',
            '',
            '=== AUGIMAS ===',
            'Pajamos ($)',
            'Revenue Growth (%)',
            'Grynasis pelnas ($)',
            'EBITDA ($)',
            'EPS ($)',
            '',
            '=== PELNINGUMAS ===',
            'ROE (%)',
            'ROA (%)',
            'Gross Margin (%)',
            'Net Margin (%)',
            '',
            '=== LIKVIDUMAS ===',
            'Current Ratio',
            'Grynieji pinigai ($)',
            '',
            '=== SKOLA ===',
            'Debt to Equity',
            'Debt to EBITDA',
            'Viso skolos ($)',
            '',
            '=== PINIGŲ SRAUTAI ===',
            'Operacinis CF ($)',
            'Laisvas CF ($)',
            '',
            '=== BALANSAS ===',
            'Turtas ($)',
            'Nuosavas kapitalas ($)'
        ],
        'Reikšmė': [
            '',
            f'{dabartine_kaina:.2f}' if dabartine_kaina else 'N/A',
            f'{market_cap:,.0f}' if market_cap else 'N/A',
            '',
            '',
            f'{pajamos_dabar:,.0f}' if pajamos_dabar else 'N/A',
            f'{revenue_growth:.2f}' if revenue_growth else 'N/A',
            f'{grynasis_pelnas:,.0f}' if grynasis_pelnas else 'N/A',
            f'{ebitda:,.0f}' if ebitda else 'N/A',
            f'{eps:.2f}' if eps else 'N/A',
            '',
            '',
            f'{roe:.2f}' if roe else 'N/A',
            f'{roa:.2f}' if roa else 'N/A',
            f'{gross_margin:.2f}' if gross_margin else 'N/A',
            f'{net_margin:.2f}' if net_margin else 'N/A',
            '',
            '',
            f'{current_ratio:.2f}' if current_ratio else 'N/A',
            f'{grynieji:,.0f}' if grynieji else 'N/A',
            '',
            '',
            f'{debt_to_equity:.2f}' if debt_to_equity else 'N/A',
            f'{debt_to_ebitda:.2f}' if debt_to_ebitda else 'N/A',
            f'{skolos:,.0f}' if skolos else 'N/A',
            '',
            '',
            f'{operacinis_cf:,.0f}' if operacinis_cf else 'N/A',
            f'{laisvas_cf:,.0f}' if laisvas_cf else 'N/A',
            '',
            '',
            f'{turtas:,.0f}' if turtas else 'N/A',
            f'{nuosavas_kapitalas:,.0f}' if nuosavas_kapitalas else 'N/A'
        ]
    })

    return santrauka


def palyginti_imones(tickers):
    """
    Palygina kelias įmones ir grąžina DataFrame
    """

    palyginimo_duomenys = []

    for ticker in tickers:
        try:
            print(f"\n📊 Analizuojama: {ticker}")

            duomenys = gauti_imones_duomenis(ticker)

            kaina_df = duomenys['kaina']
            balance_df = duomenys['balansas']
            income_df = duomenys['pajamos']

            # Ištraukiame reikšmes SAUGIAI
            dabartine_kaina = kaina_df['last_price'].iloc[0] if 'last_price' in kaina_df.columns else None
            market_cap = kaina_df['market_cap'].iloc[0] if 'market_cap' in kaina_df.columns else None

            turtas = balance_df['total_assets'].iloc[0] if 'total_assets' in balance_df.columns else 0
            skolos = balance_df['total_debt'].iloc[0] if 'total_debt' in balance_df.columns else 0
            nuosavas_kapitalas = balance_df['total_equity'].iloc[0] if 'total_equity' in balance_df.columns else 0

            pajamos = income_df['revenue'].iloc[0] if 'revenue' in income_df.columns else 0
            grynasis_pelnas = income_df['net_income'].iloc[0] if 'net_income' in income_df.columns else 0
            eps = income_df['eps'].iloc[0] if 'eps' in income_df.columns else 0

            # Santykiai
            pe = dabartine_kaina / eps if eps else None
            roe = (grynasis_pelnas / nuosavas_kapitalas) * 100 if nuosavas_kapitalas else None
            debt_to_equity = skolos / nuosavas_kapitalas if nuosavas_kapitalas else None
            net_margin = (grynasis_pelnas / pajamos) * 100 if pajamos else None

            palyginimo_duomenys.append({
                'Ticker': ticker,
                'Kaina ($)': f'{dabartine_kaina:.2f}',
                'Market Cap ($)': f'{market_cap:,.0f}',
                'PE Ratio': f'{pe:.2f}' if pe else 'N/A',
                'ROE (%)': f'{roe:.2f}' if roe else 'N/A',
                'Debt/Equity': f'{debt_to_equity:.2f}' if debt_to_equity else 'N/A',
                'Net Margin (%)': f'{net_margin:.2f}' if net_margin else 'N/A',
                'Pajamos ($)': f'{pajamos:,.0f}',
                'Pelnas ($)': f'{grynasis_pelnas:,.0f}'
            })

        except Exception as e:
            print(f"❌ Klaida su {ticker}: {e}")

    return pd.DataFrame(palyginimo_duomenys)


def eksportuoti_i_excel(df, ticker, failas="imones_analize.xlsx"):
    """
    Eksportuoja DataFrame į Excel failą
    """
    df.to_excel(failas, index=False, sheet_name=ticker)
    print(f"\n💾 Duomenys išsaugoti į: {failas}")


# === PROGRAMA ===
if __name__ == "__main__":

    print("\n" + "=" * 70)
    print("📊 ĮMONIŲ ANALIZĖ SU PANDAS DATAFRAME")
    print("=" * 70)
    print("✅ Visi duomenys konvertuojami į pandas DataFrame")
    print("✅ Lengva eksportuoti į Excel")
    print("✅ Lengva analizuoti ir vizualizuoti")

    while True:
        print("\n" + "=" * 70)
        print("MENIU")
        print("=" * 70)
        print("1 - Analizuoti vieną įmonę (santrauka)")
        print("2 - Analizuoti vieną įmonę (visi DataFrame)")
        print("3 - Palyginti kelias įmones")
        print("4 - Eksportuoti į Excel")
        print("0 - Išeiti")

        choice = input("\nPasirinkimas: ").strip()

        if choice == "0":
            print("\n👋 Viso gero!")
            break

        elif choice == "1":
            ticker = input("\nĮveskite ticker (pvz. AAPL): ").strip().upper()
            santrauka_df = sukurti_santrauka(ticker)
            print(f"\n{'=' * 70}")
            print(f"📊 ĮMONĖS SANTRAUKA: {ticker}")
            print(f"{'=' * 70}\n")
            print(santrauka_df.to_string(index=False))

        elif choice == "2":
            ticker = input("\nĮveskite ticker (pvz. AAPL): ").strip().upper()
            duomenys = gauti_imones_duomenis(ticker)

            print(f"\n{'=' * 70}")
            print("💰 KAINA")
            print(f"{'=' * 70}")
            print(duomenys['kaina'])

            print(f"\n{'=' * 70}")
            print("💼 BALANSAS")
            print(f"{'=' * 70}")
            print(duomenys['balansas'])

            print(f"\n{'=' * 70}")
            print("💵 PAJAMOS")
            print(f"{'=' * 70}")
            print(duomenys['pajamos'])

            print(f"\n{'=' * 70}")
            print("💸 CASH FLOW")
            print(f"{'=' * 70}")
            print(duomenys['cf'])

        elif choice == "3":
            tickers_input = input("\nĮveskite ticker'ius (pvz. AAPL,MSFT,GOOGL): ").strip().upper()
            tickers = [t.strip() for t in tickers_input.split(",")]

            palyginimas_df = palyginti_imones(tickers)

            print(f"\n{'=' * 70}")
            print("📊 ĮMONIŲ PALYGINIMAS")
            print(f"{'=' * 70}\n")
            print(palyginimas_df.to_string(index=False))

        elif choice == "4":
            ticker = input("\nĮveskite ticker (pvz. AAPL): ").strip().upper()
            failas = input("Failo pavadinimas (pvz. apple.xlsx): ").strip()
            if not failas:
                failas = f"{ticker}_analize.xlsx"

            santrauka_df = sukurti_santrauka(ticker)
            eksportuoti_i_excel(santrauka_df, ticker, failas)

        else:
            print("❌ Neteisingas pasirinkimas!")
