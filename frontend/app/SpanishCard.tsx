import type { Card, Suit } from "./gameTypes";

const suitLabel: Record<Suit, string> = {
  espada: "Espadas",
  basto: "Bastos",
  oro: "Oros",
  copa: "Copas",
};

function SuitDrawing({ suit }: { suit: Suit }) {
  if (suit === "espada") {
    return <svg viewBox="0 0 64 72" aria-hidden="true"><path d="M32 4 37 43 32 49 27 43 32 4Z" fill="currentColor" opacity=".18" /><path d="M32 4 37 43 32 49 27 43 32 4ZM32 12v29M16 48q16 10 32 0M23 46l-5 7M41 46l5 7M32 50v13M26 63h12M32 63v5" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" /></svg>;
  }
  if (suit === "basto") {
    return <svg viewBox="0 0 64 72" aria-hidden="true"><path d="M29 8q7-7 13 0l-7 49q-2 9-10 8l4-57Z" fill="currentColor" opacity=".2" /><path d="M29 8q7-7 13 0l-7 49q-2 9-10 8l4-57ZM27 18l13 4M25 34l13 4M23 49l13 4M25 64q6 3 10-2" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" /><path d="M27 12q-5-7-10-2m24 1q5-7 8-2" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" /></svg>;
  }
  if (suit === "oro") {
    return <svg viewBox="0 0 64 72" aria-hidden="true"><circle cx="32" cy="36" r="25" fill="currentColor" opacity=".13" /><circle cx="32" cy="36" r="25" fill="none" stroke="currentColor" strokeWidth="2.6" /><circle cx="32" cy="36" r="19" fill="none" stroke="currentColor" strokeWidth="1.6" /><path d="m32 21 4 9 10 2-7 7 2 10-9-5-9 5 2-10-7-7 10-2 4-9Z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" /></svg>;
  }
  return <svg viewBox="0 0 64 72" aria-hidden="true"><path d="M12 13h40l-5 24q-2 13-15 16-13-3-15-16l-5-24Z" fill="currentColor" opacity=".17" /><path d="M12 13h40l-5 24q-2 13-15 16-13-3-15-16l-5-24ZM18 22h28M32 53v10M21 65h22M32 65v3M13 18q-6 0-5 9 0 11 10 13M51 18q6 0 5 9 0 11-10 13" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

function Face({ card }: { card: Card }) {
  return <>
    <span className="face-corner"><strong>{card.rank}</strong><span>{suitLabel[card.suit]}</span></span>
    <span className="face-art"><SuitDrawing suit={card.suit} /></span>
    <span className="face-footer">{suitLabel[card.suit]}</span>
  </>;
}

export function SpanishCard({ card, onPlay, disabled = false, compact = false }: { card: Card; onPlay?: () => void; disabled?: boolean; compact?: boolean }) {
  const className = `spanish-card suit-${card.suit}${compact ? " compact" : ""}${onPlay ? " playable" : ""}`;
  const label = `${card.rank} de ${suitLabel[card.suit].toLowerCase()}`;
  if (onPlay) {
    return <button type="button" className={className} onClick={onPlay} disabled={disabled} aria-label={`Jugar ${label}`}><Face card={card} /></button>;
  }
  return <div className={className} role="img" aria-label={label}><Face card={card} /></div>;
}

export function CardBack({ style }: { style?: React.CSSProperties }) {
  return <span className="card-back" style={style} role="img" aria-label="Carta boca abajo"><span className="back-inner"><span className="back-crest">T</span></span></span>;
}
