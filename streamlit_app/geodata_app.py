import os
import streamlit as st
import geopandas as gpd
import plotly.express as px

# Ensure target folder exists
save_dir = "/Users/cristylegarrard/repos/ElectionTime/streamlit_app"
os.makedirs(save_dir, exist_ok=True)

# File paths
geojson_path = os.path.join(save_dir, "reps_with_geo_data.geojson")
json_path    = os.path.join(save_dir, "reps_with_geo_data.json")

# ✅ Load your GeoDataFrame from the existing geojson
all_data = gpd.read_file(geojson_path)

# Save attributes only as JSON
all_data.drop(columns="geometry").to_json(json_path, orient="records")



print(f"✅ Loaded GeoJSON from {geojson_path}")
print(f"✅ Saved JSON to {json_path}")
print(all_data.columns)

st.title("Utah District Map")

# Convert GeoDataFrame to GeoJSON
# geojson_data = all_data.__geo_interface__

# Pick something to color by (Representative, Party, etc.)
# color_col = "Representative" if "Representative" in all_data.columns else None

print(all_data.head())
print(all_data.columns)


minimized_all_data = all_data[['Representative', 'Img_ID', 'Party', 'DistrictKey', 'COLOR4', 'Shape__Area', 'Shape__Length', 'Chamber', 'geometry']].copy()

# Simplify polygons (tolerance controls how much detail is removed)
simplified = all_data.copy()
simplified["geometry"] = simplified["geometry"].simplify(tolerance=0.02, preserve_topology=True)

print("Before:", all_data.memory_usage(deep=True).sum() / 1e6, "MB")
print("After:", simplified.memory_usage(deep=True).sum() / 1e6, "MB")


# geojson_data = minimized_all_data.__geo_interface__
color_col = "Representative" if "Representative" in simplified.columns else None

geojson_data = simplified.__geo_interface__
print(geojson_data["features"][0]["properties"])

fig = px.choropleth_mapbox(
    simplified,
    geojson=geojson_data,
    locations="Representative",
    featureidkey="properties.Representative",  # must match geojson property
    color="Representative",
    hover_name="Representative",
    mapbox_style="carto-positron",
    center={"lat": 39.5, "lon": -111.5},
    zoom=6,
    opacity=0.6
)



st.plotly_chart(fig, use_container_width=True)


