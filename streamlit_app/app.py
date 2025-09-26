# app.py
import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely import wkt
import pydeck as pdk
from shapely.geometry import mapping
from dateutil import parser
import altair as alt
from fuzzywuzzy import process
from urllib.parse import urlparse
import os

st.set_page_config(page_title="ElectionTime — Rep KPI Dashboard", layout="wide")

# -------------------------
# Helper functions
# -------------------------
@st.cache_data
def load_data(path):
    gdf = gpd.read_file(path)
    simplified = gdf.copy()
    simplified["geometry"] = simplified["geometry"].simplify(tolerance=0.02, preserve_topology=True)
    return simplified

@st.cache_data
def load_csv(path):
    return pd.read_csv(path)

@st.cache_data
def load_json(path):
    return pd.read_json(path)

def normalize_rep_name(name):
    # Standard lightweight normalization; expand as needed
    return name.strip().replace('.', '').lower()

def get_best_match(query, choices, limit=5):
    # returns best fuzzy match and score
    result = process.extract(query, choices, limit=limit)
    return result

def parse_list_column(cell):
    """
    Turn a cell like "Comm A; Comm B; Comm C" or "['Comm A','Comm B']" into list.
    """
    if pd.isna(cell):
        return []
    if isinstance(cell, list):
        return cell
    s = str(cell).strip()
    # common separators ; | ,  and handle bracket notation
    if s.startswith('[') and s.endswith(']'):
        # crude parse
        s2 = s.strip('[]')
        items = [i.strip().strip("'\"") for i in s2.split(',') if i.strip()]
        return items
    if ';' in s:
        return [i.strip() for i in s.split(';') if i.strip()]
    if '|' in s:
        return [i.strip() for i in s.split('|') if i.strip()]
    # fallback split on comma but avoid splitting "Last, F." style by heuristics:
    parts = [p.strip() for p in s.split(',') if p.strip()]
    # if we get too many tiny parts it's probably not a list, return original single entry
    if len(parts) > 3:
        return [s]
    return [s]

def committees_roles_df(comm_list, role_list):
    """
    Align two lists (committees and roles) that match by position.
    """
    comms = parse_list_column(comm_list)
    roles = parse_list_column(role_list)
    # pad the shorter list
    n = max(len(comms), len(roles))
    comms += [''] * (n - len(comms))
    roles += [''] * (n - len(roles))
    return pd.DataFrame({'Committee': comms, 'Role': roles})

def geometry_to_pydeck_polygon(geom_wkt):
    try:
        geom = wkt.loads(geom_wkt)
    except Exception:
        return None
    # We support Polygon and MultiPolygon
    coords = []
    if geom.geom_type == 'Polygon':
        exterior = list(geom.exterior.coords)
        # pydeck expects list of lists of [lon,lat] pairs
        coords = [ [[c[0], c[1]] for c in exterior] ]
    elif geom.geom_type == 'MultiPolygon':
        coords = []
        for poly in geom.geoms:
            exterior = list(poly.exterior.coords)
            coords.append([[c[0], c[1]] for c in exterior])
    else:
        return None
    return coords, geom.centroid.y, geom.centroid.x

def safe_image_url(url):
    # very small check so st.image doesn't choke on weird strings
    try:
        parsed = urlparse(url)
        return url if parsed.scheme in ('http','https') else None
    except:
        return None

# -------------------------
# Load data (edit paths here)
# -------------------------
st.sidebar.title("Data sources")
base_path = 'data/'
bills_file = os.path.join(base_path, "combinedBills_2025.json")
kpi_file = os.path.join(base_path, "repKPIs_2025.json")
geo_file = os.path.join(base_path, "reps_with_geo_data.geojson")

bills_path = st.sidebar.text_input(base_path, "combinedBills_2025.json")
# bills_path = st.sidebar.text_input("Bills CSV path", "combinedBills_2025.csv")
# repkpis_path = st.sidebar.text_input("Rep KPIs CSV path", "repKPIs_2025.csv")
# repsgeo_path = st.sidebar.text_input("Reps geo CSV path", "reps_with_geo_data.csv")

