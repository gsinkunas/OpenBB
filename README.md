# OpenBB Yahoo Finance rodiklių pavyzdžiai

Trumpas skriptas, parodantis kaip vienu užklausos kvietimu pasiimti konkrečius finansinius rodiklius iš **Yahoo Finance** tiekėjo per OpenBB.

## Paruošimas

1. Aplinka ir priklausomybės:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install openbb
    ```

Yahoo Finance tiekėjui papildomo API rakto nereikia.

## Naudojimas

Pagrindinės funkcijos turi aiškius pavadinimus ir grąžina žodynus su `.get` paimtais laukais:

```python
from company_analysis import (
    kainos_duomenys,
    finansiniai_santykiai,
    gauti_santyki,
    finansines_ataskaitos,
    pajamu_ataskaita,
    pinigu_srautai,
)

print(kainos_duomenys("AAPL"))
print(finansiniai_santykiai("AAPL"))
print("ROE:", gauti_santyki("AAPL", "roe"))
print(finansines_ataskaitos("AAPL"))
print(pajamu_ataskaita("AAPL"))
print(pinigu_srautai("AAPL"))
```

Paleidę `python company_analysis.py` būsite paprašyti įvesti `ticker`, o skriptas paeiliui atspausdins kainą, santykius ir pagrindines balansų bei ataskaitų eilutes.
