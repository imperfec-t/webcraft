---
title: SaaS landing page
category: SaaS
tags: [landing page, product, pricing, faq]
stack: React or HTML, Tailwind CSS, Framer Motion or GSAP
motion: subtle
description: Complete product landing page ordered by the visitor's questions: hero with product screenshot, logos, features, how it works, pricing, testimonials, FAQ and a closing CTA.
---
Build a complete landing page for [PRODUCT NAME], a [PRODUCT CATEGORY] that helps [TARGET USER] [MAIN OUTCOME].

Stack: [REACT + TAILWIND OR PLAIN HTML/CSS]. Motion with [FRAMER MOTION OR GSAP], kept subtle. Design tokens as CSS custom properties: background [BACKGROUND COLOR], text [TEXT COLOR], one accent [ACCENT COLOR], [CORNER STYLE: SHARP, SOFT OR PILL] corners used everywhere.

SECTIONS, IN THIS ORDER (each answers the visitor's next question)
1. Header: logo [PRODUCT NAME], links (Features, Pricing, Docs, Changelog), "Sign in" text link, primary button "[CTA LABEL]". Sticky, gains a hairline border and blur after scroll.
2. Hero (am I in the right place?): headline [HEADLINE, 6 TO 10 WORDS], subline [SUBLINE, MAX 20 WORDS], primary "[CTA LABEL]" plus secondary "See how it works". Below, a large product screenshot [SCREENSHOT] in a rounded frame with a soft shadow that tilts slightly toward flat as you scroll.
3. Proof strip (can I trust this?): "Trusted by teams at" plus [5 TO 8 CUSTOMER LOGOS], greyscale, or one real metric if logos are not available.
4. Features (what exactly does it do?): 3 to 6 cards, each an icon, a 3-word title and one sentence: [FEATURE LIST].
5. How it works: 3 numbered steps with a small UI snippet each: [STEP 1], [STEP 2], [STEP 3].
6. Deep-dive: two alternating split rows (text and image swap sides) for the two most important features.
7. Pricing (what will it cost?): [PLAN NAMES AND PRICES]; monthly/annual toggle that animates the price digits; the recommended plan raised and outlined in the accent; a comparison list under each.
8. Testimonials: 3 real quotes with name, role and company: [TESTIMONIALS]. Never invent them; if none exist, omit the section.
9. FAQ: 6 to 8 real objections in an accessible accordion (button with aria-expanded): [FAQ ITEMS].
10. Closing CTA band in the accent color: one line plus the same "[CTA LABEL]" button.
11. Footer: product, company and legal columns, social links, copyright.

MOTION
- Sections fade up on first entry only (y 32 to 0, opacity 0 to 1, 0.6s, stagger 0.08 inside groups).
- Pricing toggle: numbers roll (transform) in 0.3s.
- No pinning or horizontal scroll on this page; it is a conversion page.

QUALITY BAR
- One CTA label repeated through the page. One h1.
- prefers-reduced-motion disables every animation; content never depends on JS to be visible.
- Responsive at 320, 390, 768, 1024 and 1440; no horizontal scroll; tap targets at least 44px.
- Images in WebP or AVIF with width and height; the hero screenshot preloaded, everything else lazy.
- Unique title and meta description, Open Graph image, canonical URL.