@st.spinner("Loading datasets...")
def load_all():
    bills = load_json(bills_file)
    # bills = load_csv(bills_path)
    repkpis = load_json(kpi_file)
    # repkpis = load_csv(repkpis_path)
    repsgeo = load_data(geo_file)
    # repsgeo = load_csv(repsgeo_path)
    return bills, repkpis, repsgeo

try:
    bills_df, repkpis_df, repsgeo_df = load_all()
except Exception as e:
    st.error(f"Error loading data from files: {e}")
    st.stop()

# normalize some column names to make code robust
bills_df.columns = [c.strip() for c in bills_df.columns]
repkpis_df.columns = [c.strip() for c in repkpis_df.columns]
repsgeo_df.columns = [c.strip() for c in repsgeo_df.columns]

# unify representative identifier
# prefer 'Representative' in repsgeo, or 'Bill Sponsor' in bills, or 'Bill Sponsor' in repkpis
rep_names = repsgeo_df['Representative'].astype(str).tolist()
rep_key_map = {normalize_rep_name(r): r for r in rep_names}

# Search UI
st.title("ElectionTime — Representative KPI Dashboard")
st.markdown("Search a representative by name (fuzzy search). Select a rep to view KPIs, committees, links, and a map of their district.")

query = st.text_input("Search representative (name or last name)", "")

if query.strip() == "":
    st.info("Type a name to search or pick one from the dropdown below.")
    # show dropdown list of reps to choose
    selected_rep = st.selectbox("Or choose a representative", options=sorted(rep_names))
else:
    # fuzzy match
    choices = rep_names
    matches = get_best_match(query, choices, limit=8)
    # show as selectbox
    match_texts = [f"{m[0]}  —  score {m[1]}" for m in matches]
    st.write("Top matches:")
    for m in matches:
        st.write(f"- **{m[0]}**  (score {m[1]})")
    best = matches[0][0] if matches else None
    selected_rep = st.selectbox("Pick from matches", options=[m[0] for m in matches]) if matches else None

if not selected_rep:
    st.stop()

# fetch rep rows
rep_norm = normalize_rep_name(selected_rep)
rep_row_geo = repsgeo_df[repsgeo_df['Representative'].str.lower().str.replace('.', '') == rep_norm]
if rep_row_geo.empty:
    # try fuzzy in repsgeo
    best = process.extractOne(selected_rep, repsgeo_df['Representative'].astype(str).tolist())
    if best:
        rep_name_real = best[0]
        rep_row_geo = repsgeo_df[repsgeo_df['Representative'] == rep_name_real]
        st.warning(f"Exact match not found for '{selected_rep}'. Using fuzzy match '{best[0]}'.")
if rep_row_geo.empty:
    st.error("Could not find representative in `reps_with_geo_data` dataset.")
    st.stop()

rep_row = rep_row_geo.iloc[0]

# Determine key for linking to bill counts in repKPIs or bills
# Try matching by last, first initial patterns
# Many datasets use 'Escamilla, L.' vs 'Escamilla, L' etc.
rep_key_variants = [
    rep_row.get('Representative'),
    rep_row.get('Representative').replace('.', '') if isinstance(rep_row.get('Representative'), str) else None,
    rep_row.get('Representative').split()[0] if isinstance(rep_row.get('Representative'), str) else None
]
# find in repkpis by fuzzy
repkpi_choices = repkpis_df['Bill Sponsor'].astype(str).tolist() if 'Bill Sponsor' in repkpis_df.columns else repkpis_df['Representative'].astype(str).tolist()
best_kpi = process.extractOne(rep_row['Representative'], repkpi_choices)
if best_kpi and best_kpi[1] >= 80:
    repkpi_row = repkpis_df[ (repkpis_df['Bill Sponsor'] == best_kpi[0]) | (repkpis_df.get('Representative', '') == best_kpi[0]) ]
else:
    # attempt to match by normalized names
    mask = repkpis_df['Bill Sponsor'].astype(str).str.lower().str.replace('.', '') == normalize_rep_name(rep_row['Representative'])
    repkpi_row = repkpis_df[mask]

