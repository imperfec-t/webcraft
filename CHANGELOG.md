# Changelog

## 0.1.0

- Ten website-design skills in Agent Skills format, including the new `website-workflow` and `design-md`.
- `webcraft` CLI: `install` / `uninstall` / `status` for Claude Code, Codex, Gemini CLI, Copilot, `.agents`, Cursor, Windsurf and AGENTS.md; `tokens`, `contrast`, `audit`, `detect`, `teardown`, `validate`, `list`, `show`.
- `webcraft ui`: local web interface for tokens (live preview), contrast, audit, detect, teardown, skills, install and MCP setup. It binds to localhost, checks the Host header, requires a per-launch API secret and serves a nonce-based CSP.
- Stdio MCP server with seven tools, one prompt per skill, and every skill file as a resource.
- DESIGN.md support: `webcraft design sync|list|show|check|tokens|use|status`, `webcraft tokens --format design-md`, a frontmatter and prose parser, role mapping, component contrast checks, and the VoltAgent/awesome-design-md reference library (MIT, downloaded on request). Adds a Design library page in the UI, MCP tools `list_designs` and `get_design`, and the `design-md` skill.
- Prompt library: 13 original MIT website prompts in `prompts/`, plus a private personal library stored only in the user-data folder. Adds `webcraft prompts list|show|add|remove|where` with placeholder filling, a Prompts page in the UI, and the MCP tools `list_prompts` and `get_prompt`.
- UI redesign:
  - Overview home page with illustrated diagrams (architecture, project timeline, agent walkthrough), live status and data locations.
  - Grouped navigation, a Ctrl/Cmd+K command palette, `/` to focus search, and a mobile drawer.
  - "How this works" panels on every tool page, skeleton loaders, illustrated empty states, and focus management on navigation.
  - README screenshots and a theme-aware architecture diagram in `docs/images/`.
- Claude Code plugin and marketplace manifests; Gemini CLI extension manifest.
