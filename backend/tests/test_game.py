from random import Random

import pytest

from truco.ai import LayaDecisionMaker
from truco.domain import Card, Game, InvalidMove, envido_points
from truco.service import GameService


class FirstLegalDecision:
    def choose(self, game: Game, player: int) -> str:
        return next((action for action in game.legal_actions(player) if action.startswith("play:")), game.legal_actions(player)[0])


def test_deal_and_team_layout():
    for count in (2, 4, 6):
        game = Game.create(count, Random(12))
        assert [player.team for player in game.players] == [i % 2 for i in range(count)]
        assert len({card.id for player in game.players for card in player.hand}) == count * 3
        assert len(game.view()["players"][0]["cards"]) == 3
        assert all(player["cards"] is None for player in game.view()["players"][1:])


def test_invalid_action_is_rejected():
    game = Game.create(2, Random(4))
    with pytest.raises(InvalidMove):
        game.act(0, "play:99-oro")
    with pytest.raises(InvalidMove):
        Game.create(3)


def test_envido_value():
    assert envido_points([Card(7, "oro"), Card(6, "oro"), Card(12, "copa")]) == 33
    assert envido_points([Card(7, "oro"), Card(6, "copa"), Card(12, "basto")]) == 7


def test_service_completes_game_with_bot_port():
    service = GameService(FirstLegalDecision())
    game_id, state = service.create(6)
    for _ in range(250):
        if state["winner"] is not None:
            break
        if state["handOver"]:
            state = service.next_hand(game_id)
        else:
            action = next((a for a in state["legalActions"] if a.startswith("play:")), state["legalActions"][0])
            state = service.act(game_id, action)
    assert state["winner"] in (0, 1)
    assert max(state["scores"]) >= 30


def test_laya_adapter_selects_only_legal_action():
    game = Game.create(2, Random(7))
    chosen = game.legal_actions(game.turn)[0]

    class RouterStub:
        def predict(self, context, questions, model):
            assert model == "multilingual"
            assert "jugada" in questions
            assert "cartas_propias" in context
            assert "cartas" not in context
            return {"answers": {"jugada": {"choice": chosen}}}

    adapter = LayaDecisionMaker()
    adapter._router = RouterStub()
    assert adapter.choose(game, game.turn) == chosen
