from geopy.geocoders import Nominatim
from math import radians, cos, sin, asin, sqrt
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from typing import List
import time


def get_lat_lon_from_address(address: str):
    """Return latitude and longitude for a given address."""
    geolocator = Nominatim(user_agent="drt_app")
    location = geolocator.geocode(address)
    if location:
        return (location.latitude, location.longitude)
    else:
        raise ValueError("Address not found")


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on earth."""
    # convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers.
    return c * r


def find_nearest_bus_stop(user_location, bus_stops):
    """
    Given user's location (lat, lon) and a list of bus stops (each with lat, lon),
    return the stop closest to the user.
    """
    nearest_stop = None
    min_distance = float("inf")
    user_lat, user_lon = user_location
    for stop in bus_stops:
        stop_lat, stop_lon = stop["latitude"], stop["longitude"]
        distance = haversine_distance(user_lat, user_lon, stop_lat, stop_lon)
        if distance < min_distance:
            min_distance = distance
            nearest_stop = stop
    return nearest_stop






def get_address_suggestions(query: str, country: str = "ca", max_results: int = 5) -> List[str]:
    """
    Return address suggestions using Geopy/Nominatim.
    
    Args:
        query (str): Partial address to search for
        country (str): Country code to limit results (default: gb for UK)
        max_results (int): Maximum number of suggestions to return
    
    Returns:
        List[str]: List of suggested addresses
    """
    if len(query.strip()) < 3:
        return []
        
    geolocator = Nominatim(
        user_agent="drt_app",
        timeout=2
    )
    
    try:
        locations = geolocator.geocode(
            query,
            exactly_one=False,
            limit=max_results,
            country_codes=[country],
            addressdetails=True,
            language="en"
        )
        
        if not locations:
            return []
            
        # Format the addresses
        suggestions = [loc.address for loc in locations if   loc.raw.get('address', {}).get('state') == 'Ontario']
        return suggestions
        
    except GeocoderTimedOut:
        time.sleep(1)  # Respect rate limiting
        return []
    except Exception as e:
        print(f"Error fetching suggestions: {e}")
        return []




li = get_address_suggestions("99 Mary St ")







