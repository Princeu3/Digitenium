import os
from dotenv import load_dotenv
from groq import Groq


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

print(extract_city_from_address("700 College St, Beloit, WI 53511"))