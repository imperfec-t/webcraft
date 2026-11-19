---
title: Animated gradient mesh background
category: Backgrounds
tags: [gradient, background, webgl, css, ambient]
stack: CSS (with an optional WebGL upgrade)
motion: subtle
description: A soft, slowly shifting gradient-mesh background for a hero or full page, built in CSS first with an optional lightweight WebGL shader, tuned to keep text readable and the GPU cool.
---
Build an ambient animated gradient-mesh background for the [HERO OR FULL PAGE] of [BRAND NAME], in a [MOOD, E.G. CALM / ELECTRIC / WARM] mood.

Stack: CSS first. Optional upgrade: a single full-screen WebGL fragment shader (no Three.js) when [USE WEBGL: YES/NO] is yes.

CSS VERSION (default)
- A fixed or absolutely positioned layer behind the content: `position: absolute; inset: 0; z-index: -1; overflow: hidden`.
- 3 to 5 large blurred blobs (divs with border-radius 50%, filter: blur(80px) to blur(120px)) in [3 TO 5 GRADIENT COLORS], each 40 to 70% of the viewport wide, opacity 0.5 to 0.8.
- Each blob drifts on its own slow loop with CSS keyframes (translate and scale only, 18 to 30s, ease-in-out, alternate), different durations so the pattern never visibly repeats.
- A subtle film-grain overlay: an inline SVG feTurbulence noise at 4 to 6% opacity on top, to prevent banding.
- Base color [BASE BACKGROUND COLOR] behind the blobs.

WEBGL VERSION (optional)
- One fragment shader: domain-warped noise mapping to the same [GRADIENT COLORS], time scaled to a very slow speed, rendered at half resolution and upscaled with CSS.
- Cap the frame rate to 30fps; pause when off-screen or the tab is hidden; fall back to the CSS version if WebGL fails.

READABILITY
- Text over the background must pass 4.5:1 at every point: add a scrim or a solid content card if any blob color is close to the text color. Test the brightest frame.
- Keep the accent of buttons distinct from the background colors.

CONTENT ON TOP (for the demo)
- Headline [HEADLINE], one line [SUPPORTING LINE], a "[CTA LABEL]" button, centered.

QUALITY BAR
- prefers-reduced-motion: freeze the blobs in a pleasing static composition (no animation, keep the gradient).
- Animate only transform (and opacity); never animate filter or background-position each frame.
- GPU-friendly: `will-change: transform` only on the blobs, no more than 5 layers, no backdrop-filter on top.
- No layout shift: the background layer is out of flow. Lighthouse performance stays above 90 on mobile.
