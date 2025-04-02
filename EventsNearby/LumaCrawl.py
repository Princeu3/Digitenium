import asyncio
import csv
from dotenv import load_dotenv
from pydantic import BaseModel
from .URL_generator import get_luma_url
import json
from typing import List, Set
import os

load_dotenv()

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    LLMExtractionStrategy,
)

CSS_SELECTOR = "[class*='main-content-wrapper zm-container']"
REQUIRED_KEYS = [
    "name",
    "href",
]

class Venue(BaseModel):
    """
    Represents the data structure of an Event.
    """
    name: str
    url: str
    date: str
    address: str
    description: str

def save_venues_to_csv(venues: list, filename: str):
    if not venues:
        print("No venues to save.")
        return

    # Use field names from the Venue model
    fieldnames = Venue.model_fields.keys()

    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(venues)
    print(f"Saved {len(venues)} venues to '{filename}'.")

def is_duplicate_venue(venue_name: str, seen_names: set) -> bool:
    """
    Check if a venue name has already been processed.
    
    Args:
        venue_name (str): The name of the venue to check
        seen_names (set): Set of previously processed names
    
    Returns:
        bool: True if the name has been seen before, False otherwise
    """
    return venue_name in seen_names


def is_complete_venue(venue: dict, required_keys: list) -> bool:
    return all(key in venue for key in required_keys)

def get_browser_config() -> BrowserConfig:
    """
    Returns the browser configuration for the crawler.

    Returns:
        BrowserConfig: The configuration settings for the browser.
    """
    # https://docs.crawl4ai.com/core/browser-crawler-config/
    return BrowserConfig(
        browser_type="chromium",  # Type of browser to simulate
        headless=False,  # Whether to run in headless mode (no GUI)
        verbose=True,  # Enable verbose logging (False = No Logs)
    )


def get_llm_strategy(is_detail_page: bool = False) -> LLMExtractionStrategy:
    """
    Returns the configuration for the language model extraction strategy.
    """
    # Create a simplified schema for the initial list page
    list_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "href": {"type": "string"}
        },
        "required": ["name", "href"]
    }
    
    instruction = (
        "Extract all events with their names and links. For each event, get the 'name' and the 'href' (link) field. "
        "Make sure to capture all events visible on the page."
    ) if not is_detail_page else (
        "Extract the following information from the event page: "
        "name of the event, date of the event, address/location, "
        "and a brief description. Ensure the description is concise."
    )
    
    return LLMExtractionStrategy(
        provider="openai/gpt-3.5-turbo",
        api_token=os.getenv("OPENAI_API_KEY"),
        schema=list_schema if not is_detail_page else Venue.model_json_schema(),
        extraction_type="schema",
        instruction=instruction,
        input_format="markdown",
        verbose=True,
    )

async def fetch_event_details(
    crawler: AsyncWebCrawler,
    event_url: str,
    llm_strategy: LLMExtractionStrategy,
    session_id: str,
) -> dict:
    """
    Fetches detailed information from an individual event page.
    """
    # Clean the URL by removing any </ > characters
    cleaned_url = event_url.replace('<','').replace('>','')
    print(f"Fetching details for: {cleaned_url}")
    
    result = await crawler.arun(
        url=cleaned_url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=llm_strategy,
            session_id=session_id,
        ),
    )

    if not (result.success and result.extracted_content):
        print(f"Error fetching event details: {result.error_message}")
        return None

    event_data = json.loads(result.extracted_content)
    if isinstance(event_data, list) and event_data:
        return event_data[0]  # Take first result if list
    return event_data

