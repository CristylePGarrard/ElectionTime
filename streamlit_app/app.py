# app.py
"""
ElectionTime — Representative KPI dashboard (merged datasets)

Place this file at: streamlit_app/app.py
Data files expected at: streamlit_app/data/
  - combinedBills_2025.json
  - repKPIs_2025.json
  - reps_with_geo_data.geojson
"""

import streamlit as st
from pathlib import Path
import pandas as pd
import geopandas as gpd
import json
from shapely import wkt
from shapely.geometry import mapping, Polygon, MultiPolygon
import pydeck as pdk
from datetime import datetime
import altair as alt

# fuzzy matching: prefer rapidfuzz if available (faster, no C deps)
try:
    from rapidfuzz import process as rf_process
    fuzzy_extract = lambda q, choices, limit=8: rf_process.extract(q, choices, limit=limit)
    fuzzy_extract_one = lambda q, choices: rf_process.extractOne(q, choices)
except Exception:
    from fuzzywuzzy import process as fw_process
    fuzzy_extract = lambda q, choices, limit=8: fw_process.extract(q, choices, limit=limit)
    fuzzy_extract_one = lambda q, choices: fw_process.extractOne(q, choices)

st.set_page_config(page_title="ElectionTime — Rep KPI Dashboard", layout="wide")

# ---------------------
# Paths
# ---------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

BILLS_PATH = DATA_DIR / "combinedBills_2025.json"
REPKPIS_PATH = DATA_DIR / "repKPIs_2025.json"

# ---------------------
# Helpers
# ---------------------
def safe_read_json(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    try:
        return pd.read_json(path, orient="records")
    except Exception:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return pd.DataFrame(data)

def find_col(df, candidates):
    if df is None:
        return None
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand is None:
            continue
        if cand.lower() in cols_lower:
            return cols_lower[cand.lower()]
    for cand in candidates:
        for c in df.columns:
            if cand and cand.lower() in c.lower():
                return c
    return None

def make_rep_key(name):
    if pd.isna(name):
        return None
    s = str(name).strip()
    if s == "":
        return None
    s_clean = s.replace('.', '').strip()
    if ',' in s_clean:
        left, right = [p.strip() for p in s_clean.split(',', 1)]
        last = left
        initial = next((ch for ch in right if ch.isalpha()), "")
        return f"{last.lower().replace(' ','')}_{initial.lower()}"
    else:
        parts = s_clean.split()
        if len(parts) >= 2:
            last = parts[-1]
            first = parts[0]
            return f"{last.lower().replace(' ','')}_{first[0].lower()}"
        return s_clean.lower().replace(' ', '')

def parse_list_column(cell):
    if pd.isna(cell):
        return []
    if isinstance(cell, list):
        return cell
    s = str(cell).strip()
    if s == "":
        return []
    if s.startswith("[") and s.endswith("]"):
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed]
        except Exception:
            inner = s.strip("[]")
            return [i.strip().strip("'\"") for i in inner.split(",") if i.strip()]
    if ";" in s:
        return [i.strip() for i in s.split(";") if i.strip()]
    if "|" in s:
        return [i.strip() for i in s.split("|") if i.strip()]
    parts = [p.strip() for p in s.split(",") if p.strip()]
    if len(parts) > 3:
        return [s]
    if len(parts) > 1:
        return parts
    return [s]

def shapely_to_pydeck_polygons(geom):
    if geom is None:
        return []
    polys = []
    if isinstance(geom, (Polygon, MultiPolygon)):
        if geom.geom_type == "Polygon":
            ext = list(geom.exterior.coords)
            polys.append([[c[0], c[1]] for c in ext])
        else:
            for p in geom.geoms:
                polys.append([[c[0], c[1]] for c in list(p.exterior.coords)])
    else:
        try:
            gg = wkt.loads(str(geom))
            return shapely_to_pydeck_polygons(gg)
        except Exception:
            return []
    return polys

# ---------------------
# Load datasets
# ---------------------
@st.cache_data
def load_datasets():
    bills = safe_read_json(BILLS_PATH)
    repkpis = safe_read_json(REPKPIS_PATH)

    geo_a_path = DATA_DIR / "reps_with_geo_data_a.geojson"
    geo_b_path = DATA_DIR / "reps_with_geo_data_b.geojson"
    geo_parts = []
    for p in [geo_a_path, geo_b_path]:
        if p.exists():
            geo_parts.append(gpd.read_file(p))
    if geo_parts:
        repsgeo = pd.concat(geo_parts, ignore_index=True)
    else:
        raise FileNotFoundError("Missing both geojson parts.")

    return bills, repkpis, repsgeo

try:
    bills_df, repkpis_df, repsgeo_gdf = load_datasets()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# # ------------------------------------------------------------------ #
# # ----------------DEBUGGING ---------------------------------------- #
# # ------------------------------------------------------------------ #
# bills_df = safe_read_json(BILLS_PATH)
# repkpis_df = safe_read_json(REPKPIS_PATH)
# geo_a_path =  "data/reps_with_geo_data_a.geojson"
# geo_b_path = "data/reps_with_geo_data_b.geojson"
# geo_parts = []
# for p in [geo_a_path, geo_b_path]:
#     try:
#         geo_parts.append(gpd.read_file(p))
#     except FileNotFoundError:
#         print(f"geojson file not found! Expected location {p}")
#
# if len(geo_parts) == 2:
#     repsgeo_gdf = pd.concat(geo_parts, ignore_index=True)
# else:
#     raise FileNotFoundError("Missing both geojson parts!")
# # ------------------------------------------------------------------ #
# # ------------------------------------------------------------------ #

