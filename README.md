### The GitHub Page

- gh-pages branch is for the git-pages code 
- The main branch has the code for the data work

---
## The Data
**I need to start figuring out documentation. But it's hard jugling all the hats so it will be slow and clunky at first.**

- Where is the data coming from?
- What?
- Why?
- When?

### utah_bills_2025
This script scrape_numbered_bills.py scrapes the [Bills and Resolutions for the 2025 General Session](https://le.utah.gov/billlist.jsp?session=2025GS) website creating a csv and json file with the following info

```commandline
[
  {
    "Category":"House Bills",
    "Bill Number":"HB. 1",
    "Bill Title":"Higher Education Base Budget",
    "Bill Sponsor Raw":"(Rep. Peterson, K.)",
    "Bill Sponsor":"Peterson, K.",
    "Bill Date Raw":"Mon, 20 Jan 2025 15:49 -0700",
    "Bill Date (utc_iso)":"2025-01-20T22:49:00+00:00",
    "Bill URL":"https:\/\/le.utah.gov\/~2025\/bills\/static\/HB0001.html",
    "Scrape Timestamp":"2025-09-19T04:10:12.049183+00:00"
  }, 
  ...
  ]
```


| Key                 | Example Value                                            | Description                                                                                                                                                                                                                            |
|---------------------|----------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Category            | House Bills                                              | The website has sections that group the bills. The category is the title of the section.                                                                                                                                               |
| Bill Number         | H.B. 1                                                   | The is the bill number HB for House Bill, SB for Senate Bill and there are a few other prefixes as well                                                                                                                                |
| Bill Title          | Higher Education Base Budget                             | This is the title of the bill                                                                                                                                                                                                          |
| Bill Sponsor Raw    | (Rep. Peterson, K.)                                      | The name is formatted weird on the website with the () so I fix it and add a column this is the og value from the website                                                                                                              |
| Bill Sponsor        | Peterson, K.                                             | This is the cleaned up bill sponsor name                                                                                                                                                                                               |
| Bill Date Raw       | Mon, 20 Jan 2025 15:49 -0700                             | There's a date for each bill. I don't know what it is, the data the bill was numbered, the date it was updated, the data something happened with it. idk i figured i'd grab it with the rest of it. This is the og value from the site |
| Bill Date (utc_iso) | 2025-01-20T22:49:00+00:00                                | This is the date changed into a date format                                                                                                                                                                                            |
| Bill URL            | https:\/\/le.utah.gov\/~2025\/bills\/static\/HB0001.html | The url to the bill text on the state website                                                                                                                                                                                          |
| Scrape Timestamp    | m2025-09-19T03:49:26.120647+00:00                        | This is the date and time the data was gathered                                                                                                                                                                                        |



### passedBills

passedBills.csv is a file i downloaded from the [state website](https://le.utah.gov/asp/passedbills/passedbills.asp)
The 2025 General Session Bills Passed as of 9/17/2025 2:27 pm MST


```commandline
<class 'pandas.core.frame.DataFrame'>
RangeIndex: 104 entries, 0 to 103
Data columns (total 18 columns):
 #   Column                  Non-Null Count  Dtype   
---  ------                  --------------  -----   
 0   Representative          104 non-null    object  
 1   Webpage                 104 non-null    object  
 2   Img_ID                  104 non-null    object  
 3   Img_URL                 104 non-null    object  
 4   Legislation_By_Senator  104 non-null    object  
 5   Party                   104 non-null    object  
 6   Email                   104 non-null    object  
 7   County(ies)             104 non-null    object  
 8   DistrictKey             104 non-null    object  
 9   COLOR4                  104 non-null    int32   
 10  Shape__Area             104 non-null    float64 
 11  Shape__Length           104 non-null    float64 
 12  geometry                104 non-null    geometry
 13  Chamber                 104 non-null    object  
 14  lat                     104 non-null    float64 
 15  lon                     104 non-null    float64 
 16  geometry_wkt            104 non-null    object  
 17  lat_lon                 104 non-null    object  
dtypes: float64(4), geometry(1), int32(1), object(12)
memory usage: 14.3+ KB
```


### UTsTateLegIslaTurE_02122025

This is a google sheet I created from the state website
-  [Senate Roster](https://senate.utah.gov/senate-roster/)
- [House Roster](https://house.utleg.gov/house-members/)

It has the names and other info for the 2025 Utah state legislators


```commandline
<class 'pandas.core.frame.DataFrame'>
RangeIndex: 104 entries, 0 to 103
Data columns (total 10 columns):
 #   Column                  Non-Null Count  Dtype 
---  ------                  --------------  ----- 
 0   District                104 non-null    int64 
 1   Office                  104 non-null    object
 2   Representative          104 non-null    object
 3   Webpage                 104 non-null    object
 4   Img_ID                  104 non-null    object
 5   Img_URL                 104 non-null    object
 6   Legislation_By_Senator  104 non-null    object
 7   Party                   104 non-null    object
 8   Email                   104 non-null    object
 9   County(ies)             104 non-null    object
dtypes: int64(1), object(9)
memory usage: 8.3+ KB
```

### reps_with_geo_data

This is a file i created in google colab the script is
```commandline
scripts/extract_geo_data_for_districts.py
```
Info about the data the script gathers

#### house.geojson

```python
house_url = "https://services1.arcgis.com/99lidPhWCzftIe9K/arcgis/rest/services/UtahHouseDistricts2022to2032/FeatureServer/0/query"

params["f"] = "geojson"  # reuse params
response = requests.get(house_url, params=params)
with open("house.geojson", "wb") as f:
    f.write(response.content)

house_gdf = gpd.read_file("house.geojson")

house_gdf['District'] = house_gdf['DIST'].astype(int)
house_gdf['Chamber'] = "House"
house_gdf['DistrictKey'] = "H" + house_gdf['District'].astype(str)

print(house_gdf.columns)
house_gdf.head()
```

```commandline
<class 'geopandas.geodataframe.GeoDataFrame'>
RangeIndex: 75 entries, 0 to 74
Data columns (total 9 columns):
 #   Column         Non-Null Count  Dtype   
---  ------         --------------  -----   
 0   OBJECTID       75 non-null     int32   
 1   DIST           75 non-null     int32   
 2   COLOR4         75 non-null     int32   
 3   Shape__Area    75 non-null     float64 
 4   Shape__Length  75 non-null     float64 
 5   geometry       75 non-null     geometry
 6   District       75 non-null     int64   
 7   Chamber        75 non-null     object  
 8   DistrictKey    75 non-null     object  
dtypes: float64(2), geometry(1), int32(3), int64(1), object(2)
memory usage: 4.5+ KB
```
#### senate.geojson
```python
# Senate districts URL
senate_url = "https://services1.arcgis.com/99lidPhWCzftIe9K/arcgis/rest/services/UtahSenateDistricts2022to2032/FeatureServer/0/query"
params = {
    "where": "1=1",
    "outFields": "*",
    "outSR": "4326",
    "f": "geojson"   # <- request GeoJSON instead of JSON
}

# Request GeoJSON
response = requests.get(senate_url, params=params)
with open("senate.geojson", "wb") as f:
    f.write(response.content)

# Load into GeoDataFrame
senate_gdf = gpd.read_file("senate.geojson")

print(senate_gdf.columns)
senate_gdf.head()
```

```commandline
<class 'geopandas.geodataframe.GeoDataFrame'>
RangeIndex: 29 entries, 0 to 28
Data columns (total 9 columns):
 #   Column         Non-Null Count  Dtype   
---  ------         --------------  -----   
 0   OBJECTID       29 non-null     int32   
 1   DIST           29 non-null     int32   
 2   COLOR4         29 non-null     int32   
 3   Shape__Area    29 non-null     float64 
 4   Shape__Length  29 non-null     float64 
 5   geometry       29 non-null     geometry
 6   District       29 non-null     int64   
 7   Chamber        29 non-null     object  
 8   DistrictKey    29 non-null     object  
dtypes: float64(2), geometry(1), int32(3), int64(1), object(2)
memory usage: 1.8+ KB
```