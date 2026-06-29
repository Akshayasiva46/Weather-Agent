import os
import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

DEBUG = False

WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

# Open-Meteo -> free, no API key, used for geocoding + historical weather
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def get_weather(city: str):
    """
    Looks up current weather for a city using OpenWeatherMap.
    Returns a plain dict (main.py will json.dumps it before sending to the LLM).
    """
    if not WEATHER_API_KEY:
        return {"error": "WEATHER_API_KEY is missing. Add it to your .env file."}

    params = {
        "q": city,
        "appid": WEATHER_API_KEY,
        "units": "metric"
    }

    try:
        response = requests.get(WEATHER_URL, params=params, timeout=10)
    except requests.exceptions.RequestException as e:
        return {"error": f"Could not reach weather API: {e}"}

    if DEBUG:
        print("Status Code:", response.status_code)
        print("Response:", response.text)

    if response.status_code == 401:
        return {"error": "Weather API key is invalid or not yet activated "
                          "(new OpenWeatherMap keys can take up to ~2 hours to activate)."}

    if response.status_code == 404:
        return {"error": f"City '{city}' not found. Check the spelling."}

    if response.status_code != 200:
        return {"error": f"Weather API returned status {response.status_code}: {response.text}"}

    data = response.json()

    try:
        weather = data["weather"][0]
        icon_code = weather.get("icon")
        return {
            "city": city,
            "temperature": data["main"]["temp"],
            "feels_like": data["main"].get("feels_like"),
            "humidity": data["main"]["humidity"],
            "weather": weather["description"],
            "condition_main": weather.get("main"),  # e.g. "Rain", "Clear", "Clouds"
            "icon_code": icon_code,
            # Free icon CDN, no key needed - just needs the code above
            "icon_url": f"https://openweathermap.org/img/wn/{icon_code}@4x.png" if icon_code else None,
            "wind_speed": data["wind"]["speed"]
        }
    except (KeyError, IndexError) as e:
        return {"error": f"Unexpected response shape from weather API: {e}"}


def _geocode_city(city: str):
    """Resolve a city name to (lat, lon, resolved_name, country) using Open-Meteo's free geocoder."""
    try:
        resp = requests.get(GEOCODE_URL, params={"name": city, "count": 1}, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        return None, f"Could not reach geocoding API: {e}"

    results = resp.json().get("results")
    if not results:
        return None, f"Could not find location '{city}'."

    r = results[0]
    return (r["latitude"], r["longitude"], r.get("name", city), r.get("country")), None


def get_weather_history(city: str, days: int = 30):
    """
    Returns historical daily weather for a city over the last `days` days
    (week = 7, month = 30), using the free Open-Meteo archive API.

    Includes summary stats (average/min/max temperature, total rainfall)
    plus a day-by-day series for charting.
    """
    coords, err = _geocode_city(city)
    if err:
        return {"error": err}

    lat, lon, resolved_name, country = coords

    # Archive data needs a few days to finalize, so end a small buffer back
    # from today rather than asking for "today" itself.
    end_date = datetime.date.today() - datetime.timedelta(days=5)
    start_date = end_date - datetime.timedelta(days=days - 1)

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum",
        "timezone": "auto",
    }

    try:
        resp = requests.get(ARCHIVE_URL, params=params, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"error": f"Could not reach historical weather API: {e}"}

    daily = resp.json().get("daily", {})
    dates = daily.get("time", [])

    if not dates:
        return {"error": "No historical data available for this period."}

    tmax = daily.get("temperature_2m_max", [])
    tmin = daily.get("temperature_2m_min", [])
    tmean = daily.get("temperature_2m_mean", [])
    precip = daily.get("precipitation_sum", [])

    valid_mean = [t for t in tmean if t is not None]
    valid_max = [t for t in tmax if t is not None]
    valid_min = [t for t in tmin if t is not None]
    valid_precip = [p for p in precip if p is not None]

    return {
        "city": resolved_name,
        "country": country,
        "period_start": dates[0],
        "period_end": dates[-1],
        "num_days": len(dates),
        "avg_temp": round(sum(valid_mean) / len(valid_mean), 1) if valid_mean else None,
        "max_temp": max(valid_max) if valid_max else None,
        "min_temp": min(valid_min) if valid_min else None,
        "total_precipitation_mm": round(sum(valid_precip), 1) if valid_precip else None,
        "daily": [
            {
                "date": dates[i],
                "max": tmax[i] if i < len(tmax) else None,
                "min": tmin[i] if i < len(tmin) else None,
                "mean": tmean[i] if i < len(tmean) else None,
                "precipitation": precip[i] if i < len(precip) else None,
            }
            for i in range(len(dates))
        ],
    }


TOOL_FUNCTIONS = {
    "get_weather": get_weather,
    "get_weather_history": get_weather_history,
}


if __name__ == "__main__":
    print(get_weather("Coimbatore"))
    print(get_weather_history("Coimbatore", days=7))
