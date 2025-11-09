from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from typing import List, Tuple, Dict, Any
import time
from pathlib import Path
import sys
import os
import requests
import folium
import pandas as pd
from google.transit import gtfs_realtime_pb2

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
import src.data.drt_gtfs as gtfs
from flask import Flask, render_template, jsonify, request, flash, redirect, url_for


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
app.config["MIME_TYPES"] = {"avif": "image/avif"}
# Durham Region center coordinates
DURHAM_CENTER = [43.8971, -78.8658]

def fetch_vehicle_positions() -> List[Dict[str, Any]]:
    """Fetch real-time vehicle positions from DRT API"""
    try:
        response = requests.get("https://drtonline.durhamregiontransit.com/gtfsrealtime/VehiclePositions")
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        
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
        return vehicles
    except Exception as e:
        app.logger.error(f"Error fetching vehicle positions: {e}")
        return []

def fetch_static_routes() -> Dict[str, Any]:
    """Fetch static routes data from Durham Region Transit API"""
    try:
        url = "https://maps.durham.ca/arcgis/rest/services/Open_Data/Durham_OpenData/MapServer/20/query"
        params = {
            'outFields': '*',
            'where': '1=1',
            'f': 'geojson'
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        app.logger.error(f"Error fetching static routes: {e}")
        return {}

def create_combined_map(source_coords: Tuple[float, float], dest_coords: Tuple[float, float]) -> folium.Map:
    """Create a combined map with source, destination, live vehicles, and static routes"""
    # Calculate center point between source and destination
    center_lat = (source_coords[0] + dest_coords[0]) / 2
    center_lng = (source_coords[1] + dest_coords[1]) / 2
    
    # Create base map
    m = folium.Map(location=[center_lat, center_lng], zoom_start=12)
    
    # Add source and destination markers
    folium.Marker(
        source_coords,
        popup='Source',
        icon=folium.Icon(color='green', icon='info-sign')
    ).add_to(m)
    
    folium.Marker(
        dest_coords,
        popup='Destination',
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)
    
    # Add live vehicles
    vehicles = fetch_vehicle_positions()
    vehicle_group = folium.FeatureGroup(name="Live Vehicles")
    for vehicle in vehicles:
        folium.CircleMarker(
            location=[vehicle["latitude"], vehicle["longitude"]],
            popup=f"Route ID: {vehicle['route_id']}, Vehicle ID: {vehicle['id']}",
            color="blue",
            fill=True,
            radius=6,
        ).add_to(vehicle_group)
    
    # Add static routes
    static_routes = fetch_static_routes()
    route_groups = {}
    for feature in static_routes.get('features', []):
        route_name = feature['properties']['ROUTE_NAME']
        route_id = feature['properties']['ROUTE_ID']
        group_name = f"Route {route_id}: {route_name}"
        if group_name not in route_groups:
            route_groups[group_name] = folium.FeatureGroup(name=group_name)
        folium.GeoJson(
            feature,
            style_function=lambda x: {
                "color": "orange",
                "weight": 3,
                "opacity": 0.8,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["ROUTE_NAME", "ROUTE_ID"],
                aliases=["Route Name", "Route ID"]
            )
        ).add_to(route_groups[group_name])
    
    # Add all layers to map
    vehicle_group.add_to(m)
    for group in route_groups.values():
        group.add_to(m)
    
    # Add layer control
    folium.LayerControl(collapsed=False).add_to(m)
    
    return m




def get_address_suggestions(query: str, country: str = "ca", max_results: int = 5) -> List[str]:
    if len(query.strip()) < 3:
        return []

    geolocator = Nominatim(user_agent="drt_app", timeout=2)

    try:
        locations = geolocator.geocode(
            query,
            exactly_one=False,
            limit=max_results,
            country_codes=[country],
            addressdetails=True,
            language="en",
        )

        if not locations:
            return []

        suggestions = [
            loc.address
            for loc in locations
            if loc.raw.get("address", {}).get("state") == "Ontario"
        ]
        return suggestions

    except GeocoderTimedOut:
        time.sleep(1)
        return []
    except Exception as e:
        app.logger.error(f"Error fetching suggestions: {e}")
        return []

def geocode_selected_address(address: str) -> Tuple[float, float]:
    """Geocode an address with better error handling and Durham Region focus"""
    try:
        geolocator = Nominatim(user_agent="drt_app", timeout=10)
        
        # First try with exact address
        location = geolocator.geocode(
            address,
            exactly_one=True,
            country_codes=["ca"],
            language="en",
        )
        
        # If not found, try with Durham Region
        if not location:
            location = geolocator.geocode(
                f"{address}, Durham Region, Ontario, Canada",
                exactly_one=True,
                country_codes=["ca"],
                language="en",
            )
        
        if location:
            # Verify coordinates are within Durham Region bounds (with some flexibility)
            lat, lon = location.latitude, location.longitude
            durham_bounds = {
                'north': 44.3341,  # Extended bounds
                'south': 43.7429,  # Extended bounds
                'east': -78.5226,  # Extended bounds
                'west': -79.2647   # Extended bounds
            }
            
            if (durham_bounds['south'] <= lat <= durham_bounds['north'] and 
                durham_bounds['west'] <= lon <= durham_bounds['east']):
                app.logger.info(f"Successfully geocoded address: {address} to {lat}, {lon}")
                return (lat, lon)
            else:
                app.logger.warning(f"Address {address} geocoded but outside Durham Region: {lat}, {lon}")
                return None
                
        app.logger.error(f"Could not geocode address: {address}")
        return None
    except Exception as e:
        app.logger.error(f"Geocoding error for {address}: {str(e)}")
        return None
    



@app.route('/')
def index():
    return render_template('index.html')

@app.route("/second_page")
def second_page():
    return render_template("second_page.html")


@app.route('/address-suggestions')
def address_suggestions():
    query = request.args.get('query', '')
    suggestions = get_address_suggestions(query)
    return jsonify({'suggestions': suggestions})


@app.route("/get_map", methods=["POST"])
def get_map():
    source = request.form.get("source")
    destination = request.form.get("destination")

    if not source or not destination:
        flash("Both source and destination are required")
        return redirect(url_for("second_page"))

    try:
        # Create static folder if it doesn't exist
        static_folder = os.path.join(os.path.dirname(__file__), "static")
        os.makedirs(static_folder, exist_ok=True)

        # Try geocoding source address
        source_coords = geocode_selected_address(source)
        if not source_coords:
            flash(
                f"'{source}' not found in Durham Region. Please select from the suggested addresses."
            )
            return redirect(url_for("second_page"))

        # Try geocoding destination address
        dest_coords = geocode_selected_address(destination)
        if not dest_coords:
            flash(
                f"'{destination}' not found in Durham Region. Please select from the suggested addresses."
            )
            return redirect(url_for("second_page"))

        # Create and save map
        map_obj = create_combined_map(source_coords, dest_coords)
        map_path = os.path.join(static_folder, "temp_map.html")
        map_obj.save(map_path)

        return render_template(
            "map.html",
            source=source,
            destination=destination,
            source_coords=source_coords,
            dest_coords=dest_coords,
            map_created=True,
        )
    except Exception as e:
        app.logger.error(f"Error in get_map: {str(e)}")
        flash(f"Error generating map: {str(e)}")
        return redirect(url_for("second_page"))
    


# if __name__ == "__main__":
#     app.run(debug=True,host = "0.0.0.0", port=5002)


