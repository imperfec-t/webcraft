---
name: launch-qa
description: Run a pre-launch quality check on a website covering performance, accessibility, SEO basics, forms, cross-device behavior and content, and report findings ranked by severity with fixes. Use this whenever someone says a site is "ready to launch", "going live", asks "can you check my site", wants a QA pass, a website audit, a Lighthouse-style review, or wants to know why a page is slow or scoring badly.
---

# Launch QA

Find what will embarrass the owner or cost them enquiries, rank it, and say how to fix it. A list of forty equal-weight nitpicks is not useful; three blockers and a short tail is.

## How to run it

1. Establish what you can inspect: live URL, source files, or both. Say which checks you could not perform (for example, real-device testing or form delivery) instead of marking them passed.
2. If the `webcraft` CLI is available, run it first for the measurable checks (or call the `audit_site` MCP tool):

   ```bash
   webcraft audit https://example.com --pages 10     # live site: also robots, sitemap, redirects, 404, links
   webcraft audit ./dist                             # local build folder
   webcraft audit ./dist --json --fail-on blocker    # CI: exit 1 on blockers
   ```

   It produces the report template below with a "Not checked" list. Verify surprising findings before repeating them, then spend your own effort on what it cannot see: rendering, keyboard use, real devices, content accuracy.
3. Work through the areas below. Prefer measurement to opinion: run the page, read the markup, count the bytes.
4. Classify each finding:
   - **Blocker:** broken functionality, inaccessible core content, form that does not deliver, wrong or placeholder content, site not indexable when it should be.
   - **Should fix:** measurable harm to speed, accessibility or search appearance.
   - **Polish:** minor inconsistencies.
5. Report with the template at the end.

## Functionality and content

- Every link and button goes somewhere real. No `#`, no `lorem ipsum`, no template leftovers, no test email addresses.
- Forms: required validation, clear error messages, success state, spam protection, and a real test submission that arrives in the right inbox.
- Phone numbers use `tel:`, emails use `mailto:`, and they are the correct ones (check for mismatched numbers between header and footer).
- 404 page exists and links home.
- Legal pages present where needed: privacy policy, terms, cookie notice if tracking is used.
- Copyright year and business details are current and consistent.

## Performance

Targets on a mid-range phone over 4G: LCP under 2.5s, INP under 200ms, CLS under 0.1.

- Images: modern format (WebP or AVIF), sized to their display size, `width` and `height` set, `loading="lazy"` below the fold, and the LCP image preloaded and not lazy.
- Video: poster image, no autoplay with sound, compressed, not loaded on small screens if decorative.
- Fonts: at most two families, `font-display: swap`, preload the above-the-fold files.
- CSS and JS: minified, deferred where possible, no unused libraries (a slider library loaded for one static image is common).
- Third-party scripts: each one justified. Chat widgets and trackers are frequent LCP and INP offenders.
- Caching and compression enabled on the server.

## Accessibility

- One `h1`; heading levels do not skip.
- All meaningful images have `alt` text; decorative ones have empty `alt=""`.
- Text contrast at least 4.5:1 (3:1 for large text). Check text over images and muted grey text first.
- Everything works by keyboard: visible focus ring, logical order, menus and accordions operable, no focus trap.
- Form fields have associated `<label>` elements; errors are announced, not shown by color alone.
- `prefers-reduced-motion` respected; nothing flashes; autoplaying motion can be paused.
- `lang` attribute on `<html>`; page works at 200% zoom.

## SEO basics

- Unique `<title>` (50 to 60 characters) and meta description (around 150) per page.
- Canonical URL set; one version of the domain (https, with or without `www`) redirecting the others.
- `robots.txt` not blocking the site, no stray `noindex` from staging, XML sitemap present.
- Open Graph title, description and image (1200 by 630, served over https) so shared links look right.
- Structured data where it fits (Organization or LocalBusiness, FAQ, Article) and valid.
- Descriptive link text rather than "click here"; clean URLs.

## Cross-device

- Widths 320, 390, 768, 1024, 1440: no horizontal scroll, no overlapping text, tap targets at least 44px.
- Current Chrome, Safari, Firefox and Edge; iOS Safari specifically for `vh` units, sticky positioning and video autoplay.
- Animations do not hide content if JavaScript fails.

## Security and operations

- HTTPS everywhere, no mixed content.
- CMS, theme and plugins updated; unused plugins and themes removed; no default admin username.
- Backups scheduled and one restore tested.
- Analytics and search console connected, with consent handling where required.
- Favicon and touch icon present.

## Report template

```
# Launch QA: [site]   Checked: [date]   Scope: [what was and was not inspected]

Verdict: Ready / Ready after blockers / Not ready

## Blockers
1. [What is wrong] — [where] — [fix]

## Should fix
...

## Polish
...

## Not checked
- [Check] — [why, and how the owner can check it]
```

Keep each finding to one line of problem, one of location, one of fix. Lead with the verdict so the owner knows immediately where they stand.
