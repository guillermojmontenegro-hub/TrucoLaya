"use client";

import { useState } from "react";

type Card = { id: string; rank: number; suit: string };
type Player = { name: string; team: number; human: boolean; cards: Card[] | null; cardCount: number };
type Played = { player: number; card: Card };
type State = {
  players: Player[]; scores: number[]; target: number; dealer: number; turn: number;
  trick: number; table: Played[]; history: Played[][]; trickWinners: (number | null)[];
  trucoLevel: number; pending: { kind: string; level?: number; team: number } | null;
  envidoResult: { points: number[]; winner: number } | null;
  handOver: boolean; winner: number | null; message: string; legalActions: string[];
};

const suitSymbol: Record<string, string> = { espada: "♠", basto: "♣", oro: "◆", copa: "♥" };
const actionLabel: Record<string, string> = {
  fold: "Ir al mazo", truco: "Cantar truco", envido: "Cantar envido",
  accept: "Quiero", reject: "No quiero", raise_truco: "Subir truco",
};

async function request<T>(path: string, body?: object): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: body ? "POST" : "GET", headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail ?? "No se pudo completar la acción");
  return data as T;
}

function CardFace({ card, onClick, disabled = false }: { card: Card; onClick?: () => void; disabled?: boolean }) {
  return <button type="button" className={`card ${card.suit}`} onClick={onClick} disabled={disabled || !onClick} aria-label={`${card.rank} de ${card.suit}`}>
    <span className="card-rank">{card.rank}</span><span className="card-suit">{suitSymbol[card.suit]}</span><small>{card.suit}</small>
  </button>;
}

export default function Home() {
  const [count, setCount] = useState(2);
  const [gameId, setGameId] = useState<string | null>(null);
  const [state, setState] = useState<State | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run(task: () => Promise<void>) {
    setBusy(true); setError("");
    try { await task(); } catch (caught) { setError(caught instanceof Error ? caught.message : "Error inesperado"); }
    finally { setBusy(false); }
  }

  function start() {
    void run(async () => {
      const result = await request<{ id: string; state: State }>("/games", { players: count });
      setGameId(result.id); setState(result.state);
    });
  }

  function action(value: string) {
    if (!gameId) return;
    void run(async () => setState(await request<State>(`/games/${gameId}/actions`, { action: value })));
  }

  function nextHand() {
    if (!gameId) return;
    void run(async () => setState(await request<State>(`/games/${gameId}/next-hand`, {})));
  }

  function retry() {
    if (!gameId) { start(); return; }
    void run(async () => setState(await request<State>(`/games/${gameId}`)));
  }

  return <main className="shell">
    <header className="topbar"><div><p className="eyebrow">MESA ARGENTINA · IA LOCAL</p><h1>Truco <em>Laya</em></h1></div><span className="brand-mark">♠</span></header>
    {!state ? <section className="welcome panel">
      <div className="welcome-icon">♠</div><p className="eyebrow">ARMÁ TU MESA</p>
      <h2>La mesa está servida.</h2><p>Jugá al truco argentino contra jugadores que deciden cada movimiento con Laya.</p>
      <div className="player-options" role="group" aria-label="Cantidad de jugadores">{[2, 4, 6].map(n => <button key={n} type="button" className={count === n ? "selected" : ""} onClick={() => setCount(n)}>{n} jugadores</button>)}</div>
      <button className="primary" type="button" disabled={busy} onClick={start}>{busy ? "Laya está pensando…" : "Empezar partida →"}</button>
      <p className="hint">Vos ocupás el equipo 1. Los demás asientos los juega Laya.</p>
    </section> : <>
      <section className="scoreboard panel"><div><span>EQUIPO 1</span><strong>{state.scores[0]}</strong></div><div className="score-middle">A {state.target} PUNTOS<br /><b>MANO {state.trick + 1} / 3</b></div><div><span>EQUIPO 2</span><strong>{state.scores[1]}</strong></div></section>
      <section className="table panel" aria-label="Mesa de juego">
        <div className="opponents">{state.players.slice(1).map((player, offset) => <div className={`opponent team-${player.team}`} key={offset}><div className="avatar">{player.name.slice(-1)}</div><div><strong>{player.name}</strong><small>Equipo {player.team + 1} · {player.cardCount} cartas</small></div>{state.turn === offset + 1 && !state.handOver && <span className="turn-dot" title="En turno" />}</div>)}</div>
        <div className="felt"><span className="felt-label">{state.pending ? `Esperando respuesta: ${state.pending.kind === "envido" ? "envido" : "truco"}` : "CARTAS EN MESA"}</span><div className="played-cards">{state.table.length ? state.table.map(({ player, card }) => <div key={player} className="played"><CardFace card={card} /><small>{state.players[player].name}</small></div>) : <span className="empty-table">Esperando la primera carta…</span>}</div></div>
        <div className="hand-area"><div className="hand-heading"><strong>Tu mano</strong><small>{state.handOver ? "Mano terminada" : state.turn === 0 ? "Es tu turno" : "Laya está pensando"}</small></div><div className="hand">{state.players[0].cards?.map(card => <CardFace card={card} key={card.id} disabled={busy || !state.legalActions.includes(`play:${card.id}`)} onClick={() => action(`play:${card.id}`)} />)}</div></div>
      </section>
      <section className="game-footer panel"><p className="status" role="status">{state.winner !== null ? `¡Ganó el equipo ${state.winner + 1}!` : state.message}</p>{state.envidoResult && <p className="envido">Envido: {state.envidoResult.points[0]}–{state.envidoResult.points[1]} · equipo {state.envidoResult.winner + 1}</p>}
        {state.handOver ? state.winner === null ? <button className="primary" type="button" disabled={busy} onClick={nextHand}>Siguiente mano →</button> : <button className="primary" type="button" onClick={() => { setState(null); setGameId(null); }}>Nueva partida →</button> : <div className="actions">{state.legalActions.filter(value => !value.startsWith("play:")).map(value => <button type="button" key={value} disabled={busy} onClick={() => action(value)}>{actionLabel[value]}</button>)}</div>}</section>
    </>}
    {error && <div className="error" role="alert">{error} <button type="button" disabled={busy} onClick={retry}>Reintentar</button></div>}
    <footer>TRUCO LAYA · JUGÁ TUS CARTAS</footer>
  </main>;
}
