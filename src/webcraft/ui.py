"""Local web interface: `webcraft ui`.

A small JSON API over the same functions the CLI uses, plus one static page.
Standard library only.

Safety: the server binds to 127.0.0.1, rejects requests whose Host header is
not the local address (DNS rebinding), and requires a per-launch secret on
every API call (cross-site requests from other pages cannot read it).
"""
from __future__ import annotations

import json
import os
import secrets
import sys
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Dict

from . import __version__, agents, audit, color, css, designmd, detect, prompts, skills, source, teardown, tokens

PAGE = Path(__file__).resolve().parent / "ui" / "index.html"
MAX_BODY = 4 * 1024 * 1024


# --- API ---------------------------------------------------------------------

def _sample_site() -> str:
    p = Path(__file__).resolve().parents[2] / "examples" / "sample-site"
    return str(p) if p.is_dir() else ""


def api_meta(body: dict, ctx: dict) -> dict:
    sample = _sample_site()
    return {
        "sample_site": sample,
        "sample_index": str(Path(sample) / "index.html") if sample else "",
        "version": __version__,
        "cwd": ctx["cwd"],
        "tones": list(tokens.TONES),
        "radii": list(tokens.RADII),
        "agents": [{"key": t.key, "label": t.label, "kind": t.kind, "user": t.user, "project": t.project,
                    "note": t.note} for t in agents.TARGETS.values()],
        "mcp_clients": agents.MCP_CLIENTS,
        "skills": [{"name": s.name, "description": s.description} for s in skills.load_all()],
    }


def api_tokens(body: dict, ctx: dict) -> dict:
    t = tokens.generate(body.get("brand", "#e4572e"), base=body.get("base", "light"),
                        tone=body.get("tone", "corporate"), radius=body.get("radius") or None)
    return {
        "tokens": t,
        "css": tokens.render_css(t, base_styles=bool(body.get("base_styles"))),
        "theme_json": tokens.render_theme_json(t),
        "dtcg": tokens.render_dtcg(t),
        "design_md": designmd.from_tokens(t, body.get("name") or "my-site"),
        "report": tokens.render_report(t),
    }


def api_contrast(body: dict, ctx: dict) -> dict:
    if body.get("css"):
        return {"themes": css.check_tokens_css(body["css"])}
    fg, bg = body.get("fg", ""), body.get("bg", "")
    fgc, bgc = color.parse(fg), color.parse(bg)
    r = color.contrast(fgc, bgc)
    return {"ratio": round(r, 2), "levels": color.levels(r), "fg": color.to_hex(fgc), "bg": color.to_hex(bgc)}


def api_audit(body: dict, ctx: dict) -> dict:
    target = (body.get("target") or "").strip()
    if not target:
        raise ValueError("enter a URL, an HTML file or a folder")
    rep = audit.audit(target, max_pages=max(1, min(int(body.get("pages") or 1), 50)),
                      remote_checks=not body.get("offline"))
    return {"report": rep.to_dict(), "text": audit.render(rep)}


def api_detect(body: dict, ctx: dict) -> dict:
    target = (body.get("target") or "").strip()
    if not target:
        raise ValueError("enter a URL, an HTML file or a folder")
    res = detect.detect(source.load(target))
    return {"result": res, "text": detect.render(res)}


def api_teardown(body: dict, ctx: dict) -> dict:
    target = (body.get("target") or "").strip()
    if not target:
        raise ValueError("enter a URL, an HTML file or a folder")
    res = teardown.teardown(target)
    return {"result": res, "text": teardown.render(res)}


def api_skill(body: dict, ctx: dict) -> dict:
    s = skills.get(body.get("name", ""))
    f = body.get("file")
    return {"name": s.name, "description": s.description, "files": s.files(),
            "file": f or "SKILL.md", "text": s.read_file(f) if f else s.text}