# normalize col names
bills_df.columns = [c.strip() for c in bills_df.columns]
repkpis_df.columns = [c.strip() for c in repkpis_df.columns]
repsgeo_gdf.columns = [c.strip() for c in repsgeo_gdf.columns]

# identify sponsor/name columns
bill_sponsor_col = find_col(bills_df, ["Bill Sponsor", "Sponsor"])
repkpi_name_col = find_col(repkpis_df, ["Bill Sponsor", "Representative", "Rep_Name"])
repgeo_name_col = find_col(repsgeo_gdf, ["Bill Sponsor", "Representative", "Rep_Name"])

# build rep_key consistently
bills_df["rep_key"]   = bills_df[bill_sponsor_col].apply(make_rep_key)
repkpis_df["rep_key"] = repkpis_df[repkpi_name_col].apply(make_rep_key)
repsgeo_gdf["rep_key"] = repsgeo_gdf[repgeo_name_col].apply(make_rep_key)

# merge geo + KPIs
reps_merged = repsgeo_gdf.merge(repkpis_df, on="rep_key", how="left", suffixes=("_geo", "_kpi"))

# merge bills with reps
bills_with_rep = bills_df.merge(
    reps_merged.drop(columns="geometry", errors="ignore"),
    on="rep_key", how="left"
)

# ---------------------
# Sidebar filters
# ---------------------
st.title("ElectionTime — Rep KPI Dashboard")
st.markdown("Search a representative, view KPIs, committees, bills, and district map.")

office_col = find_col(repkpis_df, ["Office", "office", "Chamber"])
offices = sorted(repkpis_df[office_col].dropna().unique().tolist()) if office_col else []
party_col = find_col(reps_merged, ["Party", "party"])
parties = sorted(reps_merged[party_col].dropna().unique().tolist()) if party_col else []

st.sidebar.header("Filters")
# selected_office = st.sidebar.multiselect("Office", options=offices, default=[])
# selected_party = st.sidebar.multiselect("Party", options=parties, default=[])

# find rep name column
possible_name_cols = ["Bill Sponsor", "Representative", "Rep_Name",
                      "Bill Sponsor_geo", "Representative_geo",
                      "Bill Sponsor_kpi", "Representative_kpi"]
rep_name_col = next((c for c in possible_name_cols if c in reps_merged.columns), None)

if not rep_name_col:
    st.error("Could not find a representative name column.")
    st.stop()

rep_choices = reps_merged[rep_name_col].fillna("").astype(str).unique().tolist()
query = st.sidebar.text_input("Search representative (fuzzy)", "")

if query.strip() == "":
    selected_rep = st.sidebar.selectbox("Choose representative", options=sorted([r for r in rep_choices if r]))
else:
    matches = fuzzy_extract(query, rep_choices, limit=8)
    match_names = [m[0] for m in matches]
    st.sidebar.write("Top matches:")
    for m in matches:
        st.sidebar.write(f"- {m[0]} (score {m[1]})")
    selected_rep = st.sidebar.selectbox("Pick one", options=match_names)

if not selected_rep:
    st.info("Pick a representative to continue.")
    st.stop()

rep_row = reps_merged[reps_merged[rep_name_col] == selected_rep]
if rep_row.empty:
    best = fuzzy_extract_one(selected_rep, reps_merged[repgeo_name_col].astype(str).tolist())
    if best:
        selected_rep = best[0]
        rep_row = reps_merged[reps_merged[repgeo_name_col] == selected_rep]
if rep_row.empty:
    st.error("Could not locate the selected representative.")
    st.stop()

rep = rep_row.iloc[0]

# ---------------------
# Left column: summary
# ---------------------
col1, col2 = st.columns([2, 3])
with col1:
    st.subheader(selected_rep)

    # --- KPIs ---
    total_col = find_col(repkpis_df, ["total_bills", "Total Bills", "total"])
    passed_col = find_col(repkpis_df, ["passed_bills", "passed"])
    failed_col = find_col(repkpis_df, ["failed_bills", "failed"])
    passrate_col = find_col(repkpis_df, ["pass_rate", "Pass Rate"])

    # fallback: build rep_bills first
    rep_key = rep.get("rep_key")
    rep_bills = bills_with_rep[bills_with_rep["rep_key"] == rep_key] if rep_key else pd.DataFrame()

    bill_status_col = find_col(bills_df, ["Bill Status", "Status", "Outcome"])

    if total_col and total_col in rep.index and pd.notna(rep.get(total_col)):
        total_bills = int(rep.get(total_col))
        passed_bills = int(rep.get(passed_col)) if passed_col and pd.notna(rep.get(passed_col)) else 0
        failed_bills = int(rep.get(failed_col)) if failed_col and pd.notna(rep.get(failed_col)) else max(0, total_bills - passed_bills)
        pass_rate = float(rep.get(passrate_col)) if passrate_col and pd.notna(rep.get(passrate_col)) else (passed_bills / total_bills * 100 if total_bills else 0)
    else:
        total_bills = len(rep_bills)
        if bill_status_col and bill_status_col in rep_bills.columns:
            passed_bills = len(rep_bills[rep_bills[bill_status_col].str.contains("Pass", case=False, na=False)])
        else:
            passed_bills = 0
        failed_bills = total_bills - passed_bills
        pass_rate = (passed_bills / total_bills * 100) if total_bills else 0

    k1, k2, k3 = st.columns(3)
    k1.metric("Total bills", total_bills)
    k2.metric("Passed", passed_bills)
    k3.metric("Failed", failed_bills)
    st.metric("Pass rate", f"{pass_rate:.1f}%")

# (col2 = bills overview, map, etc. would continue below…)
