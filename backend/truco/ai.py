"""Adapter between legal game actions and Laya's typed choice API."""

from __future__ import annotations

from typing import Protocol

from truco.domain import Game


class DecisionMaker(Protocol):
    def choose(self, game: Game, player: int) -> str: ...


class LayaDecisionMaker:
    def __init__(self) -> None:
        self._router = None

    def choose(self, game: Game, player: int) -> str:
        if self._router is None:
            from laya import Router

            self._router = Router()
        actions = game.legal_actions(player)
        if len(actions) == 1:
            return actions[0]
        actor = game.players[player]
        context = {
            "jugador": actor.name,
            "equipo": actor.team + 1,
            "cartas_propias": [card.public() | {"fuerza": card.power, "envido": card.envido} for card in actor.hand],
            "mesa": [{"jugador": i, "equipo": game.players[i].team + 1, "carta": card.public()} for i, card in game.table],
            "bazas": game.trick_winners,
            "puntos": game.scores,
            "mano": game.trick + 1,
            "truco_nivel": game.truco_level,
            "canto_pendiente": game.pending,
            "envido_propio": max((sum(sorted([c.envido for c in actor.hand if c.suit == suit], reverse=True)[:2]) + 20 for suit in {c.suit for c in actor.hand} if sum(c.suit == suit for c in actor.hand) >= 2), default=max((c.envido for c in actor.hand), default=0)),
        }
        descriptions = {
            "fold": "Irse al mazo y conceder los puntos de la mano",
            "truco": "Desafiar al rival para subir los puntos de la mano",
            "envido": "Cantar envido para competir por los puntos de cartas del mismo palo",
            "accept": "Aceptar el canto pendiente",
            "reject": "Rechazar el canto pendiente",
            "raise_truco": "Responder subiendo la apuesta de truco",
        }
        criteria = {action: descriptions.get(action, f"Jugar la carta {action.removeprefix('play:')}") for action in actions}
        question = {"jugada": {"type": "choice", "instructions": "Elegí la mejor jugada legal para ganar esta mano de truco argentino. Considerá fuerza de cartas, bazas, puntaje y apuestas. Respondé con una opción disponible.", "criteria": criteria}}
        result = self._router.predict(context, question, model="multilingual")
        chosen = result["answers"]["jugada"]["choice"]
        if chosen not in actions:
            raise RuntimeError(f"Laya devolvió una acción no permitida: {chosen}")
        return chosen
