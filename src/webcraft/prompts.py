"""Prompt libraries: webcraft's built-in prompts plus a private personal library.

Built-in prompts live in prompts/*.md (MIT, shipped with webcraft). Personal
prompts are files the user saves themselves (for example prompts they bought
elsewhere); they are stored only in the local user-data folder and are never
bundled, uploaded or exported by webcraft unless the user asks for one.

Both use the same format: markdown with frontmatter (title, category, tags,
stack, motion, description) and a body that is the prompt itself, with
placeholders written as [UPPERCASE WORDS].
"""
from __future__ import annotations

import datetime as _dt
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .designmd import parse_yaml

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")
PLACEHOLDER_RE = re.compile(r"\[([A-Z][A-Z0-9 ,/&'()+.:-]{1,80})\]")
BUILTIN = "webcraft"
MINE = "mine"


def builtin_root() -> Path:
    env = os.environ.get("WEBCRAFT_PROMPTS_DIR")
    here = Path(__file__).resolve().parent
    for c in ([Path(env)] if env else []) + [here / "prompts", here.parents[1] / "prompts"]:
        if c.is_dir() and any(c.glob("*.md")):
            return c
    raise FileNotFoundError("built-in prompts not found; set WEBCRAFT_PROMPTS_DIR")


def data_dir() -> Path:
    env = os.environ.get("WEBCRAFT_DATA")
    if env:
        return Path(env)
    if os.name == "nt" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / "webcraft"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "webcraft"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "webcraft"


def mine_root() -> Path:
    return data_dir() / "prompts"


@dataclass
class Prompt:
    id: str                    # webcraft/<slug> or mine/<slug>
    library: str               # webcraft | mine
    slug: str
    title: str
    category: str
    description: str
    body: str
    tags: List[str] = field(default_factory=list)
    stack: str = ""
    motion: str = ""
    source: str = ""
    source_url: str = ""
    added: str = ""
    path: Optional[Path] = None

    @property
    def placeholders(self) -> List[str]:
        return list(dict.fromkeys(m.group(1) for m in PLACEHOLDER_RE.finditer(self.body)))

    def summary(self) -> dict:
        return {"id": self.id, "library": self.library, "title": self.title, "category": self.category,
                "description": self.description, "tags": self.tags, "stack": self.stack, "motion": self.motion,
                "source": self.source, "placeholders": len(self.placeholders)}

    def to_dict(self) -> dict:
        d = self.summary()
        d.update({"body": self.body, "placeholders": self.placeholders, "source_url": self.source_url,
                  "added": self.added, "slug": self.slug})
        return d


def _split(text: str):
    text = text.replace("\r\n", "\n")
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            return parse_yaml(text[4:end]), text[end + 4:].lstrip("-").lstrip("\n")
    return {}, text


def _tags(v) -> List[str]:
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str):
        return [t.strip() for t in v.split(",") if t.strip()]
    return []


def _load(path: Path, library: str) -> Optional[Prompt]:
    fm, body = _split(path.read_text(encoding="utf-8", errors="replace"))
    slug = path.stem
    if not SLUG_RE.match(slug):
        return None
    return Prompt(
        id=f"{library}/{slug}", library=library, slug=slug,
        title=str(fm.get("title") or slug.replace("-", " ").capitalize()),
        category=str(fm.get("category") or "Uncategorized"),
        description=str(fm.get("description") or body.strip().split("\n")[0][:160]),
        body=body.strip() + "\n", tags=_tags(fm.get("tags")), stack=str(fm.get("stack") or ""),
        motion=str(fm.get("motion") or ""), source=str(fm.get("source") or ("webcraft" if library == BUILTIN else "")),
        source_url=str(fm.get("source_url") or ""), added=str(fm.get("added") or ""), path=path)


def load_all(library: str = "all") -> List[Prompt]:
    out: List[Prompt] = []
    if library in ("all", BUILTIN):
        out += [p for p in (_load(f, BUILTIN) for f in sorted(builtin_root().glob("*.md"))) if p]
    if library in ("all", MINE) and mine_root().is_dir():
        out += [p for p in (_load(f, MINE) for f in sorted(mine_root().glob("*.md"))) if p]
    return out


