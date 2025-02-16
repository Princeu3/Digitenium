import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry

def setup_openmeteo_client():
	# Setup the Open-Meteo API client with cache and retry on error
	cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
	retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
	return openmeteo_requests.Client(session=retry_session)

def get_weather_data(client, latitude, longitude, forecast_days=3):
	# Make sure all required weather variables are listed here
	url = "https://api.open-meteo.com/v1/forecast"
	params = {
		"latitude": latitude,
		"longitude": longitude,
		"hourly": ["temperature_2m", "relative_humidity_2m", "precipitation", "snowfall", "uv_index", "is_day"],
		"temperature_unit": "fahrenheit",
		"timezone": "auto",
		"forecast_days": forecast_days
	}
	return client.weather_api(url, params=params)

def process_hourly_data(response):
	# Process hourly data. The order of variables needs to be the same as requested.
	hourly = response.Hourly()
	hourly_data = {
		"date": pd.date_range(
			start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
			end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
			freq=pd.Timedelta(seconds=hourly.Interval()),
			inclusive="left"
		),
		"temperature_2m": hourly.Variables(0).ValuesAsNumpy(),
		"relative_humidity_2m": hourly.Variables(1).ValuesAsNumpy(),
		"precipitation": hourly.Variables(2).ValuesAsNumpy(),
		"snowfall": hourly.Variables(3).ValuesAsNumpy(),
		"uv_index": hourly.Variables(4).ValuesAsNumpy(),
		"is_day": hourly.Variables(5).ValuesAsNumpy()
	}
	return pd.DataFrame(data=hourly_data)

def get_forecast_for_day(responses, day_index):
	if day_index < 0 or day_index >= len(responses):
		raise IndexError("Day index out of range")
	response = responses[day_index]
	return process_hourly_data(response)

def get_forecast_for_all_days(responses):
	return [process_hourly_data(response) for response in responses]

# Example usage
if __name__ == "__main__":
	openmeteo = setup_openmeteo_client()
	responses = get_weather_data(openmeteo, latitude=33.749, longitude=-84.388)

	# Get forecast for a specific day
	day_1_forecast = get_forecast_for_day(responses, 0)
	print(day_1_forecast)

	# Get forecast for all days
	all_days_forecast = get_forecast_for_all_days(responses)
	for day_forecast in all_days_forecast:
		print(day_forecast)