if repkpi_row.empty:
    repkpi_row = repkpis_df[repkpis_df['Bill Sponsor'].astype(str).str.contains(rep_row['Representative'].split()[-1], na=False)]

# UI layout: KPIs left, details right
col1, col2 = st.columns([2, 3])

with col1:
    st.subheader(selected_rep)
    # photo
    img_url = safe_image_url(rep_row.get('Img_URL', ''))
    if img_url:
        st.image(img_url, width=180)
    else:
        st.write("_No image available_")
    # basic info
    info_md = f"""
**Party:** {rep_row.get('Party', '—')}  
**District:** {rep_row.get('DistrictKey', '—')}  
**Counties:** {rep_row.get('County(ies)', '—')}  
**Email:** {rep_row.get('Email', '—')}  
[Legislation]({rep_row.get('Legislation_By_Senator', rep_row.get('Legislation_By_Representative', '#'))}) — [Profile]({rep_row.get('Webpage', '#')})
"""
    st.markdown(info_md, unsafe_allow_html=True)

    # KPI metrics area
    st.markdown("### KPIs")
    # try to pull from repkpis_row
    if not repkpi_row.empty:
        r = repkpi_row.iloc[0]
        total_bills = int(r.get('total_bills', 0) if pd.notna(r.get('total_bills', 0)) else 0)
        passed_bills = int(r.get('passed_bills', 0) if pd.notna(r.get('passed_bills', 0)) else 0)
        failed_bills = int(r.get('failed_bills', 0) if pd.notna(r.get('failed_bills', 0)) else 0)
        pass_rate = float(r.get('pass_rate', (passed_bills / total_bills * 100) if total_bills else 0))
    else:
        # compute from bills dataset
        sponsor_mask = bills_df['Bill Sponsor'].astype(str).str.lower().str.replace('.', '') == normalize_rep_name(rep_row['Representative'])
        sponsor_bills = bills_df[sponsor_mask]
        total_bills = len(sponsor_bills)
        passed_bills = len(sponsor_bills[sponsor_bills['Bill Status'].str.contains('Passed', na=False)])
        failed_bills = total_bills - passed_bills
        pass_rate = (passed_bills / total_bills * 100) if total_bills else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total bills", total_bills)
    c2.metric("Passed", passed_bills)
    c3.metric("Failed", failed_bills)
    st.metric("Pass rate", f"{pass_rate:.1f}%")

    # committees and roles
    st.markdown("### Committees & roles")
    # attempt to find committees and roles columns in repkpis_df
    committees_col_name = None
    roles_col_name = None
    for possible in ['committees', 'Committees', 'committee_list', 'Committee List', 'committee', 'Committees_list']:
        if possible in repkpi_row.columns:
            committees_col_name = possible
            break
    for possible in ['committee_roles', 'roles', 'Roles', 'role_list', 'Role List']:
        if possible in repkpi_row.columns:
            roles_col_name = possible
            break

    if not repkpi_row.empty and committees_col_name:
        comm_cell = repkpi_row.iloc[0].get(committees_col_name)
        role_cell = repkpi_row.iloc[0].get(roles_col_name) if roles_col_name else None
        crdf = committees_roles_df(comm_cell, role_cell)
        st.dataframe(crdf)
    else:
        st.write("_No committee information available in KPIs dataset._")

