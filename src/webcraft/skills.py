"""Find, read and validate the bundled skills (Agent Skills / SKILL.md format)."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
REF_RE = re.compile(r"`((?:references|scripts|assets)/[\w./-]+)`")


def skills_root() -> Path:
    env = os.environ.get("WEBCRAFT_SKILLS_DIR")
    here = Path(__file__).resolve().parent
    for candidate in ([Path(env)] if env else []) + [here / "skills", here.parents[1] / "skills"]:
        if candidate.is_dir() and any((d / "SKILL.md").is_file() for d in candidate.iterdir() if d.is_dir()):
            return candidate
    raise FileNotFoundError("bundled skills not found; set WEBCRAFT_SKILLS_DIR to a folder of skills")


@dataclass
class Skill:
    name: str
    description: str
    path: Path
    body: str
    meta: Dict[str, str] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return (self.path / "SKILL.md").read_text(encoding="utf-8")

    def files(self) -> List[str]:
        """Supporting files relative to the skill folder (not SKILL.md)."""
        out = []
        for f in sorted(self.path.rglob("*")):
            if f.is_file() and f.name != "SKILL.md" and not f.name.startswith(".") and "__pycache__" not in f.parts:
                out.append(f.relative_to(self.path).as_posix())
        return out

    def read_file(self, rel: str) -> str:
        target = (self.path / rel).resolve()
        if self.path.resolve() not in target.parents:
            raise ValueError("path escapes the skill folder")
        if not target.is_file():
            raise FileNotFoundError(f"{self.name} has no file {rel}")
        return target.read_text(encoding="utf-8")


def parse_frontmatter(text: str):
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    if end == -1:
        return None, text
    fields: Dict[str, str] = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip().strip("\"'")
    body = text[end + 4:].lstrip("-").lstrip("\n")
    return fields, body


def load_dir(d: Path) -> Optional[Skill]:
    md = d / "SKILL.md"
    if not md.is_file():
        return None
    fields, body = parse_frontmatter(md.read_text(encoding="utf-8"))
    if not fields:
        return None
    return Skill(fields.get("name", d.name), fields.get("description", ""), d, body, fields)


def load_all(root: Optional[Path] = None) -> List[Skill]:
    root = root or skills_root()
    out = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        s = load_dir(d)
        if s:
            out.append(s)
    return out


def get(name: str, root: Optional[Path] = None) -> Skill:
    for s in load_all(root):
        if s.name == name:
            return s
    raise KeyError(f"no skill named {name!r}")


def validate_dir(skill_dir: Path) -> List[str]:
    """The checks from the original scripts/validate.py, plus a few more."""
    errors: List[str] = []
    md = skill_dir / "SKILL.md"
    if not md.is_file():
        return ["missing SKILL.md"]
    fields, body = parse_frontmatter(md.read_text(encoding="utf-8"))
    if fields is None:
        return ["SKILL.md must start with a --- frontmatter block"]
    name, desc = fields.get("name", ""), fields.get("description", "")
    if not name:
        errors.append("frontmatter is missing name")
    elif name != skill_dir.name:
        errors.append(f"name '{name}' does not match folder '{skill_dir.name}'")
    if name and (not NAME_RE.match(name) or len(name) > 64):
        errors.append("name must be kebab-case, at most 64 characters")
    if not desc:
        errors.append("frontmatter is missing description")
    elif len(desc) > 1024:
        errors.append(f"description is {len(desc)} characters (max 1024)")
    if "<" in desc or ">" in desc:
        errors.append("description must not contain angle brackets")
    lines = body.strip().splitlines()
    if not lines:
        errors.append("SKILL.md has no body")
    if len(lines) > 500:
        errors.append(f"body is {len(lines)} lines (keep under 500; move detail to references/)")
    for ref in sorted(set(REF_RE.findall(body))):
        if not (skill_dir / ref).exists():
            errors.append(f"mentions {ref} but that file does not exist")
    return errors


def validate(root: Optional[Path] = None) -> Dict[str, List[str]]:
    root = root or skills_root()
    return {d.name: validate_dir(d) for d in sorted(p for p in root.iterdir() if p.is_dir())}
