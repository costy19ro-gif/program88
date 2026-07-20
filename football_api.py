import requests

class FootballAPI:
    BASE_URL = "https://api-football-v1.p.rapidapi.com/v3"

    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
        }

    def get(self, endpoint, params=None):
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("response", [])
        except Exception as e:
            return {"error": str(e)}

    def fixtures_by_date(self, date):
        return self.get("fixtures", {"date": date})

    def predictions(self, fixture_id):
        return self.get("predictions", {"fixture": fixture_id})

    def odds(self, fixture_id):
        return self.get("odds", {"fixture": fixture_id})
