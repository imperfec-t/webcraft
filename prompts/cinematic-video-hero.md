---
title: Cinematic video hero
category: Hero
tags: [video, full-bleed, dark, gsap]
stack: HTML, CSS, GSAP
motion: medium
description: Full-screen looping video behind a scrimmed headline that reveals line by line, with a poster-first load so the video never blocks LCP.
---
Build the first screen of a website for [BRAND NAME], [WHAT THEY DO, ONE LINE], as a full-bleed cinematic video hero.

Stack: semantic HTML, modern CSS (custom properties, clamp, svh), GSAP 3 for the entrance. No other libraries.

LAYOUT
- Section fills the viewport: `min-height: 100svh`. Video covers it with `object-fit: cover`.
- A gradient scrim sits between video and text: from rgb(0 0 0 / .62) at the bottom-left to transparent at the top-right, so text passes 4.5:1 on any frame.
- Content bottom-left inside the page container, max width about 14 words per line:
  1. Eyebrow: [EYEBROW, 2 TO 4 WORDS], uppercase, letter-spacing .14em, small.
  2. Headline: [HEADLINE, 6 TO 10 WORDS] split by hand into 2 or 3 lines of similar length. Size clamp(2.75rem, 7vw, 6.5rem), line-height 1, letter-spacing -0.03em.
  3. Supporting line: [SUPPORTING LINE, MAX 20 WORDS].
  4. One primary button "[CTA LABEL]" and a text link "[SECONDARY LINK LABEL]".
- Bottom-right: a small proof badge, [PROOF, E.G. RATING OR CLIENT COUNT]. Use only real numbers.
- A thin header over the video: logo text [BRAND NAME] left, 3 to 5 links right, transparent background turning solid after 80px of scroll.

VIDEO
- `<video autoplay muted loop playsinline preload="metadata" poster="[POSTER IMAGE]">` with WebM and MP4 sources of [VIDEO DESCRIPTION, 8 TO 12 SECONDS].
- Preload the poster as the LCP image. Keep the video under 3 MB, 1280px wide, no audio track.
- Below 768px wide, or when prefers-reduced-motion is set, show the poster image only and do not load the video.

MOTION (GSAP, total under 1.6s)
- Wrap each headline line as `<span class="line"><span>…</span></span>`; outer span clips.
- Lines: yPercent 110 to 0, duration 0.9, ease power3.out, stagger 0.08.
- Eyebrow, supporting line and buttons: y 24 to 0, opacity 0 to 1, duration 0.7, stagger 0.08, delay 0.35.
- Scroll cue at the bottom center fades in last and gently bobs (transform only).
- Set initial states in JS, not CSS, so content is visible if the script fails.

COLORS AND TYPE
- Text [TEXT COLOR ON VIDEO, USUALLY OFF-WHITE], accent [ACCENT COLOR] on the button only.
- Display font [DISPLAY FONT], body font [BODY FONT], at most two families, font-display: swap.

QUALITY BAR
- Respect prefers-reduced-motion: no video, no entrance animation, everything visible.
- Animate only transform and opacity. LCP under 2.5s on 4G with the poster preloaded.
- At 390px wide the headline, button and part of the media are visible without scrolling.
- One h1, real alt text for the poster image, keyboard-visible focus states, buttons at least 44px tall.
