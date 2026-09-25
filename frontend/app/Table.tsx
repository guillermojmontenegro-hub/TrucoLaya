import type { CSSProperties } from "react";
import { CardBack, SpanishCard } from "./SpanishCard";
import type { GameState, Player } from "./gameTypes";
import { playedBy } from "./tableState";

function point(index: number, count: number): CSSProperties {
  const angle = Math.PI / 2 - (index * Math.PI * 2) / count;
  return {
    "--spot-left": `${50 + Math.cos(angle) * 29}%`,
    "--spot-top": `${50 + Math.sin(angle) * 25}%`,
    "--spot-left-mobile": `${50 + Math.cos(angle) * 29}%`,
  } as CSSProperties;
}

function RemainingCards({ count }: { count: number }) {
  return <div className="back-fan" aria-label={`${count} cartas en mano`}>
    {Array.from({ length: count }, (_, index) => {
      const offset = index - (count - 1) / 2;
      return <CardBack key={index} style={{ transform: `translateX(${offset * 17}px) rotate(${offset * 10}deg)` }} />;
    })}
    {count === 0 && <span className="no-cards">Sin cartas</span>}
  </div>;
}

function Seat({ player, index, active }: { player: Player; index: number; active: boolean }) {
  return <div className={`seat team-${player.team}${active ? " active" : ""}`}>
    <div className="seat-head"><span className="seat-avatar">{index}</span><div><strong>{player.name}</strong><small>Equipo {player.team + 1}</small></div>{active && <span className="active-pulse" />}</div>
    <RemainingCards count={player.cardCount} />
  </div>;
}

function PlayedPile({ state, index }: { state: GameState; index: number }) {
  const cards = playedBy(state, index);
  return <div className={`played-pile team-${state.players[index].team}`} style={point(index, state.players.length)} aria-label={`Cartas jugadas por ${state.players[index].name}`}>
    {cards.length ? cards.map((card, order) => <div className="pile-layer" key={card.id} style={{ transform: `translate(${order * 14}px, ${order * 18}px) rotate(${(order - 1) * 3}deg)`, zIndex: order + 1 }}><SpanishCard card={card} compact /></div>) : <div className="pile-empty"><span>＋</span><small>{state.players[index].name}</small></div>}
    {cards.length > 0 && <span className="pile-name">{state.players[index].name}</span>}
  </div>;
}

export function Table({ state }: { state: GameState }) {
  return <section className="table-panel" aria-label="Mesa de juego">
    <div className="table-topline"><span>MESA · {state.players.length} JUGADORES</span><div className="trick-progress">{[0, 1, 2].map(index => <span className={index === state.trick && !state.handOver ? "current" : state.trickWinners[index] !== undefined ? "done" : ""} key={index}>{index + 1}ª mano{state.trickWinners[index] !== undefined && <b>{state.trickWinners[index] === null ? "· parda" : `· E${state.trickWinners[index]! + 1}`}</b>}</span>)}</div></div>
    <div className="opponent-rail">{state.players.slice(1).map((player, offset) => <Seat key={offset + 1} player={player} index={offset + 1} active={state.turn === offset + 1 && !state.handOver} />)}</div>
    <div className="arena"><div className="arena-grain" /><div className="center-seal"><span>TRUCO</span><strong>LAYA</strong><i>EST. 2026</i></div>
      {state.players.map((_, index) => <PlayedPile key={index} state={state} index={index} />)}
      <div className="you-marker">TUS JUGADAS</div>
    </div>
  </section>;
}

export { RemainingCards };
