"""HTTP transport; game rules remain in the domain module."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from truco.domain import InvalidMove
from truco.service import GameService

app = FastAPI(title="Truco Laya", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
service = GameService()


class CreateGame(BaseModel):
    players: int = Field(..., description="2, 4 o 6 jugadores")


class Action(BaseModel):
    action: str


def failure(error: Exception) -> HTTPException:
    if isinstance(error, KeyError):
        return HTTPException(404, "Partida inexistente")
    if isinstance(error, InvalidMove):
        return HTTPException(400, str(error))
    return HTTPException(503, f"Laya no pudo decidir: {error}")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/games")
def create_game(body: CreateGame) -> dict:
    try:
        game_id, state = service.create(body.players)
        return {"id": game_id, "state": state}
    except Exception as error:
        raise failure(error) from error


@app.get("/games/{game_id}")
def get_game(game_id: str) -> dict:
    try:
        return service.get(game_id)
    except Exception as error:
        raise failure(error) from error


@app.post("/games/{game_id}/actions")
def act(game_id: str, body: Action) -> dict:
    try:
        return service.act(game_id, body.action)
    except Exception as error:
        raise failure(error) from error


@app.post("/games/{game_id}/next-hand")
def next_hand(game_id: str) -> dict:
    try:
        return service.next_hand(game_id)
    except Exception as error:
        raise failure(error) from error
