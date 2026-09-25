"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { LayaLog, type LayaLogEntry } from "./LayaLog";
import { SpanishCard } from "./SpanishCard";
import { RemainingCards, Table } from "./Table";
import type { GameState } from "./gameTypes";

const actionLabel: Record<string, string> = {
  fold: "Ir al mazo",
  truco: "Cantar truco",
  envido: "Cantar envido",
  accept: "Quiero",
  reject: "No quiero",
  raise_truco: "Subir truco",
};

async function request<T>(path: string, body?: object): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: body ? "POST" : "GET",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const raw = await response.text();
  let data: Record<string, unknown>;
  try {
    data = JSON.parse(raw) as Record<string, unknown>;
  } catch {
    throw new Error(response.ok
      ? "El servidor devolvió una respuesta inválida. Reintentá la acción."
      : "No se pudo conectar con el servidor de juego. Reintentá en unos segundos.");
  }
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "No se pudo completar la acción");
  return data as T;
}

export default function Home() {
  const [count, setCount] = useState(2);
  const [gameId, setGameId] = useState<string | null>(null);
  const [state, setState] = useState<GameState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showLog, setShowLog] = useState(false);
  const [logEntries, setLogEntries] = useState<LayaLogEntry[]>([]);
  const [logLoading, setLogLoading] = useState(false);
  const [logError, setLogError] = useState("");
  const [logRefresh, setLogRefresh] = useState(0);

  useEffect(() => {
    if (!showLog || !gameId) return;
    let active = true;
    request<{ entries: LayaLogEntry[] }>(`/games/${gameId}/laya-log`)
      .then(result => { if (active) { setLogEntries(result.entries); setLogError(""); } })
      .catch(caught => { if (active) setLogError(caught instanceof Error ? caught.message : "No se pudo cargar el registro"); })
      .finally(() => { if (active) setLogLoading(false); });
    return () => { active = false; };
  }, [showLog, gameId, state, logRefresh]);

  useEffect(() => {
    if (!gameId || !state?.botThinking) return;
    const timer = window.setTimeout(() => {
      request<GameState>(`/games/${gameId}`)
        .then(updated => { setState(updated); setError(""); })
        .catch(caught => setError(caught instanceof Error ? caught.message : "No se pudo actualizar la partida"));
    }, 1200);
    return () => window.clearTimeout(timer);
  }, [gameId, state]);

  async function run(task: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await task();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Error inesperado");
    } finally {
      setBusy(false);
    }
  }

  function start() {
    void run(async () => {
      const created = await request<{ id: string; state: GameState }>("/games", { players: count });
      setGameId(created.id);
      setState(created.state);
      setLogEntries([]);
      setShowLog(false);
    });
  }

  function action(value: string) {
    if (!gameId) return;
    void run(async () => setState(await request<GameState>(`/games/${gameId}/actions`, { action: value })));
  }

  function nextHand() {
    if (!gameId) return;
    void run(async () => setState(await request<GameState>(`/games/${gameId}/next-hand`, {})));
  }

  function retry() {
    if (!gameId) { start(); return; }
    void run(async () => setState(await request<GameState>(state?.botError ? `/games/${gameId}/retry` : `/games/${gameId}`, state?.botError ? {} : undefined)));
  }

  return <main className="shell">
    <header className="topbar"><Link className="wordmark" href="/"><span className="brand-badge">TL</span><span><strong>TRUCO <em>LAYA</em></strong><small>LA MESA ARGENTINA</small></span></Link><div className="topbar-right"><span className="online-dot" /> UNA NUEVA FORMA DE JUGAR</div></header>
    {!state ? <section className="welcome">
      <div className="welcome-copy"><p className="eyebrow">TRUCO ARGENTINO × INTELIGENCIA ARTIFICIAL</p><h1>El truco de siempre.<br /><em>Una mesa distinta.</em></h1><p className="welcome-lead">Repartí, cantá y jugá tus cartas frente a rivales que toman cada decisión con Laya.</p><div className="welcome-rule" /><p className="selector-label">ELEGÍ TU MESA</p><div className="player-options" role="group" aria-label="Cantidad de jugadores">{[2, 4, 6].map(n => <button key={n} type="button" className={count === n ? "selected" : ""} onClick={() => setCount(n)}><strong>{n}</strong><span>jugadores</span></button>)}</div><button className="primary" type="button" disabled={busy} onClick={start}>{busy ? "Laya está pensando…" : "Sentarme a jugar"}<span aria-hidden="true">↗</span></button><p className="hint">Vos jugás en el equipo 1. Los demás asientos los ocupa Laya.</p></div>
      <div className="welcome-art" aria-hidden="true"><div className="art-orbit orbit-one" /><div className="art-orbit orbit-two" /><div className="art-card art-back"><span>TL</span></div><div className="art-card art-face"><span>1</span><b>ESPADAS</b><i>✦</i></div><div className="art-stamp">40 CARTAS<br />30 PUNTOS</div></div>
    </section> : <>
      <div className="game-heading"><div><p className="eyebrow">PARTIDA EN CURSO</p><h1>Tu mesa de truco</h1></div><div className="heading-actions"><button className="laya-toggle" type="button" aria-expanded={showLog} aria-controls="laya-log" onClick={() => { setShowLog(value => !value); setLogLoading(true); }}>{showLog ? "Ocultar Laya" : "Ver Laya"} <span aria-hidden="true">✦</span></button><span className="game-format">{state.players.length === 2 ? "MANO A MANO" : state.players.length === 4 ? "POR PAREJAS" : "POR TRÍOS"}</span></div></div>
      <div className="game-layout"><div className="game-board">
      <Table state={state} />
      </div><div className="game-sidebar">
      <section className="scoreboard" aria-label="Puntaje"><div className="score-team your-team"><span className="team-token">01</span><div><small>TU EQUIPO</small><strong>{state.scores[0]}</strong></div></div><div className="score-center"><span>PARTIDA A {state.target}</span><i>◆</i><span>{state.trucoLevel === 0 ? "SIN TRUCO" : state.trucoLevel === 1 ? "TRUCO" : state.trucoLevel === 2 ? "RETRUCO" : "VALE CUATRO"}</span></div><div className="score-team rivals"><div><small>RIVALES</small><strong>{state.scores[1]}</strong></div><span className="team-token">02</span></div></section>
      <section className="hand-dock" aria-label="Tus cartas"><div className="hand-info"><div><p className="eyebrow">TU LUGAR EN LA MESA</p><h2>Tus cartas <span>· {state.players[0].cardCount} en mano</span></h2></div><div className="your-backs"><RemainingCards count={state.players[0].cardCount} /><small>DORSOS EN MANO</small></div></div><div className="hand-cards">{state.players[0].cards?.map(card => <SpanishCard card={card} key={card.id} disabled={busy || !state.legalActions.includes(`play:${card.id}`)} onPlay={() => action(`play:${card.id}`)} />)}</div><p className="hand-hint" role="status">{state.botThinking ? "Laya está pensando… La primera vez puede tardar mientras descarga el modelo." : state.botError ? "Laya no pudo completar su turno. Reintentá desde el aviso inferior." : state.handOver ? "Terminó el reparto. Las cartas jugadas siguen sobre la mesa." : state.turn === 0 ? "Elegí una carta para jugar o cantá antes de tirar." : "Esperando a los otros jugadores…"}</p></section>
      <section className="game-footer"><div className="game-message"><span className="message-mark">✦</span><div><small>EN LA MESA</small><p role="status">{state.winner !== null ? `¡Ganó el equipo ${state.winner + 1}!` : state.message}</p>{state.envidoResult && <small>Envido: {state.envidoResult.points[0]} a {state.envidoResult.points[1]} · equipo {state.envidoResult.winner + 1}</small>}</div></div>{state.handOver ? state.winner === null ? <button className="primary" type="button" disabled={busy} onClick={nextHand}>Repartir nuevas cartas <span aria-hidden="true">↗</span></button> : <button className="primary" type="button" onClick={() => { setState(null); setGameId(null); }}>Nueva partida <span aria-hidden="true">↗</span></button> : <div className="actions">{state.legalActions.filter(value => !value.startsWith("play:")).map(value => <button type="button" key={value} disabled={busy} onClick={() => action(value)}>{actionLabel[value]}</button>)}</div>}</section>
      </div></div>
      {showLog && <LayaLog entries={logEntries} loading={logLoading} error={logError} onRefresh={() => { setLogLoading(true); setLogRefresh(value => value + 1); }} />}
    </>}
    {(error || state?.botError) && <div className="error" role="alert">{error || `Laya no pudo decidir: ${state?.botError}`} <button type="button" disabled={busy} onClick={retry}>Reintentar</button></div>}
    <footer>TRUCO LAYA <span>·</span> BARAJA ESPAÑOLA <span>·</span> HECHO PARA JUGAR</footer>
  </main>;
}
