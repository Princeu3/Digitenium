import streamlit as st
import asyncio
import os
import pandas as pd
from dotenv import load_dotenv
from EventsNearby.find_nearby_events import extract_city_from_address, scrape_luma_events, scrape_EB_events, find_nearby_events
import requests

# Initialize session state for address suggestions
if 'address_suggestions' not in st.session_state:
    st.session_state.address_suggestions = []
if 'selected_address' not in st.session_state:
    st.session_state.selected_address = ""

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

def remove_duplicates_from_csv(file_path):
    """Remove duplicate entries from CSV files based on event name and URL"""
    if not os.path.exists(file_path):
        return False
    
    try:
        # Read the CSV file
        df = pd.read_csv(file_path)
        
        # Check if the dataframe is empty
        if df.empty:
            return False
            
        # Count rows before deduplication
        rows_before = len(df)
        
        # Remove duplicates based on name and URL (if these columns exist)
        dedup_columns = []
        if 'name' in df.columns:
            dedup_columns.append('name')
            
        if dedup_columns:
            df = df.drop_duplicates(subset=dedup_columns)
        else:
            # If neither column exists, drop complete duplicates
            df = df.drop_duplicates()
            
        # Count rows after deduplication
        rows_after = len(df)
        
        # Save the cleaned dataframe back to the CSV
        df.to_csv(file_path, index=False)
        
        return rows_before - rows_after  # Return number of duplicates removed
    except Exception as e:
        st.warning(f"Error cleaning {file_path}: {str(e)}")
        return False

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
    key="address_input",
    on_change=None
)

# Update suggestions when address input changes
if address_input:
    st.session_state.address_suggestions = get_place_suggestions(address_input, gmaps_api_key)

# Display dropdown for address suggestions
address = address_input  # Default to what user typed
if st.session_state.address_suggestions:
    selected_address = st.selectbox(
        "Select an address:",
        options=st.session_state.address_suggestions,
        key="address_dropdown"
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
                luma_success = False
                
                # Try to scrape Luma events first
                try:
                    status_container.info("Scraping Luma events...")
                    await scrape_luma_events(city)
                    progress_bar.progress(50, text="Scraped Luma events...")
                    luma_success = True
                except Exception as e:
                    st.warning(f"Luma events not available for {city}. Reason: {str(e)}")
                    progress_bar.progress(50, text="Luma events not available, trying Eventbrite...")
                
                # Always try to scrape Eventbrite events
                try:
                    status_container.info("Scraping Eventbrite events...")
                    await scrape_EB_events(city=city, max_pages=max_pages)
                    progress_bar.progress(100, text="Finished scraping events!")
                except Exception as e:
                    if not luma_success:
                        st.error(f"Error: Could not retrieve events from either Luma or Eventbrite. {str(e)}")
                        return False
                    else:
                        st.warning(f"Eventbrite scraping failed, but Luma events were retrieved. {str(e)}")
                
                return True
            
            if not asyncio.run(run_scraping()):
                st.stop()
        else:
            status_container.info("Using existing event data files...")
            
        # Clean CSV files to remove duplicates
        with st.spinner("Cleaning event data..."):
            luma_dupes = remove_duplicates_from_csv(luma_file) if os.path.exists(luma_file) else 0
            eb_dupes = remove_duplicates_from_csv(eb_file) if os.path.exists(eb_file) else 0
            
            if luma_dupes or eb_dupes:
                st.info(f"Removed {luma_dupes} duplicate Luma events and {eb_dupes} duplicate Eventbrite events.")
            
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