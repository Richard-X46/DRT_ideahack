import requests
import folium
from typing import Dict, Any, List
from google.transit import gtfs_realtime_pb2

"""
1. Create two overlays: live transit bus data and static transit overlay.
2. Use GTFS Realtime Vehicle Positions for live data.
    - provide a drop down menu to select routes,multi-select dropdown
    - show route name and route id in the tooltip
3. Use GeoJSON for static routes.
   - provide a drop down menu to select routes,multi-select dropdown
   - show route name and route id in the tooltip
"""


# Center of Durham Region
durham_center = [43.8971, -78.8658]


# Fetch GTFS realtime data
response = requests.get("https://drtonline.durhamregiontransit.com/gtfsrealtime/VehiclePositions")
feed = gtfs_realtime_pb2.FeedMessage()
feed.ParseFromString(response.content)

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


# plot the vehicles on a map
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


# Fetch static routes data
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

static_routes_data = fetch_static_routes()




def create_static_routes_map(geojson_data: Dict[str, Any], map_center: List[float], zoom_start: int = 11) -> folium.Map:
    """Create a map overlay using the GeoJSON data with route selection."""
    m = folium.Map(location=map_center, zoom_start=zoom_start)
    
    # Create a feature group for all routes
    route_groups = {}
    
    # Extract unique routes from the GeoJSON data
    for feature in geojson_data['features']:
        route_name = feature['properties']['ROUTE_NAME']
        route_id = feature['properties']['ROUTE_ID']
        
        # Create a feature group for this route if it doesn't exist
        group_name = f"Route {route_id}: {route_name}"
        if group_name not in route_groups:
            route_groups[group_name] = folium.FeatureGroup(name=group_name)
        
        # Add this route to its feature group
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
    
    # Add all feature groups to the map
    for group in route_groups.values():
        group.add_to(m)
    
    # Add layer control with collapsed view
    folium.LayerControl(collapsed=False).add_to(m)
    
    return m

# Create map with static routes
static_routes_map = create_static_routes_map(static_routes_data, durham_center)
static_routes_map


# combine the two maps


def create_combined_map(vehicles: List[Dict[str, Any]], geojson_data: Dict[str, Any], 
                       map_center: List[float], zoom_start: int = 11) -> folium.Map:
    """Create a combined map with both live vehicle positions and static routes."""
    # Initialize the base map
    m = folium.Map(location=map_center, zoom_start=zoom_start)
    
    # Create a feature group for vehicles
    vehicle_group = folium.FeatureGroup(name="Live Vehicles")
    
    # Add vehicles to their group
    for vehicle in vehicles:
        folium.CircleMarker(
            location=[vehicle["latitude"], vehicle["longitude"]],
            popup=f"Route ID: {vehicle['route_id']}, Vehicle ID: {vehicle['id']}",
            color="green",
            fill=True,
            radius=8,
        ).add_to(vehicle_group)
    
    # Create feature groups for routes
    route_groups = {}
    
    # Add routes to their respective groups
    for feature in geojson_data['features']:
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
    
    # Add all groups to the map
    vehicle_group.add_to(m)
    for group in route_groups.values():
        group.add_to(m)
    
    # Add layer control
    folium.LayerControl(collapsed=False).add_to(m)
    
    return m



# usage

if __name__ == "__main__":
    # Create map with vehicles
    vehicles_map = plot_vehicles(vehicles, durham_center)

    # Create map with static routes
    static_routes_map = create_static_routes_map(static_routes_data, durham_center)
    
    # Create combined map
    combined_map = create_combined_map(vehicles, static_routes_data, durham_center)
