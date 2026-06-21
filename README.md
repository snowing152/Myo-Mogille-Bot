# куда пойдём 🍽 — Telegram food-decider bot

A Telegram group-chat bot. When someone asks **«куда пойдём кушать?»**, it collects
everyone's cravings, then suggests ~3 nearby Korean restaurants with KakaoMap links.

## How it works
1. Someone sends a trigger phrase (e.g. «куда пойдём кушать?») or `/eat`.
2. The bot opens a collection session and shows a **🍽 Найти места** button.
3. Everyone types what they want (соджу, кимчи, мясо…). Optionally name a district
   (e.g. «в Хондэ»).
4. Anyone taps the button (or sends `/go`).
5. The bot replies with matched places — name, type, distance, and a KakaoMap link.

If Kakao or Gemini is temporarily unavailable, the bot falls back where it can. If
restaurant search itself is unavailable, it returns a temporary error instead of
claiming that nothing was found nearby.

Long sessions are bounded by message count and total text length. When the limit is
reached, the bot tells the group to run the search instead of silently collecting
more text.

## Setup

### 1. Telegram bot
- You already have a token from [@BotFather](https://t.me/BotFather).
- **Disable privacy mode** so the bot can read group messages:
  BotFather → `/setprivacy` → select your bot → **Disable**.
  (Without this the bot only sees commands, not cravings.)
- Add the bot to your group.

### 2. API keys (both free)
- **Kakao REST key:** https://developers.kakao.com → create an app → REST API key.
- **Gemini key:** https://aistudio.google.com/apikey

### 3. Configure
```powershell
copy .env.example .env
```
Fill in `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`, `KAKAO_REST_API_KEY`, and
`DEFAULT_LAT` / `DEFAULT_LNG` / `DEFAULT_AREA_NAME` (your usual area; the example
values point at Hongdae, Seoul).

### 4. Install & run
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python bot.py
```
The bot runs on your PC via long-polling — it's online while this process runs.

## Development
```powershell
pip install -r requirements-dev.txt
python -m pytest -v
```

## Configuration reference
| Variable | Meaning | Default |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | BotFather token | required |
| `GEMINI_API_KEY` | Google AI Studio key | required |
| `KAKAO_REST_API_KEY` | Kakao Developers REST key | required |
| `DEFAULT_LAT` / `DEFAULT_LNG` | Default search center | required |
| `DEFAULT_AREA_NAME` | Label for the default area | required |
| `SEARCH_RADIUS_M` | Search radius (meters) | 1500 |
| `RESULTS_COUNT` | Places returned | 3 |
| `SESSION_TIMEOUT_MIN` | Collection window | 20 |
| `LLM_MODEL` | Gemini model id | gemini-2.5-flash |
| `TRIGGER_PHRASES` | Comma-separated override | built-in list |
| `MAX_SESSION_MESSAGES` | Max collected messages per session | 50 |
| `MAX_SESSION_CHARS` | Max collected text characters per session | 4000 |
