import os
import asyncio
from dotenv import load_dotenv
from groq import Groq
from .LumaCrawl import crawl_venues as crawl_luma_venues
from .EventBriteCrawl import crawl_venues as crawl_eventbrite_venues
from .distance_calculator import get_lat_lng, calculate_distances
import pandas as pd

def extract_city_from_address(address: str) -> str:
    """
    Use Groq API to extract the city from a full address.
    
    Args:
        address (str): Full address string
        
    Returns:
        str: Extracted city name
    """
    load_dotenv()
    client = Groq(api_key=os.getenv('GROQ_API_KEY'))
    
    prompt = f"""Given the address "{address}", respond with ONLY the city name.
    Example: for "123 Main St, New York, NY 10001", respond with "New York" """
    
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that only responds with city names."
            },
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama-3.3-70b-versatile",
    )

    city = chat_completion.choices[0].message.content.strip()
    return city

async def scrape_EB_events(city: str, max_pages: int = 1):
    """
    Scrape events from Eventbrite for the given city
    
    Args:
        city (str): The city to scrape events for
        max_pages (int): Maximum number of pages to scrape (default: 1)
    """ 
    print("\nScraping Eventbrite events...")
    await crawl_eventbrite_venues(city=city, max_pages=max_pages)

async def scrape_luma_events(city: str):
    """
    Scrape events from Luma for the given city
    """
    print(f"\nStarting event scraping for {city}...")
    await crawl_luma_venues(city)

def find_nearby_events(reference_address: str, api_key: str, max_distance: float = 20) -> tuple[list, int]:
    """
    Find events near a reference address from both CSV files
    
    Args:
        reference_address (str): The address to find events near
        api_key (str): Google Maps API key
        max_distance (float): Maximum distance in miles (default: 10)
        
    Returns:
        tuple: (List of nearby events, Total number of locations compared)
    """
    # Get coordinates for reference address
    ref_coords = get_lat_lng(reference_address, api_key)
    if not ref_coords:
        return {"error": "Could not geocode the reference address"}, 0
    
    # Extract city from reference address
    city = extract_city_from_address(reference_address).lower()
    
    all_events = []
    total_comparisons = 0
    
    # Process Luma events
    luma_file = f"{city}_luma.csv"
    if os.path.exists(luma_file):
        luma_df = pd.read_csv(luma_file)
        luma_df['source'] = 'Luma'
        nearby_luma, luma_comparisons = calculate_distances(ref_coords, luma_df, api_key, max_distance)
        all_events.extend(nearby_luma)
        total_comparisons += luma_comparisons
    else:
        print(f"Warning: Luma events file {luma_file} not found")
    
    # Process Eventbrite events
    eb_file = f"{city}_EB.csv"
    if os.path.exists(eb_file):
        eb_df = pd.read_csv(eb_file)
        eb_df['source'] = 'Eventbrite'
        nearby_eb, eb_comparisons = calculate_distances(ref_coords, eb_df, api_key, max_distance)
        all_events.extend(nearby_eb)
        total_comparisons += eb_comparisons
    else:
        print(f"Warning: Eventbrite events file {eb_file} not found")
    
    if not all_events:
        return [], total_comparisons
    
    # Sort events by distance and get top 10
    all_events.sort(key=lambda x: x['distance'])
    return all_events[:10], total_comparisons

async def main():
    """
    Main function to orchestrate the entire workflow:
    1. Load environment variables
    2. Extract city from address
    3. Scrape events if needed
    4. Find and display nearby events
    """
    load_dotenv()
    
    # Get API keys
    gmaps_api_key = os.getenv('gmaps_api_key')
    if not gmaps_api_key:
        print("Error: Google Maps API key not found in .env file")
        return
    
    # Get company address
    address = "720 S Michigan Ave, Chicago, IL 60605"
    
    # Extract city from address
    print("\nExtracting city from address...")
    city = extract_city_from_address(address)
    print(f"Detected city: {city}")
    
    # Check if CSV files already exist
    luma_file = f"{city.lower()}_luma.csv"
    eb_file = f"{city.lower()}_EB.csv"
    
    if not os.path.exists(luma_file) or not os.path.exists(eb_file):
        print("\nScraping events data...")
        # Scrape events from both sources
        await scrape_luma_events(city)
        await scrape_EB_events(city=city, max_pages=1)
        
    else:
        print("\nUsing existing event data files...")
    
    # Verify files exist after scraping
    if not (os.path.exists(luma_file) and os.path.exists(eb_file)):
        print("\nError: Failed to create event data files.")
        return
    
    # Find nearby events using the distance calculator
    print("\nCalculating distances to nearby events...")
    events, total_comparisons = find_nearby_events(address, gmaps_api_key)
    
    # Display results
    if isinstance(events, dict) and "error" in events:
        print(f"\nError: {events['error']}")
    else:
        print(f"\nTop 10 Nearest Events (from {total_comparisons} total locations checked):")
        for i, event in enumerate(events, 1):
            print(f"\n{i}. {event['name']}")
            print(f"   Source: {event['source']}")
            print(f"   Distance: {event['distance']} miles")
            print(f"   Date: {event['date']}")
            print(f"   Address: {event['address']}")
            print(f"   URL: {event['url']}")

if __name__ == "__main__":
    asyncio.run(main()) 