# Weather WhatsApp Bot 🌤️📱

This is a personal automation project that sends a daily weather update via WhatsApp.

## Overview

The system retrieves the daily forecast for a selected city (currently Philadelphia) and sends a message using the WhatsApp Cloud API.

The goal of this project is to explore:
- AI agents and automation
- API integrations
- Messaging platforms
- Backend workflows in Python

## Features

- 🌍 Dynamic city weather retrieval
- 📊 Daily forecast summary (temperature, conditions, etc.)
- 💬 WhatsApp message delivery using Meta Cloud API
- 🔁 Designed for scheduled daily notifications

## Tech Stack

- Python
- Open-Meteo API (weather data)
- Meta WhatsApp Cloud API
- PyWa (WhatsApp Python client)
- HTTP / REST APIs

## Architecture

- **Weather Agent**  
  Fetches and formats weather data.

- **Client Layer**  
  Sends requests to the agent.

- **Notification Layer**  
  Sends messages via WhatsApp API.

- **(Planned)** Scheduler for daily automation.

## Status

🚧 Work in progress  
Currently supports sending test messages via WhatsApp API.

## Future Improvements

- ⏰ Daily scheduled messages (7 AM)
- 📍 User-defined locations
- 📈 Multi-day forecast
- 🤖 Smarter summarization
- 📲 Support for multiple users

## Motivation

This project is part of a learning journey into:
- AI-driven applications
- Real-world API integrations
- Building end-to-end systems

## Disclaimer

This is a personal project built for learning purposes and experimentation with messaging APIs.
