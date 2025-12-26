from fastapi import FastAPI, HTTPException
import yfinance as yf
import math
import numpy as np

app = FastAPI(title="Auto Growth Suggestion API")


# -----------------------------
# SECTOR LIMITS
# -----------------------------
SECTOR_LIMITS = {
    "ENERGY": {"min": 4, "max": 10},                    
    "IT": {"min": 6, "max": 15},
    "BANKING": {"min": 7, "max": 14},
    "FMCG": {"min": 5, "max": 12},
    "DEFAULT": {"min": 5, "max": 12}
}


# -----------------------------
# SAFE FLOAT
# -----------------------------
def safe_float(x):
    if x is None:
        return 0.0
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return 0.0
    return float(x)


# -----------------------------
# CAGR
# -----------------------------
def calculate_cagr(start, end, years):
    start = safe_float(start)
    end = safe_float(end)

    if start <= 0 or end <= 0 or years <= 0:
        return 0.0

    return ((end / start) ** (1 / years) - 1) * 100


# -----------------------------
# FETCH FINANCIALS
# -----------------------------
def fetch_financials(ticker: str):
    stock = yf.Ticker(ticker)
    fin = stock.financials

    if fin is None or fin.empty:
        raise ValueError("Financial data not available")

    # Revenue
    if "Total Revenue" not in fin.index:
        raise ValueError("Revenue missing")

    revenue = fin.loc["Total Revenue"]

    # PAT
    if "Net Income" in fin.index:
        pat = fin.loc["Net Income"]
    else:
        raise ValueError("PAT missing")

    # EBITDA safe logic
    if "Ebitda" in fin.index:
        ebitda = fin.loc["Ebitda"]
    elif "EBIT" in fin.index:
        ebitda = fin.loc["EBIT"]
    elif "Operating Income" in fin.index:
        ebitda = fin.loc["Operating Income"]
    else:
        ebitda = revenue * 0.15  # fallback

    # Oldest → Latest & clean
    revenue = [safe_float(x) for x in revenue.values[::-1]]
    ebitda = [safe_float(x) for x in ebitda.values[::-1]]
    pat = [safe_float(x) for x in pat.values[::-1]]

    return revenue, ebitda, pat


# -----------------------------
# GROWTH ENGINE
# -----------------------------
def suggest_growth(values, sector):
    values = [safe_float(v) for v in values if v > 0]

    if len(values) < 4:
        return 0.0, 0.0, 0.0

    years = len(values) - 1
    cagr = calculate_cagr(values[0], values[-1], years)

    recent = []
    for i in range(-3, -1):
        if values[i] > 0:
            g = ((values[i + 1] / values[i]) - 1) * 100
            recent.append(g)

    recent_avg = sum(recent) / len(recent) if recent else 0.0

    raw = 0.6 * cagr + 0.4 * recent_avg
    limits = SECTOR_LIMITS.get(sector.upper(), SECTOR_LIMITS["DEFAULT"])

    final = min(max(raw, limits["min"]), limits["max"])

    return round(final, 2), round(cagr, 2), round(recent_avg, 2)


# -----------------------------
# API ENDPOINT
# -----------------------------
@app.get("/suggest_growth")
def growth_api(ticker: str, sector: str = "DEFAULT"):
    try:
        revenue, ebitda, pat = fetch_financials(ticker)

        rev_g, rev_cagr, rev_recent = suggest_growth(revenue, sector)
        ebitda_g, ebitda_cagr, ebitda_recent = suggest_growth(ebitda, sector)
        pat_g, pat_cagr, pat_recent = suggest_growth(pat, sector)

        return {
            "company": ticker,
            "sector": sector,
            "suggested_growth_%": {
                "Revenue": rev_g,
                "EBITDA": ebitda_g,
                "PAT": pat_g
            },
            "analysis": {
                "Revenue": {"CAGR_%": rev_cagr, "Recent_%": rev_recent},
                "EBITDA": {"CAGR_%": ebitda_cagr, "Recent_%": ebitda_recent},
                "PAT": {"CAGR_%": pat_cagr, "Recent_%": pat_recent}
            },
            "confidence": "MEDIUM",
            "note": "Auto-calculated from cleaned historical financials"
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/")
def home():
    return {"status": "API running successfully"}
