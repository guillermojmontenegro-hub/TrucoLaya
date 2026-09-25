export type LayaLogEntry = {
  number: number;
  hand: number;
  round: number;
  player: string;
  team: number;
  action: string;
  intent: string | null;
  choiceType: string;
  model: string;
  probability: number | null;
  confidence: number | null;
  alternatives: Record<string, number>;
  inputTokens: number | null;
  elapsedMs: number | null;
  at: string;
};

const intentLabels: Record<string, string> = {
  play: "Jugar carta",
  fold: "Ir al mazo",
  truco: "Cantar truco",
  envido: "Cantar envido",
  accept: "Quiero",
  reject: "No quiero",
  raise_truco: "Subir truco",
};

function actionName(action: string): string {
  if (action.startsWith("play:")) {
    const [rank, suit] = action.slice(5).split("-");
    const suits: Record<string, string> = { espada: "espadas", basto: "bastos", oro: "oros", copa: "copas" };
    return `Jugó ${rank} de ${suits[suit] ?? suit}`;
  }
  return intentLabels[action] ?? action;
}

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function LayaLog({ entries, loading, error, onRefresh }: { entries: LayaLogEntry[]; loading: boolean; error: string; onRefresh: () => void }) {
  return <section className="laya-log" id="laya-log" aria-label="Registro de decisiones de Laya">
    <div className="log-heading"><div><p className="eyebrow">REGISTRO DE IA</p><h2>Así decidió Laya</h2></div><button type="button" onClick={onRefresh} disabled={loading}>Actualizar ↻</button></div>
    <p className="log-explainer">Laya elige opciones; no genera una explicación en texto. Acá ves las acciones ejecutadas y los valores que devolvió el modelo. No se muestran cartas ocultas de otros jugadores.</p>
    {loading && <p className="log-notice" role="status">Cargando decisiones…</p>}
    {error && <p className="log-error" role="alert">{error}</p>}
    {!loading && !error && entries.length === 0 && <p className="log-notice">Todavía no hubo decisiones de Laya en esta partida.</p>}
    <ol className="log-list">{[...entries].reverse().map(entry => <li className="log-entry" key={entry.number}>
      <div className="log-entry-top"><span className="log-sequence">#{String(entry.number).padStart(2, "0")}</span><span>Reparto {entry.hand} · Mano {entry.round}</span><span>{entry.player} · Equipo {entry.team}</span></div>
      <div className="log-choice"><strong>{actionName(entry.action)}</strong><span>{entry.model === "reglas" ? "Única acción legal" : `Modelo ${entry.model}`}</span></div>
      {entry.intent && entry.intent !== entry.action && <p className="log-intent">Primero eligió: {intentLabels[entry.intent] ?? entry.intent}</p>}
      <div className="log-metrics">{entry.probability !== null && <span>{entry.choiceType === "carta" ? "Carta elegida" : "Opción elegida"}: <b>{percent(entry.probability)}</b></span>}{entry.confidence !== null && <span title="Confianza reportada por Laya; no es una probabilidad de acierto">Confianza: <b>{percent(entry.confidence)}</b></span>}{entry.elapsedMs !== null && <span>Inferencia: <b>{Math.round(entry.elapsedMs)} ms</b></span>}{entry.inputTokens !== null && <span>Entrada: <b>{entry.inputTokens} tokens</b></span>}</div>
      {Object.keys(entry.alternatives).length > 0 && <div className="log-alternatives"><small>{entry.choiceType === "respuesta" ? "RESPUESTAS EVALUADAS" : "INTENCIONES EVALUADAS"}</small><div>{Object.entries(entry.alternatives).sort((a, b) => b[1] - a[1]).map(([option, probability]) => <span key={option}>{intentLabels[option] ?? option} <b>{percent(probability)}</b></span>)}</div></div>}
    </li>)}</ol>
  </section>;
}