async def fetch_and_process_page(
    crawler: AsyncWebCrawler,
    base_url: str,
    css_selector: str,
    llm_strategy: LLMExtractionStrategy,
    detail_llm_strategy: LLMExtractionStrategy,
    session_id: str,
    required_keys: List[str],
    seen_urls: Set[str],
) -> List[dict]:
    """
    Fetches and processes venue data from the infinite scroll page.
    """

    print(f"Processing venues from {base_url}...")
    
    # Add a set to track seen venue names
    seen_names = set()

    # Custom JavaScript to scroll down and wait for new content to load
    scroll_js = """
    async function scrollToBottom() {
        const scrollHeight = document.body.scrollHeight;
        window.scrollTo(0, scrollHeight);
        return new Promise(resolve => setTimeout(resolve, 2000));
    }
    
    // Scroll several times to load more content
    for (let i = 0; i < 5; i++) {
        await scrollToBottom();
        console.log("Scrolled to bottom, waiting for content to load...");
    }
    
    return true;
    """

    result = await crawler.arun(
        url=base_url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=llm_strategy,
            css_selector=css_selector,
            session_id=session_id,
            scan_full_page=True,  # Enable full page scanning
            scroll_delay=3,  # Delay between auto-scrolls
            js_code=scroll_js,  # Custom scrolling logic
            wait_until="networkidle",  # Wait for network to be idle
            page_timeout=60000,  # Increase page timeout to 60 seconds
        ),
    )

    if not (result.success and result.extracted_content):
        print(f"Error fetching page: {result.error_message}")
        return []

    extracted_data = json.loads(result.extracted_content)
    if not extracted_data:
        print("No venues found.")
        return []

    print("Extracted data:", extracted_data)

    # Process venues
    complete_venues = []
    for venue in extracted_data:
        # Remove the error field if present
        venue.pop('error', None)
        
        # Skip venues without required fields
        if not is_complete_venue(venue, required_keys):
            print(f"Skipping incomplete venue: {venue}")
            continue

        # Skip empty names
        if not venue.get("name", "").strip():
            print("Skipping venue with empty name")
            continue

        if is_duplicate_venue(venue["name"], seen_names):
            print(f"Duplicate venue name '{venue['name']}' found. Skipping.")
            continue

        # Add the venue name to seen_names after checking
        seen_names.add(venue["name"])

        # Map href to url
        venue["url"] = venue.pop("href")

        # Fetch detailed information
        detailed_info = await fetch_event_details(
            crawler,
            venue["url"],
            detail_llm_strategy,
            session_id
        )
        
        if detailed_info:
            detailed_info.pop('error', None)
            venue.update(detailed_info)
            seen_urls.add(venue["url"])
            complete_venues.append(venue)
            
            await asyncio.sleep(1)

    print(f"Extracted {len(complete_venues)} venues.")
    return complete_venues

async def crawl_venues(city: str):
    """
    Main function to crawl venue data from the website.
    
    Args:
        city (str): The city to search events for
    """
    BASE_URL = get_luma_url(city)
    
    browser_config = get_browser_config()
    list_llm_strategy = get_llm_strategy(is_detail_page=False)
    detail_llm_strategy = get_llm_strategy(is_detail_page=True)
    session_id = f"luma_crawl_session_{city}"

    all_venues = []
    seen_urls = set()

    async with AsyncWebCrawler(config=browser_config) as crawler:
        print(f"Crawling venues for {city}")
        
        venues = await fetch_and_process_page(
            crawler,
            BASE_URL,
            CSS_SELECTOR,
            list_llm_strategy,
            detail_llm_strategy,
            session_id,
            REQUIRED_KEYS,
            seen_urls,
        )

        if venues:
            all_venues.extend(venues)

    # Save the collected venues to a CSV file with city name
    if all_venues:
        filename = f"{city.lower()}_luma.csv"
        save_venues_to_csv(all_venues, filename)
        print(f"Saved {len(all_venues)} venues to '{filename}'.")
    else:
        print(f"No venues were found during the crawl for {city}.")

    list_llm_strategy.show_usage()

async def main():
    """
    Entry point of the script.
    """
    city = "Chicago"  # You can change this to any city
    await crawl_venues(city=city)


if __name__ == "__main__":
    asyncio.run(main())
