import requests
import time

class RapidAPIClient:
    BASE_URL = "https://api-football-v1.p.rapidapi.com/v3"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
        }

    def get(self, endpoint: str, params: dict = None):
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "errors" in data and data["errors"]:
                return {"status": "error", "data": data["errors"]}

            return {"status": "ok", "data": data.get("response", [])}

        except requests.exceptions.RequestException as e:
            return {"status": "error", "data": str(e)}
