import os
import streamlit as st
import geopandas as gpd
import plotly.express as px
import json

# -----------------------------
# Load data (cached for speed)
# -----------------------------
@st.cache_data
def load_data(path):
    gdf = gpd.read_file(path)
    simplified = gdf.copy()
    simplified["geometry"] = simplified["geometry"].simplify(tolerance=0.02, preserve_topology=True)
    return simplified

# -------------------------------
# File paths
# -------------------------------
# Ensure target folder exists
save_dir = "repos/ElectionTime/streamlit_app"
os.makedirs(save_dir, exist_ok=True)

# File paths
geojson_path = os.path.join(save_dir, "reps_with_geo_data.geojson")
json_path    = os.path.join(save_dir, "reps_with_geo_data.json")

# -------------------------------
# Load data
# -------------------------------
with open(geojson_path) as f:
    geojson = json.load(f)

if isinstance(geojson, dict) and "features" in geojson:
    all_data = gpd.GeoDataFrame.from_features(geojson["features"])
elif isinstance(geojson, list):  # fallback if file is a list of features
    all_data = gpd.GeoDataFrame.from_features(geojson)
else:
    raise ValueError("Unsupported GeoJSON structure")


# Save attributes only as JSON
all_data.drop(columns="geometry").to_json(json_path, orient="records")

st.title("Reps by District Map")

# -----------------------------
# Sidebar: Rep selector
# -----------------------------
rep_options = all_data["Representative"].unique().tolist()
selected_rep = st.sidebar.selectbox("Select a Representative", rep_options)


reps = sorted(all_data["Representative"].unique())
selected_reps = st.sidebar.multiselect("Select Representative", reps, default=[])


# If nothing selected, show all
if selected_reps:
    filtered = all_data[all_data["Representative"] == selected_rep]
    # filtered = all_data[all_data["Representative"].isin(selected_reps)]
else:
    filtered = all_data

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


# # -----------------------------
# # Map (rendered once)
# # -----------------------------
# # geojson_data = all_data.__geo_interface__
#
# fig = px.choropleth_mapbox(
#     filtered,
#     geojson=filtered.__geo_interface__,
#     locations="Representative",
#     featureidkey="properties.Representative",
#     color="Representative",  # keeps all districts colored
#     hover_name="Representative",
#     mapbox_style="carto-positron",
#     center={"lat": 39.5, "lon": -111.5},
#     zoom=6,
#     opacity=0.5,
#     height=700
# )
#
# st.plotly_chart(fig, use_container_width=True)

# Set figure size (height in px, width is auto by container)
fig.update_layout(height=800)  # try 800–1000 for taller map

st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Info Panel (updates instantly)
# -----------------------------
st.markdown("---")
st.header(f"📊 Details for {selected_rep}")

rep_data = all_data[all_data["Representative"] == selected_rep].iloc[0]

st.write(f"**Party:** {rep_data['Party']}")
st.write(f"**County(ies):** {rep_data['County(ies)']}")
st.write(f"**Chamber:** {rep_data['Chamber']}")
st.write(f"**Website** {rep_data['Webpage']}")

# Example: add charts/tables here
dummy_chart_data = {
    "Bills Sponsored": [5, 7, 8, 4],
    "Year": [2021, 2022, 2023, 2024]
}

st.bar_chart(dummy_chart_data, x="Year", y="Bills Sponsored")

# -------------------------------
# Debug info (optional)
# -------------------------------
st.write("✅ Loaded districts:", len(all_data))
st.write("Memory before simplification (MB):", round(all_data.memory_usage(deep=True).sum() / 1e6, 2))
st.write("Memory after simplification (MB):", round(filtered.memory_usage(deep=True).sum() / 1e6, 2))

