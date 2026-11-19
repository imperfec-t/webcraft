"""webcraft command line."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__

EPILOG = """examples:
  webcraft ui                             open the web interface
  webcraft install claude                 skills -> ~/.claude/skills
  webcraft install codex --scope project  skills -> ./.agents/skills
  webcraft install cursor                 rules  -> ./.cursor/rules
  webcraft tokens "#e4572e" --tone editorial -o tokens.css
  webcraft contrast "#6b6b6b" "#ffffff"
  webcraft audit https://example.com --pages 5
  webcraft teardown https://example.com > brief.md
  webcraft prompts list hero               browse website prompts
  webcraft prompts show cinematic-video-hero --set "BRAND NAME=Northwind"
  webcraft design list dark                browse the DESIGN.md reference library
  webcraft design check linear.app        contrast-check a DESIGN.md
  webcraft tokens "#e4572e" --format design-md -o DESIGN.md
  webcraft mcp-config codex
"""


def _out(text: str, path: str = None) -> None:
    if path:
        Path(path).write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
        print(f"wrote {path}", file=sys.stderr)
    else:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")


def cmd_list(a):
    from . import skills
    items = skills.load_all()
    if a.json:
        _out(json.dumps([{"name": s.name, "description": s.description, "files": s.files()} for s in items], indent=2))
        return 0
    width = max(len(s.name) for s in items)
    for s in items:
        desc = s.description.split(". Use this")[0]
        print(f"{s.name:<{width}}  {desc}")
    return 0


def cmd_show(a):
    from . import skills
    s = skills.get(a.name)
    _out(s.read_file(a.file) if a.file else s.text)
    return 0


def cmd_install(a):
    from . import agents
    agents_list = list(agents.TARGETS) if a.agent == "all" else [x.strip() for x in a.agent.split(",")]
    only = [x.strip() for x in a.only.split(",")] if a.only else None
    for ag in agents_list:
        if ag == "agents" and a.agent == "all":
            continue
        print(f"[{ag}] {agents.TARGETS[ag].label}" if ag in agents.TARGETS else f"[{ag}]")
        for line in agents.install(ag, scope=a.scope, project_dir=a.project, dest=a.dest, only=only,
                                   force=a.force, dry_run=a.dry_run, index_file=a.file):
            print("  " + line)
    if not a.dry_run:
        print("\nRestart the agent (or start a new session) so it picks up the skills.")
        print("For the deterministic tools inside the agent, also add the MCP server: webcraft mcp-config <client>")
    return 0


def cmd_uninstall(a):
    from . import agents
    for line in agents.uninstall(a.agent, scope=a.scope, project_dir=a.project, dest=a.dest,
                                 dry_run=a.dry_run, index_file=a.file):
        print(line)
    return 0


def cmd_status(a):
    from . import agents
    rows = agents.status(a.project)
    if a.json:
        _out(json.dumps(rows, indent=2))
        return 0
    for r in rows:
        mark = f"{r['installed']}/{r['of']}" if r["installed"] else "-"
        print(f"{r['agent']:<10} {r['scope']:<8} {mark:<6} {r['path']}")
    return 0


def cmd_validate(a):
    from . import skills
    root = Path(a.path) if a.path else None
    results = skills.validate(root)
    failed = 0
    for name, errors in results.items():
        if errors:
            failed += 1
            print(f"FAIL  {name}")
            for e in errors:
                print(f"      - {e}")
        else:
            print(f"ok    {name}")
    print(f"\n{len(results) - failed} of {len(results)} skills valid")
    return 1 if failed else 0


def cmd_tokens(a):
    from . import tokens
    t = tokens.generate(a.brand, base=a.base, tone=a.tone, radius=a.radius)
    if a.format == "css":
        body = tokens.render_css(t, auto_dark=not a.no_auto_dark, base_styles=a.base_styles)
    elif a.format == "theme-json":
        body = tokens.render_theme_json(t)
    elif a.format == "dtcg":
        body = tokens.render_dtcg(t)
    elif a.format == "design-md":
        from . import designmd
        body = designmd.from_tokens(t, a.name)
    else:
        body = json.dumps(t, indent=2)
    _out(body, a.output)
    if a.format != "json":
        print(tokens.render_report(t), file=sys.stderr if not a.output else sys.stdout)
    fails = [r for rs in t["contrast"].values() for r in rs if r["status"] == "fail"]
    return 1 if fails else 0


def cmd_contrast(a):
    from . import color, css
    if a.tokens:
        text = Path(a.tokens).read_text(encoding="utf-8")
        res = css.check_tokens_css(text)
        if not any(res.values()):
            print("No role pairs found. Expected custom properties such as --text and --bg on :root.")
            return 2
        bad = 0
        if a.json:
            _out(json.dumps(res, indent=2))
        for label, rows in res.items():
            if not a.json:
                print(label)
            for r in rows:
                bad += r["status"] == "fail"
                if not a.json:
                    mark = {"pass": "pass", "warn": "below guideline", "fail": "FAIL"}.get(r["status"], r["status"])
                    ratio = f"{r['ratio']:5.2f}:1" if r["ratio"] is not None else "   ?  "
                    print(f"  {r['pair']:<24} {r['fg']} on {r['bg']}  {ratio}  {mark} (min {r['minimum']})")
        return 1 if bad else 0
    if not (a.foreground and a.background):
        print("usage: webcraft contrast FOREGROUND BACKGROUND   or   webcraft contrast --tokens tokens.css", file=sys.stderr)
        return 2
    r = color.contrast(a.foreground, a.background)
    lv = color.levels(r)
    if a.json:
        _out(json.dumps({"ratio": round(r, 2), "levels": lv}))
    else:
        print(f"{a.foreground} on {a.background}  {r:.2f}:1")
        for k, ok in lv.items():
            print(f"  {'pass' if ok else 'FAIL'}  {k}")
    return 0 if r >= 4.5 else 1


def cmd_audit(a):
    from . import audit
    rep = audit.audit(a.target, max_pages=a.pages, remote_checks=not a.offline)
    _out(json.dumps(rep.to_dict(), indent=2) if a.json else audit.render(rep), a.output)
    order = {"blocker": 0, "should-fix": 1, "polish": 2}
    if a.fail_on == "never":
        return 0
    limit = order[a.fail_on]
    return 1 if any(order[f.severity] <= limit for f in rep.findings) else 0


def cmd_detect(a):
    from . import detect, source
    res = detect.detect(source.load(a.target))
    _out(json.dumps(res, indent=2) if a.json else detect.render(res))
    return 0


def cmd_teardown(a):
    from . import teardown
    res = teardown.teardown(a.target)
    _out(json.dumps(res, indent=2) if a.json else teardown.render(res), a.output)
    return 0


def cmd_mcp(a):
    from . import mcp
    mcp.main()
    return 0


def cmd_design(a):
    from . import designmd as dm
    act = a.action
    if act == "sync":
        print(f"Downloading {dm.LIBRARY_URL} ..." if not a.source else f"Importing {a.source} ...", file=sys.stderr)
        meta = dm.sync(a.source)
        print(f"{meta['count']} DESIGN.md files -> {dm.cache_dir()}  (MIT, VoltAgent; commit {meta['commit'][:10] or '?'})")
        return 0
    if act == "status":
        _out(json.dumps(dm.library_status(), indent=2))
        return 0
    if act == "list":
        try:
            items = dm.search(" ".join(a.args))
        except dm.LibraryMissing:
            print("Library not downloaded yet; fetching it now (about 1 MB).", file=sys.stderr)
            dm.sync()
            items = dm.search(" ".join(a.args))
        if a.json:
            _out(json.dumps(items, indent=2))
            return 0
        for i in items:
            sw = i["swatches"]
            print(f"{i['name']:<16} {i['theme']:<6} bg {sw.get('--bg', '-'):<8} accent {sw.get('--accent', '-'):<8} "
                  f"{i['description'][:70]}")
        print(f"\n{len(items)} design(s). Read one: webcraft design show NAME", file=sys.stderr)
        return 0
    if not a.args:
        print(f"usage: webcraft design {act} NAME_OR_FILE", file=sys.stderr)
        return 2
    target = a.args[0]
    if act == "show":
        label, text = dm.read(target)
        _out(text)
        return 0
    if act == "check":
        label, text = dm.read(target)
        d = dm.parse(text)
        res = dm.check(d)
        _out(json.dumps(res, indent=2) if a.json else dm.render_check(label, d, res))
        return 1 if res["fails"] else 0
    if act == "tokens":
        label, text = dm.read(target)
        _out(dm.to_tokens_css(dm.parse(text), label), a.output)
        return 0
    if act == "use":
        for line in dm.use(target, a.dir, tokens=a.tokens, force=a.force):
            print(line)
        print("The file is a reference for visual language: replace the brand's name, logo, imagery and copy, "
              "and license or swap proprietary fonts.")
        return 0
    print(f"unknown action {act}", file=sys.stderr)
    return 2


def cmd_prompts(a):
    from . import prompts as pr
    act = a.action
    if act == "where":
        print(pr.mine_root())
        return 0
    if act == "list":
        lib = "mine" if a.mine else "webcraft" if a.builtin else "all"
        items = pr.search(" ".join(a.args), lib, a.category or "")
        if a.json:
            _out(json.dumps([p.summary() for p in items], indent=2))
            return 0
        for p in items:
            print(f"{p.id:<42} {p.category:<13} {p.motion or '-':<7} {p.title}")
        print(f"\n{len(items)} prompt(s). Fill one: webcraft prompts show ID --set \"BRAND NAME=Acme\"", file=sys.stderr)
        return 0
    if act == "add":
        title = a.title or (a.args[0] if a.args else "")
        if a.file:
            body = Path(a.file).read_text(encoding="utf-8")
        elif not sys.stdin.isatty():
            body = sys.stdin.read()
        else:
            print("Paste the prompt, then press Ctrl+D (Ctrl+Z then Enter on Windows):", file=sys.stderr)
            body = sys.stdin.read()
        p = pr.save(title, body, category=a.category or "Uncategorized",
                    tags=[t for t in (a.tags or "").split(",") if t.strip()], description=a.description or "",
                    source=a.source or "", source_url=a.source_url or "")
        print(f"saved {p.id} -> {p.path}")
        print("Stored only on this computer. webcraft never uploads or bundles your prompts.")
        return 0
    if not a.args:
        print(f"usage: webcraft prompts {act} ID", file=sys.stderr)
        return 2
    if act == "show":
        p = pr.get(a.args[0])
        values = {}
        if a.values:
            values.update(json.loads(Path(a.values).read_text(encoding="utf-8")))
        for kv in a.set or []:
            k, _, v = kv.partition("=")
            values[k] = v
        if a.json:
            d = p.to_dict()
            d["filled"] = pr.fill(p.body, values)
            _out(json.dumps(d, indent=2))
            return 0
        text = pr.fill(p.body, values)
        _out(text, a.output)
        left = [ph for ph in pr.PLACEHOLDER_RE.findall(text)]
        if left and not a.output:
            print(f"\n[{len(set(left))} placeholder(s) still open: {', '.join(list(dict.fromkeys(left))[:6])}"
                  f"{' ...' if len(set(left)) > 6 else ''}]", file=sys.stderr)
        return 0
    if act == "remove":
        path = pr.delete(a.args[0])
        print(f"removed {path}")
        return 0
    print(f"unknown action {act}", file=sys.stderr)
    return 2


def cmd_ui(a):
    from . import ui
    ui.run(port=a.port, open_browser=not a.no_open, verbose=a.verbose)
    return 0


def cmd_mcp_config(a):
    from . import agents
    clients = agents.MCP_CLIENTS if a.client == "all" else [a.client]
    for c in clients:
        if len(clients) > 1:
            print(f"== {c} ==")
        print(agents.mcp_config(c))
        if len(clients) > 1:
            print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    from . import agents, tokens
    p = argparse.ArgumentParser(prog="webcraft", description="Website-design skills and checks for any coding agent.",
                                epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"webcraft {__version__}")
    sub = p.add_subparsers(dest="cmd", metavar="command")

    s = sub.add_parser("list", help="list the bundled skills")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("show", help="print a skill (or one of its files)")
    s.add_argument("name")
    s.add_argument("file", nargs="?", help="e.g. references/snippets.md")
    s.set_defaults(func=cmd_show)

    agent_help = "agent: " + ", ".join(agents.TARGETS) + ", or all (comma-separate several)"
    s = sub.add_parser("install", help="install the skills into an agent", description=agent_help)
    s.add_argument("agent", help=agent_help)
    s.add_argument("--scope", choices=["user", "project"], default="user",
                   help="user: available in every project; project: this repo only (default user)")
    s.add_argument("--project", default=".", help="project folder for project-scope installs (default .)")
    s.add_argument("--dest", help="install into this folder instead")
    s.add_argument("--only", help="comma-separated skill names")
    s.add_argument("--file", help="agents-md: index file to write (default AGENTS.md; e.g. CLAUDE.md, GEMINI.md, "
                                  ".github/copilot-instructions.md, CONVENTIONS.md)")
    s.add_argument("--force", action="store_true", help="overwrite skill folders not installed by webcraft")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_install)

    s = sub.add_parser("uninstall", help="remove skills installed by webcraft")
    s.add_argument("agent", choices=list(agents.TARGETS))
    s.add_argument("--scope", choices=["user", "project"], default="user")
    s.add_argument("--project", default=".")
    s.add_argument("--dest")
    s.add_argument("--file")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_uninstall)

    s = sub.add_parser("status", help="show where the skills are installed")
    s.add_argument("--project", default=".")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("validate", help="check skill folders against the Agent Skills format")
    s.add_argument("path", nargs="?", help="folder of skills (default: the bundled skills)")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("tokens", help="generate design tokens from one brand color")
    s.add_argument("brand", help='brand color, e.g. "#e4572e" or "oklch(0.65 0.2 35)"')
    s.add_argument("--tone", choices=list(tokens.TONES), default="corporate")
    s.add_argument("--base", choices=["light", "dark"], default="light", help="which theme :root holds")
    s.add_argument("--radius", choices=list(tokens.RADII), help="corner personality (default by tone)")
    s.add_argument("--format", choices=["css", "theme-json", "dtcg", "design-md", "json"], default="css")
    s.add_argument("--name", default="my-site", help="design-md: name for the design system")
    s.add_argument("--base-styles", action="store_true", help="append starter element styles")
    s.add_argument("--no-auto-dark", action="store_true", help="omit the prefers-color-scheme block")
    s.add_argument("-o", "--output", help="write to a file")
    s.set_defaults(func=cmd_tokens)

    s = sub.add_parser("contrast", help="WCAG contrast for a pair, or for token pairs in a CSS file")
    s.add_argument("foreground", nargs="?")
    s.add_argument("background", nargs="?")
    s.add_argument("--tokens", metavar="CSS_FILE")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_contrast)

    s = sub.add_parser("audit", help="pre-launch QA of a URL, HTML file or site folder")
    s.add_argument("target")
    s.add_argument("--pages", type=int, default=1, help="URL: also audit up to N same-site pages (default 1)")
    s.add_argument("--offline", action="store_true", help="skip robots/sitemap/redirect/link requests")
    s.add_argument("--fail-on", choices=["blocker", "should-fix", "polish", "never"], default="blocker",
                   help="exit 1 when a finding at or above this severity exists (default blocker)")
    s.add_argument("--json", action="store_true")
    s.add_argument("-o", "--output")
    s.set_defaults(func=cmd_audit)

    s = sub.add_parser("detect", help="detect a site's CMS, framework, motion libraries, fonts and palette")
    s.add_argument("target")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_detect)

    s = sub.add_parser("teardown", help="draft a placeholder-based rebuild brief of a page")
    s.add_argument("target")
    s.add_argument("--json", action="store_true")
    s.add_argument("-o", "--output")
    s.set_defaults(func=cmd_teardown)

    s = sub.add_parser("design", help="DESIGN.md: reference library, check, convert to tokens",
                       description="Work with DESIGN.md files and the VoltAgent/awesome-design-md reference library.",
                       epilog="""actions:
  sync [--source ZIP_OR_FOLDER]   download (or import) the library
  list [QUERY]                    search the library, e.g. list dark fintech
  show NAME|FILE                  print a DESIGN.md
  check NAME|FILE                 contrast-check its palette and components
  tokens NAME|FILE [-o FILE]      convert to webcraft tokens.css
  use NAME [--dir D] [--tokens]   copy into a project as DESIGN.md (with a reference notice)
  status                          where the library is cached""",
                       formatter_class=argparse.RawDescriptionHelpFormatter)
    s.add_argument("action", choices=["sync", "list", "show", "check", "tokens", "use", "status"])
    s.add_argument("args", nargs="*")
    s.add_argument("--source", help="sync: local zip or folder instead of downloading")
    s.add_argument("--dir", default=".", help="use: project folder (default .)")
    s.add_argument("--tokens", action="store_true", help="use: also write tokens.css")
    s.add_argument("--force", action="store_true", help="use: overwrite existing files")
    s.add_argument("--json", action="store_true")
    s.add_argument("-o", "--output")
    s.set_defaults(func=cmd_design)

    s = sub.add_parser("prompts", help="website prompt library: webcraft's own plus your private prompts",
                       description="Browse webcraft's MIT prompt library and keep a private library of your own prompts "
                                   "(stored only on this computer).",
                       epilog="""actions:
  list [QUERY] [--mine|--builtin] [--category C]   search prompts
  show ID [--set "KEY=VALUE" ...] [-o FILE]        print a prompt, filling [PLACEHOLDERS]
  add "TITLE" [--file F] [--category C] [--tags a,b] [--source S] [--source-url U]
                                                   save a prompt to your private library (or pipe it in)
  remove mine/ID                                   delete one of your prompts
  where                                            show where your prompts are stored""",
                       formatter_class=argparse.RawDescriptionHelpFormatter)
    s.add_argument("action", choices=["list", "show", "add", "remove", "where"])
    s.add_argument("args", nargs="*")
    s.add_argument("--mine", action="store_true", help="list: only your prompts")
    s.add_argument("--builtin", action="store_true", help="list: only webcraft's prompts")
    s.add_argument("--category")
    s.add_argument("--set", action="append", metavar="KEY=VALUE", help="show: fill a placeholder (repeatable)")
    s.add_argument("--values", metavar="JSON_FILE", help="show: fill placeholders from a JSON object")
    s.add_argument("--title")
    s.add_argument("--file", help="add: read the prompt text from a file")
    s.add_argument("--tags")
    s.add_argument("--description")
    s.add_argument("--source", help="add: where it came from, e.g. a site you bought it from")
    s.add_argument("--source-url")
    s.add_argument("--json", action="store_true")
    s.add_argument("-o", "--output")
    s.set_defaults(func=cmd_prompts)

    s = sub.add_parser("ui", help="open the web interface in your browser")
    s.add_argument("--port", type=int, default=8765, help="port to try first (default 8765; 0 picks any)")
    s.add_argument("--no-open", action="store_true", help="do not open a browser")
    s.add_argument("--verbose", action="store_true", help="log requests")
    s.set_defaults(func=cmd_ui)

    s = sub.add_parser("mcp", help="run the MCP server on stdio")
    s.set_defaults(func=cmd_mcp)

    s = sub.add_parser("mcp-config", help="print MCP setup for a client")
    s.add_argument("client", nargs="?", default="all", choices=agents.MCP_CLIENTS + ["all"])
    s.set_defaults(func=cmd_mcp_config)
    return p


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass
    parser = build_parser()
    a = parser.parse_args(argv)
    if not getattr(a, "func", None):
        parser.print_help()
        return 0
    try:
        return a.func(a)
    except Exception as e:
        from .designmd import LibraryMissing
        if isinstance(e, (KeyError, ValueError, OSError, ConnectionError, LibraryMissing)):
            msg = e.args[0] if isinstance(e, KeyError) and e.args else e
            print(f"error: {msg}", file=sys.stderr)
            return 2
        raise


if __name__ == "__main__":
    sys.exit(main())