def api_install(body: dict, ctx: dict) -> dict:
    chosen = body.get("agents") or []
    if not chosen:
        raise ValueError("choose at least one agent")
    only = body.get("only") or None
    out = []
    for key in chosen:
        log = agents.install(key, scope=body.get("scope", "user"), project_dir=body.get("project") or ctx["cwd"],
                             only=only, force=bool(body.get("force")), dry_run=bool(body.get("dry_run", True)))
        out.append({"agent": key, "label": agents.TARGETS[key].label, "log": log})
    return {"results": out, "dry_run": bool(body.get("dry_run", True))}


def api_uninstall(body: dict, ctx: dict) -> dict:
    key = body.get("agent", "")
    log = agents.uninstall(key, scope=body.get("scope", "user"), project_dir=body.get("project") or ctx["cwd"],
                           dry_run=bool(body.get("dry_run", False)))
    return {"agent": key, "log": log}


def api_status(body: dict, ctx: dict) -> dict:
    return {"rows": agents.status(body.get("project") or ctx["cwd"])}


def api_mcp_config(body: dict, ctx: dict) -> dict:
    return {"client": body.get("client", "generic"), "text": agents.mcp_config(body.get("client", "generic"))}


def api_design_status(body: dict, ctx: dict) -> dict:
    return designmd.library_status()


def api_design_sync(body: dict, ctx: dict) -> dict:
    return designmd.sync(body.get("source") or None)


def api_design_list(body: dict, ctx: dict) -> dict:
    return {"items": designmd.search(body.get("query", "")), "status": designmd.library_status()}


def api_design_get(body: dict, ctx: dict) -> dict:
    name = body.get("name", "")
    label, text = designmd.read(name)
    d = designmd.parse(text)
    res = designmd.check(d)
    fonts = {k: v.get("fontFamily") for k, v in d["typography"].items() if isinstance(v, dict)}
    return {"label": label, "text": designmd.with_notice(text), "raw": text,
            "parsed": {k: d[k] for k in ("name", "description", "has_frontmatter", "colors", "sections")},
            "fonts": fonts, "rounded": d["rounded"], "check": res,
            "tokens_css": designmd.to_tokens_css(d, label), "notice": designmd.REFERENCE_NOTICE}


def api_design_use(body: dict, ctx: dict) -> dict:
    log = designmd.use(body.get("name", ""), body.get("dir") or ctx["cwd"], tokens=bool(body.get("tokens")),
                       force=bool(body.get("force")))
    return {"log": log}


def api_overview(body: dict, ctx: dict) -> dict:
    rows = agents.status(ctx["cwd"])
    installed = sum(1 for r in rows if r["installed"])
    builtin = len(prompts.load_all(prompts.BUILTIN))
    mine = len(prompts.load_all(prompts.MINE))
    return {
        "version": __version__,
        "skills": len(skills.load_all()),
        "installed_agents": installed,
        "agent_targets": len(agents.TARGETS),
        "designs": designmd.library_status(),
        "prompts": {"builtin": builtin, "mine": mine},
        "paths": {"cwd": ctx["cwd"], "prompts": str(prompts.mine_root()), "designs": str(designmd.cache_dir()),
                  "skills": str(skills.skills_root())},
        "mcp_command": " ".join(agents.server_command()),
    }


def api_prompts_list(body: dict, ctx: dict) -> dict:
    lib = body.get("library") or "all"
    items = prompts.search(body.get("query", ""), lib, body.get("category", ""))
    return {"items": [p.summary() for p in items], "categories": prompts.categories(),
            "mine_path": str(prompts.mine_root())}


def api_prompts_get(body: dict, ctx: dict) -> dict:
    return prompts.get(body.get("id", "")).to_dict()


def api_prompts_save(body: dict, ctx: dict) -> dict:
    slug = None
    overwrite = False
    if body.get("id", "").startswith("mine/"):
        slug, overwrite = body["id"].split("/", 1)[1], True
    tags = body.get("tags") or []
    if isinstance(tags, str):
        tags = tags.split(",")
    p = prompts.save(body.get("title", ""), body.get("body", ""), category=body.get("category") or "Uncategorized",
                     tags=tags, description=body.get("description", ""), source=body.get("source", ""),
                     source_url=body.get("source_url", ""), stack=body.get("stack", ""), motion=body.get("motion", ""),
                     slug=slug, overwrite=overwrite)
    return p.to_dict()


