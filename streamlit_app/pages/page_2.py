import streamlit as st
import geopandas as gpd
import json
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------
# Load data (cached for speed)
# -----------------------------
@st.cache_data
def load_data(path):
    with open(path) as f:
        geojson = json.load(f)
    if isinstance(geojson, dict) and "features" in geojson:
        df = gpd.GeoDataFrame.from_features(geojson["features"])
    elif isinstance(geojson, list):  # fallback if file is a list of features
        df = gpd.GeoDataFrame.from_features(geojson)
    else:
        raise ValueError("Unsupported GeoJSON structure")
    simplified = df.copy()
    simplified["geometry"] = simplified["geometry"].simplify(tolerance=0.02, preserve_topology=True)
    return simplified


# -------------------------------
# Load data
# -------------------------------
geojson_path = "repos/ElectionTime/streamlit_app/data/reps_with_geo_data.geojson"
json_path = "repos/ElectionTime/streamlit_app/data/reps_with_geo_data.json"

# with open(geojson_path) as f:
#     geojson = json.load(f)
#
# if isinstance(geojson, dict) and "features" in geojson:
#     all_data = gpd.GeoDataFrame.from_features(geojson["features"])
# elif isinstance(geojson, list):  # fallback if file is a list of features
#     all_data = gpd.GeoDataFrame.from_features(geojson)
# else:
#     raise ValueError("Unsupported GeoJSON structure")

all_data = load_data(geojson_path)
# -------------------------------
# Sidebar Rep Selector
# -------------------------------
st.sidebar.markdown("# Representatives ❄️")
rep_options = all_data["Representative"].unique().tolist()
selected_rep = st.sidebar.selectbox("Select a Representative", rep_options)

# Filter selected rep
rep_data = all_data[all_data["Representative"] == selected_rep].iloc[0]

# -------------------------------
# Main Layout (3 equal columns)
# -------------------------------
col1, col2, col3 = st.columns(3)

# ---- Column 1: Representative Image ----
with col1:
    st.image(rep_data["Img_URL"], use_container_width=True)

# ---- Column 2: Representative Info ----
with col2:
    st.subheader(rep_data["Representative"])
    st.write(f"**Office:** {rep_data['Chamber']} District {str(rep_data['DistrictKey'])[1:]}")
    st.write(f"**Party:** {rep_data['Party']}")
    st.write(f"**County(ies):** {rep_data['County(ies)']}")
    st.markdown(f"[Website]({rep_data['Webpage']})")

# ---- Column 3: District Map ----
with col3:
    # -------------------------------
    # Simplify geometries for speed
    # -------------------------------
    # Filter to GeoDataFrame instead of Series
    filtered = all_data[all_data["Representative"] == selected_rep]

    # # Simplify geometries for speed
    # filtered["geometry"] = filtered["geometry"].simplify(
    #     tolerance=0.02, preserve_topology=True)


    fig = go.Figure(go.Choroplethmap(
        geojson=filtered.__geo_interface__,
        locations=[0],
        z=[1],
        featureidkey="properties.Representative",
        colorscale=[[0, "blue"], [1, "blue"]],
        showscale=False,
    ))

    fig.update_layout(
        mapbox_style="carto-positron",  # works with MapLibre too
        mapbox_zoom=7,
        mapbox_center={"lat": 39.5, "lon": -111.5},
    )



# fig = px.choropleth_mapbox(
#     filtered,
#     geojson=filtered.__geo_interface__,
#     locations="Representative",                # column to match features
#     featureidkey="properties.Representative",  # must match GeoJSON property
#     color="Representative",                    # coloring variable
#     hover_name="Representative",
#     mapbox_style="carto-positron",
#     center={"lat": 39.5, "lon": -111.5},       # Utah center
#     zoom=6,
#     opacity=0.6
# )

