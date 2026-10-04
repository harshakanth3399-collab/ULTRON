"""ULTRON Instant 100% Free Weather Service (Open-Meteo & IP Geolocation)."""

from __future__ import annotations

import json
import urllib.request
from typing import Tuple, Dict, Any

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail"
}

def get_live_weather(location_query: str = "") -> Tuple[bool, str]:
    """
    Fetches real-time weather data using Open-Meteo API (100% free, no key required).
    Returns (success, response_message).
    """
    try:
        lat, lon, city_name = 14.68, 77.60, "Anantapur" # Default fallback location
        
        # 1. Geolocation lookup if user specified a city or for auto-detection
        if location_query and location_query.strip().lower() not in ["my location", "here", "location", "current location"]:
            clean_city = location_query.strip()
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(clean_city)}&count=1&language=en&format=json"
            req = urllib.request.Request(geo_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                geo_data = json.loads(resp.read().decode('utf-8'))
                if geo_data.get("results"):
                    first = geo_data["results"][0]
                    lat = first.get("latitude", lat)
                    lon = first.get("longitude", lon)
                    city_name = first.get("name", clean_city.capitalize())
        else:
            # Auto-detect IP location
            try:
                ip_req = urllib.request.Request("http://ip-api.com/json/", headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(ip_req, timeout=3.0) as ip_resp:
                    ip_data = json.loads(ip_resp.read().decode('utf-8'))
                    if ip_data.get("status") == "success":
                        city_name = ip_data.get("city", "Anantapur")
                        lat = ip_data.get("lat", 14.68)
                        lon = ip_data.get("lon", 77.60)
            except Exception:
                pass

        # 2. Query Open-Meteo Current Weather API
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        req = urllib.request.Request(weather_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            w_data = json.loads(resp.read().decode('utf-8'))
            cw = w_data.get("current_weather", {})
            temp = cw.get("temperature")
            wind = cw.get("windspeed")
            w_code = cw.get("weathercode", 0)
            condition = WEATHER_CODES.get(w_code, "Clear")
            
            msg = f"The weather in {city_name} is currently {temp} degrees Celsius with {condition.lower()} and wind speed of {wind} km/h."
            print(f"[WEATHER SERVICE] {msg}")
            return True, msg
    except Exception as e:
        print(f"[WEATHER SERVICE ERROR] {e}")
        return False, "I couldn't retrieve the live weather data right now."
