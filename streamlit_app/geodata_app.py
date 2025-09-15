import os
import streamlit as st
import geopandas as gpd
import plotly.express as px

# -------------------------------
# File paths
# -------------------------------
BASE_DIR = "repos/ElectionTime/streamlit_app"
os.makedirs(BASE_DIR, exist_ok=True)

GEOJSON_PATH = os.path.join(BASE_DIR, "reps_with_geo_data.geojson")
JSON_PATH    = os.path.join(BASE_DIR, "reps_with_geo_data.json")

# -------------------------------
# Load data
# -------------------------------
gdf = gpd.read_file(GEOJSON_PATH)

# Save attributes only (without geometry) as JSON
gdf.drop(columns="geometry").to_json(JSON_PATH, orient="records")

st.title("Reps by District Map")

# -------------------------------
# Sidebar

reps = sorted(gdf["Representative"].unique())
selected_reps = st.sidebar.multiselect("Select Representative", reps, default=[])


# If nothing selected, show all
if selected_reps:
    filtered = gdf[gdf["Representative"].isin(selected_reps)]
else:
    filtered = gdf

# -------------------------------
# Simplify geometries for speed
# -------------------------------
filtered = filtered.copy()
filtered["geometry"] = filtered["geometry"].simplify(
    tolerance=0.02, preserve_topology=True
)


# -------------------------------
# Build choropleth
# -------------------------------
fig = px.choropleth_mapbox(
    filtered,
    geojson=filtered.__geo_interface__,
    locations="Representative",                # column to match features
    featureidkey="properties.Representative",  # must match GeoJSON property
    color="Representative",                    # coloring variable
    hover_name="Representative",
    mapbox_style="carto-positron",
    center={"lat": 39.5, "lon": -111.5},       # Utah center
    zoom=6,
    opacity=0.6
)

# Set figure size (height in px, width is auto by container)
fig.update_layout(height=800)  # try 800–1000 for taller map

st.plotly_chart(fig, use_container_width=True)

# -------------------------------
# Debug info (optional)
# -------------------------------
st.write("✅ Loaded districts:", len(gdf))
st.write("Memory before simplification (MB):", round(gdf.memory_usage(deep=True).sum() / 1e6, 2))
st.write("Memory after simplification (MB):", round(filtered.memory_usage(deep=True).sum() / 1e6, 2))
