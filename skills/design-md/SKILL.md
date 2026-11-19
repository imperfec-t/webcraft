---
name: design-md
description: Use, write or adapt a DESIGN.md, the plain-markdown design-system file that coding and design agents read to keep UI visually consistent, including picking a visual direction from a library of DESIGN.md files analyzing real sites. Use this whenever a project has or needs a DESIGN.md, someone says "make it look like Linear / Stripe / Vercel", wants a design direction or mood for a site, asks for a design system file for their agent, or mentions Google Stitch or awesome-design-md.
---

# DESIGN.md

`AGENTS.md` tells an agent how to build a project; `DESIGN.md` tells it how the project should look. It is markdown with optional YAML frontmatter (`colors`, `typography`, `rounded`, `spacing`, `components`) followed by prose sections: Overview, Colors, Typography, Layout, Elevation & Depth, Shapes, Components, Do's and Don'ts. When a project has one, read it before writing any UI and follow it over your own taste.

## Three ways in

| Situation | Do this |
|---|---|
| Project already has a DESIGN.md | Read it fully. Use its tokens for every color, size, radius and space. Check it first (below). |
| Person has a brand color but no system | Generate one: `webcraft tokens "#hex" --tone editorial --format design-md -o DESIGN.md` (plus `-o tokens.css` without `--format`). Every pair is contrast-checked. |
| Person wants "a look like X" | Browse the reference library, pick a direction with them, then adapt it as below. |

## Using the reference library

`webcraft design list` searches about 84 DESIGN.md files from VoltAgent/awesome-design-md (MIT), each analyzing a real site's visual language. `dark`/`light` filter by theme; other words match descriptions (`webcraft design list dark developer`). In MCP clients use `list_designs` and `get_design`. The library downloads on first use.

These files describe **other companies' brands**. They are references for a visual direction, not assets to ship:

- Never use the company's name, logo, wordmark, product imagery, illustrations or marketing copy. Replace them with the person's own, or placeholders.
- Fonts named in these files are often proprietary (custom brand faces, Sohne, SF Pro, Circular). Suggest an open alternative with similar structure unless the person holds a license.
- Do not reproduce a brand closely enough to be mistaken for it. Take the principles (density, contrast strategy, accent discipline, corner personality, type rhythm) and apply them to the person's brand color and content.

`webcraft design use NAME --tokens` copies the file into the project with a reference notice and writes a `tokens.css` mapped onto webcraft roles. Then edit DESIGN.md: rename it, swap the accent for the person's brand color, replace fonts, delete brand-specific sections.

## Check before you trust it

Reference designs often ship low-contrast secondary text. Always run:

```bash
webcraft design check DESIGN.md        # or a library name
```

It maps the palette onto roles (`--bg`, `--text`, `--muted`, `--accent`...) and checks every component's declared background and text pair against WCAG AA, skipping disabled states, which WCAG exempts. Fix failures in the file itself (usually darken muted text a step), not in individual components. For prose-only files the role mapping is inferred from the palette descriptions; the output shows which color each role came from, so verify it.

## Writing or editing one

- Keep frontmatter values literal (`"#1d4ed8"`, `16px`) and reference them in components as `{colors.primary}`, `{typography.button}`, `{rounded.md}`.
- Name colors by role (`canvas`, `surface-1`, `ink`, `ink-muted`, `hairline`, `primary`, `on-primary`), not by hue, so a rebrand changes values, not names.
- Every component with a `backgroundColor` should state its `textColor`; that is what makes it checkable.
- The prose matters as much as the tokens: say where the accent may and may not appear, what the type rhythm is, and the don'ts. Agents follow explicit prohibitions well.
- Keep `tokens.css` and DESIGN.md in sync. Regenerate one from the other rather than editing both by hand: `webcraft design tokens DESIGN.md -o tokens.css`.

## Hand-off

State which direction was chosen and why, what was changed from the reference (name, accent, fonts), the `design check` result, and anything still borrowed that the person must replace before launch.
