from api_client import RapidAPIClient

class FootballAPI:
    def __init__(self, api_key):
        self.client = RapidAPIClient(api_key)

    def fixtures_by_date(self, date: str):
        return self.client.get("fixtures", {"date": date})

    def fixtures_by_league(self, league_id: int, season: int):
        return self.client.get("fixtures", {"league": league_id, "season": season})

    def odds(self, fixture_id: int):
        return self.client.get("odds", {"fixture": fixture_id})

    def predictions(self, fixture_id: int):
        return self.client.get("predictions", {"fixture": fixture_id})

    def standings(self, league_id: int, season: int):
        return self.client.get("standings", {"league": league_id, "season": season})

    def teams(self, league_id: int, season: int):
        return self.client.get("teams", {"league": league_id, "season": season})
