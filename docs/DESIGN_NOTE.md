# Design note

**Concept: an operations log, not an "AI dashboard".** The reference is the instrument
panel and duty log of a real control room: a grid operator's desk, a flight-ops room, a
ship's bridge. Information is labelled, numbered, timestamped and ruled off. Nothing
floats, glows or blurs.

## Palette: two neutrals, one signal, one alarm

| Token | Value | Job |
|---|---|---|
| `--ink` | `#16150f` | Page: warm graphite, deliberately not blue-black |
| `--panel`, `--panel-2` | `#1f1e17`, `#29281f` | One and two steps above the page |
| `--rule` | `#3a382d` | 1 px hairlines |
| `--bone` | `#e9e5d6` | Text and healthy components |
| `--dim` | `#a29d89` | Labels, secondary text (WCAG AA on ink and panel) |
| `--signal` | `#f2a900` | Sodium amber: live state, selection, "this changed", focus, degraded |
| `--fault` | `#e5484d` | Only for "down" and for losses. Never decoration |

Amber is the caution colour of control rooms and aviation, and it sits warmly on warm
graphite. That keeps the product clear of the blue-and-purple "AI" look. Red stays
scarce so that when it appears it means something. State is never carried by colour
alone: a failed component also shows a hatch pattern and the word DOWN, and changed
sliders show their saved value.

The printable brief flips to ink on paper (`brief.css`), with amber darkened so it still
reads as a rule colour on a light background.

## Type: one condensed grotesque, one mono

- **Barlow Semi Condensed** for the interface. It descends from DIN and road signage,
  the faces real panels use. The condensed width fits dense rows, and in uppercase with
  tracking it makes the panel labels (`S-02 · SYSTEM VIEW`).
- **IBM Plex Mono** for every figure, timestamp and key. Tabular figures stop gauges from
  jittering as they tick, and it signals "the machine computed this".

## Rules we kept

- Square corners (0–2 px), hairline frames, corner ticks instead of shadows.
- Every panel has an ID and a title strip; IDs are the vocabulary used in class ("look at
  S-03").
- Numbers use Indian grouping (₹1,23,45,678) and always carry a unit.
- Every value carries its source tag: USR, ILL (illustrative), SITE, WHAT-IF.
- AI output always sits in a dashed frame labelled **AI analysis**, and flagged numbers
  are listed underneath.
- Empty, loading and error states have written copy that says what to do next.
- Icons: none. Words and the panel grid do the job.

## The 3D view

An orthographic camera at an isometric angle: it reads like a technical drawing rather
than a game. Components stand on plinths, with a column whose height is their health and
whose colour is their state. Small blocks travel along the edges, and fewer blocks means
fewer orders getting through. Deliveries return to customers along an arc so no edge
crosses a node.

The fallbacks use the same data and the same `update()` call:
- **SVG schematic:** used with `?view=2d`, when WebGL is unavailable, or if Three.js fails
  to load.
- **Reduced motion:** with `prefers-reduced-motion`, the flows stand still and nothing
  plays unless you press Play.

## What we avoided on purpose

- Gradients, glassmorphism, glow.
- Rounded card grids.
- An Inter hero, "AI sparkle" art, emoji as icons.
- Any number on screen that the engine didn't produce.
