"""Refresh data/fundamentals.csv from Yahoo Finance (yfinance, unofficial).

Columns: ticker, price, mcap_cr, pe, eps, opm, sales_growth_3y, asof
  opm              = latest annual operating income / total revenue x 100
  sales_growth_3y  = 3-year CAGR of annual total revenue, in % (needs 4 annual figures)
Values that cannot be fetched keep their previous value, so one bad day never blanks the sheet.
"""
import csv, sys, time, datetime, os
import yfinance as yf

OUT = "data/fundamentals.csv"
ETFS = {"GOLDBEES", "EBBETF0430", "ALPHA"}
FIELDS = ["ticker", "price", "mcap_cr", "pe", "eps", "opm", "sales_growth_3y", "asof"]


def num(x):
    try:
        x = float(x)
        return None if x != x else x
    except (TypeError, ValueError):
        return None


def fetch(sym):
    t = yf.Ticker(sym + ".NS")
    out = {}
    try:
        out["price"] = num(t.fast_info.get("last_price"))
    except Exception:
        out["price"] = None
    if sym in ETFS:
        return out
    try:
        info = t.info or {}
        if out.get("price") is None:
            out["price"] = num(info.get("currentPrice") or info.get("regularMarketPrice"))
        mc = num(info.get("marketCap"))
        out["mcap_cr"] = mc / 1e7 if mc else None
        out["pe"] = num(info.get("trailingPE"))
        out["eps"] = num(info.get("trailingEps"))
    except Exception:
        pass
    try:
        fin = t.financials
        rev = fin.loc["Total Revenue"].dropna()
        op = fin.loc["Operating Income"].dropna()
        out["opm"] = float(op.iloc[0] / rev.iloc[0] * 100) if len(op) and len(rev) and rev.iloc[0] else None
        out["sales_growth_3y"] = float(((rev.iloc[0] / rev.iloc[3]) ** (1 / 3) - 1) * 100) if len(rev) >= 4 and rev.iloc[3] > 0 and rev.iloc[0] > 0 else None
    except Exception:
        pass
    return out


def main():
    tickers = [l.strip() for l in open("tickers.txt") if l.strip()]
    old = {}
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT)):
            old[r["ticker"]] = r
    today = datetime.date.today().isoformat()
    rows, failed = [], 0
    for sym in tickers:
        new = {}
        for attempt in range(2):
            new = fetch(sym)
            if any(v is not None for v in new.values()):
                break
            time.sleep(2)
        if not any(v is not None for v in new.values()):
            failed += 1
        row = {"ticker": sym}
        prev = old.get(sym, {})
        for k in FIELDS[1:7]:
            v = new.get(k)
            row[k] = ("%.4f" % v) if v is not None else prev.get(k, "")
        row["asof"] = today if any(new.get(k) is not None for k in FIELDS[1:7]) else prev.get("asof", "")
        rows.append(row)
        time.sleep(0.4)
    if failed > 0.3 * len(tickers):
        sys.exit("Too many failures (%d of %d): keeping the previous file." % (failed, len(tickers)))
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print("updated %d tickers, %d failed" % (len(rows), failed))


if __name__ == "__main__":
    main()
