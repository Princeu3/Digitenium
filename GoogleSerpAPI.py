from serpapi import GoogleSearch
import json
from typing import Dict, List, Optional
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables from local.env
load_dotenv('local.env')

class GoogleSerpAPI:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('GoogleSerpAPI_KEY')
        if not self.api_key:
            raise ValueError("API key must be provided either directly or through environment variable 'GoogleSerpAPI_KEY'")

    def search_local_news(self, location: str, language: str = "en", num_results: int = 5) -> List[Dict]:
        """
        Search for news related to a specific location with pagination support.
    
        """
        all_results = []
        start = 0
        
        while len(all_results) < num_results:
            params = {
                "engine": "google",
                "q": f"news {location}",
                "location": location,
                "google_domain": "google.com",
                "gl": "us",
                "hl": language,
                "tbm": "nws",
                "start": start,  # Pagination parameter
                "num": min(100, num_results),  # Results per page
                "api_key": self.api_key
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            if "news_results" not in results or not results["news_results"]:
                break
                
            all_results.extend(results["news_results"])
            
            # If we got fewer results than requested, there are no more results
            if len(results["news_results"]) < 100:
                break
                
            start += 100  # Move to next page
            
        return all_results[:num_results]

    def search_local_events(self, location: str, date: Optional[str] = None) -> List[Dict]:
        params = {
            "engine": "google_events",
            "q": f"Events in {location}",
            "hl": "en",
            "gl": "us",
            "htichips": "date:today",
            "api_key": self.api_key
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        return results.get("events_results", [])

# Example usage
def main():
    try:
        serp_api = GoogleSerpAPI()
        
        # Example location
        location = "Austin"
        
        # Get news (requesting 20 results)
        news = serp_api.search_local_news(location, num_results=20)
        print(f"\nLocal News (Found {len(news)} results):")
        for article in news:  # Print all articles
            print(f"- {article['title']}")
            print(f"  {article['link']}\n")
        
        # Get events
        events = serp_api.search_local_events(location)
        print("\nLocal Events:")
        for event in events[:5]:  # Print first 3 events
            print(f"- Title: {event.get('title', 'N/A')}")
            print(f"  Date: {event.get('date', 'N/A')}")
            print(f"  Address: {event.get('address', 'N/A')}")
            print(f"  Description: {event.get('description', 'N/A')[:100]}...")
            print(f"  Link: {event.get('link', 'N/A')}\n")
    
    except ValueError as e:
        print(f"Error: {e}")
        print("Please make sure GoogleSerpAPI_KEY is set in your local.env file")

if __name__ == "__main__":
    main() 