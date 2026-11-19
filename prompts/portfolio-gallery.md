---
title: Designer portfolio gallery
category: Portfolio
tags: [portfolio, gallery, hover preview, page transition]
stack: HTML, CSS, GSAP (optional Barba.js for transitions)
motion: medium
description: Minimal personal portfolio where the work leads: an intro line over a filterable project grid, hover-reveal previews and smooth project-page transitions.
---
Build a personal portfolio for [YOUR NAME], a [ROLE, E.G. PRODUCT DESIGNER] based in [CITY]. The work is the hero; the chrome is quiet.

Stack: HTML, CSS, GSAP 3. Optional Barba.js for page transitions between the index and project pages.

LAYOUT
- Header: [YOUR NAME] left; Work, About, Contact right; availability dot with "[AVAILABILITY, E.G. AVAILABLE FROM MARCH]".
- Intro: one sentence of about 15 words, [INTRO SENTENCE], at clamp(1.75rem, 3.5vw, 3rem), max 22ch per line. Nothing else above the fold except the start of the grid.
- Filter chips: All, [CATEGORY 1], [CATEGORY 2], [CATEGORY 3]. Filtering animates the grid with FLIP (positions, not layout jumps).
- Project grid: 2 columns on desktop, 1 on mobile, mixed aspect ratios (4:5 and 16:10) for rhythm. Each card: image or muted looping video [PROJECT MEDIA], title, client, year.
- Hover (pointer devices only): image scales 1 to 1.04 inside its frame, title slides 8px right, and a small "View" pill follows the cursor.
- Project page: full-width cover, a facts row (Client, Role, Year, Deliverables), then alternating full-bleed images and short text blocks, then "Next project" with a large image link.
- About: portrait [PORTRAIT IMAGE], a 120-word bio [BIO], a list of clients and a CV link.

MOTION
- Grid items fade and rise once as they enter (y 40 to 0, opacity, 0.8s, power3.out, batch stagger 0.1).
- Index to project transition: the clicked card's image expands to the cover position (FLIP), other content fades out in 0.3s.
- Next-project link: the image scales from 0.9 to 1 with scroll (scrub).

COLORS AND TYPE
- Neutral background [BACKGROUND COLOR] with text [TEXT COLOR]; a single accent [ACCENT COLOR] for links and the availability dot.
- One family in two weights ([FONT FAMILY]), or a serif display with a sans body.

QUALITY BAR
- prefers-reduced-motion: instant filtering, no transitions, no cursor pill.
- Every project image has descriptive alt text, width and height, WebP or AVIF, lazy below the fold.
- Cards are real links with visible focus states; hover-only details are also visible on focus.
- Videos are muted, playsinline, loop, with a poster, and pause when off-screen.
