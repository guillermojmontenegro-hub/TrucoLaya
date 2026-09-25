"""Pure game rules. No HTTP or model dependencies live here."""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

SUITS = ("espada", "basto", "oro", "copa")
RANKS = (1, 2, 3, 4, 5, 6, 7, 10, 11, 12)
POWER = {
    (1, "espada"): 14, (1, "basto"): 13, (7, "espada"): 12, (7, "oro"): 11,
    (3, None): 10, (2, None): 9, (1, None): 8, (12, None): 7,
    (11, None): 6, (10, None): 5, (7, None): 4, (6, None): 3,
    (5, None): 2, (4, None): 1,
}
TRUCO_NAMES = {1: "Truco", 2: "Retruco", 3: "Vale cuatro"}


class InvalidMove(ValueError):
    pass


@dataclass(frozen=True)
class Card:
    rank: int
    suit: str

    @property
    def id(self) -> str:
        return f"{self.rank}-{self.suit}"

    @property
    def power(self) -> int:
        return POWER.get((self.rank, self.suit), POWER[(self.rank, None)])

    @property
    def envido(self) -> int:
        return self.rank if self.rank < 8 else 0

    def public(self) -> dict:
        return {"id": self.id, "rank": self.rank, "suit": self.suit}


def envido_points(cards: list[Card]) -> int:
    pairs = [20 + a.envido + b.envido for i, a in enumerate(cards) for b in cards[i + 1:] if a.suit == b.suit]
    return max(pairs, default=max(card.envido for card in cards))


@dataclass
class Player:
    name: str
    team: int
    human: bool
    hand: list[Card] = field(default_factory=list)


