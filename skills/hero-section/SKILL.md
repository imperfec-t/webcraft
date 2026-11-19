---
name: hero-section
description: Design and build the hero (first screen) of a website, including headline layout, media treatment, CTA, proof badge, marquee and entrance animation. Use this whenever someone asks for a hero section, a landing page header, "the top of my homepage", a cinematic or animated intro, a video background, a text marquee, or says their first screen looks plain or generic.
---

# Hero section

The hero decides whether a visitor scrolls. It needs to say what this is, look intentional, and load fast. Most weak heroes fail on the first or third point, not the second.

## Decide the pattern first

Pick one. Mixing them is how heroes get cluttered.

| Pattern | Use when | Core structure |
|---|---|---|
| **Type-led** | Strong positioning, no great imagery | Oversized multi-line headline, small supporting line, CTA |
| **Split** | A product, person or screenshot to show | Text left, media right, 55/45 |
| **Full-bleed media** | Cinematic brand, strong video or photo | Media fills the screen, text overlaid with a scrim |
| **Stacked with media card** | Agency or studio feel | Headline on top, rounded media block below that grows on scroll |
| **Portfolio wall** | Designers, photographers | Small intro line over a grid or carousel of work |

## Content rules

- **Headline:** what you do and for whom, in 6 to 12 words. For type-led heroes, break into 2 or 3 short lines of similar length so the block reads as a shape.
- **Supporting line:** one sentence, max 20 words. It adds the detail the headline left out.
- **CTA:** a verb plus outcome ("Plan your project"), one primary button. A secondary text link is fine.
- **Proof element:** one small badge near the CTA or overlapping the media: a rating, a count, or client logos. Use real numbers only.
- **Do not** put a paragraph, a form with more than two fields, or a slider in the hero.

## Layout specifics

- Headline size: `clamp(2.5rem, 7vw, 6.5rem)`, line-height 0.95 to 1.05, letter-spacing -0.02em to -0.04em for large display type.
- Hero height: `min-height: 100svh` only for full-bleed media; otherwise let content define height so the next section peeks in.
- Media corners: 16 to 32px radius for the stacked pattern. Keep one radius across the site.
- Text over media needs a scrim: a gradient from 60% black to transparent, or 4.5:1 contrast will fail.

## Motion that helps

Entrance order: headline lines, then supporting line and CTA, then media, then decorations. Total under 1.6 seconds, because the visitor is waiting.

```js
// Line-by-line headline reveal. Wrap each line: <span class="line"><span>Text</span></span>
// .line { display:block; overflow:hidden }  .line > span { display:block }
gsap.from(".hero .line > span", {
  yPercent: 110, duration: 0.9, ease: "power3.out", stagger: 0.08
});
gsap.from(".hero [data-fade]", {
  y: 24, opacity: 0, duration: 0.7, ease: "power2.out", stagger: 0.08, delay: 0.35
});
```

Media that grows on scroll:

```js
gsap.fromTo(".hero-media", { scale: 0.86, borderRadius: 32 }, {
  scale: 1, borderRadius: 0, ease: "none",
  scrollTrigger: { trigger: ".hero-media", start: "top 85%", end: "top 15%", scrub: true }
});
```

Infinite marquee (duplicate the track's content once so the loop is seamless):

```css
.marquee { overflow: hidden; }
.marquee__track { display: flex; gap: 3rem; width: max-content; animation: marquee 28s linear infinite; }
@keyframes marquee { to { transform: translateX(-50%); } }
@media (prefers-reduced-motion: reduce) { .marquee__track { animation: none; } }
```

## Video backgrounds

- `autoplay muted loop playsinline` plus a `poster` image; without `muted` and `playsinline` mobile browsers will not autoplay.
- Keep it under 3 MB: 8 to 12 seconds, 1280px wide, no audio track, H.264 MP4 with a WebM alternative.
- Never make the video the LCP blocker: the poster should be a preloaded image.
- On small screens or `prefers-reduced-motion`, show the poster only.

## Checks

- Cover the headline: can a stranger still tell what the business does from the rest? If yes, the headline is too vague.
- First screen at 390px wide shows headline, CTA and part of the media without scrolling.
- Largest Contentful Paint under 2.5s on a throttled connection.
- With animations disabled, nothing is invisible or misplaced.
