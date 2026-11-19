---
title: Kinetic typography hero
category: Hero
tags: [typography, marquee, minimal, gsap]
stack: HTML, CSS, GSAP
motion: medium
description: Type-led hero with an oversized multi-line headline, a word that cycles, an infinite marquee strip and a cursor-aware accent shape.
---
Build a type-led hero for [BRAND NAME], [WHAT THEY DO, ONE LINE]. No photography: the typography is the design.

Stack: HTML, CSS, GSAP 3 (core only).

LAYOUT
- Height set by content, not 100vh, so the next section peeks in at the bottom.
- Headline across nearly the full container width, 3 lines of similar length:
  line 1: [HEADLINE LINE 1]
  line 2: [HEADLINE LINE 2] with one word that cycles through [3 TO 5 ROTATING WORDS]
  line 3: [HEADLINE LINE 3]
  Size clamp(3rem, 9vw, 8.5rem), line-height 0.95, letter-spacing -0.04em, weight 700 or the display weight of [DISPLAY FONT].
- The rotating word is in [ACCENT COLOR] and italic or a contrasting width, so it reads as the hook.
- Below, a two-column row: left a supporting paragraph [SUPPORTING LINE, MAX 25 WORDS]; right the primary button "[CTA LABEL]" and a small proof line [PROOF].
- Full-width marquee strip under the hero: [6 TO 10 SHORT WORDS OR SERVICES] separated by a small accent glyph, repeated twice so the loop is seamless.
- A soft blurred circle in [ACCENT COLOR] at 25% opacity drifts toward the pointer (max 40px offset). Decorative, aria-hidden.

MOTION
- Entrance: each line slides up from a clipped mask (yPercent 110 to 0, 0.9s, power3.out, stagger 0.08), then the paragraph and button fade up (y 20 to 0, 0.6s).
- Rotating word: every 2.2s the current word slides up and out while the next slides in from below (0.5s, power2.inOut). Reserve the width of the longest word so the line never reflows.
- Marquee: CSS animation translateX(0 to -50%), 30s linear infinite; it pauses on hover. Optionally speed up with scroll velocity, capped at 3x.
- Pointer shape: gsap.quickTo on x and y, duration 0.8.

COLORS AND TYPE
- Background [BACKGROUND COLOR], text [TEXT COLOR], accent [ACCENT COLOR]. Check text and button contrast at 4.5:1 or better.
- [DISPLAY FONT] for headline and marquee, [BODY FONT] for paragraph and button.

QUALITY BAR
- prefers-reduced-motion: no word rotation (show the first word), marquee static, no pointer shape, no entrance.
- Screen readers get the full headline once: put the rotating words in an aria-live="off" span and give the h1 an aria-label with the static sentence.
- Animate only transform and opacity; no layout shift when words change.
- Works at 320px: headline wraps without overflow; use `overflow-wrap: anywhere` as a last resort.
