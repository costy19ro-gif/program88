import streamlit as st
from football_api import FootballAPI
from cache import SimpleCache

st.set_page_config(page_title="BetMachine RapidAPI", layout="wide")

RAPIDAPI_KEY = st.secrets["RAPIDAPI_KEY"]

api = FootballAPI(RAPIDAPI_KEY)
cache = SimpleCache(ttl=120)

st.title("BetMachine – RapidAPI Integration")

date = st.date_input("Selectează data meciurilor")
date_str = date.strftime("%Y-%m-%d")

cache_key = f"fixtures_{date_str}"
data = cache.get(cache_key)

if not data:
    data = api.fixtures_by_date(date_str)
    cache.set(cache_key, data)

if data["status"] == "ok":
    fixtures = data["data"]
    st.success(f"{len(fixtures)} meciuri găsite")
    st.write(fixtures)
else:
    st.error(data["data"])
