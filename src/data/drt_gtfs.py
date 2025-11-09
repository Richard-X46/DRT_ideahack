import requests
import folium
from typing import Dict, Any, List
from google.transit import gtfs_realtime_pb2
import pandas as pd
import pytz
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from pathlib import Path
import sys
# Add project root to Python path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))


# Center of Durham Region
durham_center = [43.8971, -78.8658]

# Fetch GTFS realtime data
response = requests.get("https://drtonline.durhamregiontransit.com/gtfsrealtime/VehiclePositions")
feed = gtfs_realtime_pb2.FeedMessage()
feed.ParseFromString(response.content)

# checking data in feed
response = requests.get(
    "https://drtonline.durhamregiontransit.com/gtfsrealtime/VehiclePositions"
)


# Extract vehicle positions
vehicles = []
for entity in feed.entity:
    if entity.HasField('vehicle'):
        vehicle = {
            'id': entity.vehicle.vehicle.id,
            'route_id': entity.vehicle.trip.route_id,
            'latitude': entity.vehicle.position.latitude,
            'longitude': entity.vehicle.position.longitude,
            'speed': entity.vehicle.position.speed if entity.vehicle.position.HasField('speed') else None,
            'timestamp': entity.vehicle.timestamp
        }
        vehicles.append(vehicle)



def plot_vehicles(vehicles: List[Dict[str, Any]], map_center: List[float], zoom_start: int = 12) -> folium.Map:
    """Plot vehicles on a map."""
    m = folium.Map(location=map_center, zoom_start=zoom_start)
    for vehicle in vehicles:
        folium.CircleMarker(
            location=[vehicle["latitude"], vehicle["longitude"]],
            popup=f"Route ID: {vehicle['route_id']}, Vehicle ID: {vehicle['id']}",
            color="green",
            fill=True,
            radius=8,
        ).add_to(m)
    return m


def fetch_static_routes() -> Dict[str, Any]:
    """Fetch static routes data from Durham Region Transit API."""
    url = "https://maps.durham.ca/arcgis/rest/services/Open_Data/Durham_OpenData/MapServer/20/query"
    params = {
        'outFields': '*',
        'where': '1=1',
        'f': 'geojson'
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def create_static_routes_map(geojson_data: Dict[str, Any], map_center: List[float], zoom_start: int = 11) -> folium.Map:
    """Create a map overlay using the GeoJSON data with route selection."""
    m = folium.Map(location=map_center, zoom_start=zoom_start)
    route_groups = {}
    for feature in geojson_data.get('features', []):
        route_name = feature['properties']['ROUTE_NAME']
        route_id = feature['properties']['ROUTE_ID']
        group_name = f"Route {route_id}: {route_name}"
        if group_name not in route_groups:
            route_groups[group_name] = folium.FeatureGroup(name=group_name)
        folium.GeoJson(
            feature,
            style_function=lambda x: {
                "color": "black",
                "weight": 3,
                "opacity": 0.6,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["ROUTE_NAME", "ROUTE_ID"],
                aliases=["Route Name", "Route ID"]
            )
        ).add_to(route_groups[group_name])
    for group in route_groups.values():
        group.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    return m


def create_combined_map(vehicles: List[Dict[str, Any]], geojson_data: Dict[str, Any], 
                        map_center: List[float], zoom_start: int = 11) -> folium.Map:
    """Create a combined map with both live vehicle positions and static routes."""
    m = folium.Map(location=map_center, zoom_start=zoom_start)
    
    # Create a feature group for live vehicles
    vehicle_group = folium.FeatureGroup(name="Live Vehicles")
    for vehicle in vehicles:
        folium.CircleMarker(
            location=[vehicle["latitude"], vehicle["longitude"]],
            popup=f"Route ID: {vehicle['route_id']}, Vehicle ID: {vehicle['id']}",
            color="green",
            fill=True,
            radius=8,
        ).add_to(vehicle_group)
    
    # Create feature groups for static routes
    route_groups = {}
    for feature in geojson_data.get('features', []):
        route_name = feature['properties']['ROUTE_NAME']
        route_id = feature['properties']['ROUTE_ID']
        group_name = f"Route {route_id}: {route_name}"
        if group_name not in route_groups:
            route_groups[group_name] = folium.FeatureGroup(name=group_name)
        folium.GeoJson(
            feature,
            style_function=lambda x: {
                "color": "black",
                "weight": 3,
                "opacity": 0.6,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["ROUTE_NAME", "ROUTE_ID"],
                aliases=["Route Name", "Route ID"]
            )
        ).add_to(route_groups[group_name])
    
    vehicle_group.add_to(m)
    for group in route_groups.values():
        group.add_to(m)
    
    folium.LayerControl(collapsed=False).add_to(m)
    return m


# get bus stops from opendata
def get_bus_stops() -> List[Dict[str, Any]]:
    """Fetch bus stops data from Durham Region Transit API."""
    url = "https://maps.durham.ca/arcgis/rest/services/Open_Data/Durham_OpenData/MapServer/0/query"
    params = {
        'outFields': '*',
        'where': '1=1',
        'f': 'geojson'
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json().get('features', [])




if __name__ == "__main__":
    # When running this file directly, fetch the static routes data then create the maps.
    static_routes_data = fetch_static_routes()
    vehicles_map = plot_vehicles(vehicles, durham_center)
    # vehicles_map.save("vehicles_map.html")
    
    static_routes_map = create_static_routes_map(static_routes_data, durham_center)
    # static_routes_map.save("static_routes_map.html")

    combined_map = create_combined_map(vehicles, static_routes_data, durham_center)
    # combined_map.save("combined_map.html")

    # print("Maps saved to vehicles_map.html, static_routes_map.html, and combined_map.html")





