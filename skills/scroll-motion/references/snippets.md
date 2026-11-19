# Scroll motion snippets

All snippets assume GSAP and ScrollTrigger are registered and should run inside a reduced-motion guard.

Contents: Reveals · Images · Pinning · Details · No-library fallback

## Reveals

### Masked headline reveal

Markup: each line wrapped twice so the outer span clips the inner one.

```html
<h2 class="reveal-lines">
  <span class="line"><span>First line</span></span>
  <span class="line"><span>Second line</span></span>
</h2>
```

```css
.line { display: block; overflow: hidden; }
.line > span { display: block; }
```

```js
gsap.utils.toArray(".reveal-lines").forEach((el) => {
  gsap.from(el.querySelectorAll(".line > span"), {
    yPercent: 110, duration: 0.9, ease: "power3.out", stagger: 0.08,
    scrollTrigger: { trigger: el, start: "top 85%", once: true }
  });
});
```

Lines must be split by hand or by a script that re-splits on resize; splitting by fixed `<br>` breaks on narrow screens.

### Staggered fade-up for groups

```js
ScrollTrigger.batch("[data-fade]", {
  start: "top 88%", once: true,
  onEnter: (els) => gsap.from(els, {
    y: 40, opacity: 0, duration: 0.8, ease: "power3.out", stagger: 0.1
  })
});
```

`batch` groups elements entering together, so a row of cards staggers while a lone paragraph does not wait.

## Images

### Clip-path reveal

```js
gsap.utils.toArray("[data-clip]").forEach((el) => {
  gsap.fromTo(el,
    { clipPath: "inset(0 0 100% 0)" },
    { clipPath: "inset(0 0 0% 0)", duration: 1.1, ease: "power3.inOut",
      scrollTrigger: { trigger: el, start: "top 80%", once: true } });
});
```

### Parallax inside a frame

The wrapper clips; the image is taller than the wrapper and slides.

```css
.parallax { overflow: hidden; }
.parallax img { height: 120%; width: 100%; object-fit: cover; }
```

```js
gsap.utils.toArray(".parallax img").forEach((img) => {
  gsap.fromTo(img, { yPercent: -16 }, {
    yPercent: 0, ease: "none",
    scrollTrigger: { trigger: img.parentElement, start: "top bottom", end: "bottom top", scrub: true }
  });
});
```

### Floating decorative shapes

```js
gsap.utils.toArray("[data-drift]").forEach((el) => {
  const d = parseFloat(el.dataset.drift) || 60;
  gsap.to(el, { y: -d, ease: "none",
    scrollTrigger: { trigger: el.closest("section"), start: "top bottom", end: "bottom top", scrub: 0.6 } });
});
```

## Pinning

### Pinned step sequence

```js
const mm = gsap.matchMedia();
mm.add("(min-width: 768px)", () => {
  const steps = gsap.utils.toArray(".step");
  const tl = gsap.timeline({
    scrollTrigger: { trigger: ".steps", start: "top top", end: "+=" + steps.length * 600, pin: true, scrub: 0.5 }
  });
  steps.forEach((s, i) => {
    if (i) tl.from(s, { opacity: 0, y: 60, duration: 1 });
    if (i < steps.length - 1) tl.to(s, { opacity: 0.25, duration: 0.5 }, "+=0.5");
  });
});
```

### Horizontal scroll section

```js
mm.add("(min-width: 768px)", () => {
  const track = document.querySelector(".h-track");
  gsap.to(track, {
    x: () => -(track.scrollWidth - innerWidth), ease: "none",
    scrollTrigger: { trigger: ".h-section", start: "top top",
      end: () => "+=" + (track.scrollWidth - innerWidth), pin: true, scrub: 0.6, invalidateOnRefresh: true }
  });
});
```

### Line that draws between steps

```css
.process-line { transform-origin: left center; transform: scaleX(0); height: 1px; background: currentColor; }
```

```js
gsap.to(".process-line", { scaleX: 1, ease: "none",
  scrollTrigger: { trigger: ".process", start: "top 70%", end: "bottom 60%", scrub: true } });
```

For an SVG path, set `stroke-dasharray` and `stroke-dashoffset` to the path length and animate the offset to 0.

## Details

### Count-up number

```js
gsap.utils.toArray("[data-count]").forEach((el) => {
  const end = parseFloat(el.dataset.count);
  const decimals = (el.dataset.count.split(".")[1] || "").length;
  const o = { v: 0 };
  gsap.to(o, { v: end, duration: 1.4, ease: "power2.out",
    onUpdate: () => (el.textContent = o.v.toFixed(decimals)),
    scrollTrigger: { trigger: el, start: "top 90%", once: true } });
});
```

Put the final value in the HTML so it is correct without JS.

### Preloader

```js
const tl = gsap.timeline({ onComplete: () => document.querySelector(".preloader").remove() });
tl.from(".preloader .char", { yPercent: 100, stagger: 0.04, duration: 0.6, ease: "power3.out" })
  .to(".preloader", { yPercent: -100, duration: 0.8, ease: "power3.inOut" }, "+=0.3")
  .add(() => document.body.classList.add("is-ready"));
```

Keep it under 1.5 seconds and never block on it: if the page is already interactive, skip straight to the exit. Do not show it on repeat visits in the same session (`sessionStorage`).

### Sticky header that hides on scroll down

```js
ScrollTrigger.create({
  start: 80, end: "max",
  onUpdate: (self) => document.querySelector(".header")
    .classList.toggle("is-hidden", self.direction === 1 && self.scroll() > 400),
  onToggle: (self) => document.querySelector(".header").classList.toggle("is-solid", self.isActive)
});
```

### Marquee that speeds up while scrolling

The track holds its content twice, so moving it by -50% loops seamlessly.

```js
const loop = gsap.to(".marquee__track", { xPercent: -50, repeat: -1, duration: 28, ease: "none" });
let settle;
ScrollTrigger.create({
  onUpdate: (self) => {
    const boost = 1 + Math.min(Math.abs(self.getVelocity()) / 800, 3);
    gsap.to(loop, { timeScale: boost, duration: 0.2, overwrite: true });
    clearTimeout(settle);
    settle = setTimeout(() => gsap.to(loop, { timeScale: 1, duration: 0.6, overwrite: true }), 150);
  }
});
```

## No-library fallback

```css
[data-io] { opacity: 0; transform: translateY(32px); transition: opacity .7s ease, transform .7s cubic-bezier(.2,.7,.2,1); }
[data-io].in { opacity: 1; transform: none; }
@media (prefers-reduced-motion: reduce) { [data-io] { opacity: 1; transform: none; transition: none; } }
.no-js [data-io] { opacity: 1; transform: none; }
```

```js
const io = new IntersectionObserver((entries) => {
  entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
}, { rootMargin: "0px 0px -12% 0px" });
document.querySelectorAll("[data-io]").forEach((el) => io.observe(el));
```
