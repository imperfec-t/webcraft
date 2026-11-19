---
name: scroll-motion
description: Add scroll-driven and entrance animation to a website with GSAP, ScrollTrigger and Lenis, including reveals, parallax, pinned sections, horizontal scroll, line drawing, counters and preloaders. Use this whenever someone wants a site to "feel premium", asks for smooth scrolling, scroll animations, parallax, text reveals, a pinned or sticky scroll section, an animated preloader, or names GSAP, ScrollTrigger, Lenis, Locomotive or AOS.
---

# Scroll motion

Motion should explain structure: what is new, what belongs together, what to look at next. Animation that does none of these is decoration and costs performance, so each effect below is tied to a purpose.

## Setup

```html
<script defer src="https://cdn.jsdelivr.net/npm/gsap@3/dist/gsap.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/gsap@3/dist/ScrollTrigger.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/lenis@1/dist/lenis.min.js"></script>
<script defer src="/js/main.js"></script>
```

`defer` keeps the scripts from blocking the first paint and still runs them in order, so `main.js` (the code below) sees `gsap`. For production, pin exact versions (`gsap@3.12.5`) or self-host the files.

```js
gsap.registerPlugin(ScrollTrigger);

const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
if (!reduce) {
  const lenis = new Lenis({ duration: 1.1, smoothWheel: true });
  lenis.on("scroll", ScrollTrigger.update);
  gsap.ticker.add((t) => lenis.raf(t * 1000));
  gsap.ticker.lagSmoothing(0);
}
```

Wrap every animation in `if (!reduce)` or use `gsap.matchMedia()`. People with vestibular disorders set that preference for a reason, and content must be fully visible without motion.

## Choosing an effect

| Purpose | Effect | Reference section |
|---|---|---|
| Announce a new section | Masked headline reveal | Reveals |
| Show items belong together | Staggered fade-up | Reveals |
| Add depth to imagery | Parallax, clip-path reveal | Images |
| Tell a sequence | Pinned steps, drawn line | Pinning |
| Show a range of work | Horizontal scroll | Pinning |
| Emphasize a number | Count-up | Details |
| Cover initial load | Preloader | Details |

Copy-ready code for each is in `references/snippets.md`. Read it when you are about to implement an effect; you do not need it to plan.

## House rules

- **Animate only `transform` and `opacity`.** Animating `top`, `width`, `margin` or `box-shadow` triggers layout or paint each frame and stutters on mid-range phones.
- **Durations:** 0.6 to 1.0s for reveals, 0.2 to 0.3s for hovers. Longer feels slow on the second visit.
- **Easing:** `power3.out` for entrances, `power2.inOut` for transitions, `none` for scrubbed animations (scrub supplies the easing).
- **Stagger:** 0.06 to 0.12s. Cap the total: with 12 cards, stagger the first 6 and bring the rest together.
- **Play once.** Use `once: true` or `toggleActions: "play none none none"`. Re-animating on every scroll-back is tiring.
- **One showpiece per page.** A pinned or horizontal section is memorable once and exhausting three times.
- **Set initial state in JS, not CSS.** If the script fails to load, CSS-hidden content stays hidden forever.
- **Refresh after layout changes:** call `ScrollTrigger.refresh()` after fonts and images load, or trigger positions drift.

```js
window.addEventListener("load", () => ScrollTrigger.refresh());
document.fonts?.ready.then(() => ScrollTrigger.refresh());
```

## Mobile

- Disable pinning and horizontal scroll below 768px with `gsap.matchMedia()`; stack the content normally.
- Lenis smooth scrolling on touch often fights native momentum. Leave touch scrolling native (the default) unless the person insists.
- Halve parallax distances on small screens.

## Debugging

- Add `markers: true` to a ScrollTrigger to see start and end lines.
- Jumping at pin start usually means the pinned element has a transform parent or changing height.
- Animation fires too early: images above it loaded late. Set explicit `width` and `height` on images.
- Nothing animates: check the plugin is registered and the selector matches.

## Without GSAP

For simple fade-ups on a small site, an IntersectionObserver adding a class plus a CSS transition is enough and saves about 70 KB. See the last section of `references/snippets.md`.
