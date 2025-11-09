from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Tuple, Dict, Any
import httpx
import folium
from google.transit import gtfs_realtime_pb2
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import asyncio
from pathlib import Path

# Configure paths
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Debug: Print paths and verify they exist
print(f"BASE_DIR: {BASE_DIR}")
print(f"STATIC_DIR: {STATIC_DIR}")
print(f"STATIC_DIR exists: {STATIC_DIR.exists()}")
if STATIC_DIR.exists():
    print(f"STATIC_DIR contents: {list(STATIC_DIR.iterdir())}")
    resource_dir = STATIC_DIR / "resource"
    if resource_dir.exists():
        print(f"resource directory contents: {list(resource_dir.iterdir())}")

# Create FastAPI app with subpath support
app = FastAPI(
    title="DRT IdeaHack",
    description="Durham Region Transit Route Mapper",
    version="0.2.0",
    root_path="/drt-ideahack"
)

# Mount static files with html parameter to serve all file types
app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=False), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Durham Region center coordinates
DURHAM_CENTER = [43.8971, -78.8658]


async def fetch_vehicle_positions() -> List[Dict[str, Any]]:
    """Fetch real-time vehicle positions from DRT API"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://drtonline.durhamregiontransit.com/gtfsrealtime/VehiclePositions"
            )
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
        print(f"Error fetching vehicle positions: {e}")
        return []


async def fetch_static_routes() -> Dict[str, Any]:
    """Fetch static routes data from Durham Region Transit API"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://maps.durham.ca/arcgis/rest/services/Open_Data/Durham_OpenData/MapServer/20/query",
                params={
                    'outFields': '*',
                    'where': '1=1',
                    'f': 'geojson'
                }
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"Error fetching static routes: {e}")
        return {}


async def create_combined_map(source_coords: Tuple[float, float], dest_coords: Tuple[float, float]) -> folium.Map:
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
    
    # Add live vehicles (async call)
    vehicles = await fetch_vehicle_positions()
    vehicle_group = folium.FeatureGroup(name="Live Vehicles")
    for vehicle in vehicles:
        folium.CircleMarker(
            location=[vehicle["latitude"], vehicle["longitude"]],
            popup=f"Route ID: {vehicle['route_id']}, Vehicle ID: {vehicle['id']}",
            color="blue",
            fill=True,
            radius=6,
        ).add_to(vehicle_group)
    
    # Add static routes (async call)
    static_routes = await fetch_static_routes()
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


async def get_address_suggestions(query: str, country: str = "ca", max_results: int = 5) -> List[str]:
    """Get address suggestions using Nominatim"""
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
        await asyncio.sleep(1)
        return []
    except Exception as e:
        print(f"Error fetching suggestions: {e}")
        return []


async def geocode_selected_address(address: str) -> Tuple[float, float] | None:
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
            # Verify coordinates are within Durham Region bounds
            lat, lon = location.latitude, location.longitude
            durham_bounds = {
                'north': 44.3341,
                'south': 43.7429,
                'east': -78.5226,
                'west': -79.2647
            }
            
            if (durham_bounds['south'] <= lat <= durham_bounds['north'] and 
                durham_bounds['west'] <= lon <= durham_bounds['east']):
                print(f"Successfully geocoded address: {address} to {lat}, {lon}")
                return (lat, lon)
            else:
                print(f"Address {address} geocoded but outside Durham Region: {lat}, {lon}")
                return None
                
        print(f"Could not geocode address: {address}")
        return None
    except Exception as e:
        print(f"Geocoding error for {address}: {str(e)}")
        return None


# Routes

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Homepage"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/second_page", response_class=HTMLResponse)
async def second_page(request: Request):
    """Address selection page"""
    return templates.TemplateResponse("second_page.html", {"request": request})


@app.get("/address-suggestions")
async def address_suggestions(query: str = ""):
    """Get address suggestions based on query"""
    suggestions = await get_address_suggestions(query)
    return {"suggestions": suggestions}


@app.post("/get_map", response_class=HTMLResponse)
async def get_map(
    request: Request,
    source: str = Form(...),
    destination: str = Form(...)
):
    """Generate map based on source and destination"""
    if not source or not destination:
        return templates.TemplateResponse(
            "second_page.html",
            {
                "request": request,
                "error": "Both source and destination are required"
            }
        )

    try:
        # Try geocoding source address
        source_coords = await geocode_selected_address(source)
        if not source_coords:
            return templates.TemplateResponse(
                "second_page.html",
                {
                    "request": request,
                    "error": f"'{source}' not found in Durham Region. Please select from the suggested addresses."
                }
            )

        # Try geocoding destination address
        dest_coords = await geocode_selected_address(destination)
        if not dest_coords:
            return templates.TemplateResponse(
                "second_page.html",
                {
                    "request": request,
                    "error": f"'{destination}' not found in Durham Region. Please select from the suggested addresses."
                }
            )

        # Create and save map
        map_obj = await create_combined_map(source_coords, dest_coords)
        map_html = map_obj._repr_html_()

        return templates.TemplateResponse(
            "map.html",
            {
                "request": request,
                "source": source,
                "destination": destination,
                "source_coords": source_coords,
                "dest_coords": dest_coords,
                "map_created": True,
                "map_html": map_html
            }
        )
    except Exception as e:
        print(f"Error in get_map: {str(e)}")
        return templates.TemplateResponse(
            "second_page.html",
            {
                "request": request,
                "error": f"Error generating map: {str(e)}"
            }
        )


# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
