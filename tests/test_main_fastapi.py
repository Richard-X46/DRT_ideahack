import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
import folium
from src.app.main_fastapi import (
    app,
    fetch_vehicle_positions,
    fetch_static_routes,
    create_combined_map,
    get_address_suggestions,
    geocode_selected_address,
)


@pytest.fixture
def client():
    """Create a test client for FastAPI"""
    return TestClient(app)


@pytest.fixture
def sample_vehicles():
    """Sample vehicle data for testing"""
    return [
        {
            "id": "vehicle_1",
            "route_id": "1",
            "latitude": 43.8971,
            "longitude": -78.8658,
            "speed": 25.0,
            "timestamp": 1616343600,
        },
        {
            "id": "vehicle_2",
            "route_id": "2",
            "latitude": 43.9000,
            "longitude": -78.8700,
            "speed": 30.0,
            "timestamp": 1616343601,
        }
    ]


@pytest.fixture
def sample_geojson():
    """Sample GeoJSON data for testing"""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"ROUTE_NAME": "Test Route", "ROUTE_ID": "1"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-78.8658, 43.8971], [-78.8659, 43.8972]],
                },
            }
        ],
    }


@pytest.fixture
def sample_coordinates():
    """Sample coordinate pairs for testing"""
    return {
        "source": (43.8971, -78.8658),
        "destination": (43.9000, -78.8700),
    }


# Test Routes

def test_index_route(client):
    """Test homepage route returns HTML"""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert b"<!DOCTYPE html>" in response.content or b"<html" in response.content


def test_second_page_route(client):
    """Test second page route returns HTML"""
    response = client.get("/second_page")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_address_suggestions_route(client):
    """Test address suggestions endpoint"""
    response = client.get("/address-suggestions?query=Durham")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert "suggestions" in response.json()


def test_address_suggestions_empty_query(client):
    """Test address suggestions with empty query"""
    response = client.get("/address-suggestions?query=")
    assert response.status_code == 200
    data = response.json()
    assert data["suggestions"] == []


def test_address_suggestions_short_query(client):
    """Test address suggestions with query less than 3 characters"""
    response = client.get("/address-suggestions?query=Du")
    assert response.status_code == 200
    data = response.json()
    assert data["suggestions"] == []


def test_get_map_missing_source(client):
    """Test get_map route with missing source"""
    response = client.post("/get_map", data={"destination": "123 Test St"})
    assert response.status_code == 422  # FastAPI validation error


def test_get_map_missing_destination(client):
    """Test get_map route with missing destination"""
    response = client.post("/get_map", data={"source": "123 Test St"})
    assert response.status_code == 422  # FastAPI validation error


@patch("src.app.main_fastapi.geocode_selected_address")
def test_get_map_invalid_source(mock_geocode, client):
    """Test get_map route with invalid source address"""
    mock_geocode.return_value = None
    response = client.post(
        "/get_map",
        data={"source": "Invalid Address", "destination": "123 Test St"}
    )
    assert response.status_code == 200
    assert b"not found" in response.content


@patch("src.app.main_fastapi.geocode_selected_address")
@patch("src.app.main_fastapi.create_combined_map")
def test_get_map_success(mock_map, mock_geocode, client):
    """Test get_map route with valid addresses"""
    # Mock geocoding
    mock_geocode.side_effect = [
        (43.8971, -78.8658),  # source
        (43.9000, -78.8700),  # destination
    ]
    
    # Mock map creation
    mock_folium_map = Mock(spec=folium.Map)
    mock_folium_map._repr_html_ = Mock(return_value="<div>Map HTML</div>")
    mock_map.return_value = mock_folium_map
    
    response = client.post(
        "/get_map",
        data={
            "source": "100 City Centre Dr, Mississauga",
            "destination": "200 King St, Oshawa"
        }
    )
    assert response.status_code == 200


# Test Async Functions

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_fetch_vehicle_positions_success(mock_get):
    """Test fetching vehicle positions successfully"""
    # Mock GTFS realtime response
    mock_response = Mock()
    mock_response.content = b""  # Empty GTFS feed for simplicity
    mock_get.return_value = mock_response
    
    with patch("src.app.main_fastapi.gtfs_realtime_pb2.FeedMessage") as mock_feed:
        mock_feed_instance = Mock()
        mock_feed_instance.entity = []
        mock_feed.return_value = mock_feed_instance
        
        result = await fetch_vehicle_positions()
        assert isinstance(result, list)


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_fetch_vehicle_positions_error(mock_get):
    """Test fetch_vehicle_positions handles errors gracefully"""
    mock_get.side_effect = Exception("API Error")
    
    result = await fetch_vehicle_positions()
    assert result == []


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_fetch_static_routes_success(mock_get, sample_geojson):
    """Test fetching static routes successfully"""
    mock_response = Mock()
    mock_response.json.return_value = sample_geojson
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    result = await fetch_static_routes()
    assert isinstance(result, dict)
    assert result.get("type") == "FeatureCollection"


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_fetch_static_routes_error(mock_get):
    """Test fetch_static_routes handles errors gracefully"""
    mock_get.side_effect = Exception("API Error")
    
    result = await fetch_static_routes()
    assert result == {}


