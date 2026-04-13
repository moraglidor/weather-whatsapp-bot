import os
import httpx
import anthropic
from pywa import WhatsApp
from pywa.types.templates import TemplateLanguage, BodyText

TOKEN = os.environ["WA_TOKEN"]
PHONE_NUMBER_ID = os.environ["WA_PHONE_NUMBER_ID"]

RECIPIENTS = [
    {"name": "Lidor", "number": "972527730595"},
    {"name": "Amir", "number": "972523830553"},
]

PHILADELPHIA_LAT = 39.9526
PHILADELPHIA_LON = -75.1652

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODE = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Moderate showers",
    82: "Violent showers",
    95: "Thunderstorm",
}

wa = WhatsApp(
    phone_id=PHONE_NUMBER_ID,
    token=TOKEN,
)


def get_hourly_forecast(lat: float, lon: float, tz: str = "America/New_York") -> dict:
    """Fetch hourly weather for today from open-meteo."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": tz,
        "hourly": ",".join([
            "temperature_2m",
            "precipitation_probability",
            "precipitation",
            "weathercode",
            "windspeed_10m",
        ]),
        "daily": ",".join([
            "weathercode",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "sunrise",
            "sunset",
        ]),
        "forecast_days": 2,
    }

    r = httpx.get(FORECAST_URL, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def build_weather_summary(data: dict) -> str:
    """Turn raw API data into a structured summary for Claude."""
    daily = data["daily"]
    hourly = data["hourly"]

    date = daily["time"][0]
    precip_total = daily["precipitation_sum"][0]

    tomorrow_date = daily["time"][1]
    tomorrow_tmax = daily["temperature_2m_max"][1]
    tomorrow_tmin = daily["temperature_2m_min"][1]
    tomorrow_precip = daily["precipitation_sum"][1]
    tomorrow_code = daily["weathercode"][1] if "weathercode" in daily else None

    # Extract key hours: morning (7-9), midday (12), afternoon (15-17), evening (20)
    times = hourly["time"]
    temps = hourly["temperature_2m"]
    precip_prob = hourly["precipitation_probability"]
    codes = hourly["weathercode"]

    def hour_data(hour: int) -> str:
        idx = next((i for i, t in enumerate(times) if t.endswith(f"T{hour:02d}:00")), None)
        if idx is None:
            return ""
        desc = WEATHER_CODE.get(codes[idx], "Unknown")
        wind = hourly["windspeed_10m"][idx]
        return f"{hour}:00 → {temps[idx]}°C, {desc}, wind {wind} km/h, {precip_prob[idx]}% rain chance"

    sections = [
        f"Date: {date}",
        f"Philadelphia, PA",
        f"Total precip: {precip_total} mm",
        "",
        "Relevant hours:",
        hour_data(8),
        hour_data(12),
        hour_data(15),
        hour_data(18),
        hour_data(22),
    ]
    tomorrow_desc = WEATHER_CODE.get(tomorrow_code, "Unknown") if tomorrow_code is not None else "Unknown"
    tomorrow_section = (
        f"\nTomorrow ({tomorrow_date}): {tomorrow_desc}, "
        f"High {tomorrow_tmax}°C / Low {tomorrow_tmin}°C, Precip {tomorrow_precip} mm"
    )

    return "\n".join(s for s in sections if s is not None) + tomorrow_section


def generate_friendly_message(weather_summary: str, name: str) -> str:
    """Use Claude to turn raw weather data into a friendly WhatsApp message."""
    client = anthropic.Anthropic()

    prompt = f"""You are a weather assistant writing a short daily WhatsApp message for Philadelphia.

Rules:
- Start with "Hi {name}," then follow this exact structure:
  Morning - [temp + condition], Noon - [temp + condition], Afternoon - [temp + condition], Evening - [temp + condition]. Tomorrow - [one short sentence].
- Example: "Hi Lidor, Morning - chilly 10c strong wind, Noon - warms to 15c light breeze dry, Afternoon - 15c sunny calm, Evening - gets cold 12c windy. Tomorrow will be colder."
- Always mention wind if it's notable (above 20 km/h), otherwise skip it
- Plain text only, no emojis, no bold, no formatting, no newlines
- Max 300 characters total

Weather data:
{weather_summary}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text.strip()
    # Meta doesn't allow newlines in template parameters — replace with space
    text = " ".join(text.splitlines())
    return text[:1024]


def main() -> None:
    data = get_hourly_forecast(PHILADELPHIA_LAT, PHILADELPHIA_LON)
    weather_summary = build_weather_summary(data)
    print(f"Weather summary:\n{weather_summary}\n")

    for recipient in RECIPIENTS:
        friendly_message = generate_friendly_message(weather_summary, recipient["name"])
        print(f"Message to {recipient['name']}:\n{friendly_message}\n")
        wa.send_template(
            to=recipient["number"],
            name="daily_weather",
            language=TemplateLanguage.ENGLISH,
            params=[
                BodyText.params(weather_today=friendly_message),
            ],
        )
        print(f"Sent to {recipient['name']} ({recipient['number']})")

    print("All messages sent.")


if __name__ == "__main__":
    main()
