import asyncio
import csv
from dotenv import load_dotenv
from pydantic import BaseModel
from .URL_generator import get_eventbrite_url
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
    LLMConfig,
)

CSS_SELECTOR = "[class^='event-card-link']"
REQUIRED_KEYS = [
    "name",
    "url",
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
        headless=True,  # Whether to run in headless mode (no GUI)
        verbose=True,  # Enable verbose logging
    )


def get_llm_strategy(is_detail_page: bool = False) -> LLMExtractionStrategy:
    """
    Returns the configuration for the language model extraction strategy.
    
    Args:
        is_detail_page (bool): Whether this is for detail page extraction
    """
    instruction = (
        "Extract all events objects with 'url','name' from the "
        "following content. Each event should have a name and link field."
    ) if not is_detail_page else (
        "Extract the following information from the event page: "
        "name of the event, date of the event, address/location, "
        "and a brief description. Ensure the description is concise."
    )
    
    return LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="openai/gpt-3.5-turbo",
            api_token=os.getenv("OPENAI_API_KEY"),
        ),
        schema=Venue.model_json_schema(),
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
    print(f"Fetching details for: {event_url}")
    
    result = await crawler.arun(
        url=event_url,
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
    page_number: int,
    base_url: str,
    css_selector: str,
    llm_strategy: LLMExtractionStrategy,
    detail_llm_strategy: LLMExtractionStrategy,
    session_id: str,
    required_keys: List[str],
    seen_names: Set[str],
) -> List[dict]:
    """
    Fetches and processes a single page of venue data.
    """
    url = f"{base_url}?page={page_number}"
    print(f"Processing page {page_number}...")

    # Fetch page content with the extraction strategy
    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,  # Do not use cached data
            extraction_strategy=llm_strategy,  # Strategy for data extraction
            css_selector=css_selector,  # Target specific content on the page
            session_id=session_id,  # Unique session ID for the crawl
        ),
    )

    if not (result.success and result.extracted_content):
        print(f"Error fetching page {page_number}: {result.error_message}")
        return []

    # Parse extracted content
    extracted_data = json.loads(result.extracted_content)
    if not extracted_data:
        print(f"No venues found on page {page_number}.")
        return []

    # After parsing extracted content
    print("Extracted data:", extracted_data)

    # Process venues
    complete_venues = []
    for venue in extracted_data:
        # Debugging: Print each venue to understand its structure
        print("Processing venue:", venue)

        # Ignore the 'error' key if it's False
        if venue.get("error") is False:
            venue.pop("error", None)  # Remove the 'error' key if it's False

        if not is_complete_venue(venue, required_keys):
            continue  # Skip incomplete venues

        if is_duplicate_venue(venue["name"], seen_names):
            print(f"Duplicate venue '{venue['name']}' found. Skipping.")
            continue  # Skip duplicate venues

        # Fetch detailed information for this event
        detailed_info = await fetch_event_details(
            crawler,
            venue["url"],
            detail_llm_strategy,
            session_id
        )
        
        if detailed_info:
            # Merge the detailed info with basic info
            venue.update(detailed_info)
            seen_names.add(venue["name"])
            complete_venues.append(venue)
            
            # Be polite and wait between requests
            await asyncio.sleep(1)

    if not complete_venues:
        print(f"No complete venues found on page {page_number}.")
        
    print(f"Extracted {len(complete_venues)} venues from page {page_number}.")
    return complete_venues

async def crawl_venues(city: str, max_pages: int = 10):
    """
    Main function to crawl venue data from the website.
    
    Args:
        city (str): The city to search events for
        max_pages (int): Maximum number of pages to crawl
    """
    # Get the URL for the specified city
    BASE_URL = get_eventbrite_url(city)
    
    browser_config = get_browser_config()
    list_llm_strategy = get_llm_strategy(is_detail_page=False)
    detail_llm_strategy = get_llm_strategy(is_detail_page=True)
    session_id = f"venue_crawl_session_{city}"

    # Initialize state variables
    page_number = 1
    all_venues = []
    seen_names = set()

    async with AsyncWebCrawler(config=browser_config) as crawler:
        while page_number <= max_pages:
            print(f"Crawling page {page_number} of {max_pages} for {city}")
            
            venues = await fetch_and_process_page(
                crawler,
                page_number,
                BASE_URL,
                CSS_SELECTOR,
                list_llm_strategy,
                detail_llm_strategy,
                session_id,
                REQUIRED_KEYS,
                seen_names,
            )

            if not venues:
                print(f"No venues extracted from page {page_number}.")
                break

            all_venues.extend(venues)
            page_number += 1
            await asyncio.sleep(2)

    # Save the collected venues to a CSV file with city name
    if all_venues:
        filename = f"output/{city.lower()}_EB.csv"
        save_venues_to_csv(all_venues, filename)
        print(f"Saved {len(all_venues)} venues to '{filename}'.")
    else:
        print(f"No venues were found during the crawl for {city}.")

    list_llm_strategy.show_usage()


async def main():
    """
    Entry point of the script.
    """
    # Example usage with city and pages as parameters
    city = "Atlanta"  # You can change this to any city
    pages = 1  # You can change this to any number of pages
    await crawl_venues(city=city, max_pages=pages)


if __name__ == "__main__":
    asyncio.run(main())
