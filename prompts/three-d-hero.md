---
title: Interactive 3D hero
category: 3D
tags: [three.js, webgl, react three fiber, pointer]
stack: Three.js (or React Three Fiber), HTML, CSS
motion: high
description: A hero with one real-time 3D object that reacts to the pointer and scroll, a lightweight loading strategy, and a static image fallback for low-power and reduced-motion users.
---
Build a hero with an interactive 3D centerpiece for [BRAND NAME], [WHAT THEY DO, ONE LINE].

Stack: [THREE.JS OR REACT THREE FIBER + DREI], HTML and CSS for all text. Text is never rendered inside WebGL.

LAYOUT
- Split hero on desktop: text left (45%), canvas right (55%). On mobile the canvas sits behind the text at 60% opacity, or is replaced by the fallback image.
- Text: eyebrow [EYEBROW], headline [HEADLINE, 6 TO 10 WORDS], supporting line [SUPPORTING LINE], button "[CTA LABEL]".
- Canvas object: [3D OBJECT, E.G. A GLASS TORUS KNOT, A PRODUCT MODEL IN GLB, AN ABSTRACT BLOB].
  - For a product: load [MODEL FILE].glb compressed with Draco or Meshopt, under 2 MB.
  - For abstract: procedural geometry with a physical material (transmission, roughness 0.15) and an HDRI environment at low resolution.
- Lighting: environment map plus one key light; soft contact shadow under the object.

INTERACTION AND MOTION
- Idle: slow rotation (0.1 rad/s) and a floating bob (y ±0.05, 4s).
- Pointer: the object tilts toward the cursor, up to 12 degrees, eased with a damping factor of 0.08 per frame.
- Scroll: as the hero leaves the viewport, the object scales 1 to 0.85 and moves up slightly (map scroll progress, no ScrollTrigger needed inside the render loop).
- Entrance: text lines reveal (masked, 0.9s, stagger 0.08) while the object fades and scales from 0.9 to 1 once its assets are ready.

PERFORMANCE
- Render the fallback image [FALLBACK IMAGE] first as the LCP element; mount the canvas after load, then crossfade.
- devicePixelRatio capped at 1.5; pause the render loop when the hero is off-screen or the tab is hidden.
- Detect low power (hardwareConcurrency 4 or less, or a failed WebGL context) and keep the static image.
- Total JS for the 3D part under 250 KB gzipped; lazy-import the 3D bundle.

COLORS AND TYPE
- Background [BACKGROUND COLOR] with a subtle radial glow in [ACCENT COLOR] behind the object; text [TEXT COLOR].
- [DISPLAY FONT] for the headline, [BODY FONT] for the rest.

QUALITY BAR
- prefers-reduced-motion: no rotation, no pointer tilt; show the static fallback or a still render.
- The canvas is aria-hidden; the image fallback has meaningful alt text.
- LCP under 2.5s, no layout shift when the canvas mounts (reserve its box).
- Works with JS disabled: text and fallback image are plain HTML.
