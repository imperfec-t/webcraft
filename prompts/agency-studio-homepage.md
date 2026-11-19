---
title: Agency studio homepage
category: Agency
tags: [studio, portfolio, smooth scroll, horizontal scroll, gsap, lenis]
stack: HTML, CSS, GSAP, ScrollTrigger, Lenis
motion: high
description: Premium creative-studio homepage with a media card that grows to full bleed, numbered sections, a horizontal work showcase and a large contact footer.
---
Build the homepage of [STUDIO NAME], a [DISCIPLINE, E.G. BRAND AND WEB DESIGN] studio in [CITY], for [IDEAL CLIENT].

Stack: HTML, CSS, GSAP 3 with ScrollTrigger, Lenis smooth scroll on desktop only. Theme: [LIGHT OR DARK]. Colors background [BACKGROUND COLOR], text [TEXT COLOR], accent [ACCENT COLOR] used sparingly. Display [DISPLAY FONT], body [BODY FONT]. Soft corners, 24px radius on media.

SECTIONS
1. Header: [STUDIO NAME] wordmark left; Work, Services, About, Contact; a "Let's talk" pill button. Hides on scroll down, shows on scroll up.
2. Hero, stacked pattern: oversized headline [HEADLINE, 2 TO 3 LINES] across the container, a small intro line [INTRO LINE] at the right of the last line, then a rounded media card [SHOWREEL VIDEO OR IMAGE] below.
3. Section label format everywhere: "(01) Work", small, uppercase, in the muted color, top-left of each section.
4. Selected work (01): a horizontal scroll showcase of [4 TO 6 PROJECTS], each a large image, project name, client and discipline tags. Desktop: pinned while the track scrolls sideways. Mobile: a normal vertical list.
5. Services (02): an accordion list of [SERVICES]; each row has a big title, opens to show a short description and 3 deliverables; hovering a row shows a small floating image following the cursor.
6. Approach (03): 3 to 4 steps [PROCESS STEPS] with a vertical line that draws as you scroll.
7. Numbers (04): [2 TO 4 REAL STATS] counting up once.
8. Testimonial: one large quote [CLIENT QUOTE, NAME, ROLE].
9. Footer CTA: huge "Let's work together" headline that links to [CONTACT EMAIL], plus office address, socials and a live local time for [CITY].

MOTION
- Hero media: scale 0.86 to 1 and border-radius 24px to 0 while scrolling from top 85% to top 15% (scrub).
- Headline lines: masked slide-up on load, 0.9s, power3.out, stagger 0.08.
- Section labels and headings: masked reveal at 85% viewport, once.
- Horizontal work: pin the section, translate the track by its overflow width, scrub 1; disable below 768px with gsap.matchMedia.
- Approach line: scaleY 0 to 1, scrubbed with the section.
- Stats: count up over 1.2s when 70% visible, once.
- One showpiece only (the horizontal work). Everything else stays simple.

QUALITY BAR
- prefers-reduced-motion: no Lenis, no pin, no scrub; everything visible and static.
- Call ScrollTrigger.refresh() after fonts and images load. Images have width and height.
- Animate only transform and opacity (radius on the hero card is the single exception).
- Keyboard: the accordion is buttons with aria-expanded; the horizontal list is reachable with Tab.
- LCP under 2.5s: the hero media's poster is preloaded; project images are lazy.