@pytest.mark.asyncio
@patch("src.app.main_fastapi.fetch_vehicle_positions")
@patch("src.app.main_fastapi.fetch_static_routes")
async def test_create_combined_map(
    mock_routes, mock_vehicles, sample_vehicles, sample_geojson, sample_coordinates
):
    """Test creating combined map with all elements"""
    mock_vehicles.return_value = sample_vehicles
    mock_routes.return_value = sample_geojson
    
    result = await create_combined_map(
        sample_coordinates["source"],
        sample_coordinates["destination"]
    )
    
    assert isinstance(result, folium.Map)
    # Check that map has layer control
    controls = [
        child for child in result._children.values()
        if isinstance(child, folium.LayerControl)
    ]
    assert len(controls) > 0


@pytest.mark.asyncio
@patch("src.app.main_fastapi.fetch_vehicle_positions")
@patch("src.app.main_fastapi.fetch_static_routes")
async def test_create_combined_map_empty_data(mock_routes, mock_vehicles, sample_coordinates):
    """Test create_combined_map with empty vehicle and route data"""
    mock_vehicles.return_value = []
    mock_routes.return_value = {"type": "FeatureCollection", "features": []}
    
    result = await create_combined_map(
        sample_coordinates["source"],
        sample_coordinates["destination"]
    )
    
    assert isinstance(result, folium.Map)


@pytest.mark.asyncio
async def test_get_address_suggestions_valid():
    """Test getting address suggestions with valid query"""
    # This will make a real call to Nominatim - may want to mock in CI/CD
    result = await get_address_suggestions("Durham Ontario")
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_get_address_suggestions_short_query():
    """Test get_address_suggestions with query less than 3 chars"""
    result = await get_address_suggestions("Du")
    assert result == []


@pytest.mark.asyncio
async def test_get_address_suggestions_empty():
    """Test get_address_suggestions with empty query"""
    result = await get_address_suggestions("")
    assert result == []


@pytest.mark.asyncio
@patch("src.app.main_fastapi.Nominatim")
async def test_get_address_suggestions_timeout(mock_nominatim):
    """Test get_address_suggestions handles timeout"""
    from geopy.exc import GeocoderTimedOut
    
    mock_geolocator = Mock()
    mock_geolocator.geocode.side_effect = GeocoderTimedOut()
    mock_nominatim.return_value = mock_geolocator
    
    result = await get_address_suggestions("Durham")
    assert result == []


@pytest.mark.asyncio
@patch("src.app.main_fastapi.Nominatim")
async def test_geocode_selected_address_success(mock_nominatim):
    """Test geocoding a valid address in Durham Region"""
    mock_geolocator = Mock()
    mock_location = Mock()
    mock_location.latitude = 43.8971
    mock_location.longitude = -78.8658
    mock_geolocator.geocode.return_value = mock_location
    mock_nominatim.return_value = mock_geolocator
    
    result = await geocode_selected_address("100 City Centre Dr, Durham")
    assert result == (43.8971, -78.8658)


@pytest.mark.asyncio
@patch("src.app.main_fastapi.Nominatim")
async def test_geocode_selected_address_not_found(mock_nominatim):
    """Test geocoding with address not found"""
    mock_geolocator = Mock()
    mock_geolocator.geocode.return_value = None
    mock_nominatim.return_value = mock_geolocator
    
    result = await geocode_selected_address("NonExistent Address")
    assert result is None


@pytest.mark.asyncio
@patch("src.app.main_fastapi.Nominatim")
async def test_geocode_selected_address_outside_durham(mock_nominatim):
    """Test geocoding with address outside Durham Region"""
    mock_geolocator = Mock()
    mock_location = Mock()
    # Coordinates outside Durham bounds
    mock_location.latitude = 45.0000
    mock_location.longitude = -80.0000
    mock_geolocator.geocode.return_value = mock_location
    mock_nominatim.return_value = mock_geolocator
    
    result = await geocode_selected_address("123 Test St, Toronto")
    assert result is None


@pytest.mark.asyncio
@patch("src.app.main_fastapi.Nominatim")
async def test_geocode_selected_address_error(mock_nominatim):
    """Test geocode_selected_address handles errors gracefully"""
    mock_geolocator = Mock()
    mock_geolocator.geocode.side_effect = Exception("Geocoding Error")
    mock_nominatim.return_value = mock_geolocator
    
    result = await geocode_selected_address("Test Address")
    assert result is None


# Test Edge Cases

@pytest.mark.asyncio
@patch("src.app.main_fastapi.fetch_vehicle_positions")
@patch("src.app.main_fastapi.fetch_static_routes")
async def test_create_combined_map_same_coordinates(mock_routes, mock_vehicles):
    """Test create_combined_map when source and destination are the same"""
    mock_vehicles.return_value = []
    mock_routes.return_value = {"type": "FeatureCollection", "features": []}
    
    same_coords = (43.8971, -78.8658)
    result = await create_combined_map(same_coords, same_coords)
    
    assert isinstance(result, folium.Map)


def test_root_path_configuration():
    """Test that FastAPI app is configured with correct root_path"""
    assert app.root_path == "/drt-ideahack"


def test_app_metadata():
    """Test app metadata configuration"""
    assert app.title == "DRT IdeaHack"
    assert app.description == "Durham Region Transit Route Mapper"
    assert app.version == "0.2.0"
