"""A dependency-free MCP server over stdio (JSON-RPC 2.0, one message per line).

Exposes:
  tools      deterministic helpers (tokens, contrast, audit, detect, teardown)
             plus list_skills / get_skill for clients without native skills
  prompts    one per skill, so clients show them as slash commands
  resources  webcraft://skills/<name>/<file> for every skill file
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from . import __version__, audit, color, css, detect, skills, teardown, tokens

PROTOCOL_VERSIONS = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]

INSTRUCTIONS = (
    "webcraft bundles website-design skills (homepage structure, hero, layout, motion, tokens, "
    "WordPress, launch QA, site teardown) and deterministic tools. Before planning or building a site, "
    "call list_skills and read the matching skill with get_skill, then use the tools for anything "
    "measurable: generate_tokens for a palette, check_contrast for color pairs, audit_site before launch, "
    "detect_stack and teardown_site to analyze a reference site. For a visual direction, list_designs and "
    "get_design browse a library of DESIGN.md files (references only: never copy a brand's name, logo or fonts)."
)


def _schema(props: Dict[str, dict], required=()):
    return {"type": "object", "properties": props, "required": list(required), "additionalProperties": False}


TARGET = {"type": "string", "description": "A URL (https://...), an HTML file path or a site folder path"}

TOOLS = [
    {
        "name": "list_skills",
        "title": "List website-design skills",
        "description": "List the bundled website-design skills with their descriptions. Read one with get_skill.",
        "inputSchema": _schema({}),
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "get_skill",
        "title": "Read a skill",
        "description": "Return a skill's SKILL.md instructions, or one of its reference files.",
        "inputSchema": _schema({
            "name": {"type": "string", "description": "Skill name from list_skills"},
            "file": {"type": "string", "description": "Optional supporting file, e.g. references/snippets.md"},
        }, ["name"]),
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "generate_tokens",
        "title": "Generate design tokens",
        "description": "Build a contrast-checked token set (colors for light and dark, fluid type scale, spacing, "
                       "radius, shadow) from one brand color. Formats: css (tokens.css), theme-json (WordPress), "
                       "dtcg (W3C design tokens JSON), json (raw with contrast results).",
        "inputSchema": _schema({
            "brand": {"type": "string", "description": "Brand color in any CSS syntax, e.g. #e4572e or oklch(0.65 0.2 35)"},
            "base": {"type": "string", "enum": ["light", "dark"], "default": "light"},
            "tone": {"type": "string", "enum": list(tokens.TONES), "default": "corporate"},
            "radius": {"type": "string", "enum": list(tokens.RADII), "description": "Corner personality; defaults by tone"},
            "format": {"type": "string", "enum": ["css", "theme-json", "dtcg", "design-md", "json"], "default": "css"},
            "base_styles": {"type": "boolean", "default": False, "description": "Append starter body/heading/button styles"},
        }, ["brand"]),
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "check_contrast",
        "title": "Check color contrast",
        "description": "WCAG 2.x contrast ratio for a foreground/background pair (any CSS color syntax), "
                       "or the standard role pairs (--text/--bg, --muted/--bg, --on-accent/--accent...) in a CSS file.",
        "inputSchema": _schema({
            "foreground": {"type": "string"},
            "background": {"type": "string"},
            "css": {"type": "string", "description": "CSS text holding token custom properties (instead of a pair)"},
            "path": {"type": "string", "description": "Path to a CSS file (instead of a pair)"},
        }),
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "audit_site",
        "title": "Pre-launch audit",
        "description": "Static launch QA of a URL, HTML file or folder: SEO basics, accessibility markup, "
                       "performance hints, placeholder content, broken links, motion guards. Findings are ranked "
                       "blocker / should-fix / polish, with a 'Not checked' list of what needs a human or a browser.",
        "inputSchema": _schema({
            "target": TARGET,
            "pages": {"type": "integer", "minimum": 1, "maximum": 50, "default": 1,
                      "description": "For a URL, also audit up to this many same-site pages linked from it"},
            "format": {"type": "string", "enum": ["text", "json"], "default": "text"},
        }, ["target"]),
        "annotations": {"readOnlyHint": True, "openWorldHint": True},
    },
    {
        "name": "detect_stack",
        "title": "Detect a site's stack",
        "description": "Fingerprint the CMS, framework, motion libraries (GSAP, Lenis, AOS...), sliders, fonts, "
                       "analytics and palette of a page.",
        "inputSchema": _schema({"target": TARGET, "format": {"type": "string", "enum": ["text", "json"], "default": "text"}},
                               ["target"]),
        "annotations": {"readOnlyHint": True, "openWorldHint": True},
    },
    {
        "name": "list_designs",
        "title": "Search the DESIGN.md library",
        "description": "Search the VoltAgent/awesome-design-md reference library (84+ DESIGN.md files analyzing real "
                       "sites' visual language). Words match name and description; 'dark' or 'light' filter by theme. "
                       "Downloads the library on first use.",
        "inputSchema": _schema({"query": {"type": "string", "description": "e.g. 'dark fintech', 'editorial', 'linear'"}}),
        "annotations": {"readOnlyHint": True, "openWorldHint": True},
    },
    {
        "name": "get_design",
        "title": "Read, check or convert a DESIGN.md",
        "description": "For a library design name or a DESIGN.md path: format 'markdown' returns the file, 'check' "
                       "contrast-checks its palette and components, 'tokens' converts it to webcraft tokens.css. Library "
                       "files describe other companies' brands: use them as a visual reference, never their name, logo, "
                       "imagery, copy or proprietary fonts.",
        "inputSchema": _schema({
            "name": {"type": "string", "description": "Library name (from list_designs) or a path to a DESIGN.md"},
            "format": {"type": "string", "enum": ["markdown", "check", "tokens"], "default": "markdown"},
        }, ["name"]),
        "annotations": {"readOnlyHint": True, "openWorldHint": True},
    },
    {
        "name": "list_prompts",
        "title": "Search website prompts",
        "description": "Search website-building prompts: webcraft's own MIT library (heroes, landing pages, SaaS, "
                       "agency, portfolio, 3D, dashboards, backgrounds) plus the user's private prompts saved on this "
                       "computer. Returns ids, categories and how many placeholders each has.",
        "inputSchema": _schema({
            "query": {"type": "string", "description": "Words to match, e.g. 'hero video', 'dashboard'"},
            "library": {"type": "string", "enum": ["all", "webcraft", "mine"], "default": "all"},
        }),
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "get_prompt",
        "title": "Get and fill a website prompt",
        "description": "Return a prompt by id with its [PLACEHOLDERS] filled from `values` (unfilled ones stay visible "
                       "so you can ask the user). Prompts from the user's private library are for their own projects "
                       "only: do not publish or share their text.",
        "inputSchema": _schema({
            "id": {"type": "string", "description": "Prompt id from list_prompts, e.g. webcraft/saas-landing-page"},
            "values": {"type": "object", "additionalProperties": {"type": "string"},
                       "description": "Placeholder name to value, e.g. {\"BRAND NAME\": \"Northwind\"}"},
        }, ["id"]),
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "teardown_site",
        "title": "Draft a rebuild brief",
        "description": "Draft a section-by-section, placeholder-based rebuild brief of a page (follows the "
                       "site-teardown skill). Copy, brand and images are replaced by placeholders; layout and "
                       "motion values are marked for verification in a browser.",
        "inputSchema": _schema({"target": TARGET, "format": {"type": "string", "enum": ["text", "json"], "default": "text"}},
                               ["target"]),
        "annotations": {"readOnlyHint": True, "openWorldHint": True},
    },
]


def _text(s: str, is_error: bool = False) -> dict:
    return {"content": [{"type": "text", "text": s}], "isError": is_error}


def tool_list_skills(args):
    return _text("\n".join(f"- {s.name}: {s.description}" for s in skills.load_all()))


def tool_get_skill(args):
    s = skills.get(args["name"])
    if args.get("file"):
        return _text(s.read_file(args["file"]))
    extra = s.files()
    tail = ("\n\n---\nSupporting files (read with get_skill name=%s file=...): %s" % (s.name, ", ".join(extra))) if extra else ""
    return _text(s.text + tail)


def tool_generate_tokens(args):
    t = tokens.generate(args["brand"], base=args.get("base", "light"), tone=args.get("tone", "corporate"),
                        radius=args.get("radius"))
    fmt = args.get("format", "css")
    if fmt == "json":
        return _text(json.dumps(t, indent=2))
    from . import designmd
    body = {"css": lambda: tokens.render_css(t, base_styles=bool(args.get("base_styles"))),
            "theme-json": lambda: tokens.render_theme_json(t),
            "dtcg": lambda: tokens.render_dtcg(t),
            "design-md": lambda: designmd.from_tokens(t)}[fmt]()
    return _text(body + "\n\n" + tokens.render_report(t))


def tool_check_contrast(args):
    if args.get("css") or args.get("path"):
        text = args.get("css") or open(args["path"], encoding="utf-8").read()
        res = css.check_tokens_css(text)
        if not any(res.values()):
            return _text("No role pairs found. Expected custom properties such as --text and --bg.", True)
        lines = []
        for label, rows in res.items():
            for r in rows:
                lines.append(f"{label:<28} {r['pair']:<24} {r['ratio']}:1 {r['status']}")
        return _text("\n".join(lines))
    if not (args.get("foreground") and args.get("background")):
        return _text("Pass foreground and background, or css / path.", True)
    r = color.contrast(args["foreground"], args["background"])
    lv = color.levels(r)
    return _text(f"{args['foreground']} on {args['background']}: {r:.2f}:1\n" +
                 "\n".join(f"{k}: {'pass' if ok else 'fail'}" for k, ok in lv.items()))


def tool_audit_site(args):
    rep = audit.audit(args["target"], max_pages=int(args.get("pages", 1)))
    if args.get("format") == "json":
        return _text(json.dumps(rep.to_dict(), indent=2))
    return _text(audit.render(rep))


def tool_detect_stack(args):
    from . import source
    res = detect.detect(source.load(args["target"]))
    return _text(json.dumps(res, indent=2) if args.get("format") == "json" else detect.render(res))


def tool_teardown_site(args):
    res = teardown.teardown(args["target"])
    return _text(json.dumps(res, indent=2) if args.get("format") == "json" else teardown.render(res))


def _ensure_library():
    from . import designmd
    try:
        designmd.library_index()
    except designmd.LibraryMissing:
        designmd.sync()


def tool_list_designs(args):
    from . import designmd
    _ensure_library()
    items = designmd.search(args.get("query", ""))
    lines = [f"- {i['name']} ({i['theme']}; bg {i['swatches'].get('--bg', '?')}, accent {i['swatches'].get('--accent', '?')}): "
             f"{i['description'][:160]}" for i in items]
    return _text(("\n".join(lines) or "No matches.") + f"\n\n{len(items)} design(s). Source: {designmd.LIBRARY_URL} (MIT).")


def tool_get_design(args):
    from . import designmd
    name = args["name"]
    from_library = not Path(name).is_file()
    if from_library:
        _ensure_library()
    label, text = designmd.read(name)
    fmt = args.get("format", "markdown")
    if fmt == "check":
        d = designmd.parse(text)
        return _text(designmd.render_check(label, d, designmd.check(d)))
    if fmt == "tokens":
        return _text(designmd.to_tokens_css(designmd.parse(text), label))
    return _text(designmd.with_notice(text) if from_library else text)


def tool_list_prompts(args):
    from . import prompts
    items = prompts.search(args.get("query", ""), args.get("library", "all"))
    lines = [f"- {p.id} [{p.category}, motion {p.motion or '-'}, {len(p.placeholders)} placeholders]: {p.description}"
             for p in items]
    return _text("\n".join(lines) or "No prompts match.")


def tool_get_prompt(args):
    from . import prompts
    p = prompts.get(args["id"])
    filled = prompts.fill(p.body, args.get("values") or {})
    left = list(dict.fromkeys(prompts.PLACEHOLDER_RE.findall(filled)))
    head = f"# {p.title} ({p.id})\n"
    if p.library == "mine":
        head += "Private prompt from the user's own library: use it for their project, do not publish its text.\n"
    tail = f"\n\nOpen placeholders: {', '.join(left)}" if left else ""
    return _text(head + "\n" + filled + tail)


HANDLERS: Dict[str, Callable[[dict], dict]] = {
    "list_prompts": tool_list_prompts,
    "get_prompt": tool_get_prompt,
    "list_designs": tool_list_designs,
    "get_design": tool_get_design,
    "list_skills": tool_list_skills,
    "get_skill": tool_get_skill,
    "generate_tokens": tool_generate_tokens,
    "check_contrast": tool_check_contrast,
    "audit_site": tool_audit_site,
    "detect_stack": tool_detect_stack,
    "teardown_site": tool_teardown_site,
}


class Server:
    def __init__(self):
        self.protocol = PROTOCOL_VERSIONS[0]

    def handle(self, msg: dict) -> Optional[dict]:
        method = msg.get("method")
        mid = msg.get("id")
        is_request = "id" in msg
        if method is None:
            return None  # a response to something we never send; ignore
        try:
            result = self.dispatch(method, msg.get("params") or {})
        except RpcError as e:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": e.code, "message": e.message}} if is_request else None
        except Exception as e:  # never crash the server on one bad call
            if not is_request:
                return None
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32603, "message": f"{type(e).__name__}: {e}"}}
        if not is_request:
            return None
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def dispatch(self, method: str, params: dict) -> Any:
        if method == "initialize":
            requested = params.get("protocolVersion")
            self.protocol = requested if requested in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
            return {
                "protocolVersion": self.protocol,
                "capabilities": {"tools": {"listChanged": False}, "prompts": {"listChanged": False},
                                 "resources": {"listChanged": False, "subscribe": False}},
                "serverInfo": {"name": "webcraft", "title": "webcraft website-design skills", "version": __version__},
                "instructions": INSTRUCTIONS,
            }
        if method in ("notifications/initialized", "notifications/cancelled", "initialized"):
            return None
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": TOOLS}
        if method == "tools/call":
            name = params.get("name")
            if name not in HANDLERS:
                raise RpcError(-32602, f"unknown tool {name}")
            try:
                return HANDLERS[name](params.get("arguments") or {})
            except Exception as e:
                from .designmd import LibraryMissing
                if isinstance(e, (KeyError, ValueError, OSError, ConnectionError, LibraryMissing)):
                    return _text(f"{type(e).__name__}: {e}", True)
                raise
        if method == "prompts/list":
            return {"prompts": [{"name": s.name, "title": s.name.replace("-", " ").title(), "description": s.description,
                                 "arguments": [{"name": "task", "description": "What you want done", "required": False}]}
                                for s in skills.load_all()]}
        if method == "prompts/get":
            try:
                s = skills.get(params.get("name", ""))
            except KeyError as e:
                raise RpcError(-32602, str(e))
            task = (params.get("arguments") or {}).get("task", "").strip()
            files = s.files()
            text = (f"Follow this skill ({s.name}) for the task below.\n\n{s.body.strip()}\n")
            if files:
                text += f"\nSupporting files are available via the get_skill tool (name={s.name}): {', '.join(files)}\n"
            text += f"\nTask: {task or '[describe the task]'}"
            return {"description": s.description, "messages": [{"role": "user", "content": {"type": "text", "text": text}}]}
        if method == "resources/list":
            res = []
            for s in skills.load_all():
                res.append({"uri": f"webcraft://skills/{s.name}/SKILL.md", "name": f"{s.name}/SKILL.md",
                            "description": s.description, "mimeType": "text/markdown"})
                for f in s.files():
                    res.append({"uri": f"webcraft://skills/{s.name}/{f}", "name": f"{s.name}/{f}",
                                "mimeType": "text/markdown" if f.endswith(".md") else "text/plain"})
            return {"resources": res}
        if method == "resources/templates/list":
            return {"resourceTemplates": []}
        if method == "resources/read":
            uri = params.get("uri", "")
            prefix = "webcraft://skills/"
            if not uri.startswith(prefix) or "/" not in uri[len(prefix):]:
                raise RpcError(-32602, f"unknown resource {uri}")
            name, rel = uri[len(prefix):].split("/", 1)
            try:
                s = skills.get(name)
                text = s.text if rel == "SKILL.md" else s.read_file(rel)
            except (KeyError, FileNotFoundError, ValueError) as e:
                raise RpcError(-32002, str(e))
            mime = "text/markdown" if rel.endswith(".md") else "text/plain"
            return {"contents": [{"uri": uri, "mimeType": mime, "text": text}]}
        if method == "logging/setLevel":
            return {}
        raise RpcError(-32601, f"method not found: {method}")


class RpcError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def serve(stdin=None, stdout=None) -> None:
    stdin = stdin or sys.stdin.buffer
    stdout = stdout or sys.stdout.buffer
    server = Server()
    for raw in stdin:
        line = raw.decode("utf-8", errors="replace").strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            out = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        else:
            if isinstance(msg, list):  # batch (2025-03-26)
                replies = [r for r in (server.handle(m) for m in msg) if r is not None]
                out = replies or None
            else:
                out = server.handle(msg)
        if out is not None:
            stdout.write((json.dumps(out, ensure_ascii=False) + "\n").encode("utf-8"))
            stdout.flush()


def main() -> None:
    try:
        serve()
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        raise
