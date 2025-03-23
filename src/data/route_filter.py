import requests
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import numpy as np
import folium
from typing import Dict, Any, List



def geocode_address(address: str) -> tuple[float, float]:
    """Convert address to coordinates."""
    geolocator = Nominatim(user_agent="drt_transit_app")
    location = geolocator.geocode(f"{address}, Durham Region, Ontario")
    if location:
        return (location.latitude, location.longitude)
    raise ValueError(f"Could not geocode address: {address}")

def find_closest_stop(point: tuple[float, float], stops_data: Dict[str, Any]) -> Dict[str, Any]:
    """Find the closest bus stop to a given point."""
    closest_stop = None
    min_distance = float('inf')
    
    for feature in stops_data.get('features', []):
        stop_coords = feature['geometry']['coordinates']
        stop_point = (stop_coords[1], stop_coords[0])  # Convert from [lon, lat] to [lat, lon]
        distance = geodesic(point, stop_point).kilometers
        
        if distance < min_distance:
            min_distance = distance
            closest_stop = {
                'stop_id': feature['properties']['STOP_ID'],
                'stop_name': feature['properties']['STOP_NAME'],
                'coordinates': stop_point,
                'distance': distance
            }
    
    return closest_stop

def filter_relevant_routes(point_a: tuple[float, float], 
                         point_b: tuple[float, float],
                         geojson_data: Dict[str, Any],
                         max_distance_km: float = 1.0) -> List[str]:
    """Filter routes that are relevant for the journey between two points."""
    relevant_route_ids = []
    
    # Create a bounding box between points A and B
    min_lat = min(point_a[0], point_b[0])
    max_lat = max(point_a[0], point_b[0])
    min_lon = min(point_a[1], point_b[1])
    max_lon = max(point_a[1], point_b[1])
    
    # Add some padding to the bounding box
    padding = max_distance_km / 111  # Rough conversion from km to degrees
    min_lat -= padding
    max_lat += padding
    min_lon -= padding
    max_lon += padding
    
    for feature in geojson_data.get('features', []):
        coordinates = feature['geometry']['coordinates']
        route_id = feature['properties']['ROUTE_ID']
        
        # Check if any part of the route falls within our bounding box
        for coord_group in coordinates:
            for coord in coord_group:
                lon, lat = coord
                if (min_lat <= lat <= max_lat and 
                    min_lon <= lon <= max_lon):
                    relevant_route_ids.append(route_id)
                    break
            if route_id in relevant_route_ids:
                break
    
    return list(set(relevant_route_ids))

def create_journey_map(point_a: tuple[float, float],
                      point_b: tuple[float, float],
                      vehicles: List[Dict[str, Any]],
                      geojson_data: Dict[str, Any],
                      stops_data: Dict[str, Any],
                      map_center: List[float],
                      zoom_start: int = 11) -> folium.Map:
    """Create a map showing the journey-specific routes and vehicles."""
    m = folium.Map(location=map_center, zoom_start=zoom_start)
    
    # Find relevant routes
    relevant_routes = filter_relevant_routes(point_a, point_b, geojson_data)
    
    # Add markers for points A and B
    folium.Marker(
        location=point_a,
        popup='Start Point',
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)
    
    folium.Marker(
        location=point_b,
        popup='End Point',
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)
    
    # Find and mark closest stops
    start_stop = find_closest_stop(point_a, stops_data)
    end_stop = find_closest_stop(point_b, stops_data)
    
    if start_stop:
        folium.Marker(
            location=start_stop['coordinates'],
            popup=f"Nearest Stop: {start_stop['stop_name']} ({start_stop['distance']:.2f} km)",
            icon=folium.Icon(color='green', icon='bus')
        ).add_to(m)
    
    if end_stop:
        folium.Marker(
            location=end_stop['coordinates'],
            popup=f"Nearest Stop: {end_stop['stop_name']} ({end_stop['distance']:.2f} km)",
            icon=folium.Icon(color='green', icon='bus')
        ).add_to(m)
    
    # Add filtered routes and vehicles
    vehicle_group = folium.FeatureGroup(name="Live Vehicles")
    for vehicle in vehicles:
        if vehicle['route_id'] in relevant_routes:
            folium.CircleMarker(
                location=[vehicle["latitude"], vehicle["longitude"]],
                popup=f"Route ID: {vehicle['route_id']}, Vehicle ID: {vehicle['id']}",
                color="blue",
                fill=True,
                radius=8,
            ).add_to(vehicle_group)
    
    route_groups = {}
    for feature in geojson_data.get('features', []):
        route_id = feature['properties']['ROUTE_ID']
        if route_id in relevant_routes:
            route_name = feature['properties']['ROUTE_NAME']
            group_name = f"Route {route_id}: {route_name}"
            if group_name not in route_groups:
                route_groups[group_name] = folium.FeatureGroup(name=group_name)
            folium.GeoJson(
                feature,
                style_function=lambda x: {
                    "color": "purple",
                    "weight": 3,
                    "opacity": 0.8,
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

