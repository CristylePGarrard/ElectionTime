# app.py
"""
ElectionTime — Representative KPI dashboard (merged datasets)

Place this file at: streamlit_app/app.py
Data files expected at: streamlit_app/data/
  - combinedBills_2025.json
  - repKPIs_2025.json
  - reps_with_geo_data_a.geojson
  - reps_with_geo_data_b.geojson
"""

import streamlit as st
from pathlib import Path
import pandas as pd
import geopandas as gpd
import json
from shapely import wkt
from shapely.geometry import Polygon, MultiPolygon
import pydeck as pdk
import altair as alt

# fuzzy matching (rapidfuzz preferred)
try:
    from rapidfuzz import process as rf_process
    def fuzzy_extract(q, choices, limit=8):
        return rf_process.extract(q, choices, limit=limit)
    def fuzzy_extract_one(q, choices):
        return rf_process.extractOne(q, choices)
except Exception:
    from fuzzywuzzy import process as fw_process
    def fuzzy_extract(q, choices, limit=8):
        return fw_process.extract(q, choices, limit=limit)
    def fuzzy_extract_one(q, choices):
        return fw_process.extractOne(q, choices)

st.set_page_config(page_title="ElectionTime — Rep KPI Dashboard", layout="wide")

# ---------------------
# Paths
# ---------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

BILLS_PATH = DATA_DIR / "combinedBills_2025.json"
REPKPIS_PATH = DATA_DIR / "repKPIs_2025.json"
GEO_PATH_A = DATA_DIR / "reps_with_geo_data_a.geojson"
GEO_PATH_B = DATA_DIR / "reps_with_geo_data_b.geojson"

