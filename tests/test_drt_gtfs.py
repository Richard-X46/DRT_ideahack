import pytest
import folium
from unittest.mock import Mock, patch
from src.data.drt_gtfs import (
    plot_vehicles, 
    fetch_static_routes, 
    create_static_routes_map,
    create_combined_map,
    durham_center
)

@pytest.fixture
def sample_vehicles():
    return [
        {
            'id': 'test_vehicle_1',
            'route_id': 'route_1',
            'latitude': 43.8971,
            'longitude': -78.8658,
            'speed': 30.0,
            'timestamp': 1616343600
        }
    ]

@pytest.fixture
def sample_geojson():
    return {
        'type': 'FeatureCollection',
        'features': [
            {
                'type': 'Feature',
                'properties': {
                    'ROUTE_NAME': 'Test Route',
                    'ROUTE_ID': '1'
                },
                'geometry': {
                    'type': 'LineString',
                    'coordinates': [[-78.8658, 43.8971], [-78.8659, 43.8972]]
                }
            }
        ]
    }

def test_plot_vehicles(sample_vehicles):
    """Test that plot_vehicles returns a Folium map with markers."""
    result = plot_vehicles(sample_vehicles, durham_center)
    assert isinstance(result, folium.Map)
    # Check that map contains at least one circle marker
    assert any(isinstance(child, folium.CircleMarker) 
              for child in result._children.values())

@patch('requests.get')
def test_fetch_static_routes(mock_get):
    """Test fetching static routes data."""
    mock_response = Mock()
    mock_response.json.return_value = {'type': 'FeatureCollection', 'features': []}
    mock_get.return_value = mock_response
    
    result = fetch_static_routes()
    assert isinstance(result, dict)
    assert 'type' in result
    assert result['type'] == 'FeatureCollection'

def test_create_static_routes_map(sample_geojson):
    """Test creating static routes map."""
    result = create_static_routes_map(sample_geojson, durham_center)
    assert isinstance(result, folium.Map)
    # Check that map contains layer control
    assert any(isinstance(child, folium.LayerControl) 
              for child in result._children.values())

def test_create_combined_map(sample_vehicles, sample_geojson):
    """Test creating combined map with both vehicles and routes."""
    result = create_combined_map(sample_vehicles, sample_geojson, durham_center)
    assert isinstance(result, folium.Map)
    # Check that map contains layer control
    assert any(isinstance(child, folium.LayerControl) 
              for child in result._children.values())
    # Check that map contains feature groups
    assert any(isinstance(child, folium.FeatureGroup) 
              for child in result._children.values())

def test_invalid_vehicle_data():
    """Test handling of invalid vehicle data."""
    with pytest.raises(TypeError):
        plot_vehicles(None, durham_center)

def test_invalid_geojson_data():
    """Test handling of invalid GeoJSON data."""
    with pytest.raises(KeyError):
        create_static_routes_map({'invalid': 'data'}, durham_center)