with col2:
    st.subheader("Bills overview")
    # Filter bills by sponsor
    sponsor_mask = bills_df['Bill Sponsor'].astype(str).str.lower().str.replace('.', '') == normalize_rep_name(rep_row['Representative'])
    sponsor_bills = bills_df[sponsor_mask].copy()
    if sponsor_bills.empty:
        # try fuzzy match
        candidate = process.extractOne(rep_row['Representative'], bills_df['Bill Sponsor'].astype(str).tolist())
        if candidate:
            sponsor_bills = bills_df[bills_df['Bill Sponsor'] == candidate[0]].copy()
    if sponsor_bills.empty:
        st.write("_No bills found for this rep in `combinedBills_2025` dataset._")
    else:
        # convert date column
        date_col = None
        for c in ['Bill Date (utc_iso)', 'Bill Date', 'Bill Date Raw', 'Bill Date (utc)', 'Bill Date Raw']:
            if c in sponsor_bills.columns:
                date_col = c
                break
        if date_col:
            try:
                sponsor_bills['bill_date_parsed'] = pd.to_datetime(sponsor_bills[date_col], errors='coerce')
            except Exception:
                sponsor_bills['bill_date_parsed'] = sponsor_bills[date_col].apply(lambda x: parser.parse(x) if pd.notna(x) else pd.NaT)
        else:
            sponsor_bills['bill_date_parsed'] = pd.NaT

        # status counts bar chart
        status_counts = sponsor_bills['Bill Status'].fillna('Unknown').value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        bar = alt.Chart(status_counts).mark_bar().encode(
            x=alt.X('Status:N', sort='-y'),
            y='Count:Q'
        ).properties(height=200)
        st.altair_chart(bar, use_container_width=True)

        # timeline of bills
        if sponsor_bills['bill_date_parsed'].notna().any():
            ts = sponsor_bills.groupby(pd.Grouper(key='bill_date_parsed', freq='W')).size().reset_index(name='count')
            line = alt.Chart(ts).mark_line(point=True).encode(
                x='bill_date_parsed:T',
                y='count:Q'
            ).properties(height=180)
            st.altair_chart(line, use_container_width=True)

        st.markdown("#### Bill list")
        # show a compact table
        display_cols = [c for c in ['Bill Number', 'Bill Title', 'Bill Status', 'Date Passed', 'Effective Date', "Bill URL"] if c in sponsor_bills.columns]
        st.dataframe(sponsor_bills[display_cols].sort_values(by='bill_date_parsed', ascending=False).reset_index(drop=True))

    # Map
    st.subheader("District map")
    geom_wkt = rep_row.get('geometry_wkt', None) or rep_row.get('geometry', None)
    polygon_result = None
    if pd.notna(geom_wkt) and geom_wkt:
        try:
            polygon_result = geometry_to_pydeck_polygon(geom_wkt)
        except Exception as e:
            st.error(f"Error parsing WKT geometry: {e}")

    if polygon_result:
        coords_list, center_lat, center_lon = polygon_result
        # build pydeck layer
        polygon_layer = pdk.Layer(
            "PolygonLayer",
            data=[{"polygon": coords_list[0]}],
            get_polygon="polygon",
            pickable=True,
            stroked=True,
            filled=True,
            extruded=False,
            get_fill_color=[200, 30, 0, 80],
            get_line_color=[0, 0, 0],
        )
        view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=7)
        deck = pdk.Deck(layers=[polygon_layer], initial_view_state=view_state, tooltip={"text":"Representative district"})
        st.pydeck_chart(deck)
    else:
        # fall back to point map using lat/lon if available
        lat = rep_row.get('lat', None)
        lon = rep_row.get('lon', None)
        try:
            latf = float(lat)
            lonf = float(lon)
            st.map(pd.DataFrame({'lat':[latf],'lon':[lonf]}))
        except Exception:
            st.write("_No geometry or coords available for map._")

# Footer suggestions
st.markdown("---")
st.markdown("**Notes & next steps (assumptions):**")
st.markdown("""
- I used fuzzy matching to line up names across datasets (your datasets use slightly different name formats like `Escamilla, L.` vs `Escamilla, L`).
- Committees/roles are parsed from text columns (supports semicolon `;`, pipe `|`, comma list, or Python-like `['A','B']`). If your lists are stored as JSON strings, we can parse that instead.
- Geometry is expected in WKT (Polygon or MultiPolygon). If your geometry uses a projected coordinate system (EPSG:######) rather than lon/lat, we'll need to reproject to EPSG:4326 before rendering.
- Map uses PyDeck PolygonLayer (client-side). You can tweak styling, colors, and zoom.
- For deployment: Streamlit Community Cloud can host this repo for free (subject to their limits). Alternatively, you can host on Heroku / Fly / a simple VM.
""")
