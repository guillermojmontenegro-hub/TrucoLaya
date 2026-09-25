import type { Card, GameState } from "./gameTypes";

/** Cards remain in seat order after a trick completes. The last card renders on top. */
export function playedBy(state: Pick<GameState, "history" | "table">, player: number): Card[] {
  return [...state.history, state.table]
    .flatMap(round => round.filter(played => played.player === player).map(played => played.card));
}
