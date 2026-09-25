# Ihtama UI elevation - design spec

Date: 2026-09-25
Status: approved
Branch: `design/elevate-ui`

## Goal

Raise the Ihtama web app from "matches the mockup" to a visually polished
product, in a **warm and reassuring** direction. The app helps families care
for an elderly parent, so the interface should feel calm, human and
trustworthy - never clinical or cold.

Non-goal: changing any behaviour. No API, graph, guardrail, eval or routing
changes. The e2e suite must stay green throughout.

## Problems with the current UI

1. **Emoji used as an icon system.** About 50 emoji across 8 files carry real
   semantic weight (navigation, item types, status markers). They render
   differently on every platform, cannot be recoloured or sized reliably, and
   read as unfinished. They were also the source of repeated encoding
   corruption while the project was being built.
2. **Font stack is machine-dependent.** `"Avenir Next", "Nunito", system-ui`
   resolves to Avenir Next on macOS only. Linux, Windows and CI see a
   different typeface, so the app does not look the same for anyone else.
3. **Greys are cool.** The `#F3F4F6` background and `#15191E` ink sit on the
   blue side, which pulls the whole interface toward a clinical feel that
   works against the product's purpose.
4. **Flat depth.** A single shadow token and hard `1px` lines everywhere; no
   sense of layering between surfaces.
5. **Placeholder states.** Spinners instead of skeletons, a large emoji as the
   empty state, and two emoji standing in for the login hero illustration.

## Decisions

### Icons: `lucide-react`

Tree-shaken stroke icons, rounded line caps that suit the warm direction.
Standardise on a 1.75px stroke via a small local `<Icon>` wrapper so size and
colour stay consistent at call sites. Icons ship as ASCII SVG, which also
removes the non-ASCII characters that previously corrupted on write.

Rejected: a hand-authored SVG sprite. Zero dependencies and full control, but
it means drawing ~25 icons by hand with consistency resting entirely on the
author.

### Typography: one self-hosted family

Self-host a single warm sans (Figtree, fallback Nunito Sans) through
`@fontsource`, not a CDN, so the offline demo mode keeps working with no
network. Replace the current ad-hoc sizes with a deliberate scale.

### Colour: warm the neutrals, keep the brand

Brand green `#2FA36B`, coral `#F2705B` and amber `#F5B841` stay exactly as
they are. Only the neutrals move: background to a warm off-white, ink to a
warm near-black, borders to warm hairlines. This softens the interface
without touching brand identity.

### Depth and motion

Layered soft shadows replacing the single shadow token. Gentle card lift on
hover, a spring on the voice modal, skeleton placeholders instead of
spinners. Everything behind `prefers-reduced-motion`.

### Illustration

A real SVG illustration for the login hero and for empty states, replacing
the emoji placeholders.

## Process

Design in Figma first - tokens, core components, and the Home, Plan and Ask
screens at both mobile and desktop widths - so the work can be reviewed
before any React changes. Implement only what is approved.

The Figma team is on the starter tier, which limits Variables. If variables
are unavailable, fall back to shared styles and keep the token names
identical to the CSS custom properties so the two stay traceable.

## Acceptance

- No emoji remain in `apps/web/src`.
- The app renders identically on macOS, Linux and CI (self-hosted font).
- `make test` passes; the Vite production build succeeds.
- Desktop and 390x844 mobile click-through verified in a browser.
- No changes under `services/`, `evals/` or `skills/`.
