# Working on webcraft

Instructions for coding agents contributing to this repository.

- `src/webcraft/` is the CLI and MCP server. **Standard library only**; do not add dependencies.
- `skills/` holds the skills in Agent Skills format. Run `python -m webcraft validate` after editing any `SKILL.md`.
- `examples/sample-site/` is intentionally broken. Do not fix it; tests depend on every planted problem.
- Run the tests with `PYTHONPATH=src python -m unittest discover -s tests` (PowerShell: `$env:PYTHONPATH="src"; python -m unittest discover -s tests`).
- `teardown` output must never contain original copy, image URLs, brand names or class names.
- New audit checks need an id, a launch-qa severity, a planted case in the sample site and a test. See CONTRIBUTING.md.
- Agent install paths live in `TARGETS` in `src/webcraft/agents.py`. Change them only with a link to the agent's docs.