def api_prompts_delete(body: dict, ctx: dict) -> dict:
    return {"removed": str(prompts.delete(body.get("id", "")))}


ROUTES: Dict[str, Callable[[dict, dict], dict]] = {
    "overview": api_overview,
    "prompts_list": api_prompts_list, "prompts_get": api_prompts_get, "prompts_save": api_prompts_save,
    "prompts_delete": api_prompts_delete,
    "design_status": api_design_status, "design_sync": api_design_sync, "design_list": api_design_list,
    "design_get": api_design_get, "design_use": api_design_use,
    "meta": api_meta, "tokens": api_tokens, "contrast": api_contrast, "audit": api_audit,
    "detect": api_detect, "teardown": api_teardown, "skill": api_skill, "install": api_install,
    "uninstall": api_uninstall, "status": api_status, "mcp_config": api_mcp_config,
}

EXPECTED_ERRORS = (KeyError, ValueError, FileNotFoundError, ConnectionError, OSError, designmd.LibraryMissing)


# --- HTTP --------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = f"webcraft-ui/{__version__}"

    def log_message(self, fmt, *args):  # quiet by default
        if self.server.verbose:
            sys.stderr.write("  " + fmt % args + "\n")

    def _host_ok(self) -> bool:
        return self.headers.get("Host", "") in self.server.allowed_hosts

    def _send(self, status: int, body: bytes, ctype: str, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: dict):
        self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, b"forbidden", "text/plain")
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            nonce = secrets.token_urlsafe(16)
            html = PAGE.read_text(encoding="utf-8")
            html = html.replace("__WEBCRAFT_TOKEN__", self.server.secret).replace("__NONCE__", nonce)
            csp = ("default-src 'none'; "
                   f"script-src 'nonce-{nonce}'; "
                   "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                   "font-src https://fonts.gstatic.com data:; img-src 'self' data:; connect-src 'self'; "
                   "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
            return self._send(200, html.encode("utf-8"), "text/html; charset=utf-8", {"Content-Security-Policy": csp})
        if path == "/favicon.ico":
            return self._send(204, b"", "image/x-icon")
        return self._send(404, b"not found", "text/plain")

    def do_POST(self):
        if not self._host_ok():
            return self._json(403, {"ok": False, "error": "forbidden host"})
        if not secrets.compare_digest(self.headers.get("X-Webcraft-Token", ""), self.server.secret):
            return self._json(403, {"ok": False, "error": "missing or wrong token; reload the page"})
        name = self.path.split("?", 1)[0].removeprefix("/api/")
        if name not in ROUTES:
            return self._json(404, {"ok": False, "error": f"unknown endpoint {name}"})
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return self._json(413, {"ok": False, "error": "request too large"})
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("expected a JSON object")
        except ValueError as e:
            return self._json(400, {"ok": False, "error": f"bad JSON: {e}"})
        try:
            data = ROUTES[name](body, self.server.ctx)
        except EXPECTED_ERRORS as e:
            msg = e.args[0] if isinstance(e, KeyError) and e.args else str(e)
            return self._json(200, {"ok": False, "error": str(msg)})
        except Exception as e:
            traceback.print_exc()
            return self._json(500, {"ok": False, "error": f"{type(e).__name__}: {e}"})
        return self._json(200, {"ok": True, "data": data})


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port: int, verbose: bool = False):
        super().__init__(("127.0.0.1", port), Handler)
        self.secret = secrets.token_urlsafe(24)
        self.verbose = verbose
        real = self.server_address[1]
        self.allowed_hosts = {f"127.0.0.1:{real}", f"localhost:{real}"}
        self.ctx = {"cwd": os.getcwd()}


def make_server(port: int = 8765, verbose: bool = False) -> Server:
    last = None
    for p in ([port + i for i in range(20)] if port else [0]):
        try:
            return Server(p, verbose)
        except OSError as e:
            last = e
    raise OSError(f"no free port near {port}: {last}")


def run(port: int = 8765, open_browser: bool = True, verbose: bool = False) -> None:
    srv = make_server(port, verbose)
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    print(f"webcraft ui running at {url}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        srv.server_close()
