"""Install the skills into coding agents, and print MCP configuration.

Agents that read the open Agent Skills format (a folder per skill holding
SKILL.md) get the folders copied as-is. Agents with their own rule format
(Cursor, Windsurf) get converted rule files. Anything else that reads an
AGENTS.md-style file gets a managed index block pointing at the skill files,
which keeps the progressive-disclosure behavior: descriptions always loaded,
bodies read on demand.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from . import __version__
from .skills import Skill, load_all

MARKER = ".webcraft"
BLOCK_START = "<!-- webcraft:start -->"
BLOCK_END = "<!-- webcraft:end -->"
RULE_PREFIX = "webcraft-"


@dataclass
class Target:
    key: str
    label: str
    kind: str                       # skills | cursor | windsurf | agents-md
    user: Optional[str] = None      # user-scope folder
    project: Optional[str] = None   # project-scope folder or file, relative to the project
    note: str = ""


def _home(*parts: str) -> str:
    return str(Path.home().joinpath(*parts))


TARGETS = {
    "claude": Target("claude", "Claude Code", "skills", "~/.claude/skills", ".claude/skills"),
    "codex": Target("codex", "OpenAI Codex", "skills", "~/.agents/skills", ".agents/skills",
                    "Older Codex builds read ~/.codex/skills; pass --dest there if /skills shows nothing."),
    "gemini": Target("gemini", "Gemini CLI", "skills", "~/.gemini/skills", ".gemini/skills",
                     "If skills are still experimental in your version, enable them in settings."),
    "copilot": Target("copilot", "GitHub Copilot (CLI, cloud agent, VS Code agent mode)", "skills",
                      "~/.copilot/skills", ".github/skills"),
    "agents": Target("agents", "Any client reading .agents/skills (OpenCode, Amp, Goose and others)", "skills",
                     "~/.agents/skills", ".agents/skills"),
    "cursor": Target("cursor", "Cursor (as Agent Requested rules)", "cursor", None, ".cursor/rules"),
    "windsurf": Target("windsurf", "Windsurf (as model-decision rules)", "windsurf", None, ".windsurf/rules"),
    "agents-md": Target("agents-md", "AGENTS.md index (Aider, Zed, Jules, Warp, any agent that reads AGENTS.md)",
                        "agents-md", None, "AGENTS.md"),
}


def expand(p: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(p)))


def destination(t: Target, scope: str, project_dir: Path, dest: Optional[str]) -> Path:
    if dest:
        return expand(dest)
    if t.kind == "skills" and scope == "user":
        return expand(t.user)
    return project_dir / t.project


def _select(only: Optional[List[str]]) -> List[Skill]:
    skills = load_all()
    if not only:
        return skills
    names = {s.name for s in skills}
    unknown = [n for n in only if n not in names]
    if unknown:
        raise KeyError(f"unknown skill(s): {', '.join(unknown)}. Available: {', '.join(sorted(names))}")
    return [s for s in skills if s.name in only]


def _copy_skill(skill: Skill, dest_dir: Path, force: bool, dry: bool, log: List[str]) -> bool:
    target = dest_dir / skill.name
    if target.exists():
        if not (target / MARKER).exists() and not force:
            log.append(f"skip   {target} (exists and was not installed by webcraft; use --force)")
            return False
        if not dry:
            shutil.rmtree(target)
    if not dry:
        shutil.copytree(skill.path, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", MARKER))
        (target / MARKER).write_text(f"installed by webcraft {__version__}\n", encoding="utf-8")
    return True


def _summary(names: List[str], where: Path, dry: bool, what: str = "skill(s)") -> str:
    verb = "would install" if dry else "installed"
    return f"{verb} {len(names)} {what} -> {where}" + (f"  ({', '.join(names)})" if len(names) <= 3 else "")


def _yaml_scalar(value: str) -> str:
    if re.search(r":\s|\s#|^[\s\"'\[\]{}>|*&!%@`,?-]", value):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


def _rewrite_refs(body: str, base: str) -> str:
    return re.sub(r"(?<![\w/.])((?:references|scripts|assets)/[\w./-]+)", rf"{base}/\1", body)


def _rule_file(skill: Skill, kind: str, support_base: str) -> str:
    desc = _yaml_scalar(skill.description.replace("\n", " "))
    body = _rewrite_refs(skill.body, support_base) if skill.files() else skill.body
    if kind == "cursor":
        head = f"---\ndescription: {desc}\nglobs:\nalwaysApply: false\n---\n"
    else:  # windsurf
        head = f"---\ntrigger: model_decision\ndescription: {desc}\n---\n"
    return head + "\n" + body.strip() + "\n"


def _index_block(skills: List[Skill], base: str) -> str:
    lines = [BLOCK_START, "## Website design skills (webcraft)", "",
             "Before any website planning, design, build or QA task, check this list. When a skill matches the task, "
             "read its SKILL.md in full first and follow it; read files it references only when you need them.", "",
             "| Skill | Use when | Instructions |", "|---|---|---|"]
    for s in skills:
        use = re.sub(r"\s+", " ", s.description).replace("|", "/")
        lines.append(f"| {s.name} | {use} | `{base}/{s.name}/SKILL.md` |")
    lines += ["", "If the project has a `DESIGN.md`, read it before writing any UI and follow it.", "",
              "Deterministic helpers (if installed): `webcraft tokens`, `webcraft contrast`, `webcraft audit`, "
              "`webcraft detect`, `webcraft teardown`, `webcraft design`. Run `webcraft --help`.", BLOCK_END]
    return "\n".join(lines) + "\n"


def write_block(path: Path, block: str, dry: bool) -> str:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if BLOCK_START in existing and BLOCK_END in existing:
        new = re.sub(re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_END) + r"\n?", lambda m: block, existing, flags=re.S)
        action = "update"
    else:
        new = (existing.rstrip() + "\n\n" if existing.strip() else "") + block
        action = "append to" if existing else "create"
    if not dry:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new, encoding="utf-8")
    return f"{'would ' + action if dry else action} {path}"


def install(agent: str, scope: str = "user", project_dir: str = ".", dest: Optional[str] = None,
            only: Optional[List[str]] = None, force: bool = False, dry_run: bool = False,
            index_file: Optional[str] = None) -> List[str]:
    if agent not in TARGETS:
        raise KeyError(f"unknown agent {agent!r}. Choose from: {', '.join(TARGETS)}")
    t = TARGETS[agent]
    proj = Path(project_dir).resolve()
    skills = _select(only)
    log: List[str] = []
    if t.kind != "skills" and scope == "user" and not dest:
        log.append(f"note   {t.label} has no user-scope skills folder; installing into the project {proj}")
    if t.kind == "skills":
        out = destination(t, scope, proj, dest)
        if not dry_run:
            out.mkdir(parents=True, exist_ok=True)
        done = [s.name for s in skills if _copy_skill(s, out, force, dry_run, log)]
        log.append(_summary(done, out, dry_run))
    elif t.kind in ("cursor", "windsurf"):
        out = destination(t, "project", proj, dest)
        support = proj / ".webcraft" / "skills"
        support_rel = ".webcraft/skills"
        if not dry_run:
            out.mkdir(parents=True, exist_ok=True)
        ext = ".mdc" if t.kind == "cursor" else ".md"
        for s in skills:
            if s.files():
                if not dry_run:
                    support.mkdir(parents=True, exist_ok=True)
                _copy_skill(s, support, True, dry_run, log)
            f = out / f"{RULE_PREFIX}{s.name}{ext}"
            if not dry_run:
                f.write_text(_rule_file(s, t.kind, f"{support_rel}/{s.name}"), encoding="utf-8")
        log.append(_summary([s.name for s in skills], out, dry_run, f"rule(s) {RULE_PREFIX}*{ext}"))
        if any(s.files() for s in skills):
            log.append(f"{'would copy' if dry_run else 'copied'} supporting files -> {support}")
    elif t.kind == "agents-md":
        skills_dir = proj / ".agents" / "skills"
        if not dry_run:
            skills_dir.mkdir(parents=True, exist_ok=True)
        done = [s.name for s in skills if _copy_skill(s, skills_dir, force, dry_run, log)]
        log.append(_summary(done, skills_dir, dry_run))
        index = Path(index_file) if index_file else proj / (dest or t.project)
        if not index.is_absolute():
            index = proj / index
        log.append(write_block(index, _index_block(skills, ".agents/skills"), dry_run))
    if t.note:
        log.append(f"note   {t.note}")
    return log


def uninstall(agent: str, scope: str = "user", project_dir: str = ".", dest: Optional[str] = None,
              dry_run: bool = False, index_file: Optional[str] = None) -> List[str]:
    t = TARGETS[agent]
    proj = Path(project_dir).resolve()
    log: List[str] = []

    def remove_marked(folder: Path):
        if not folder.is_dir():
            return
        for d in sorted(folder.iterdir()):
            if d.is_dir() and (d / MARKER).exists():
                if not dry_run:
                    shutil.rmtree(d)
                log.append(f"{'would remove' if dry_run else 'remove'} {d}")

    if t.kind == "skills":
        remove_marked(destination(t, scope, proj, dest))
    elif t.kind in ("cursor", "windsurf"):
        out = destination(t, "project", proj, dest)
        if out.is_dir():
            for f in sorted(out.glob(f"{RULE_PREFIX}*")):
                if not dry_run:
                    f.unlink()
                log.append(f"{'would remove' if dry_run else 'remove'} {f}")
        remove_marked(proj / ".webcraft" / "skills")
    else:
        remove_marked(proj / ".agents" / "skills")
        index = Path(index_file) if index_file else proj / (dest or t.project)
        if not index.is_absolute():
            index = proj / index
        if index.exists():
            text = index.read_text(encoding="utf-8")
            if BLOCK_START in text:
                new = re.sub(r"\n*" + re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_END) + r"\n?", "\n", text, flags=re.S)
                if not dry_run:
                    if new.strip():
                        index.write_text(new.strip() + "\n", encoding="utf-8")
                    else:
                        index.unlink()
                log.append(f"{'would remove block from' if dry_run else 'remove block from'} {index}")
    if not log:
        log.append("nothing to remove")
    return log


def status(project_dir: str = ".") -> List[dict]:
    proj = Path(project_dir).resolve()
    names = {s.name for s in load_all()}
    rows = []
    for t in TARGETS.values():
        places = []
        if t.kind == "skills":
            places = [("user", expand(t.user)), ("project", proj / t.project)]
        elif t.kind in ("cursor", "windsurf"):
            places = [("project", proj / t.project)]
        else:
            places = [("project", proj / ".agents" / "skills")]
        for scope, p in places:
            if t.kind in ("cursor", "windsurf"):
                count = len([f for f in p.glob(f"{RULE_PREFIX}*")]) if p.is_dir() else 0
            else:
                count = len([d for d in p.iterdir() if d.is_dir() and d.name in names and (d / MARKER).exists()]) if p.is_dir() else 0
            rows.append({"agent": t.key, "label": t.label, "scope": scope, "path": str(p), "installed": count,
                         "of": len(names)})
    return rows


# --- MCP configuration snippets -------------------------------------------

def server_command() -> List[str]:
    exe = shutil.which("webcraft")
    if exe:
        return ["webcraft", "mcp"]
    return [sys.executable, "-m", "webcraft", "mcp"]


def mcp_config(client: str) -> str:
    cmd = server_command()
    command, args = cmd[0], cmd[1:]
    std = json.dumps({"mcpServers": {"webcraft": {"command": command, "args": args}}}, indent=2)
    shell = " ".join(f'"{c}"' if " " in c else c for c in cmd)
    if client == "claude-code":
        return (f"Run:\n  claude mcp add webcraft --scope user -- {shell}\n\n"
                f"Or add to .mcp.json in a project:\n{std}")
    if client == "claude-desktop":
        where = (r"%APPDATA%\Claude\claude_desktop_config.json" if os.name == "nt"
                 else "~/Library/Application Support/Claude/claude_desktop_config.json")
        return f"Add to {where}:\n{std}"
    if client == "codex":
        toml_args = ", ".join(f"'{a}'" for a in args)
        return (f"Run:\n  codex mcp add webcraft -- {shell}\n\nOr add to ~/.codex/config.toml:\n"
                f"[mcp_servers.webcraft]\ncommand = '{command}'\nargs = [{toml_args}]")
    if client == "cursor":
        return f"Add to .cursor/mcp.json (project) or ~/.cursor/mcp.json (global):\n{std}"
    if client == "vscode":
        vs = json.dumps({"servers": {"webcraft": {"type": "stdio", "command": command, "args": args}}}, indent=2)
        return f"Add to .vscode/mcp.json (GitHub Copilot agent mode):\n{vs}"
    if client == "gemini":
        return f"Add to ~/.gemini/settings.json (or .gemini/settings.json in a project):\n{std}"
    if client == "windsurf":
        return f"Add to ~/.codeium/windsurf/mcp_config.json:\n{std}"
    if client == "generic":
        return f"Any MCP client: stdio transport, command and args:\n{std}"
    raise KeyError("client must be one of: " + ", ".join(MCP_CLIENTS))


MCP_CLIENTS = ["claude-code", "claude-desktop", "codex", "cursor", "vscode", "gemini", "windsurf", "generic"]
