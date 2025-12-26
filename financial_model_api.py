from fastapi import FastAPI
import math

app = FastAPI(title="Growth Suggestion API")


# -----------------------------
# SECTOR GROWTH CAPS (RISK CONTROL)
# -----------------------------
SECTOR_LIMITS = {
    "ENERGY": {"min": 4, "max": 10},
    "IT": {"min": 6, "max": 15},
    "BANKING": {"min": 7, "max": 14},
    "FMCG": {"min": 5, "max": 12},
    "DEFAULT": {"min": 5, "max": 12}
}


# -----------------------------
# CAGR CALCULATION
# -----------------------------
def calculate_cagr(start_value, end_value, years):
    if start_value <= 0 or end_value <= 0:
        return 0
    return (end_value / start_value) ** (1 / years) - 1


# -----------------------------
# CORE GROWTH LOGIC
# -----------------------------
def suggest_growth(historical_values, sector):
    """
    historical_values = list of values (oldest → latest)
    """

    years = len(historical_values) - 1

    # 1️⃣ Long-term CAGR
    cagr = calculate_cagr(
        historical_values[0],
        historical_values[-1],
        years
    ) * 100

    # 2️⃣ Recent 3-year average growth
    recent_growths = []
    for i in range(-3, -1):
        g = (historical_values[i + 1] / historical_values[i] - 1) * 100
        recent_growths.append(g)

    recent_avg = sum(recent_growths) / len(recent_growths)

    # 3️⃣ Weighted suggestion
    raw_suggestion = (0.6 * cagr) + (0.4 * recent_avg)

    # 4️⃣ Sector cap
    limits = SECTOR_LIMITS.get(sector.upper(), SECTOR_LIMITS["DEFAULT"])

    final_growth = min(max(raw_suggestion, limits["min"]), limits["max"])

    return round(final_growth, 1), round(cagr, 1), round(recent_avg, 1)


# -----------------------------
# API ENDPOINT
# -----------------------------
@app.post("/suggest_growth")
def growth_engine(
    company: str,
    sector: str,
    revenue_history: list[float],
    ebitda_history: list[float],
    pat_history: list[float]
):
    rev, rev_cagr, rev_recent = suggest_growth(revenue_history, sector)
    ebitda, ebitda_cagr, ebitda_recent = suggest_growth(ebitda_history, sector)
    pat, pat_cagr, pat_recent = suggest_growth(pat_history, sector)

    return {
        "company": company,
        "sector": sector,
        "suggested_growth_%": {
            "Revenue": rev,
            "EBITDA": ebitda,
            "PAT": pat
        },
        "analysis_basis": {
            "Revenue": {
                "5Y_CAGR_%": rev_cagr,
                "Recent_Trend_%": rev_recent
            },
            "EBITDA": {
                "5Y_CAGR_%": ebitda_cagr,
                "Recent_Trend_%": ebitda_recent
            },
            "PAT": {
                "5Y_CAGR_%": pat_cagr,
                "Recent_Trend_%": pat_recent
            }
        },
        "confidence": "MEDIUM",
        "note": "Suggested growth based on historical CAGR, recent trend & sector cap"
    }


@app.get("/")
def home():
    return {"message": "Growth Suggestion API running"}
