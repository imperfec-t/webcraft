# Contributing

Thanks for helping. The project has three parts, and each has a small contract.

## Ground rules

- **Standard library only** in `src/webcraft`. The tool must install anywhere Python 3.9+ runs, with nothing else. Optional extras (like `truststore`) must degrade gracefully when absent.
- **Measurement over opinion.** A check belongs in `audit` only if it can be decided from markup, CSS, JS or HTTP responses with few false positives. Anything that needs a browser, a device or a human goes in the "Not checked" list instead.
- **Briefs, not copies.** `teardown` must never output original copy, image URLs, brand names or raw class names. There is a test for this; extend it when you add output.

## Adding or changing a skill

1. Create `skills/<name>/SKILL.md` with frontmatter `name` (kebab-case, matching the folder) and `description` (what it does and when to use it, under 1024 characters, no angle brackets).
2. Keep the body under 500 lines. Move long code or tables to `references/` and mention them in backticks (e.g. `references/snippets.md`) so the validator checks they exist.
3. If a rule in the skill can be measured, reference the CLI command and keep a manual fallback for agents without webcraft.
4. Add the skill to the tables in `README.md` and, if it is a build stage, to `skills/website-workflow/SKILL.md`.
5. Run `webcraft validate`.

## Adding a prompt

1. Create `prompts/<kebab-name>.md` with frontmatter: `title`, `category`, `tags` (a list), `stack`, `motion` (`none`, `subtle`, `medium` or `high`) and `description`.
2. Write the body as a complete instruction to an AI builder: stack, layout per section, motion with numbers (property, from and to values, duration, easing, trigger), colors and type, and a QUALITY BAR. Animated prompts must require prefers-reduced-motion support.
3. Put everything the user must supply in `[UPPERCASE PLACEHOLDERS]`. Never put real brand names, testimonials or statistics in a prompt.
4. Only contribute prompts you wrote yourself. Prompts from paid libraries or sites whose terms forbid redistribution cannot be accepted.
5. Run `python -m unittest tests.test_prompts`.

## Adding an audit check

1. Add it to the right `check_*` function in `src/webcraft/audit.py` (or a new one registered in `PAGE_CHECKS`).
2. Give it a stable `id`, a severity from the launch-qa skill (`blocker` breaks something or blocks indexing; `should-fix` measurably hurts speed, accessibility or search; `polish` is minor), and one line each of problem, location and fix.
3. Plant the problem in `examples/sample-site` and assert the id in `tests/test_audit_teardown.py`. Make sure the clean page in the same test file still passes.

## Adding an agent target

Add a `Target` to `TARGETS` in `src/webcraft/agents.py`:

- `kind="skills"` if the agent reads Agent Skills folders natively. Give `user` and `project` paths.
- A new kind with a converter (see `_rule_file`) if it uses its own rule format.
- Otherwise point people at `agents-md` with `--file`.

Cite the agent's documentation in the pull request, since these paths change. Add the agent to the support table in `README.md`, and an `mcp_config` snippet if it supports MCP.

## Tests

```bash
python -m unittest discover -s tests
```

CI runs this on Linux, macOS and Windows for Python 3.9 and 3.13.
