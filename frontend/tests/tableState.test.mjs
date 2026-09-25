import assert from "node:assert/strict";
import test from "node:test";
import { playedBy } from "../app/tableState.ts";

const card = (rank, suit) => ({ id: `${rank}-${suit}`, rank, suit });

test("each player's earlier cards remain under their newest card", () => {
  const state = {
    history: [
      [{ player: 1, card: card(3, "oro") }, { player: 0, card: card(1, "espada") }],
      [{ player: 0, card: card(7, "copa") }, { player: 1, card: card(2, "basto") }],
    ],
    table: [{ player: 1, card: card(5, "oro") }],
  };
  assert.deepEqual(playedBy(state, 1).map(played => played.id), ["3-oro", "2-basto", "5-oro"]);
  assert.deepEqual(playedBy(state, 0).map(played => played.id), ["1-espada", "7-copa"]);
  assert.deepEqual(playedBy({ ...state, table: [] }, 1).map(played => played.id), ["3-oro", "2-basto"]);
});
