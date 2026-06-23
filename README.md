# Indian Mutual Fund Analytics

Look up an Indian mutual fund by name or scheme code and get its **3-Year and 5-Year return (CAGR), annualized standard deviation, and Sharpe ratio** — computed from real NAV history via [mfapi.in](https://www.mfapi.in/), a free, open mutual fund data API for India.

## What it does

1. **Lookup** — pass a fund name (e.g. `"parag parikh flexi cap fund"`) or a scheme code (e.g. `122639`). If multiple plans match a name (Direct/Regular, Growth/IDCW), you'll be prompted to pick one.
2. **Fetch NAV history** — pulls the full daily NAV series for that scheme from `api.mfapi.in`.
3. **Compute metrics**, anchored to a fixed base date convention:
   - **Base date** = the last day of the *previous* month relative to today (e.g. if today is 23-Jun-2026, base date = 31-May-2026). This avoids the return numbers shifting every single day as "today" moves, which is the standard convention used in fund fact sheets.
   - **3Y / 5Y Return** — CAGR between the NAV on (base date − N years) and the NAV on the base date. Since NAVs aren't published on weekends/holidays, the nearest available date *on or before* each target date is used.
   - **Standard Deviation** — annualized volatility of daily NAV returns, computed only within the same N-year window used for the return calculation, scaled by √252 trading days.
   - **Sharpe Ratio** — `(annualized return − risk-free rate) / annualized std dev`. Risk-free rate defaults to 6.5% (a rough India risk-free proxy) and is configurable.

## Files

- `mf_analytics.ipynb` — single-cell notebook version (Colab-friendly)
- `mf_analytics_consolidated.py` — equivalent plain Python script

## Usage

Edit the `FUND_QUERY` variable near the top of the script/notebook:

```python
FUND_QUERY = "parag parikh flexi cap fund"  # or a scheme code, e.g. 122639
```

Then run it:

```bash
pip install requests
python mf_analytics_consolidated.py
```

Or open `mf_analytics.ipynb` in Jupyter / Google Colab and run the single code cell.

### Example output

```
============================================================
Parag Parikh Flexi Cap Fund - Direct Plan - Growth
Fund House : PPFAS Mutual Fund
Scheme Code: 122639
Base date (target)    : 31-May-2026
Base date (actual NAV): 29-May-2026  (NAV = 90.0589)
Risk-free rate used   : 6.5%
------------------------------------------------------------
3Y Return (CAGR) : 15.6%   [31-May-2023 -> 29-May-2026]
3Y Std Dev (ann.) : 9.82%
3Y Sharpe Ratio   : 0.93

5Y Return (CAGR) : 15.47%   [31-May-2021 -> 29-May-2026]
5Y Std Dev (ann.) : 11.6%
5Y Sharpe Ratio   : 0.77
============================================================
```

## Notes & limitations

- If a fund's NAV history doesn't go back far enough for the 3Y or 5Y window, that metric is reported as `N/A` with an explanation rather than a wrong number.
- Returns are computed from fund NAV directly. Since growth-plan NAVs already reflect reinvested dividends, this is inherently a **total-return** calculation for the fund itself — no separate adjustment needed there.
- This repo does **not** include benchmark (index) comparison. Index TRI (Total Return Index) data for NSE/BSE benchmarks isn't available through any free, reliable API at the time of writing — NSE and BSE only publish it via manual CSV downloads from their own sites (`niftyindices.com`, `bseindia.com`), and Yahoo Finance / other free sources only carry PR (price-return) indices, which exclude dividends and aren't a valid like-for-like comparison against fund NAV returns.
- `mfapi.in` is community-run and unauthenticated — be a good citizen and don't hammer it with excessive requests.

## License

MIT — data sourced from [mfapi.in](https://www.mfapi.in/), used under their terms as a free public API.
