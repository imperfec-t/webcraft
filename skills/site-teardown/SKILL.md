---
name: site-teardown
description: Analyze a live website and turn it into a section-by-section build brief that another person or AI can rebuild from, with brand name, colors, fonts and images swapped for placeholders. Use this whenever someone shares a URL and says "analyze this site", "make something like this", "give me a prompt to build this", "recreate this effect", "clone the layout with my branding", or asks how a page's animation or structure works, even if they never say "teardown".
---

# Site teardown

Turn a page someone admires into a brief precise enough to rebuild from, without copying the original's brand, copy or media.

## Why the output is a brief, not a copy

Layout patterns, section order and motion techniques are common craft and free to learn from. The original's wording, logo, photos, illustrations and code belong to its owner. So the brief describes structure and behavior, and replaces everything brand-specific with placeholders. This also makes the brief reusable: one teardown can seed many differently branded sites.

## Workflow

1. **Fetch the page.** Read the rendered text and, if you can, the HTML source, linked stylesheets and scripts. If a browser tool is available, also scroll the page and note what moves. If the `webcraft` CLI is available, `webcraft teardown URL` (MCP: `teardown_site`) drafts the section inventory, stack and placeholder brief from the markup, and `webcraft detect URL` lists libraries with versions. Use the draft as the skeleton and fill in what it marks as inferred.
2. **Say what you could not see.** A text fetch gives structure and copy but not CSS or JS. State plainly which parts of the brief are observed and which are inferred, so the reader knows where to verify. Guessing silently produces a brief that looks confident and builds wrong.
3. **Inventory the sections in order.** For each: purpose, layout (columns, grid, alignment), content slots (eyebrow, headline, body, CTA, media), and count of repeated items.
4. **Identify recurring patterns.** Section label format, button style, card style, reveal animation. Describe each once under "Global patterns" rather than repeating it per section.
5. **Detect the stack.** Look for library fingerprints in source: `gsap`, `ScrollTrigger`, `lenis`, `swiper`, `splide`, `three`, `locomotive`, `aos`, `framer-motion`, `barba`. Check `meta generator`, theme and plugin paths for the CMS.
6. **Specify motion in numbers.** Trigger, property, from and to values, duration, easing, stagger. "Fades in nicely" cannot be built; "y 40px to 0, opacity 0 to 1, 0.8s, power3.out, 0.1s stagger, on enter at 80% viewport" can.
7. **Replace brand specifics with placeholders** in square brackets: `[BRAND NAME]`, `[ACCENT]`, `[HERO IMAGE]`, `[Headline, 6 to 8 words]`. Keep the shape of the copy (line count, rough length) because that drives layout.
8. **Write the brief** using the template below.

## Brief template

```
Build [page type] as [stack]. [Theme: light/dark]. Fully responsive.
Respect prefers-reduced-motion.

BRAND
- Name, colors (background, text, accent, surface, border), fonts, image list

GLOBAL PATTERNS
- Section label format, headline reveal, button behavior, card behavior

SECTIONS (numbered, in page order)
N. NAME
   Layout: ...
   Content slots: ...
   Motion: ...

QUALITY BAR
- Performance, accessibility, breakpoints
```

## Checks before handing over

- Every section on the page appears in the brief, in order.
- No sentence of original copy, no original image URL, no brand name survives.
- Each animation has trigger, values, duration and easing.
- Observed versus inferred is stated in one line near the top.
- The brief is paste-ready: one code block, no commentary inside it.

## When the person owns the site

If they say it is their own site, you can keep their real copy and asset names in a separate "current content" appendix. Still keep the main brief placeholder-based so it works for the rebrand they asked for.
