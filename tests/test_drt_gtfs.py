import pytest
import folium
from unittest.mock import Mock, patch

from src.data.drt_gtfs import (
    plot_vehicles,
    fetch_static_routes,
    create_static_routes_map,
    create_combined_map,
    durham_center,
)


@pytest.fixture
def sample_vehicles():
    return [
        {
            "id": "vehicle_1",
            "route_id": "1",
            "latitude": 43.8971,
            "longitude": -78.8658,
            "speed": 25.0,
            "timestamp": 1616343600,
        }
    ]


@pytest.fixture
def sample_geojson():
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
def invalid_geojson_missing_features():
    return {"invalid": "data"}


@pytest.fixture
def invalid_geojson_missing_properties():
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},  # Missing ROUTE_NAME and ROUTE_ID
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-78.8658, 43.8971], [-78.8659, 43.8972]],
                },
            }
        ],
    }


def test_plot_vehicles(sample_vehicles):
    m = plot_vehicles(sample_vehicles, durham_center)
    assert isinstance(m, folium.Map)
    # Check that at least one circle marker is in the map
    markers = [
        child
        for child in m._children.values()
        if isinstance(child, folium.CircleMarker)
    ]
    assert markers


@patch("src.data.drt_gtfs.requests.get")
def test_fetch_static_routes(mock_get):
    dummy_geojson = {"type": "FeatureCollection", "features": []}
    dummy_response = Mock()
    dummy_response.json.return_value = dummy_geojson
    dummy_response.raise_for_status = Mock()
    mock_get.return_value = dummy_response

    result = fetch_static_routes()
    assert isinstance(result, dict)
    assert result.get("type") == "FeatureCollection"


def test_create_static_routes_map(sample_geojson):
    m = create_static_routes_map(sample_geojson, durham_center)
    assert isinstance(m, folium.Map)
    # Verify that LayerControl exists in the map's children
    controls = [
        child
        for child in m._children.values()
        if isinstance(child, folium.LayerControl)
    ]
    assert controls


def test_create_static_routes_map_invalid_geojson(invalid_geojson_missing_features):
    # When geojson doesn't have a 'features' key, it should still return a map with LayerControl
    m = create_static_routes_map(invalid_geojson_missing_features, durham_center)
    assert isinstance(m, folium.Map)
    controls = [
        child
        for child in m._children.values()
        if isinstance(child, folium.LayerControl)
    ]
    assert controls


def test_create_static_routes_map_missing_properties(
    invalid_geojson_missing_properties,
):
    with pytest.raises(KeyError):
        create_static_routes_map(invalid_geojson_missing_properties, durham_center)


def test_create_combined_map(sample_vehicles, sample_geojson):
    m = create_combined_map(sample_vehicles, sample_geojson, durham_center)
    assert isinstance(m, folium.Map)
    # Check for vehicle FeatureGroup (by checking if any child has name "Live Vehicles")
    vehicle_fg = any(
        hasattr(child, "layer_name") and child.layer_name == "Live Vehicles"
        for child in m._children.values()
    )
    assert vehicle_fg
    # Check that a LayerControl exists in the map
    controls = [
        child
        for child in m._children.values()
        if isinstance(child, folium.LayerControl)
    ]
    assert controls


def test_invalid_vehicle_data():
    with pytest.raises(TypeError):
        # Passing None should trigger an error when iterating over vehicles
        plot_vehicles(None, durham_center)


def test_plot_vehicles(sample_vehicles):
    """Test that plot_vehicles returns a Folium map with markers."""
    result = plot_vehicles(sample_vehicles, durham_center)
    assert isinstance(result, folium.Map)
    # Check that map contains at least one circle marker
    assert any(
        isinstance(child, folium.CircleMarker) for child in result._children.values()
    )


@patch("requests.get")
def test_fetch_static_routes(mock_get):
    """Test fetching static routes data."""
    mock_response = Mock()
    mock_response.json.return_value = {"type": "FeatureCollection", "features": []}
    mock_get.return_value = mock_response

    result = fetch_static_routes()
    assert isinstance(result, dict)
    assert "type" in result
    assert result["type"] == "FeatureCollection"


def test_create_static_routes_map(sample_geojson):
    """Test creating static routes map."""
    result = create_static_routes_map(sample_geojson, durham_center)
    assert isinstance(result, folium.Map)
    # Check that map contains layer control
    assert any(
        isinstance(child, folium.LayerControl) for child in result._children.values()
    )


def test_create_combined_map(sample_vehicles, sample_geojson):
    """Test creating combined map with both vehicles and routes."""
    result = create_combined_map(sample_vehicles, sample_geojson, durham_center)
    assert isinstance(result, folium.Map)
    # Check that map contains layer control
    assert any(
        isinstance(child, folium.LayerControl) for child in result._children.values()
    )
    # Check that map contains feature groups
    assert any(
        isinstance(child, folium.FeatureGroup) for child in result._children.values()
    )


def test_invalid_vehicle_data():
    """Test handling of invalid vehicle data."""
    with pytest.raises(TypeError):
        plot_vehicles(None, durham_center)


def test_invalid_geojson_data():
    """
    If geojson data does not have the expected 'features' key,
    the function should return a valid map (with no routes added) rather than raising an error.
    """
    invalid_geojson = {"invalid": "data"}
    result = create_static_routes_map(invalid_geojson, durham_center)
    assert isinstance(result, folium.Map)
    # LayerControl should still be added even if no features are processed.
    assert any(
        isinstance(child, folium.LayerControl) for child in result._children.values()
    )


def test_static_routes_map_empty_features():
    """Test create_static_routes_map returns a valid map when 'features' is an empty list."""
    empty_geojson = {"type": "FeatureCollection", "features": []}
    result = create_static_routes_map(empty_geojson, durham_center)
    assert isinstance(result, folium.Map)
    # LayerControl should be present even if no routes are added.
    assert any(
        isinstance(child, folium.LayerControl) for child in result._children.values()
    )


def test_static_routes_map_missing_properties():
    """
    Test create_static_routes_map raises a KeyError when a feature is missing
    the required properties (e.g., 'ROUTE_NAME' or 'ROUTE_ID').
    """
    invalid_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},  # Missing ROUTE_NAME and ROUTE_ID keys.
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-78.8658, 43.8971], [-78.8659, 43.8972]],
                },
            }
        ],
    }
    with pytest.raises(KeyError):
        create_static_routes_map(invalid_geojson, durham_center)


def test_combined_map_with_empty_data():
    """Test create_combined_map returns a valid map when provided with empty vehicles and geojson features."""
    empty_geojson = {"type": "FeatureCollection", "features": []}
    result = create_combined_map([], empty_geojson, durham_center)
    assert isinstance(result, folium.Map)
    # Even if no vehicles or routes, LayerControl should be present.
    assert any(
        isinstance(child, folium.LayerControl) for child in result._children.values()
    )
