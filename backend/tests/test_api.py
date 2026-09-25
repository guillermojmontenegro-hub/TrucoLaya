from fastapi.testclient import TestClient

from truco import api
from truco.service import GameService


class Bot:
    def choose(self, game, player):
        return next((a for a in game.legal_actions(player) if a.startswith("play:")), game.legal_actions(player)[0])


def test_http_flow(monkeypatch):
    monkeypatch.setattr(api, "service", GameService(Bot()))
    client = TestClient(api.app)
    assert client.get("/health").json() == {"status": "ok"}
    assert client.post("/games", json={"players": 3}).status_code == 400
    created = client.post("/games", json={"players": 2})
    assert created.status_code == 200
    game_id = created.json()["id"]
    state = created.json()["state"]
    assert state["turn"] == 0
    assert client.post(f"/games/{game_id}/actions", json={"action": "play:99-oro"}).status_code == 400
    action = next(a for a in state["legalActions"] if a.startswith("play:"))
    updated = client.post(f"/games/{game_id}/actions", json={"action": action})
    assert updated.status_code == 200
    assert client.get(f"/games/{game_id}").status_code == 200
