---
name: design-tokens
description: Create a website's visual system as CSS custom properties, covering color palette, typography scale, spacing, radius and shadows, with contrast checked. Use this whenever someone asks for a color scheme, a palette from one brand color, font pairing, a type scale, "make it look consistent", dark mode, a rebrand of an existing site into new colors, or starts a build with no defined styles.
---

# Design tokens

A small set of named values, used everywhere, is what makes a site look designed rather than assembled. Define tokens before components; changing a brand later then means editing one block.

## What to ask for

One brand color (or a mood word), light or dark base, and the tone (corporate, playful, editorial, technical). Everything else can be derived.

## Color

Work in roles, not color names, so a rebrand does not require renaming.

| Token | Role | Rule of thumb |
|---|---|---|
| `--bg` | Page background | Off-white or near-black, never pure `#fff` or `#000` |
| `--surface` | Cards, inputs | 2 to 4% away from `--bg` in lightness |
| `--text` | Body text | At least 7:1 on `--bg` |
| `--muted` | Secondary text | At least 4.5:1 on `--bg` |
| `--border` | Hairlines | 10 to 15% text color mixed into background |
| `--accent` | Buttons, highlights | The brand color |
| `--accent-ink` | Links and accent text on `--bg` | The brand, darkened (or lightened on dark) until it passes 4.5:1 |
| `--on-accent` | Text on accent | Whichever of white or dark passes 4.5:1 |

Guidelines:

- Tint the neutrals slightly toward the accent hue (2 to 6% saturation). Pure greys next to a warm accent look unrelated.
- Use the accent on roughly 10% of the surface. If everything is accented, nothing is.
- A second accent is rarely needed. Add one only for a distinct meaning such as success or sale.
- For dark mode, do not invert. Raise surface lightness as elevation increases and reduce accent saturation a little so it does not glow.

If the `webcraft` CLI is available, generate a starting set instead of deriving values by hand. It applies every rule above, solves lightness until each pair passes, and builds the dark theme separately:

```bash
webcraft tokens "#e4572e" --tone editorial -o tokens.css      # also: --base dark, --radius pill
webcraft tokens "#e4572e" --format theme-json                 # WordPress theme.json with the same values
```

Inside an MCP client the same thing is the `generate_tokens` tool. Treat the output as a first draft: adjust by eye, then re-check.

Check every text and background pair before finalizing:

```bash
webcraft contrast "#1b1b1f" "#f6f4ef"
webcraft contrast --tokens tokens.css
python scripts/contrast.py --tokens tokens.css   # no-install fallback, hex values only
```

The first form prints the ratio and WCAG levels for one pair. The second reads a CSS file and checks the standard role pairs in every theme block (`:root`, `[data-theme]`, `prefers-color-scheme`), resolving `var()` and reading hex, `rgb()`, `hsl()`, `oklch()` and `color-mix()`. Failing pairs are the most common accessibility defect on new sites, and they are invisible to people with good vision on a good monitor, which is why this is a script and not a judgment call.

## Typography

- Two families at most: one for headings, one for body. A single family in two weights is often better.
- Pair by contrast of structure (serif display with sans body, or condensed display with regular body), not two similar sans-serifs.
- Body size 16 to 18px, line-height 1.5 to 1.7, line length 60 to 75 characters.
- Display type: line-height 0.95 to 1.1, negative tracking that grows with size.
- Fluid scale with `clamp()` so there are no jumps between breakpoints:

```css
:root {
  --step--1: clamp(0.83rem, 0.8rem + 0.15vw, 0.9rem);
  --step-0:  clamp(1rem, 0.95rem + 0.25vw, 1.125rem);
  --step-1:  clamp(1.25rem, 1.1rem + 0.6vw, 1.6rem);
  --step-2:  clamp(1.6rem, 1.3rem + 1.3vw, 2.4rem);
  --step-3:  clamp(2rem, 1.5rem + 2.6vw, 3.6rem);
  --step-4:  clamp(2.5rem, 1.6rem + 4.6vw, 5.5rem);
  --step-5:  clamp(3rem, 1.5rem + 7vw, 7.5rem);
}
```

- Load fonts with `font-display: swap`, preload the one or two files used above the fold, and subset if self-hosting.

## Spacing, radius, shadow

```css
:root {
  --space-1: 0.25rem; --space-2: 0.5rem; --space-3: 0.75rem; --space-4: 1rem;
  --space-6: 1.5rem;  --space-8: 2rem;   --space-12: 3rem;   --space-16: 4rem;
  --section: clamp(4rem, 3rem + 6vw, 9rem);   /* vertical padding between sections */
  --gutter:  clamp(1rem, 0.5rem + 3vw, 3rem); /* page side padding */
  --container: 76rem;

  --radius-sm: 8px; --radius: 16px; --radius-lg: 28px; --radius-pill: 999px;
  --shadow: 0 1px 2px rgb(0 0 0 / .04), 0 8px 24px rgb(0 0 0 / .06);
}
```

- Pick one corner personality (sharp, soft or pill) and hold it. Mixed radii are the quickest way to look inconsistent.
- Spacing between sections should be clearly larger than spacing inside them; that gap is what tells the eye where a section ends.

## Output

Deliver one `tokens.css` with a `:root` block, an optional `[data-theme="dark"]` block, and a short table of which token is used where. Then state the contrast results for body text, muted text and button text.

## Rebranding an existing site

Map existing hard-coded values to roles first (search the CSS for hex codes and count occurrences), replace them with tokens, verify nothing changed visually, then swap the token values. Doing both at once makes regressions impossible to trace.
