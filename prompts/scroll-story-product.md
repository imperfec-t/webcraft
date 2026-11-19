---
title: Scroll-driven product story
category: Interactive
tags: [pinned, scrollytelling, product, gsap, scrolltrigger]
stack: HTML, CSS, GSAP, ScrollTrigger
motion: high
description: A pinned product reveal where one device or object stays centered while feature steps scroll past, swapping the screen content and highlighting the active step.
---
Build a scroll-driven product story section for [PRODUCT NAME], showing [NUMBER, 3 TO 5] key features of [WHAT THE PRODUCT IS].

Stack: HTML, CSS, GSAP 3 with ScrollTrigger.

LAYOUT (desktop, 1024px and up)
- Section height: one viewport per step. The visual column is pinned while the text column scrolls.
- Left (55%): a centered device frame or object [DEVICE OR OBJECT, E.G. PHONE MOCKUP] holding stacked screens [SCREEN IMAGE PER STEP].
- Right (45%): one block per step, vertically centered in its viewport: step number "01", title [STEP TITLE], 2-sentence description [STEP DESCRIPTION], optional small metric.
- A vertical progress rail between the columns with a dot per step; the active dot fills with [ACCENT COLOR].
- Before the section: a headline [SECTION HEADLINE] and one line [SECTION INTRO]. After it: a CTA row with "[CTA LABEL]".

MOBILE (below 1024px)
- No pinning. Each step is a stacked card: screen image, then number, title and description.

MOTION
- Pin the visual column from "top top" to "bottom bottom" of the section.
- For each step, a ScrollTrigger on its text block (start "top center", end "bottom center"):
  - onEnter and onEnterBack: crossfade to that step's screen (opacity 0.4s) with a subtle scale 1.02 to 1.
  - Active text block: opacity 1; others 0.35.
  - Progress rail: scaleY tied to overall section progress (scrub 0.5).
- The device floats gently (y ±6px, 3s sine yoyo), paused when off-screen.
- Optional: rotate the device 8 degrees on the last step to reveal its side.

COLORS AND TYPE
- Background [BACKGROUND COLOR] (darker backgrounds make screens pop), text [TEXT COLOR], accent [ACCENT COLOR].
- Step numbers in a monospace or tabular-figure font.

QUALITY BAR
- prefers-reduced-motion: no pin; render the mobile stacked layout at every width.
- Build with gsap.matchMedia so desktop pinning and the mobile layout are separate and clean up on resize.
- Screens are preloaded only for the first step; the rest lazy-load as the section approaches.
- Text stays real HTML (not baked into images) and readable at 4.5:1 when inactive at 0.35 opacity; raise to 0.55 if not.
- ScrollTrigger.refresh() after images load; fixed width and height on the device frame to avoid jumps.
