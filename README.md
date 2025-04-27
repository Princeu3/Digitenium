# Digitenium: Events Nearby Assistant

An intelligent AI assistant that helps users discover and explore local events, built with Python, Streamlit, and integrated with various AI APIs.

## Features

- 🔍 Find local events based on location, date, and interests
- 🤖 AI-powered event recommendations
- 🗺️ Integration with maps for location information
- 📊 Event details and visualization
- 🌐 Web scraping capabilities to find the most up-to-date event information

## Technologies Used

- Python
- Streamlit
- Groq AI API
- Google Serp API
- Geolocation APIs
- Web scraping tools (BeautifulSoup, Selenium, Playwright)

## Installation

### Prerequisites

- Python 3.11+
- pip package manager

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/digitenium.git
   cd digitenium
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a local environment file:
   - Copy the sample environment file: `cp sample_localenv.txt local.env`
   - Edit `local.env` and add your API keys:
     ```
     GROQ_API_KEY=your_groq_api_key
     GoogleSerpAPI_KEY=your_serp_api_key
     OPENAI_API_KEY=your_openai_api_key  # Optional
     gmaps_api_key=your_google_maps_api_key  # Optional
     ```

## Usage

### Running the Streamlit App

Run the Streamlit app with:
```bash
streamlit run Events.py
```

This will launch the web interface in your default browser where you can search for events.

## Project Structure

- `Events.py` - Main Streamlit application
- `requirements.txt` - Project dependencies






