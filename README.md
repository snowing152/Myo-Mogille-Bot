# Myo Mogille Bot

> Telegram food-decider bot for Russian-speaking groups in Korea.

![Myo Mogille Bot preview](<assets/Gemini_Generated_Image_wlzahiwlzahiwlza(1).png>)

Myo Mogille Bot helps a Telegram group answer the practical question: **"куда
пойдём кушать?"** It collects everyone’s cravings, translates food intent into
Korean search terms, searches nearby restaurants through Kakao Places, and replies
with a short list of recommendations and KakaoMap links.

The bot runs locally with Telegram long polling. It is online only while
`python bot.py` is running.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Running the Project](#running-the-project)
- [Available Scripts](#available-scripts)
- [Screenshots or Preview](#screenshots-or-preview)
- [Roadmap / Future Improvements](#roadmap--future-improvements)
- [License](#license)

## Overview

Typical flow:

1. Someone sends a trigger phrase such as **"куда пойдём кушать?"** or runs
   `/eat`.
2. The bot opens a collection session and shows a **🍽 Найти места** button.
3. Group members type cravings such as `соджу`, `кимчи`, `мясо`, or mention a
   district such as `в Хондэ`.
4. Anyone taps the button or sends `/go`.
5. The bot replies with matched places, short reasons, and KakaoMap links.

If Gemini is unavailable, the bot falls back to a small Russian-to-Korean craving
dictionary. If Kakao search itself is unavailable, the bot returns a temporary
error instead of incorrectly saying that nothing was found.

## Features

- Telegram group-chat workflow with `/eat`, `/go`, trigger phrases, and an inline
  find button.
- In-memory per-chat collection sessions with timeout and input limits.
- Russian-language craving extraction with Gemini.
- Korean search query generation for Kakao Places.
- Optional area detection and geocoding through Kakao keyword search.
- Restaurant deduplication, distance sorting, and LLM-assisted ranking.
- Fallback behavior for LLM extraction/ranking failures.
- Temporary provider-error handling for failed Kakao searches.
- Telegram HTML output with escaped dynamic text.
- Stale inline-button protection so old prompts cannot submit a newer session.
- Test coverage for config, handlers, sessions, pipeline fallbacks, parsing, and
  formatting.

## Tech Stack

| Area | Technology |
|---|---|
| Language | Python 3 |
| Telegram bot framework | `python-telegram-bot` |
| LLM provider | Gemini via `google-genai` |
| Places provider | Kakao Local API via `httpx` |
| Environment loading | `python-dotenv` |
| Testing | `pytest`, `pytest-asyncio` |
| Build system | TODO |
| Lint / format tooling | TODO |

There is no `package.json` in this repository.

## Project Structure

```text
.
├── bot.py                  # Telegram app wiring and long-polling entrypoint
├── foodbot/
│   ├── config.py           # Environment parsing and validation
│   ├── dictionary.py       # Russian-to-Korean fallback craving dictionary
│   ├── formatting.py       # Telegram HTML response formatting
│   ├── geo.py              # Area geocoding helper
│   ├── handlers.py         # Telegram command, text, and callback handlers
│   ├── llm.py              # Gemini wrapper and JSON parsers
│   ├── pipeline.py         # Craving extraction, search, ranking, formatting flow
│   ├── places.py           # Kakao client and Place model
│   └── session.py          # In-memory session store
├── tests/                  # Pytest test suite
├── assets/                 # Project image assets
├── .env.example            # Environment template
├── requirements.txt        # Runtime dependencies
├── requirements-dev.txt    # Test/development dependencies
├── pytest.ini              # Pytest configuration
├── PROJECT_OVERVIEW.md     # Architecture notes
└── AGENTS.md               # Instructions for future coding agents
```

## Installation

### 1. Create a Telegram bot

1. Create a bot with [@BotFather](https://t.me/BotFather).
2. Disable privacy mode so the bot can read group messages:
   `BotFather` → `/setprivacy` → select your bot → **Disable**.
3. Add the bot to your Telegram group.

Without disabling privacy mode, the bot sees commands but not normal group
messages, so it cannot collect cravings.

### 2. Get API keys

- **Kakao REST API key:** create an app at <https://developers.kakao.com>.
- **Gemini API key:** create a key at <https://aistudio.google.com/apikey>.

### 3. Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

Runtime only:

```powershell
pip install -r requirements.txt
```

Development and tests:

```powershell
pip install -r requirements-dev.txt
```

`requirements-dev.txt` includes `requirements.txt`.

## Environment Variables

Create your local `.env` file from the example:

```powershell
copy .env.example .env
```

Fill in the required values:

| Variable | Required | Default | Description |
|---|---:|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | - | Telegram token from BotFather. |
| `GEMINI_API_KEY` | Yes | - | Google AI Studio / Gemini API key. |
| `KAKAO_REST_API_KEY` | Yes | - | Kakao Developers REST API key. |
| `DEFAULT_LAT` | Yes | - | Default search-center latitude. |
| `DEFAULT_LNG` | Yes | - | Default search-center longitude. |
| `DEFAULT_AREA_NAME` | Yes | - | Label shown for the default area. |
| `SEARCH_RADIUS_M` | No | `1500` | Search radius in meters. |
| `RESULTS_COUNT` | No | `3` | Number of places to return. |
| `SESSION_TIMEOUT_MIN` | No | `20` | Collection session timeout. |
| `LLM_MODEL` | No | `gemini-2.5-flash` | Gemini model id. |
| `TRIGGER_PHRASES` | No | built-in list | Comma-separated trigger override. |
| `MAX_SESSION_MESSAGES` | No | `50` | Max collected messages per session. |
| `MAX_SESSION_CHARS` | No | `4000` | Max collected text characters per session. |

The example default coordinates point at Hongdae, Seoul.

Do not commit `.env`. It is intentionally ignored.

## Running the Project

Start the bot:

```powershell
python bot.py
```

The app uses long polling. Keep the process running while you want the bot online.

## Available Scripts

This repository does not define package-manager scripts. Use the direct commands
below.

| Task | Command |
|---|---|
| Install runtime dependencies | `pip install -r requirements.txt` |
| Install dev/test dependencies | `pip install -r requirements-dev.txt` |
| Run the bot | `python bot.py` |
| Run tests | `python -m pytest -v` |
| Build | TODO |
| Lint | TODO |
| Format | TODO |

If using the local virtual environment directly:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

## Screenshots or Preview

Project preview image:

![Myo Mogille Bot preview](<assets/Gemini_Generated_Image_wlzahiwlzahiwlza(1).png>)

Runtime Telegram screenshots are TODO.

## Roadmap / Future Improvements

- Persist sessions outside process memory if the bot needs reliable restarts.
- Add deployment instructions for a VPS, container, or process manager.
- Add structured logging around provider calls and user-facing failures.
- Expand the fallback craving dictionary.
- Add screenshots of the Telegram group flow.
- Add linting/formatting tooling if the project grows.

## License

TODO: No license file is currently included in this repository.
