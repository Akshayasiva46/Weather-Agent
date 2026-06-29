# Weather Agent 🌤️

An AI agent that answers weather questions — current conditions *and*
historical trends (last week / last month averages) — using two free APIs
behind the scenes.

## Files
| File | Purpose |
|---|---|
| `main.py` | Agent loop: send message to LLM → if it wants a tool, run it and feed the result back → repeat → return final answer |
| `tools.py` | `get_weather(city)` — current weather via **OpenWeatherMap** (needs your key). `get_weather_history(city, days)` — historical averages/min/max/rainfall via **Open-Meteo** (free, no key) |
| `prompts.py` | System prompt telling the LLM when to use current vs. historical weather tool |
| `memory.py` | Saves/loads conversation history to `memory.json` |
| `app.py` | Streamlit dashboard — current weather card with icons, trend charts, and a chat box |
| `requirements.txt` | Python dependencies |
| `.env.example` | Template for your `.env` file |

## Setup
1. Copy `.env.example` to `.env` and fill in your keys:
   ```
   OPENROUTER_API_KEY=sk-or-...
   WEATHER_API_KEY=your_openweathermap_key
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run it (command line version):
   ```
   python main.py
   ```
   Or launch the Streamlit dashboard:
   ```
   streamlit run app.py
   ```
   Opens a browser page with:
   - Sidebar **city lookup** → current temperature, feels-like, humidity, wind,
     plus a condition icon/emoji and a colored card (sunny gold, rainy blue,
     cloudy grey, etc.)
   - Sidebar **trend toggle** ("Last 7 days" / "Last 30 days") → average/high/
     low temperature, total rainfall, and line/bar charts of the daily values
   - **Chat box** for anything else, e.g. "will it rain in Mumbai today?" or
     "what was the average temperature in Delhi last month?"

## How it decides what to do
- Current weather questions ("weather in Chennai", "is it humid in Mumbai
  right now") → the LLM calls `get_weather` (OpenWeatherMap).
- Historical/trend questions ("average temperature last month", "how much did
  it rain last week", "weather trend in Delhi") → the LLM calls
  `get_weather_history` with `days=7` for "week" or `days=30` for "month".
- Unknown city → the tool returns an `"error"` field and the agent asks the
  user to check the spelling.

## Bugs we hit and fixed along the way
Useful as a troubleshooting reference if something similar happens again:

1. **`memory.json` was empty (0 bytes).** `json.load()` on an empty file
   throws immediately. `memory.py` now checks the file size before parsing,
   and treats an empty/missing file as "no memory yet."
2. **`message.get("content", "")` doesn't catch `content: None`.**
   `.get(key, default)` only falls back when the key is *missing*, not when
   it's present but `null`. Some models put the real answer in `reasoning`
   instead. Fixed with an explicit `if not answer:` check and a fallback to
   `reasoning`.
3. **No guard for a missing `WEATHER_API_KEY`.** Previously this would
   silently call OpenWeatherMap with `appid=None` and fail with a confusing
   401. Now it fails early with a clear message telling you to check `.env`.
4. **No guard for malformed API responses.** Wrapped the
   `data["main"]["temp"]` style lookups in try/except so a weird response
   gives a clean error instead of a raw `KeyError` traceback.
5. **Debug noise.** Raw API responses, tool-call JSON, and the weather key
   itself were being printed on every request. Now gated behind a
   `DEBUG = False` flag at the top of `main.py` / `tools.py` — flip it to
   `True` if you need to troubleshoot again.

## Notes on the two weather APIs
- **OpenWeatherMap** (current weather): free tier, but only covers *current*
  conditions and short forecasts — not history. New keys can take up to ~2
  hours to activate after signup.
- **Open-Meteo** (historical trends): completely free, no signup, no key,
  used for `get_weather_history`. Its archive data has roughly a 5-day lag to
  finalize, so "last 30 days" actually covers day‑35 to day‑5 relative to
  today, not literally up to today — the trend header in the dashboard shows
  the exact date range so this is never hidden from you.
- ⚠️ **Security reminder:** the `.env` file you originally uploaded had real,
  working keys in it. Since it passed through this chat, rotate both keys
  (OpenRouter + OpenWeatherMap) from their dashboards, and keep `.env` out of
  anything you upload or commit to version control going forward.
