import sys
import requests
import pandas as pd
import numpy as np
from datetime import date, timedelta

# Fallback RFR if a month is outside the lookup table
_CURRENT_RFR = 0.053  # 5.3% — update when RBI changes rates

# Monthly RBI repo rate lookup (YYYY-MM → annual rate).
# 91-day T-bill trades ~5-15 bps below repo; repo is the standard RFR proxy used by VR/Morningstar.
_REPO_RATE_BY_MONTH = {
    # 2019
    "2019-01": 0.0635, "2019-02": 0.0635, "2019-03": 0.0625,
    "2019-04": 0.0600, "2019-05": 0.0600, "2019-06": 0.0575,
    "2019-07": 0.0575, "2019-08": 0.0540, "2019-09": 0.0540,
    "2019-10": 0.0515, "2019-11": 0.0515, "2019-12": 0.0515,
    # 2020
    "2020-01": 0.0515, "2020-02": 0.0515, "2020-03": 0.0440,
    "2020-04": 0.0440, "2020-05": 0.0400, "2020-06": 0.0400,
    "2020-07": 0.0400, "2020-08": 0.0400, "2020-09": 0.0400,
    "2020-10": 0.0400, "2020-11": 0.0400, "2020-12": 0.0400,
    # 2021
    "2021-01": 0.0400, "2021-02": 0.0400, "2021-03": 0.0400,
    "2021-04": 0.0400, "2021-05": 0.0400, "2021-06": 0.0400,
    "2021-07": 0.0400, "2021-08": 0.0400, "2021-09": 0.0400,
    "2021-10": 0.0400, "2021-11": 0.0400, "2021-12": 0.0400,
    # 2022
    "2022-01": 0.0400, "2022-02": 0.0400, "2022-03": 0.0400,
    "2022-04": 0.0400, "2022-05": 0.0440, "2022-06": 0.0490,
    "2022-07": 0.0490, "2022-08": 0.0540, "2022-09": 0.0590,
    "2022-10": 0.0590, "2022-11": 0.0590, "2022-12": 0.0625,
    # 2023
    "2023-01": 0.0625, "2023-02": 0.0650, "2023-03": 0.0650,
    "2023-04": 0.0650, "2023-05": 0.0650, "2023-06": 0.0650,
    "2023-07": 0.0650, "2023-08": 0.0650, "2023-09": 0.0650,
    "2023-10": 0.0650, "2023-11": 0.0650, "2023-12": 0.0650,
    # 2024
    "2024-01": 0.0650, "2024-02": 0.0650, "2024-03": 0.0650,
    "2024-04": 0.0650, "2024-05": 0.0650, "2024-06": 0.0650,
    "2024-07": 0.0650, "2024-08": 0.0650, "2024-09": 0.0650,
    "2024-10": 0.0650, "2024-11": 0.0650, "2024-12": 0.0650,
    # 2025 (cuts begin)
    "2025-01": 0.0650, "2025-02": 0.0625, "2025-03": 0.0625,
    "2025-04": 0.0600, "2025-05": 0.0600, "2025-06": 0.0575,
    "2025-07": 0.0575, "2025-08": 0.0575,
}


def _monthly_rfr(ym: str) -> float:
    """Return the RFR for a given YYYY-MM string, falling back to current rate."""
    return _REPO_RATE_BY_MONTH.get(ym, _CURRENT_RFR)


def period_average_rfr(start: date, end: date) -> float:
    """Average monthly RFR across all months in [start, end]."""
    months = []
    cur = date(start.year, start.month, 1)
    end_ym = date(end.year, end.month, 1)
    while cur <= end_ym:
        months.append(_monthly_rfr(cur.strftime("%Y-%m")))
        # advance one month
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)
    return float(np.mean(months))


def get_last_business_day_of_prev_month() -> date:
    today = date.today()
    last = today.replace(day=1) - timedelta(days=1)
    while last.weekday() >= 5:
        last -= timedelta(days=1)
    return last