def search(query: str = "", library: str = "all", category: str = "") -> List[Prompt]:
    terms = query.lower().split()
    res = []
    for p in load_all(library):
        if category and p.category.lower() != category.lower():
            continue
        hay = " ".join([p.title, p.category, p.description, " ".join(p.tags), p.stack, p.motion, p.source]).lower()
        if all(t in hay for t in terms):
            res.append(p)
    return res


def categories(library: str = "all") -> List[str]:
    return sorted({p.category for p in load_all(library)})


def get(pid: str) -> Prompt:
    lib, _, slug = pid.partition("/")
    if not slug:
        lib, slug = None, pid
    for p in load_all("all" if lib is None else lib):
        if p.slug == slug:
            return p
    raise KeyError(f"no prompt {pid!r}; list them with: webcraft prompts list")


def fill(body: str, values: Dict[str, str]) -> str:
    """Replace [PLACEHOLDER]s whose value is given and non-empty; leave the rest visible."""
    vals = {k.strip().upper(): v for k, v in values.items() if str(v).strip()}

    def sub(m):
        return vals.get(m.group(1).strip().upper(), m.group(0))

    return PLACEHOLDER_RE.sub(sub, body)


def slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:70] or "prompt"
    return s


def _q(v: str) -> str:
    return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def save(title: str, body: str, category: str = "Uncategorized", tags: Optional[List[str]] = None,
         description: str = "", source: str = "", source_url: str = "", stack: str = "", motion: str = "",
         slug: Optional[str] = None, overwrite: bool = False) -> Prompt:
    """Save a prompt to the personal library (local only)."""
    if not title.strip():
        raise ValueError("a prompt needs a title")
    if not body.strip():
        raise ValueError("a prompt needs text")
    if len(body) > 200_000:
        raise ValueError("prompt text is too long (200 KB max)")
    slug = slug or slugify(title)
    if not SLUG_RE.match(slug):
        raise ValueError(f"invalid prompt id {slug!r}")
    root = mine_root()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{slug}.md"
    if path.exists() and not overwrite:
        n = 2
        while (root / f"{slug}-{n}.md").exists():
            n += 1
        slug = f"{slug}-{n}"
        path = root / f"{slug}.md"
    tags = [t.strip() for t in (tags or []) if t.strip()]
    lines = ["---", f"title: {_q(title.strip())}", f"category: {_q(category.strip() or 'Uncategorized')}",
             "tags: [" + ", ".join(_q(t) for t in tags) + "]", f"description: {_q(description.strip())}",
             f"stack: {_q(stack.strip())}", f"motion: {_q(motion.strip())}", f"source: {_q(source.strip())}",
             f"source_url: {_q(source_url.strip())}", f"added: {_q(_dt.date.today().isoformat())}",
             "private: true", "---", "", body.strip(), ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    p = _load(path, MINE)
    assert p is not None
    return p


def delete(pid: str) -> Path:
    lib, _, slug = pid.partition("/")
    if lib != MINE or not SLUG_RE.match(slug):
        raise ValueError("only prompts in your own library (mine/...) can be deleted")
    path = mine_root() / f"{slug}.md"
    if not path.is_file():
        raise KeyError(f"no prompt {pid!r}")
    path.unlink()
    return path


def validate_builtin() -> Dict[str, List[str]]:
    """Check every built-in prompt has the metadata the UI and agents rely on."""
    results = {}
    for f in sorted(builtin_root().glob("*.md")):
        errors = []
        fm, body = _split(f.read_text(encoding="utf-8"))
        if not SLUG_RE.match(f.stem):
            errors.append("file name must be kebab-case")
        for key in ("title", "category", "description", "tags", "stack", "motion"):
            if not fm.get(key):
                errors.append(f"frontmatter is missing {key}")
        if fm.get("motion") and fm["motion"] not in ("none", "subtle", "medium", "high"):
            errors.append("motion must be none, subtle, medium or high")
        if len(body.strip().splitlines()) < 15:
            errors.append("prompt body is too short to be useful")
        if "prefers-reduced-motion" not in body and fm.get("motion") not in ("none",):
            errors.append("animated prompts must require prefers-reduced-motion support")
        if not PLACEHOLDER_RE.search(body):
            errors.append("no [PLACEHOLDER] for the user's brand or content")
        results[f.stem] = errors
    return results