# ---------------------
# Helpers
# ---------------------
def safe_read_json(path: Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    try:
        return pd.read_json(path, orient="records")
    except Exception:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return pd.DataFrame(data)

def find_col(df: pd.DataFrame, candidates):
    if df is None:
        return None
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if not cand:
            continue
        if cand.lower() in cols_lower:
            return cols_lower[cand.lower()]
    # substring fallback
    for cand in candidates:
        if not cand:
            continue
        for c in df.columns:
            if cand.lower() in c.lower():
                return c
    return None

def make_rep_key(name):
    """Return lastname_firstinitial (lowercase, no spaces). Handles:
       - 'Last, F.'
       - 'Last F.' (two tokens where second is single letter)
       - 'First Last'
    """
    if pd.isna(name):
        return ""
    s = str(name).strip().replace(".", "")
    if s == "":
        return ""
    # 'Last, F' pattern
    if "," in s:
        left, right = [p.strip() for p in s.split(",", 1)]
        last = left
        first_token = right.split()[0] if right else ""
        first = first_token
    else:
        parts = s.split()
        if len(parts) == 1:
            # single token, use it as last with empty initial
            last = parts[0]
            first = ""
        elif len(parts) == 2 and len(parts[1]) == 1:
            # 'Last F' pattern
            last = parts[0]
            first = parts[1]
        else:
            # assume 'First Last' or longer - use first and last
            last = parts[-1]
            first = parts[0]
    last_clean = "".join(last.split()).lower()
    first_initial = first[0].lower() if (first and len(first) > 0) else ""
    return f"{last_clean}_{first_initial}"

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

def parse_list_column(value):
    """
    Convert a stored list-like value into a real Python list.
    Handles cases where the value is already a list,
    a stringified list, or just a plain string.
    """
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            # Try to safely eval strings like "['Committee A', 'Committee B']"
            import ast
            parsed = ast.literal_eval(value)
            if isinstance(parsed, list):
                return parsed
            else:
                return [value] if value else []
        except Exception:
            # Fallback: split by common separators
            return [v.strip() for v in value.split(",") if v.strip()]
    return []


# ---------------------
# Load datasets (cached)
# ---------------------
@st.cache_data
def load_datasets():
    bills = safe_read_json(BILLS_PATH)
    repkpis = safe_read_json(REPKPIS_PATH)

    geo_parts = []
    for p in [GEO_PATH_A, GEO_PATH_B]:
        if p.exists():
            geo_parts.append(gpd.read_file(p))
    if not geo_parts:
        raise FileNotFoundError("Missing both geojson parts (reps_with_geo_data_a/b.geojson).")
    repsgeo = pd.concat(geo_parts, ignore_index=True)
    return bills, repkpis, repsgeo

try:
    bills_df, repkpis_df, repsgeo_gdf = load_datasets()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Normalize column names (strip whitespace)
bills_df.columns = bills_df.columns.str.strip()
repkpis_df.columns = repkpis_df.columns.str.strip()
repsgeo_gdf.columns = repsgeo_gdf.columns.str.strip()

# ---------------------
# Identify meaningful columns
# ---------------------
bill_sponsor_col = find_col(bills_df, ["Bill Sponsor", "Sponsor", "bill_sponsor"])
if bill_sponsor_col is None:
    st.error("Could not find a 'Bill Sponsor' column in bills data.")
    st.stop()

# try to find name columns in KPIs & geo; if not found we still proceed but warn
repkpi_name_col = find_col(repkpis_df, ["Bill Sponsor", "Representative", "Rep_Name", "Rep Name"])
repgeo_name_col = find_col(repsgeo_gdf, ["Bill Sponsor", "Representative", "Rep_Name", "Rep Name", "Representative_geo"])
# If a column is missing, we'll still try to proceed but create keys from whatever exists.

# ---------------------
# Build consistent rep_key for all three datasets
# ---------------------
# For bills we base on the Bill Sponsor column
bills_df["rep_key"] = bills_df[bill_sponsor_col].fillna("").apply(make_rep_key)

# For rep KPIs: prefer explicit name column, else fall back try other heuristics:
if repkpi_name_col:
    repkpis_df["rep_key"] = repkpis_df[repkpi_name_col].fillna("").apply(make_rep_key)
else:
    # try common alternative columns
    alt = None
    for c in ["Representative", "Rep_Name", "Bill Sponsor"]:
        if c in repkpis_df.columns:
            alt = c
            break
    if alt:
        repkpis_df["rep_key"] = repkpis_df[alt].fillna("").apply(make_rep_key)
    else:
        # as last resort, create empty keys (won't match)
        repkpis_df["rep_key"] = ""

# For geo: prefer Bill Sponsor if present (you said you added it), else representative name
if repgeo_name_col:
    repsgeo_gdf["rep_key"] = repsgeo_gdf[repgeo_name_col].fillna("").apply(make_rep_key)
else:
    # try a few likely columns
    alt_geo = None
    for c in ["Bill Sponsor", "Representative", "Rep_Name", "Representative_geo", "Bill Sponsor_geo"]:
        if c in repsgeo_gdf.columns:
            alt_geo = c
            break
    if alt_geo:
        repsgeo_gdf["rep_key"] = repsgeo_gdf[alt_geo].fillna("").apply(make_rep_key)
    else:
        repsgeo_gdf["rep_key"] = ""

# Deduplicate KPIs by rep_key keeping first KPI row per rep_key
repkpis_df = repkpis_df.drop_duplicates(subset=["rep_key"], keep="first")

# ---------------------
# Merge datasets (geo + kpi), then join bills
# ---------------------
reps_merged = repsgeo_gdf.merge(repkpis_df, on="rep_key", how="left", suffixes=("_geo", "_kpi"))

# create a friendly display name (prioritized)
def pick_display_name(row):
    candidates = [
        "Representative_kpi", "Representative_geo",
        "Bill Sponsor_kpi", "Bill Sponsor_geo",
        "Representative", "Bill Sponsor", "Rep_Name"
    ]
    for c in candidates:
        if c in row.index and pd.notna(row[c]) and str(row[c]).strip():
            return str(row[c]).strip()
    # fallback: try common columns in original geo df
    for c in ["Representative", "Representative_geo", "Bill Sponsor", "Bill Sponsor_geo"]:
        if c in row.index and pd.notna(row[c]) and str(row[c]).strip():
            return str(row[c]).strip()
    return row.get("rep_key", "")

reps_merged["display_name"] = reps_merged.apply(pick_display_name, axis=1)
# keep a cleaned version without trailing spaces
reps_merged["display_name"] = reps_merged["display_name"].fillna("").astype(str).str.strip()

# bills joined to reps (so each bill row will carry rep metadata if merged)
bills_with_rep = bills_df.merge(reps_merged.drop(columns="geometry", errors="ignore"), on="rep_key", how="left")

# ---------------------
# Sidebar + search
# ---------------------
st.title("ElectionTime — Rep KPI Dashboard")
st.markdown("Search a representative, view KPIs, committees, bills, and district map.")

# debug counts
st.sidebar.caption(f"Loaded: {len(bills_df)} bills, {len(repkpis_df)} KPI rows, {len(reps_merged)} geo rows")

# build choices (non-empty)
rep_choices = sorted([x for x in reps_merged["display_name"].unique().tolist() if str(x).strip()])
if len(rep_choices) == 0:
    st.error("No display names were created. Check your geo/KPI name columns.")
    st.stop()

query = st.sidebar.text_input("Search representative (fuzzy)", "")
if query.strip() == "":
    selected_rep = st.sidebar.selectbox("Choose representative", options=rep_choices)
else:
    raw_matches = fuzzy_extract(query, rep_choices, limit=10)
    # normalize match tuples (match, score, maybe index)
    matches = []
    for m in raw_matches:
        if isinstance(m, (tuple, list)):
            if len(m) >= 2:
                matches.append((m[0], m[1]))
            elif len(m) == 1:
                matches.append((m[0], 0))
        else:
            matches.append((m, 0))
    if len(matches) == 0:
        st.sidebar.warning("No fuzzy matches found; showing full list.")
        selected_rep = st.sidebar.selectbox("Choose representative", options=rep_choices)
    else:
        match_names = [m[0] for m in matches]
        selected_rep = st.sidebar.selectbox("Top matches", options=match_names)

if not selected_rep:
    st.info("Pick a representative to continue.")
    st.stop()

# find selected row(s)
rep_row = reps_merged[reps_merged["display_name"] == selected_rep]
if rep_row.empty:
    # fallback: use fuzzy on display_name to pick best
    best = fuzzy_extract_one(selected_rep, reps_merged["display_name"].astype(str).tolist())
    if best:
        selected_rep = best[0]
        rep_row = reps_merged[reps_merged["display_name"] == selected_rep]

if rep_row.empty:
    st.error("Could not find that representative after fallback.")
    st.stop()

rep = rep_row.iloc[0]  # Series of selected rep
# # -------------------------------------------------------- # #
# Debugging
# st.write("Debug — rep row columns:", rep.index.tolist())
# st.json(rep.to_dict())
# # -------------------------------------------------------- # #

# ---------------------
# KPIs & Summary (left column)
# ---------------------
col1, col2 = st.columns([2, 3])
with col1:
    st.subheader(selected_rep)

    # find KPI column names on the merged df (these should come from repKPIs)
    total_col = find_col(reps_merged, ["total_bills", "Total Bills", "total"])
    passed_col = find_col(reps_merged, ["passed_bills", "passed"])
    failed_col = find_col(reps_merged, ["failed_bills", "failed"])
    passrate_col = find_col(reps_merged, ["pass_rate", "pass rate"])

    # compute rep_bills from bills_with_rep (using rep_key)
    rep_key = rep.get("rep_key", "")
    rep_bills = bills_with_rep[bills_with_rep["rep_key"] == rep_key].copy() if rep_key else pd.DataFrame()

    row = rep_bills.iloc[0]
    # bill status column in bills_df
    bill_status_col = find_col(bills_df, ["Bill Status", "Status", "Outcome"])

    # Prefer KPI values from repKPIs (present in reps_merged after merge)
    if total_col and pd.notna(rep.get(total_col)):
        total_bills = int(rep.get(total_col)) if pd.notna(rep.get(total_col)) else 0
        passed_bills = int(rep.get(passed_col)) if (passed_col and pd.notna(rep.get(passed_col))) else 0
        failed_bills = int(rep.get(failed_col)) if (failed_col and pd.notna(rep.get(failed_col))) else max(0, total_bills - passed_bills)
        pass_rate = float(rep.get(passrate_col)) if (passrate_col and pd.notna(rep.get(passrate_col))) else (passed_bills / total_bills * 100 if total_bills else 0)
    else:
        # fallback compute from rep_bills
        total_bills = len(rep_bills)
        if bill_status_col and bill_status_col in rep_bills.columns and total_bills > 0:
            passed_bills = rep_bills[bill_status_col].astype(str).str.contains("pass", case=False, na=False).sum()
        else:
            passed_bills = 0
        failed_bills = total_bills - passed_bills
        pass_rate = (passed_bills / total_bills * 100) if total_bills else 0.0

    # horizontal bar chart - normalized
    # status stacked bar (horizontal, normalized to 100%)


    total = row["total_bills"] or 0
    passed = row["passed_bills"] or 0
    failed = row["failed_bills"] or 0
    unknown = max(0, total - (passed + failed))

    # Build a dataframe for the stacked bar
    data = pd.DataFrame({
        "Status": ["Passed", "Failed", "Unknown"],
        "Value": [passed, failed, unknown]
    })

    # Horizontal stacked bar, normalized to total
    chart = (
        alt.Chart(data)
        .mark_bar(size=40)  # thicker bar
        .encode(
            x=alt.X("Value:Q", stack="normalize", axis=alt.Axis(format="%", labelPadding=10, tickSize=5)),
            y=alt.value(0),  # single horizontal bar
            color=alt.Color("Status:N", scale=alt.Scale(
                domain=["Passed", "Failed", "Unknown"],
                range=["green", "red", "#f7f7f7"]  # white/light gray for unknown
            ),
                            legend=None
                            ),
            tooltip=["Status", "Value"       ]
        )
        .properties(height=50)
    )

    st.altair_chart(chart, use_container_width=True)

    # # ------------------------------------------# #
    # # --- aggregates - top level info
    # # ------------------------------------------# #
    st.image(row["Img_URL"], use_container_width=True)
    st.metric("Pass rate", f"{pass_rate:.1f}%")
    k1, k2, k3 = st.columns(3)
    k1.metric("Failed", failed_bills)
    k2.metric("Passed", passed_bills)
    k3.metric("Total bills", total_bills)



# # ==============================
# # Committees & Roles
# # ==============================
#
# st.subheader("Committee Assignments")
#
# # Identify which columns to use
# committee_col = find_col(reps_merged, ["Committee", "Committees", "committee"])
# role_col = find_col(reps_merged, ["Role", "Roles", "role"])
#
# # Extract lists for the selected representative
# comm_list = parse_list_column(rep.get(committee_col)) if committee_col else []
# role_list = parse_list_column(rep.get(role_col)) if role_col else []
#
# # Make sure lengths line up
# if len(comm_list) != len(role_list):
#     st.warning("⚠️ Committees and Roles list lengths don’t match for this representative.")
#     min_len = min(len(comm_list), len(role_list))
#     comm_list = comm_list[:min_len]
#     role_list = role_list[:min_len]
#
# # Display committees with corresponding roles
# if comm_list:
#     for c, r in zip(comm_list, role_list):
#         st.markdown(f"- **{c}** — {r}")
# else:
#     st.info("No committee data available for this representative.")


# ---------------------
# Right column: bills overview & map
# ---------------------
with col2:
    # st.subheader("Bills overview")
    if rep_bills.empty:
        st.write("_No bills found for this rep via rep_key. (We will try a last-name fallback.)_")
        # fallback by last name match from bills_df
        last_name = selected_rep.split()[-1]
        rep_bills = bills_df[bills_df[bill_sponsor_col].astype(str).str.contains(last_name, case=False, na=False)].copy()

    if rep_bills.empty:
        st.write("_No bills available for this rep in combinedBills_2025.json._")
    else:
        # always create bill_date_parsed, even if no valid date col is found
        date_col = find_col(rep_bills, ["Bill Date (utc_iso)", "Bill Date", "Bill Date Raw", "Date", "bill_date"])
        rep_bills["bill_date_parsed"] = (
            pd.to_datetime(rep_bills[date_col], errors="coerce")
            if date_col
            else pd.NaT
        )
        # # status stacked bar (horizontal, normalized to 100%)
        # row = rep_bills.iloc[0]
        #
        # total = row["total_bills"] or 0
        # passed = row["passed_bills"] or 0
        # failed = row["failed_bills"] or 0
        # unknown = max(0, total - (passed + failed))
        #
        # # Build a dataframe for the stacked bar
        # data = pd.DataFrame({
        #     "Status": ["Passed", "Failed", "Unknown"],
        #     "Value": [passed, failed, unknown]
        # })
        #
        # # Horizontal stacked bar, normalized to total
        # chart = (
        #     alt.Chart(data)
        #     .mark_bar(size=40)  # thicker bar
        #     .encode(
        #         x=alt.X("Value:Q", stack="normalize", axis=alt.Axis(format="%", labelPadding=10, tickSize=5)),
        #         y=alt.value(0),  # single horizontal bar
        #         color=alt.Color("Status:N", scale=alt.Scale(
        #             domain=["Passed", "Failed", "Unknown"],
        #             range=["green", "red", "#f7f7f7"]  # white/light gray for unknown
        #             ),
        #         legend=None
        #         ),
        #         tooltip=["Status", "Value"]
        #     )
        #     .properties(height=50)
        # )
        #
        # st.altair_chart(chart, use_container_width=True)




    # if bill_status_col and bill_status_col in rep_bills.columns:
        #     sc = rep_bills[bill_status_col].fillna("Unknown").value_counts().reset_index()
        #     sc.columns = ["Status", "Count"]
        #     chart = alt.Chart(sc).mark_bar().encode(x=alt.X("Status:N", sort="-y"), y="Count:Q").properties(height=200)
        #     st.altair_chart(chart, use_container_width=True)

        # # timeline
        # if rep_bills["bill_date_parsed"].notna().any():
        #     ts = rep_bills.groupby(pd.Grouper(key="bill_date_parsed", freq="W")).size().reset_index(name="count")
        #     line = alt.Chart(ts).mark_line(point=True).encode(x="bill_date_parsed:T", y="count:Q").properties(height=180)
        #     st.altair_chart(line, use_container_width=True)

        # # show table with expanded columns
        # display_cols = [
        #     find_col(rep_bills, ["Bill Number", "BillNumber", "bill_number"]),
        #     "Bill Title",
        #     bill_status_col,
        #     "Date Passed",
        #     "Effective Date",
        #     rep_bills["bill_date_parsed"].name if "bill_date_parsed" in rep_bills else None,
        #     find_col(rep_bills, ["Bill URL", "BillURL", "url"])
        # ]
        # display_cols = [c for c in display_cols if c]
        #
        # rep_bills_sorted = rep_bills.sort_values(by="bill_date_parsed", ascending=False).reset_index(drop=True)
        #
        # st.dataframe(rep_bills_sorted[display_cols], use_container_width=True)


# Map: use geometry from reps_merged (should be in geo)
    st.subheader("District map")
    geom = None
    if "geometry" in rep.index and pd.notna(rep.get("geometry")):
        geom = rep.get("geometry")
    else:
        # try geometry_wkt if present
        wkt_col = find_col(reps_merged, ["geometry_wkt", "geom", "wkt"])
        if wkt_col and pd.notna(rep.get(wkt_col)):
            try:
                geom = wkt.loads(rep.get(wkt_col))
            except Exception:
                geom = None

    if geom is not None:
        polygons = shapely_to_pydeck_polygons(geom)
        if polygons:
            centroid = geom.centroid
            view = pdk.ViewState(latitude=centroid.y, longitude=centroid.x, zoom=8)
            polygon_layer = pdk.Layer(
                "PolygonLayer",
                data=[{"polygon": polygons[0], "name": selected_rep}],
                get_polygon="polygon",
                pickable=True,
                stroked=True,
                filled=True,
                extruded=False,
                get_fill_color=[200, 30, 0, 80],
                get_line_color=[0, 0, 0],
            )
            st.pydeck_chart(pdk.Deck(layers=[polygon_layer], initial_view_state=view, tooltip={"text":"{name}"}))
        else:
            st.write("_Geometry present but could not convert to polygon for pydeck._")
    else:
        # fallback Lat/Lon
        lat_col = find_col(reps_merged, ["lat", "latitude"])
        lon_col = find_col(reps_merged, ["lon", "longitude"])
        try:
            lat = float(rep.get(lat_col)) if lat_col and pd.notna(rep.get(lat_col)) else None
            lon = float(rep.get(lon_col)) if lon_col and pd.notna(rep.get(lon_col)) else None
            if lat and lon:
                st.map(pd.DataFrame({"lat":[lat],"lon":[lon]}))
            else:
                st.write("_No geometry or lat/lon available for this rep._")
        except Exception:
            st.write("_No geometry or lat/lon available for this rep._")
# show table with expanded columns
st.subheader("Bills overview")
display_cols = [
    find_col(rep_bills, ["Bill Number", "BillNumber", "bill_number"]),
    "Bill Title",
    bill_status_col,
    "Date Passed",
    "Effective Date",
    rep_bills["bill_date_parsed"].name if "bill_date_parsed" in rep_bills else None,
    find_col(rep_bills, ["Bill URL", "BillURL", "url"])
]
display_cols = [c for c in display_cols if c]

rep_bills_sorted = rep_bills.sort_values(by="bill_date_parsed", ascending=False).reset_index(drop=True)

st.dataframe(rep_bills_sorted[display_cols], use_container_width=True)

# ==============================
# Committees & Roles
# ==============================

st.subheader("Committee Assignments")

# Identify which columns to use
committee_col = find_col(reps_merged, ["Committee", "Committees", "committee"])
role_col = find_col(reps_merged, ["Role", "Roles", "role"])

# Extract lists for the selected representative
comm_list = parse_list_column(rep.get(committee_col)) if committee_col else []
role_list = parse_list_column(rep.get(role_col)) if role_col else []

# Make sure lengths line up
if len(comm_list) != len(role_list):
    st.warning("⚠️ Committees and Roles list lengths don’t match for this representative.")
    min_len = min(len(comm_list), len(role_list))
    comm_list = comm_list[:min_len]
    role_list = role_list[:min_len]

# Display committees with corresponding roles
if comm_list:
    for c, r in zip(comm_list, role_list):
        st.markdown(f"- **{c}** — {r}")
else:
    st.info("No committee data available for this representative.")
# ---------------------
# Bottom: quick export
# ---------------------
st.markdown("---")
st.write(f"- Loaded {len(bills_df)} bills, {len(repkpis_df)} KPI rows, {len(reps_merged)} geo rows.")
if st.button("Download currently visible rep's bills as CSV"):
    try:
        csv = rep_bills.to_csv(index=False)
        st.download_button("Download CSV", data=csv, file_name=f"{selected_rep.replace(' ','_')}_bills.csv", mime="text/csv")
    except Exception as e:
        st.error(f"Could not prepare download: {e}")