def search_fund(query: str):
    resp = requests.get(f"https://api.mfapi.in/mf/search?q={query}", timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_nav_data(scheme_code: int):
    resp = requests.get(f"https://api.mfapi.in/mf/{scheme_code}", timeout=10)
    resp.raise_for_status()
    payload = resp.json()
    df = pd.DataFrame(payload["data"])
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna(subset=["nav"]).sort_values("date").reset_index(drop=True)
    return df, payload["meta"]


def to_monthly_nav(df: pd.DataFrame) -> pd.DataFrame:
    """Last available NAV per calendar month (end-of-month convention)."""
    df = df.copy()
    df["ym"] = df["date"].dt.to_period("M")
    return df.groupby("ym").last().reset_index()


def nearest_nav(df: pd.DataFrame, target: date):
    subset = df[df["date"] <= pd.Timestamp(target)]
    return float(subset.iloc[-1]["nav"]) if not subset.empty else None


def cagr(nav_start, nav_end, years: float):
    if nav_start is None or nav_end is None:
        return None
    return (nav_end / nav_start) ** (1 / years) - 1


def annualised_volatility_monthly(monthly_df: pd.DataFrame, start: date, end: date):
    """Annualised volatility using monthly returns × √12 (VR / Morningstar standard)."""
    mask = (monthly_df["date"] >= pd.Timestamp(start)) & (monthly_df["date"] <= pd.Timestamp(end))
    window = monthly_df[mask]["nav"].pct_change().dropna()
    return float(window.std() * np.sqrt(12)) if len(window) >= 2 else None


def sharpe(ret, vol, rfr: float):
    if ret is None or vol is None or vol == 0:
        return None
    return (ret - rfr) / vol


def fmt_pct(val):
    return f"{val * 100:.2f}%" if val is not None else "N/A"


def fmt_num(val):
    return f"{val:.4f}" if val is not None else "N/A"


def analyze(query: str):
    # Resolve to scheme code
    try:
        scheme_code = int(query)
    except ValueError:
        results = search_fund(query)
        if not results:
            print(f"No funds found for '{query}'.")
            return
        scheme_code = results[0]["schemeCode"]
        print(f"Matched: {results[0]['schemeName']}  (code {scheme_code})")
        if len(results) > 1:
            print(f"  (+ {len(results) - 1} other match(es) — using top result)")

    df, meta = get_nav_data(scheme_code)
    monthly_df = to_monthly_nav(df)

    print(f"\nFund      : {meta.get('scheme_name', 'N/A')}")
    print(f"Category  : {meta.get('scheme_category', 'N/A')}")
    print(f"Fund House: {meta.get('fund_house', 'N/A')}")

    base = get_last_business_day_of_prev_month()
    nav_base = nearest_nav(df, base)
    if nav_base is None:
        print("Could not retrieve base NAV.")
        return

    print(f"\nBase date : {base.strftime('%d %b %Y')}  |  Base NAV: {nav_base:.4f}")
    print(f"Methodology: Monthly NAV returns, Vol = std × √12, RFR = period-avg RBI repo rate")

    results_table = {}
    for years in (3, 5):
        try:
            start = base.replace(year=base.year - years)
        except ValueError:
            start = base - timedelta(days=365 * years)

        rfr = period_average_rfr(start, base)
        nav_start = nearest_nav(df, start)
        r = cagr(nav_start, nav_base, years)
        v = annualised_volatility_monthly(monthly_df, start, base)
        s = sharpe(r, v, rfr)
        results_table[years] = (r, v, s, rfr)

    print(f"\n{'Metric':<26} {'3-Year':>12} {'5-Year':>12}")
    print("-" * 52)
    print(f"{'CAGR':<26} {fmt_pct(results_table[3][0]):>12} {fmt_pct(results_table[5][0]):>12}")
    print(f"{'Volatility (Ann.)':<26} {fmt_pct(results_table[3][1]):>12} {fmt_pct(results_table[5][1]):>12}")
    print(f"{'Sharpe Ratio':<26} {fmt_num(results_table[3][2]):>12} {fmt_num(results_table[5][2]):>12}")
    print(f"{'Avg RFR used':<26} {fmt_pct(results_table[3][3]):>12} {fmt_pct(results_table[5][3]):>12}")


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Enter fund name or scheme code: ").strip()
    analyze(query)
