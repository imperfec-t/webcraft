---
title: Bento features section
category: Sections
tags: [bento, grid, features, micro-interactions]
stack: HTML, CSS (grid, container queries), small vanilla JS
motion: subtle
description: An asymmetric bento grid of feature tiles, each with a tiny looping illustration or live UI snippet, collapsing cleanly to two columns and one.
---
Build a bento-grid features section for [PRODUCT OR BRAND NAME] presenting [5 TO 7 FEATURES].

Stack: HTML and CSS grid with container queries; vanilla JS only where noted. No frameworks required.

LAYOUT
- Section label "[SECTION LABEL]", headline [SECTION HEADLINE, MAX 8 WORDS], one-line intro [INTRO LINE].
- Desktop grid: 6 columns, rows minmax(13rem, auto), gap 1rem. Every row's spans must sum to 6:
  row 1: wide (span 4) + third (span 2)
  row 2: third (span 2) + third (span 2) + third (span 2)
  row 3: half (span 3) + half (span 3), or one tall tile spanning 2 rows on the right
- Tablet (below 992px): 2 columns; wide tiles span 2. Mobile (below 576px): 1 column.
- Each tile: surface [SURFACE COLOR], 1px border [BORDER COLOR], radius [RADIUS, E.G. 20PX], padding 1.5rem. Title (3 to 5 words) and one sentence at the bottom; a visual area at the top.
- Tile visuals (pick per feature from [FEATURE LIST]):
  - live UI fragment: a mini chart, toggle, notification stack or command palette, built in HTML/CSS
  - animated icon or illustration in [ACCENT COLOR]
  - one big number with a label
- Tiles respond to their own width with container queries: wide tiles put text left and visual right.

MOTION (all subtle, transform and opacity only)
- Tiles fade up on first entry, staggered 0.06s, max 6 staggered then the rest together.
- Hover on pointer devices: the tile lifts 2px and its border brightens toward the accent; a radial highlight follows the cursor inside the tile (CSS variable updated on pointermove).
- Each tile's mini visual loops gently (3 to 6s), and only animates while visible (IntersectionObserver).

COLORS AND TYPE
- Background [BACKGROUND COLOR], text [TEXT COLOR], muted [MUTED TEXT COLOR], accent [ACCENT COLOR] on about 10% of the area.
- Headline [DISPLAY FONT], body [BODY FONT].

QUALITY BAR
- prefers-reduced-motion: visuals shown in their final state, no loops, no cursor highlight.
- No gaps in the grid at any breakpoint; sketch row spans before writing classes.
- Decorative visuals aria-hidden; feature text is real HTML with heading levels in order.
- Muted text passes 4.5:1 on the tile surface, not only on the page background.
