---
name: responsive-layout
description: Build page layouts that work from phones to wide desktops using CSS grid, flexbox, container queries and fluid sizing, including card grids, bento grids, split sections, sticky sidebars and navigation that collapses. Use this whenever someone says their site "breaks on mobile", asks for a responsive grid, a bento layout, a mobile menu, fixing horizontal scroll or overflow, or is laying out any multi-column section.
---

# Responsive layout

Write the layout so it adapts on its own, then add breakpoints only where the content actually breaks. Layouts built desktop-first and patched downward are where most mobile bugs come from.

## Base

```css
*, *::before, *::after { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; }
img, video, svg { max-width: 100%; height: auto; display: block; }

.container { width: min(100% - 2 * var(--gutter, 1.25rem), var(--container, 76rem)); margin-inline: auto; }
section { padding-block: var(--section, clamp(4rem, 3rem + 6vw, 9rem)); }
```

## Patterns

### Card grid with no breakpoints

```css
.grid { display: grid; gap: clamp(1rem, 2vw, 2rem);
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr)); }
```

`min(100%, 18rem)` stops overflow when the container is narrower than the minimum. Use `auto-fill` instead if a short last row should not stretch.

### Split section (text and media)

```css
.split { display: grid; gap: clamp(2rem, 5vw, 5rem); align-items: center; }
@media (min-width: 62em) { .split { grid-template-columns: 1.1fr 0.9fr; }
  .split--flip > :first-child { order: 2; } }
```

On mobile decide deliberately which comes first; usually text, unless the image is the message.

### Bento grid

```css
.bento { display: grid; gap: 1rem; grid-template-columns: repeat(6, 1fr); grid-auto-rows: minmax(12rem, auto); }
.bento > .wide  { grid-column: span 4; }
.bento > .half  { grid-column: span 3; }
.bento > .third { grid-column: span 2; }
.bento > .tall  { grid-row: span 2; }
@media (max-width: 61.99em) { .bento { grid-template-columns: repeat(2, 1fr); }
  .bento > * { grid-column: span 1; grid-row: auto; } .bento > .wide { grid-column: span 2; } }
@media (max-width: 35.99em) { .bento { grid-template-columns: 1fr; } .bento > * { grid-column: auto; } }
```

Each row's spans must add up to the column count or gaps appear. Sketch the rows before writing classes.

### Sticky sidebar next to long content (FAQ, article)

```css
.with-aside { display: grid; gap: 3rem; }
@media (min-width: 62em) { .with-aside { grid-template-columns: 22rem 1fr; align-items: start; }
  .with-aside aside { position: sticky; top: 6rem; } }
```

`position: sticky` silently fails if any ancestor has `overflow: hidden` or `auto`. Use `overflow: clip` on ancestors instead.

### Header and mobile menu

- Desktop: logo, inline nav, CTA. Collapse to a menu button when the nav no longer fits, not at an arbitrary width.
- The menu button is a real `<button aria-expanded aria-controls>`. The panel traps focus while open, closes on Escape, and restores focus to the button.
- Lock background scroll while open (`overflow: hidden` on `html`) and account for the scrollbar width to prevent a layout jump.
- Dropdowns open on click on touch devices; hover alone is unreachable.

## Component-level responsiveness

When a card appears in both a wide grid and a narrow sidebar, use container queries so the card responds to its own width:

```css
.card-wrap { container-type: inline-size; }
@container (min-width: 28rem) { .card { display: grid; grid-template-columns: 10rem 1fr; } }
```

## Breakpoints

Use `em` so they respect user zoom. Suggested set: `36em` (576px), `48em` (768px), `62em` (992px), `75em` (1200px). Add one only when you can name what breaks without it.

## Overflow hunt

Horizontal scroll on mobile is nearly always one of these:

1. A fixed `width` in px on an element or image.
2. `100vw` on something inside a padded parent (use `100%`).
3. Long unbroken text such as URLs or emails: `overflow-wrap: anywhere`.
4. A flex child that will not shrink: add `min-width: 0`.
5. A grid track with `minmax(20rem, 1fr)` on a 320px screen: wrap the minimum in `min(100%, …)`.
6. An absolutely positioned decoration outside the viewport: clip the section with `overflow: clip`.
7. Negative margins on a full-width row.

To find the culprit, run this in the console:

```js
[...document.querySelectorAll("*")].filter(e => e.getBoundingClientRect().right > innerWidth + 1)
```

## Touch and viewport details

- Tap targets at least 44 by 44px with 8px between them.
- Use `svh`/`dvh` instead of `vh` for full-height sections so mobile browser bars do not cut content.
- Inputs at 16px font size or larger; smaller makes iOS zoom on focus.
- Respect notches: `padding-inline: max(var(--gutter), env(safe-area-inset-left))`.

## Test widths

320, 390, 768, 1024, 1440 and 1920. Also test at 200% browser zoom and with a long translated string in the navigation.