@dataclass
class Game:
    players: list[Player]
    target: int = 30
    scores: list[int] = field(default_factory=lambda: [0, 0])
    dealer: int = -1
    turn: int = 0
    starter: int = 0
    trick: int = 0
    table: list[tuple[int, Card]] = field(default_factory=list)
    history: list[list[tuple[int, Card]]] = field(default_factory=list)
    trick_winners: list[int | None] = field(default_factory=list)
    truco_level: int = 0
    truco_owner: int | None = None
    pending: dict | None = None
    envido_called: bool = False
    envido_result: dict | None = None
    hand_over: bool = False
    winner: int | None = None
    message: str = ""

    @classmethod
    def create(cls, count: int, rng: Random | None = None) -> Game:
        if count not in (2, 4, 6):
            raise InvalidMove("La cantidad de jugadores debe ser 2, 4 o 6")
        game = cls([Player("Vos" if i == 0 else f"Laya {i}", i % 2, i == 0) for i in range(count)])
        game.new_hand(rng)
        return game

    def new_hand(self, rng: Random | None = None) -> None:
        if self.winner is not None:
            raise InvalidMove("La partida ya terminó")
        deck = [Card(rank, suit) for suit in SUITS for rank in RANKS]
        (rng or Random()).shuffle(deck)
        self.dealer = (self.dealer + 1) % len(self.players)
        self.starter = (self.dealer + 1) % len(self.players)
        self.turn = self.starter
        for player in self.players:
            player.hand = [deck.pop() for _ in range(3)]
        self.trick = 0
        self.table = []
        self.history = []
        self.trick_winners = []
        self.truco_level = 0
        self.truco_owner = None
        self.pending = None
        self.envido_called = False
        self.envido_result = None
        self.hand_over = False
        self.message = "Nuevo reparto."

    def legal_actions(self, index: int) -> list[str]:
        if self.hand_over or self.winner is not None:
            return []
        if self.pending:
            if self.players[index].team == self.pending["team"]:
                return []
            actions = ["accept", "reject"]
            if self.pending["kind"] == "truco" and self.pending["level"] < 3:
                actions.append("raise_truco")
            return actions if index == self.turn else []
        if index != self.turn:
            return []
        actions = [f"play:{card.id}" for card in self.players[index].hand]
        actions.append("fold")
        if self.truco_level < 3 and self.truco_owner != self.players[index].team:
            actions.append("truco")
        if self.trick == 0 and not self.envido_called and self.truco_level == 0:
            actions.append("envido")
        return actions

    def act(self, index: int, action: str) -> None:
        if action not in self.legal_actions(index):
            raise InvalidMove("Acción inválida o fuera de turno")
        team = self.players[index].team
        if self.pending:
            pending = self.pending
            if action == "raise_truco":
                self.truco_level = pending["level"]
                self.truco_owner = pending["team"]
                self.pending = {"kind": "truco", "level": self.truco_level + 1, "team": team, "resume": index}
                self.turn = self._next_opponent(index)
                self.message = f"{self.players[index].name} cantó {TRUCO_NAMES[self.pending['level']]}"
            elif action == "reject":
                self.pending = None
                if pending["kind"] == "truco":
                    self._award(pending["team"], pending["level"])
                    self.hand_over = True
                else:
                    self._award(pending["team"], 1)
                    self.envido_called = True
                    self.turn = pending["resume"]
                self.message = "No quiso."
            else:
                self.pending = None
                if pending["kind"] == "truco":
                    self.truco_level = pending["level"]
                    self.truco_owner = pending["team"]
                else:
                    self._resolve_envido(pending["team"])
                    self.envido_called = True
                self.turn = pending["resume"]
                self.message = "Quiso." if pending["kind"] == "truco" else self.message
            return
        if action == "fold":
            self._award(1 - team, self.truco_level + 1)
            self.hand_over = True
            self.message = f"{self.players[index].name} se fue al mazo."
        elif action == "truco":
            self.pending = {"kind": "truco", "level": self.truco_level + 1, "team": team, "resume": index}
            self.turn = self._next_opponent(index)
            self.message = f"{self.players[index].name} cantó {TRUCO_NAMES[self.pending['level']]}"
        elif action == "envido":
            self.pending = {"kind": "envido", "team": team, "resume": index}
            self.turn = self._next_opponent(index)
            self.message = f"{self.players[index].name} cantó envido."
        else:
            card_id = action.removeprefix("play:")
            card = next(card for card in self.players[index].hand if card.id == card_id)
            self.players[index].hand.remove(card)
            self.table.append((index, card))
            self.message = f"{self.players[index].name} jugó {card.rank} de {card.suit}."
            if len(self.table) == len(self.players):
                self._finish_trick()
            else:
                self.turn = (index + 1) % len(self.players)

    def _next_opponent(self, index: int) -> int:
        return (index + 1) % len(self.players)

    def _award(self, team: int, points: int) -> None:
        self.scores[team] += points
        if self.scores[team] >= self.target:
            self.winner = team

    def _resolve_envido(self, caller: int) -> None:
        values = [max(envido_points(p.hand + [card for trick in self.history for i, card in trick if i == idx] + [card for i, card in self.table if i == idx]) for idx, p in enumerate(self.players) if p.team == team) for team in (0, 1)]
        winner = 0 if values[0] > values[1] else 1 if values[1] > values[0] else self.players[self.starter].team
        self._award(winner, 2)
        self.envido_result = {"points": values, "winner": winner}
        self.message = f"Envido: {values[0]} a {values[1]}. Ganó equipo {winner + 1}."

    def _finish_trick(self) -> None:
        maximum = max(card.power for _, card in self.table)
        leaders = {self.players[index].team for index, card in self.table if card.power == maximum}
        winner = leaders.pop() if len(leaders) == 1 else None
        self.trick_winners.append(winner)
        self.history.append(self.table)
        self.table = []
        self.trick += 1
        self.message = "Parda." if winner is None else f"Mano para equipo {winner + 1}."
        hand_winner = self._hand_winner()
        if hand_winner is not None:
            self._award(hand_winner, self.truco_level + 1)
            self.hand_over = True
            self.message += f" Reparto para equipo {hand_winner + 1}."
        else:
            if winner is not None:
                self.starter = next(index for index, card in self.history[-1] if self.players[index].team == winner and card.power == maximum)
            self.turn = self.starter

    def _hand_winner(self) -> int | None:
        wins = [self.trick_winners.count(team) for team in (0, 1)]
        if 2 in wins:
            return wins.index(2)
        if self.trick < 2:
            return None
        first, second = self.trick_winners[:2]
        if first is None and second is not None:
            return second
        if first is not None and second is None:
            return first
        if self.trick == 3:
            third = self.trick_winners[2]
            return third if third is not None else next((x for x in self.trick_winners if x is not None), self.players[(self.dealer + 1) % len(self.players)].team)
        return None

    def view(self, viewer: int = 0) -> dict:
        def played(rows: list[tuple[int, Card]]) -> list[dict]:
            return [{"player": index, "card": card.public()} for index, card in rows]

        return {
            "players": [{"name": p.name, "team": p.team, "human": p.human, "cards": [c.public() for c in p.hand] if i == viewer else None, "cardCount": len(p.hand)} for i, p in enumerate(self.players)],
            "scores": self.scores, "target": self.target, "dealer": self.dealer,
            "turn": self.turn, "trick": self.trick, "table": played(self.table),
            "history": [played(row) for row in self.history], "trickWinners": self.trick_winners,
            "trucoLevel": self.truco_level, "pending": self.pending,
            "envidoResult": self.envido_result, "handOver": self.hand_over,
            "winner": self.winner, "message": self.message, "legalActions": self.legal_actions(viewer),
        }
