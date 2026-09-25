/** Warm, abstract family-care scene for the login hero. Pure SVG, no emoji. */
export function HeroArt() {
  return (
    <svg className="hero-art" viewBox="0 0 320 220" fill="none" aria-hidden>
      <ellipse cx="160" cy="198" rx="118" ry="14" fill="rgba(255,255,255,0.14)" />
      <circle cx="118" cy="86" r="28" fill="rgba(255,255,255,0.22)" />
      <path d="M90 168c0-28 12-48 28-48s28 20 28 48" stroke="rgba(255,255,255,0.9)" strokeWidth="10" strokeLinecap="round" />
      <circle cx="198" cy="78" r="34" fill="rgba(255,255,255,0.28)" />
      <path d="M162 176c0-36 16-62 36-62s36 26 36 62" stroke="#fff" strokeWidth="12" strokeLinecap="round" />
      <path d="M148 128c18 10 36 10 54 0" stroke="rgba(255,232,180,0.95)" strokeWidth="6" strokeLinecap="round" />
      <circle cx="248" cy="52" r="8" fill="rgba(255,232,180,0.85)" />
      <circle cx="72" cy="58" r="5" fill="rgba(255,255,255,0.45)" />
    </svg>
  );
}

export function EmptyArt({ tone = "green" }: { tone?: "green" | "amber" }) {
  const fill = tone === "amber" ? "var(--amber-soft)" : "var(--green-soft)";
  const stroke = tone === "amber" ? "var(--amber-deep)" : "var(--green-dark)";
  return (
    <svg width="88" height="72" viewBox="0 0 88 72" fill="none" aria-hidden>
      <rect x="8" y="16" width="72" height="48" rx="14" fill={fill} />
      <path d="M22 36h44M22 46h28" stroke={stroke} strokeWidth="2.4" strokeLinecap="round" />
      <circle cx="64" cy="20" r="10" fill={stroke} opacity="0.18" />
    </svg>
  );
}
