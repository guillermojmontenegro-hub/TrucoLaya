from threading import Event
from time import monotonic, sleep

from fastapi.testclient import TestClient

from truco import api
from truco.ai import Decision
from truco.service import GameService


class Bot:
    def choose(self, game, player):
        action = next((a for a in game.legal_actions(player) if a.startswith("play:")), game.legal_actions(player)[0])
        return Decision(action=action, model="prueba", intent="play", probability=0.8)


def ready(client, game_id, state):
    deadline = monotonic() + 10
    while state["botThinking"]:
        assert monotonic() < deadline
        sleep(0.001)
        state = client.get(f"/games/{game_id}").json()
    assert state["botError"] is None
    return state


def test_http_flow(monkeypatch):
    monkeypatch.setattr(api, "service", GameService(Bot()))
    client = TestClient(api.app)
    assert client.get("/health").json() == {"status": "ok"}
    assert client.post("/games", json={"players": 3}).status_code == 400
    created = client.post("/games", json={"players": 2})
    assert created.status_code == 200
    game_id = created.json()["id"]
    state = ready(client, game_id, created.json()["state"])
    assert state["turn"] == 0
    assert client.post(f"/games/{game_id}/actions", json={"action": "play:99-oro"}).status_code == 400
    action = next(a for a in state["legalActions"] if a.startswith("play:"))
    updated = client.post(f"/games/{game_id}/actions", json={"action": action})
    assert updated.status_code == 200
    ready(client, game_id, updated.json())
    assert client.get(f"/games/{game_id}").status_code == 200
    log = client.get(f"/games/{game_id}/laya-log")
    assert log.status_code == 200
    entries = log.json()["entries"]
    assert len(entries) >= 1
    assert entries[0]["model"] == "prueba"
    assert entries[0]["player"] == "Laya 1"
    assert entries[0]["action"].startswith("play:")
    assert "cartas_propias" not in str(entries)


def test_slow_first_decision_does_not_block_http(monkeypatch):
    release = Event()

    class SlowBot(Bot):
        def choose(self, game, player):
            release.wait(timeout=5)
            return super().choose(game, player)

    monkeypatch.setattr(api, "service", GameService(SlowBot()))
    client = TestClient(api.app)
    try:
        started = monotonic()
        response = client.post("/games", json={"players": 2})
        assert monotonic() - started < 1
        created = response.json()
        game_id = created["id"]
        assert created["state"]["botThinking"] is True
        started = monotonic()
        assert client.get(f"/games/{game_id}").json()["botThinking"] is True
        assert monotonic() - started < 1
    finally:
        release.set()
    ready(client, game_id, created["state"])


def test_failed_model_turn_can_be_retried(monkeypatch):
    class FlakyBot(Bot):
        calls = 0

        def choose(self, game, player):
            self.calls += 1
            if self.calls == 1:
                raise ValueError("modelo no disponible")
            return super().choose(game, player)

    monkeypatch.setattr(api, "service", GameService(FlakyBot()))
    client = TestClient(api.app)
    created = client.post("/games", json={"players": 2}).json()
    game_id = created["id"]
    state = created["state"]
    deadline = monotonic() + 10
    while state["botThinking"]:
        assert monotonic() < deadline
        sleep(0.001)
        state = client.get(f"/games/{game_id}").json()
    assert state["botError"] == "modelo no disponible"
    retried = client.post(f"/games/{game_id}/retry")
    assert retried.status_code == 200
    ready(client, game_id, retried.json())
