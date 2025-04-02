import os
from dotenv import load_dotenv
from groq import Groq
import streamlit as st
from pathlib import Path

def extract_city_from_address(address: str) -> str:
    """
    Use Groq API to extract the city from a full address.
    
    Args:
        address (str): Full address string
        
    Returns:
        str: Extracted city name
    """
    # Get the project root directory (2 levels up from this file)
    root_dir = Path(__file__).parent.parent
    env_path = root_dir / '.env'
    
    print(f"Looking for .env file at: {env_path}")
    print(f"File exists: {env_path.exists()}")
    
    # Clear existing environment variables
    if 'GROQ_API_KEY' in os.environ:
        del os.environ['GROQ_API_KEY']
    
    # Load environment variables
    load_dotenv(env_path, override=True)
    
    # Get and verify API key
    api_key = os.getenv('GROQ_API_KEY')
    print(f"API Key loaded: {api_key[:5]}..." if api_key else "No API key found!")
    
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables")
    
    client = Groq(api_key=api_key)
    
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

if __name__ == "__main__":
    print(extract_city_from_address("123 Main St, New York, NY 10001"))