import os
import httpx
import anthropic
from pywa import WhatsApp
from pywa.types.templates import TemplateLanguage, BodyText

TOKEN = os.environ["WA_TOKEN"]
PHONE_NUMBER_ID = os.environ["WA_PHONE_NUMBER_ID"]

RECIPIENTS = [
    {"name": "Lidor", "number": "972527730595"},
    # Add more recipients here:
    # {"name": "Jane", "number": "972501234567"},
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
    tmax = daily["temperature_2m_max"][0]
    tmin = daily["temperature_2m_min"][0]
    precip_total = daily["precipitation_sum"][0]
    sunrise = daily["sunrise"][0]
    sunset = daily["sunset"][0]

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
        return f"{hour}:00 → {temps[idx]}°C, {desc}, {precip_prob[idx]}% rain chance"

    sections = [
        f"Date: {date}",
        f"Philadelphia, PA",
        f"High: {tmax}°C | Low: {tmin}°C | Total precip: {precip_total} mm",
        f"Sunrise: {sunrise} | Sunset: {sunset}",
        "",
        "Hourly breakdown:",
        hour_data(7),
        hour_data(9),
        hour_data(12),
        hour_data(15),
        hour_data(18),
        hour_data(21),
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

    prompt = f"""You are a friendly weather assistant writing a daily WhatsApp message for Philadelphia.
Write a short, clear, and summarized message addressed to {name}.

Rules:
- Start with "Hi {name} 👋" then the date (e.g. Tuesday, April 7)
- 3-4 lines max — keep it tight and scannable
- One line for morning, one for afternoon/evening, one clothing tip, one short sentence about tomorrow
- Use WhatsApp formatting: *bold* for temperatures, emojis are welcome but keep them minimal
- Do NOT use markdown (no **, no #) — only WhatsApp formatting (*bold*, _italic_)
- Max 400 characters

Weather data:
{weather_summary}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text.strip()
    return text[:1024]  # hard cap just in case


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
                BodyText.params(friendly_message),
            ],
        )
        print(f"Sent to {recipient['name']} ({recipient['number']})")

    print("All messages sent.")


if __name__ == "__main__":
    main()
