---
title: Product launch page
category: Ecommerce
tags: [product, drop, gallery, sticky buy bar]
stack: HTML or React, CSS, GSAP
motion: medium
description: A single-product launch or drop page: hero with the product, a scroll-revealed feature walk, a swipeable gallery, specs, reviews and a sticky buy bar.
---
Build a launch page for [PRODUCT NAME], a [PRODUCT TYPE] by [BRAND NAME], priced at [PRICE], launching [LAUNCH DATE OR NOW].

Stack: [HTML/CSS OR REACT], GSAP with ScrollTrigger for the feature walk. Checkout links go to [CHECKOUT URL OR PLATFORM, E.G. SHOPIFY].

SECTIONS
1. Minimal header: brand mark, "[PRODUCT NAME]", a small "Buy - [PRICE]" button.
2. Hero: product shot [HERO PRODUCT IMAGE, TRANSPARENT PNG/WEBP] centered on [BACKGROUND COLOR], name in large display type behind or beside it, one-line promise [PROMISE LINE], "Buy now" and "Learn more". If not launched yet, a countdown to [LAUNCH DATE] and a "Notify me" email field.
3. Feature walk: [3 TO 5 FEATURES]; the product image stays in view while callouts appear around it pointing at the relevant part (lines drawn with SVG). Mobile: features as stacked cards with close-up images.
4. Colorways or variants: [VARIANTS]; swatches swap the product image with a crossfade and update the URL (?variant=).
5. Gallery: [6 TO 10 LIFESTYLE IMAGES], swipeable carousel with scroll-snap (no slider library), dots and arrow buttons.
6. Specs: a two-column table [SPECS], expandable "What's in the box".
7. Reviews: average rating and count [RATING SOURCE], 3 review cards [REVIEWS]. Real reviews only.
8. FAQ: shipping, returns, warranty [FAQ ITEMS].
9. Footer with shipping and returns policy links.
- Sticky buy bar appears after the hero leaves the viewport: thumbnail, name, selected variant, price, "Add to cart".

MOTION
- Hero: product rises 40px and fades in (1s, power3.out) while the name reveals behind it.
- Feature walk: callout lines draw (stroke-dashoffset) and labels fade in as each feature becomes active; the product rotates or zooms slightly per feature (transform only).
- Buy bar slides up (y 100% to 0, 0.3s).

COLORS AND TYPE
- Background [BACKGROUND COLOR], text [TEXT COLOR], accent [ACCENT COLOR] on buttons. Display [DISPLAY FONT], body [BODY FONT].

QUALITY BAR
- prefers-reduced-motion: no rise or rotation, lines shown drawn, buy bar appears without sliding.
- Product images in AVIF/WebP with width and height; hero image preloaded; gallery lazy.
- Price, availability and Product structured data (JSON-LD) are correct; Open Graph image is the hero shot.
- Buy buttons are real links or buttons with clear labels; the carousel is keyboard operable.
