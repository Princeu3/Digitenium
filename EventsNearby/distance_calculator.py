import requests
import math
import urllib.parse
import pandas as pd
from datetime import datetime
import os

def to_radians(degrees):
    """Convert degrees to radians"""
    return degrees * (math.pi / 180)

def haversine(p, q):
    """Calculate the distance between two points using the haversine formula"""
    R = 6371  # Earth's radius in km
    
    lat_dist = to_radians(q['lat'] - p['lat'])
    lng_dist = to_radians(q['lng'] - p['lng'])
    q_lat = to_radians(q['lat'])
    p_lat = to_radians(p['lat'])
    
    a = (math.sin(lat_dist/2) * math.sin(lat_dist/2) + 
         math.sin(lng_dist/2) * math.sin(lng_dist/2) * 
         math.cos(q_lat) * math.cos(p_lat))
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = R * c
    
    return d / 1.6  # Convert to miles

def get_lat_lng(address, api_key):
    """Get latitude and longitude for an address using Google Maps Geocoding API"""
    encoded_address = urllib.parse.quote(address)
    url = (f"https://maps.googleapis.com/maps/api/geocode/json?"
           f"address={encoded_address}&key={api_key}")
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data['status'] == 'OK':
            location = data['results'][0]['geometry']['location']
            return {
                'lat': location['lat'],
                'lng': location['lng']
            }
        else:
            print(f"Geocoding error: {data['status']}")
            return None
            
    except Exception as e:
        print(f"Error getting coordinates: {str(e)}")
        return None

def calculate_distances(reference_coords, events_df, api_key, max_distance=10):
    """
    Calculate distances for a set of events from a reference point
    
    Parameters:
    reference_coords: dict, containing 'lat' and 'lng' of reference point
    events_df: pandas DataFrame containing events
    api_key: str, Google Maps API key
    max_distance: float, maximum distance in miles to search
    
    Returns:
    list: Events within max_distance, sorted by distance
    int: Number of comparisons made
    """
    nearby_events = []
    comparisons_made = 0
    
    for _, event in events_df.iterrows():
        try:
            event_coords = get_lat_lng(event['address'], api_key)
            comparisons_made += 1
            if event_coords:
                distance = haversine(reference_coords, event_coords)
                if distance <= max_distance:
                    nearby_events.append({
                        'source': event.get('source', 'Unknown'),
                        'name': event['name'],
                        'date': event.get('start_date', event.get('date', 'N/A')),
                        'address': event['address'],
                        'distance': round(distance, 2),
                        'url': event.get('url', event.get('href', 'N/A'))
                    })
        except Exception as e:
            print(f"Error processing event: {str(e)}")
            continue
    
    return nearby_events, comparisons_made

