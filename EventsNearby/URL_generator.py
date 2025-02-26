import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv('.env')

def get_luma_url(city):
    """
    Return Luma URL for a given city using predefined city codes.
    """
    city_codes = {
        'atlanta': 'atlanta',
        'buenos aires': 'buenos-aires',
        'houston': 'houston',
        'miami': 'miami',
        'phoenix': 'phoenix',
        'san francisco': 'sf',
        'vancouver': 'vancouver',
        'austin': 'austin',
        'chicago': 'chicago',
        'las vegas': 'las-vegas',
        'montreal': 'montreal',
        'portland': 'portland',
        'sao paulo': 'saopaulo',
        'washington dc': 'dc',
        'bogota': 'bogota',
        'dallas': 'dallas',
        'los angeles': 'la',
        'new york': 'nyc',
        'salt lake city': 'salt-lake-city',
        'seattle': 'seattle',
        'waterloo': 'waterloo_ca',
        'boston': 'boston',
        'denver': 'denver',
        'mexico city': 'mexico-city',
        'philadelphia': 'philadelphia',
        'san diego': 'sd',
        'toronto': 'toronto'
    }
    
    city_lower = city.lower()
    if city_lower not in city_codes:
        raise ValueError(f"City '{city}' not found or invalid")
    
    return f'https://lu.ma/{city_codes[city_lower]}'

def get_eventbrite_url(city):
    """
    Use Groq API to determine state abbreviation for a city and return EventBrite URL.
    """
    client = Groq(api_key=os.getenv('GROQ_API_KEY'))
    
    prompt = f"""Given the city "{city}", respond with ONLY the two-letter state abbreviation in lowercase.
    If the city is not a valid US city, respond with "invalid". Example: for "New York", respond with "ny" """
    
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that only responds with state abbreviations."
            },
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama-3.1-8b-instant",
    )

    state_abbr = chat_completion.choices[0].message.content.strip().lower()
    
    if state_abbr == "invalid":
        raise ValueError(f"City '{city}' not found or invalid")
    
    city_with_hyphens = city.lower().replace(" ", "-")
    return f'https://www.eventbrite.com/d/{state_abbr}--{city_with_hyphens}/events--this-month/'
