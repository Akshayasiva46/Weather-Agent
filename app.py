import pandas as pd
import streamlit as st

from main import weather_agent
from tools import get_weather, get_weather_history

st.set_page_config(page_title="Weather Agent", page_icon="🌤️", layout="wide")

# A little extra color per condition, used for the headline card
CONDITION_EMOJI = {
    "Clear": "☀️",
    "Clouds": "☁️",
    "Rain": "🌧️",
    "Drizzle": "🌦️",
    "Thunderstorm": "⛈️",
    "Snow": "❄️",
    "Mist": "🌫️",
    "Fog": "🌫️",
    "Haze": "🌫️",
    "Smoke": "🌫️",
    "Dust": "🌪️",
    "Sand": "🌪️",
    "Tornado": "🌪️",
}

CONDITION_COLOR = {
    "Clear": "#FDB813",
    "Clouds": "#90A4AE",
    "Rain": "#4A90D9",
    "Drizzle": "#7FB3E8",
    "Thunderstorm": "#5C5C8A",
    "Snow": "#B8E2F2",
}

st.title("🌤️ Weather Agent")
st.caption("Live weather from OpenWeatherMap, plus historical trends from Open-Meteo — no extra keys needed.")

# -----------------------------
# Sidebar: lookup controls
# -----------------------------
with st.sidebar:
    st.header("🔎 City Lookup")
    city_name = st.text_input("City name", placeholder="e.g. Chennai")

    current_clicked = st.button("☀️ Show Current Weather", use_container_width=True)

    st.divider()
    st.subheader("📈 Historical Trend")
    period_label = st.radio(
        "Period",
        options=["Last 7 days", "Last 30 days"],
        horizontal=False,
    )
    trend_clicked = st.button("📊 Show Trend", use_container_width=True)

    st.divider()
    st.caption("Tip: you can also just ask in the chat below — "
               "e.g. \"Will it rain in Mumbai today?\" or "
               "\"What was the average temperature in Delhi last month?\"")

# -----------------------------
# Current weather card
# -----------------------------
if current_clicked and city_name.strip():
    data = get_weather(city_name.strip())

    if "error" in data:
        st.error(data["error"])
    else:
        condition = data.get("condition_main", "")
        emoji = CONDITION_EMOJI.get(condition, "🌡️")
        accent = CONDITION_COLOR.get(condition, "#607D8B")

        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, {accent}33, {accent}11);
                border-left: 6px solid {accent};
                border-radius: 14px;
                padding: 20px 28px;
                margin-bottom: 16px;
            ">
                <span style="font-size: 42px;">{emoji}</span>
                <span style="font-size: 32px; font-weight: 700; margin-left: 12px;">
                    {data['city'].title()}
                </span>
                <div style="font-size: 18px; opacity: 0.85; margin-top: 4px;">
                    {data['weather'].capitalize()}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_icon, col_metrics = st.columns([1, 4])
        with col_icon:
            if data.get("icon_url"):
                st.image(data["icon_url"], width=120)

        with col_metrics:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Temperature", f"{data['temperature']} °C")
            m2.metric("Feels like", f"{data.get('feels_like', 'N/A')} °C")
            m3.metric("Humidity", f"{data['humidity']}%")
            m4.metric("Wind speed", f"{data['wind_speed']} m/s")

    st.divider()

# -----------------------------
# Historical trend section
# -----------------------------
if trend_clicked and city_name.strip():
    days = 7 if period_label == "Last 7 days" else 30
    history = get_weather_history(city_name.strip(), days=days)

    if "error" in history:
        st.error(history["error"])
    else:
        st.subheader(f"📈 {history['city']} — {period_label} ({history['period_start']} to {history['period_end']})")

        h1, h2, h3, h4 = st.columns(4)
        h1.metric("Average temp", f"{history['avg_temp']} °C")
        h2.metric("Highest temp", f"{history['max_temp']} °C")
        h3.metric("Lowest temp", f"{history['min_temp']} °C")
        h4.metric("Total rainfall", f"{history['total_precipitation_mm']} mm")

        df = pd.DataFrame(history["daily"])
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        st.markdown("**Temperature range (°C)**")
        st.line_chart(df[["max", "mean", "min"]])

        st.markdown("**Daily rainfall (mm)**")
        st.bar_chart(df["precipitation"])

    st.divider()

# -----------------------------
# Chat-style free-form Q&A
# -----------------------------
st.subheader("💬 Ask anything about the weather")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for role, msg in st.session_state.chat_history:
    with st.chat_message(role):
        st.markdown(msg)

user_input = st.chat_input(
    "e.g. 'Weather in Chennai', 'Average temperature in Mumbai last month', "
    "'Should I carry an umbrella in London?'"
)

if user_input:
    st.session_state.chat_history.append(("user", user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Checking the sky..."):
            try:
                answer = weather_agent(user_input)
            except Exception as e:
                answer = f"Something went wrong: {e}"
            st.markdown(answer)

    st.session_state.chat_history.append(("assistant", answer))
