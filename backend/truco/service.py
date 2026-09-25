"""Application service: game lifecycle and bot turns."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock, Thread
from uuid import uuid4

from truco.ai import Decision, DecisionMaker, LayaDecisionMaker
from truco.domain import Game, InvalidMove


@dataclass
class Session:
    game: Game
    lock: Lock = field(default_factory=Lock)
    hand_number: int = 1
    laya_log: list[dict] = field(default_factory=list)
    bot_running: bool = False
    bot_error: str | None = None


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
        with session.lock:
            self._schedule_bots(session)
            return game_id, self._view(session)

    def get(self, game_id: str) -> dict:
        session = self._session(game_id)
        with session.lock:
            return self._view(session)

    def log(self, game_id: str) -> dict:
        session = self._session(game_id)
        with session.lock:
            return {"entries": list(session.laya_log)}

    def act(self, game_id: str, action: str) -> dict:
        session = self._session(game_id)
        with session.lock:
            if session.bot_error:
                raise InvalidMove("Laya falló. Reintentá su turno antes de jugar.")
            session.game.act(0, action)
            self._schedule_bots(session)
            return self._view(session)

    def next_hand(self, game_id: str) -> dict:
        session = self._session(game_id)
        with session.lock:
            if not session.game.hand_over:
                raise InvalidMove("El reparto todavía no terminó")
            session.game.new_hand()
            session.hand_number += 1
            session.bot_error = None
            self._schedule_bots(session)
            return self._view(session)

    def retry_bots(self, game_id: str) -> dict:
        session = self._session(game_id)
        with session.lock:
            session.bot_error = None
            self._schedule_bots(session)
            return self._view(session)

    def _session(self, game_id: str) -> Session:
        with self._lock:
            session = self._games.get(game_id)
        if session is None:
            raise KeyError(game_id)
        return session

    @staticmethod
    def _view(session: Session) -> dict:
        return {
            **session.game.view(),
            "botThinking": session.bot_running,
            "botError": session.bot_error,
        }

    def _schedule_bots(self, session: Session) -> None:
        game = session.game
        if session.bot_running or session.bot_error or game.hand_over or game.winner is not None or game.turn == 0:
            return
        session.bot_running = True
        Thread(target=self._run_bots, args=(session,), daemon=True).start()

    def _run_bots(self, session: Session) -> None:
        try:
            for _ in range(80):
                with session.lock:
                    game = session.game
                    if game.hand_over or game.winner is not None or game.turn == 0:
                        return
                    player = game.turn
                    round_number = game.trick + 1
                decision = self._ai.choose(game, player)
                with session.lock:
                    game.act(player, decision.action)
                    session.laya_log.append(self._log_entry(session, player, round_number, decision))
            raise RuntimeError("La IA excedió el límite de acciones de esta mano")
        except Exception as error:  # noqa: BLE001 - surface any model failure through game state
            with session.lock:
                session.bot_error = str(error) or type(error).__name__
        finally:
            with session.lock:
                session.bot_running = False

    @staticmethod
    def _log_entry(session: Session, player: int, round_number: int, decision: Decision) -> dict:
        return {
            "number": len(session.laya_log) + 1,
            "hand": session.hand_number,
            "round": round_number,
            "player": session.game.players[player].name,
            "team": session.game.players[player].team + 1,
            "action": decision.action,
            "intent": decision.intent,
            "choiceType": decision.choice_type,
            "model": decision.model,
            "probability": decision.probability,
            "confidence": decision.confidence,
            "alternatives": decision.alternatives,
            "inputTokens": decision.input_tokens,
            "elapsedMs": decision.elapsed_ms,
            "at": datetime.now(timezone.utc).isoformat(),
        }
