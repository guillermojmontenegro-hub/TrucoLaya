"""Translate a public Truco position into typed Laya decisions."""

from __future__ import annotations

from typing import Protocol

from truco.domain import Card, Game, envido_points


class DecisionMaker(Protocol):
    def choose(self, game: Game, player: int) -> str: ...


def card_name(card: Card) -> str:
    return f"{card.rank} de {card.suit}"


def public_play(game: Game, index: int, card: Card) -> dict:
    return {
        "jugador": game.players[index].name,
        "equipo": game.players[index].team + 1,
        "carta": card_name(card),
        "fuerza": card.power,
    }


def position(game: Game, player: int) -> dict:
    """Only own cards and cards already face up are visible to the model."""
    actor = game.players[player]
    table = [public_play(game, index, card) for index, card in game.table]
    highest = max((card.power for _, card in game.table), default=0)
    leading_teams = {
        game.players[index].team for index, card in game.table if card.power == highest
    }
    if not table:
        table_status = "Todavía nadie jugó esta baza"
    elif len(leading_teams) > 1:
        table_status = "La baza está parda por ahora"
    elif actor.team in leading_teams:
        table_status = "Tu equipo va ganando la baza por ahora"
    else:
        table_status = "El rival va ganando la baza por ahora"

    own_original = actor.hand + [
        card for trick in game.history for index, card in trick if index == player
    ] + [card for index, card in game.table if index == player]
    return {
        "regla_clave": "Mayor fuerza gana la baza; 14 es la carta más fuerte y 1 la más débil. No se conocen las cartas rivales ocultas. La primera baza suele ser decisiva: una parda posterior favorece al ganador anterior.",
        "jugador": actor.name,
        "equipo": actor.team + 1,
        "turno": player,
        "mano": game.trick + 1,
        "jugador_mano": game.players[(game.dealer + 1) % len(game.players)].name,
        "cartas_propias": [
            {"carta": card_name(card), "fuerza": card.power} for card in actor.hand
        ],
        "envido_propio": envido_points(own_original),
        "mesa_actual": table,
        "situacion_mesa": table_status,
        "historial_bazas": [
            [public_play(game, index, card) for index, card in trick] for trick in game.history
        ],
        "ganadores_bazas": [None if team is None else team + 1 for team in game.trick_winners],
        "cartas_restantes": [
            {"jugador": participant.name, "equipo": participant.team + 1, "cantidad": len(participant.hand)}
            for participant in game.players
        ],
        "puntaje": {"equipo_1": game.scores[0], "equipo_2": game.scores[1]},
        "puntos_truco_en_juego": game.truco_level + 1,
        "canto_pendiente": game.pending,
    }


def card_criteria(game: Game, player: int, actions: list[str]) -> dict[str, str]:
    actor = game.players[player]
    leader = max((card.power for _, card in game.table), default=0)
    options = {}
    for action in actions:
        card = next(card for card in actor.hand if action == f"play:{card.id}")
        comparison = (
            "abre la baza" if not game.table else
            "supera la carta más fuerte visible" if card.power > leader else
            "empata la carta más fuerte visible" if card.power == leader else
            "no supera la carta más fuerte visible"
        )
        remaining = ", ".join(card_name(other) for other in actor.hand if other != card)
        options[action] = (
            f"Jugar {card_name(card)}. Fuerza {card.power}/14; {comparison}. "
            f"Después quedarán: {remaining or 'ninguna carta'}."
        )
    return options


class LayaDecisionMaker:
    def __init__(self) -> None:
        self._router = None

    def choose(self, game: Game, player: int) -> str:
        actions = game.legal_actions(player)
        if len(actions) == 1:
            return actions[0]
        if self._router is None:
            from laya import Router

            self._router = Router()

        context = position(game, player)
        if game.pending:
            descriptions = {
                "accept": "Quiero: aceptar los puntos en juego; conviene con ventaja real o para sostener un bluff",
                "reject": "No quiero: conceder los puntos por rechazo y cerrar el canto",
                "raise_truco": "Subir la apuesta; conviene con cartas fuertes y ventaja en las bazas",
            }
            questions = {"respuesta": {
                "type": "choice",
                "instructions": "Respondé el canto pendiente según cartas propias, bazas y puntaje. Elegí una acción legal.",
                "criteria": {action: descriptions[action] for action in actions},
            }}
            answer_key = "respuesta"
        else:
            plays = [action for action in actions if action.startswith("play:")]
            intents = {"play": "Jugar una carta. Es la opción normal para avanzar la mano."}
            if "truco" in actions:
                intents["truco"] = "Cantar truco: aumentar la apuesta si hay buena posibilidad de ganar o un bluff razonable."
            if "envido" in actions:
                intents["envido"] = "Cantar envido: apostar por el tanto propio y el posible tanto de compañeros."
            if "fold" in actions:
                intents["fold"] = "Ir al mazo: conceder la mano; sólo si continuar es claramente peor."
            questions = {"intencion": {
                "type": "choice",
                "instructions": "Elegí si jugar una carta o cantar. Priorizá jugar; no repitas cantos sin ventaja. Las cartas ocultas rivales son desconocidas.",
                "criteria": intents,
            }}
            if len(plays) > 1:
                questions["carta"] = {
                    "type": "choice",
                    "instructions": "Elegí qué carta tirar EN ESTA baza. Considerá la carta líder visible, si tu compañero ya gana, bazas anteriores y qué cartas conviene guardar. Una carta más fuerte tiene mayor fuerza numérica.",
                    "criteria": card_criteria(game, player, plays),
                }
            answer_key = "intencion"

        result = self._router.predict(context, questions, model="multilingual", max_len=2048)
        answer = result["answers"][answer_key]["choice"]
        if not game.pending and answer == "play":
            answer = result["answers"]["carta"]["choice"] if "carta" in questions else plays[0]
        if answer not in actions:
            raise RuntimeError(f"Laya devolvió una acción no permitida: {answer}")
        return answer
