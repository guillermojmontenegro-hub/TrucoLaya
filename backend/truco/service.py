"""Application service: game lifecycle and bot turns."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from uuid import uuid4

from truco.ai import DecisionMaker, LayaDecisionMaker
from truco.domain import Game, InvalidMove


@dataclass
class Session:
    game: Game
    lock: Lock = field(default_factory=Lock)


class GameService:
    def __init__(self, decision_maker: DecisionMaker | None = None) -> None:
        self._games: dict[str, Session] = {}
        self._lock = Lock()
        self._ai = decision_maker or LayaDecisionMaker()

    def create(self, players: int) -> tuple[str, dict]:
        game = Game.create(players)
        game_id = uuid4().hex
        session = Session(game)
        with self._lock:
            self._games[game_id] = session
        try:
            with session.lock:
                self._run_bots(game)
                return game_id, game.view()
        except Exception:
            with self._lock:
                self._games.pop(game_id, None)
            raise

    def get(self, game_id: str) -> dict:
        session = self._session(game_id)
        with session.lock:
            self._run_bots(session.game)
            return session.game.view()

    def act(self, game_id: str, action: str) -> dict:
        session = self._session(game_id)
        with session.lock:
            session.game.act(0, action)
            self._run_bots(session.game)
            return session.game.view()

    def next_hand(self, game_id: str) -> dict:
        session = self._session(game_id)
        with session.lock:
            if not session.game.hand_over:
                raise InvalidMove("La mano todavía no terminó")
            session.game.new_hand()
            self._run_bots(session.game)
            return session.game.view()

    def _session(self, game_id: str) -> Session:
        with self._lock:
            session = self._games.get(game_id)
        if session is None:
            raise KeyError(game_id)
        return session

    def _run_bots(self, game: Game) -> None:
        for _ in range(80):
            if game.hand_over or game.winner is not None or game.turn == 0:
                return
            action = self._ai.choose(game, game.turn)
            game.act(game.turn, action)
        raise RuntimeError("La IA excedió el límite de acciones de esta mano")
