---
name: website-workflow
description: Plan and sequence a whole website build, from structure through design, code, WordPress and launch, by routing each stage to the right webcraft skill. Use this when someone asks to "build me a website", "design my site from scratch", "redo our homepage", wants an end-to-end plan for a marketing, agency, studio or service site, or the request spans more than one of structure, look, layout, motion, CMS and QA.
---

# Website workflow

A site built in the wrong order gets rebuilt: colors chosen before the content exists, motion added before the layout holds, QA done after the client has the link. This skill fixes the order and hands each stage to the skill that owns it.

## The sequence

| Stage | Skill | Produces | Done when |
|---|---|---|---|
| 0. Reference (optional) | `site-teardown` | Placeholder brief of a site they admire | Every section listed, no original copy left |
| 1. Structure | `homepage-blueprint` | Section table, content still needed | The person agrees with the order and the "left out" list |
| 2. Visual system | `design-tokens` (and `design-md` for a DESIGN.md or a reference direction) | `tokens.css`, `DESIGN.md` (and `theme.json` for WordPress) | Contrast results stated for body, muted and button text |
| 3. First screen | `hero-section` | Hero markup, CSS, entrance motion | Passes the hero checks at 390px |
| 4. Remaining sections | `responsive-layout` | Section layouts with no horizontal scroll | Tested at 320, 768 and 1440 |
| 5. Motion | `scroll-motion` | Reveals and at most one showpiece | Works with reduced motion and with JS off |
| 6. CMS (if any) | `wordpress-theme-build` | Theme with editable content | Client can edit every visible text and image |
| 7. Launch | `launch-qa` | Ranked report with a verdict | No blockers |

Read a stage's skill when you reach it. You do not need all of them up front.

## Rules

- **Skip what the request does not need.** A hero redesign is stages 2 (if no tokens exist), 3 and 7. Say which stages you are skipping and why.
- **Stages 1 and 2 need the person.** Ask the blueprint's four questions and the tokens' three inputs before producing either. Do not invent business facts, testimonials or numbers to fill slots; leave clearly marked placeholders and list them.
- **Tokens before components.** Every color, size, space and radius in stages 3 to 6 comes from `tokens.css`. A literal hex value in component CSS is a bug.
- **Static first, CMS second.** Finish and check the static build before stage 6. Converting a moving target doubles the work.
- **Each stage ends with its own check**, listed in its skill. Do not start the next stage on a failing one.

## Deterministic helpers

If the `webcraft` CLI or MCP server is available, use it where a measurement beats judgment:

```bash
webcraft prompts list hero                      # ready-made build prompts to adapt (stages 3 to 5)
webcraft teardown https://reference.example     # stage 0 draft
webcraft tokens "#1f6feb" --tone technical -o tokens.css   # stage 2 draft
webcraft contrast --tokens tokens.css           # stage 2 check
webcraft audit ./dist                           # stage 7, local build
webcraft audit https://staging.example --pages 10   # stage 7, deployed
```

## Hand-off summary

End a multi-stage build with: what was built (stages completed), what still needs real content from the person, the launch-qa verdict, and anything that was checked by tool only and still needs a human (real devices, form delivery).
