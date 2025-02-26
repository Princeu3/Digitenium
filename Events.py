import streamlit as st
import asyncio
import os
from dotenv import load_dotenv
from EventsNearby.find_nearby_events import extract_city_from_address, scrape_luma_events, scrape_EB_events, find_nearby_events
import requests

# Initialize session state for address suggestions
if 'address_suggestions' not in st.session_state:
    st.session_state.address_suggestions = []

def get_place_suggestions(input_text, api_key):
    """Get address suggestions from Google Places API"""
    url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    params = {
        "input": input_text,
        "key": api_key,
        "types": "address"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        predictions = response.json().get("predictions", [])
        return [pred["description"] for pred in predictions]
    return []

# Page config
st.set_page_config(
    page_title="Events Nearby Finder",
    page_icon="🎭",
    layout="wide"
)

# Title and description
st.title("🎭 Events Nearby Finder")
st.write("Find events happening near any address!")

# Load environment variables
load_dotenv()
gmaps_api_key = os.getenv('gmaps_api_key')

# Input fields with autocomplete
address_input = st.text_input(
    "Enter an address:",
    placeholder="Start typing an address...",
    key="address_input"
)

# Add address autocomplete
if address_input:
    suggestions = get_place_suggestions(address_input, gmaps_api_key)
    if suggestions:
        selected_address = st.selectbox(
            "Select from suggested addresses:",
            suggestions,
            key="address_selector"
        )
        if selected_address:
            address = selected_address

max_pages = st.slider("Number of Eventbrite pages to scrape:", min_value=1, max_value=10, value=1)

if st.button("Find Events"):
    if not address:
        st.error("Please enter an address")
    else:
        # Create a status container
        status_container = st.empty()
        
        # Check for API keys
        gmaps_api_key = os.getenv('gmaps_api_key')
        if not gmaps_api_key:
            st.error("Error: Google Maps API key not found in .env file")
            st.stop()
            
        with st.spinner("Extracting city from address..."):
            try:
                city = extract_city_from_address(address)
                st.info(f"Detected city: {city}")
            except Exception as e:
                st.error(f"Error extracting city: {str(e)}")
                st.stop()
        
        # Check if CSV files already exist
        luma_file = f"{city.lower()}_luma.csv"
        eb_file = f"{city.lower()}_EB.csv"
        
        # Create progress bar
        progress_text = "Operation in progress. Please wait."
        progress_bar = st.progress(0, text=progress_text)
        
        if not os.path.exists(luma_file) or not os.path.exists(eb_file):
            status_container.info("Scraping events data...")
            # Run async operations
            async def run_scraping():
                try:
                    await scrape_luma_events(city)
                    progress_bar.progress(50, text="Scraped Luma events...")
                    status_container.info("Scraping Eventbrite events...")
                    
                    await scrape_EB_events(city=city, max_pages=max_pages)
                    progress_bar.progress(100, text="Finished scraping events!")
                except Exception as e:
                    st.error(f"Error during scraping: {str(e)}")
                    return False
                return True
            
            if not asyncio.run(run_scraping()):
                st.stop()
        else:
            status_container.info("Using existing event data files...")
            
        # Find and display nearby events
        with st.spinner("Calculating distances to nearby events..."):
            try:
                events, total_comparisons = find_nearby_events(address, gmaps_api_key)
                
                if isinstance(events, dict) and "error" in events:
                    st.error(f"Error: {events['error']}")
                elif not events:
                    st.warning("No events found within range.")
                else:
                    st.success(f"Found events! Checked {total_comparisons} total locations.")
                    
                    # Display events in a more organized way
                    st.subheader("Top 10 Nearest Events")
                    for i, event in enumerate(events, 1):
                        with st.expander(f"{i}. {event['name']} ({event['distance']} miles)"):
                            st.write(f"**Source:** {event['source']}")
                            st.write(f"**Date:** {event['date']}")
                            st.write(f"**Address:** {event['address']}")
                            st.write(f"**URL:** {event['url']}")
            except Exception as e:
                st.error(f"Error calculating distances: {str(e)}")
                st.stop() 