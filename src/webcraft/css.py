"""Minimal CSS reading: rules, declarations, custom properties and themes.

Not a full CSS parser. It is enough to read design-token blocks, find
font-face rules and collect values for audits.
"""
from __future__ import annotations

import re
from typing import Dict, Iterator, List, Optional, Tuple

from . import color

COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
VAR_RE = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*(?:\([^()]*\)[^()]*)*))?\)")


def strip_comments(css: str) -> str:
    return COMMENT_RE.sub("", css)


def iter_rules(css: str) -> Iterator[Tuple[Tuple[str, ...], str, str]]:
    """Yield (at-rule context, selector, declaration text) for each block."""
    css = strip_comments(css)
    stack: List[str] = []
    buf: List[str] = []
    quote = None
    for ch in css:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch == "{":
            prelude = "".join(buf)
            # The prelude is whatever follows the last declaration in this block.
            prelude = prelude.rsplit(";", 1)[-1].strip()
            stack.append(prelude)
            buf = []
        elif ch == "}":
            if stack:
                sel = stack.pop()
                body = "".join(buf)
                buf = []
                if body.strip():
                    yield (tuple(stack), sel, body)
        else:
            buf.append(ch)


def parse_decls(body: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    depth, cur = 0, []
    parts = []
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == ";" and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    for part in parts:
        if ":" not in part:
            continue
        prop, val = part.split(":", 1)
        prop = prop.strip()
        val = re.sub(r"\s*!important\s*$", "", val.strip())
        if prop:
            out[prop if prop.startswith("--") else prop.lower()] = val
    return out


def resolve(value: str, props: Dict[str, str], depth: int = 0) -> str:
    if depth > 12 or "var(" not in value:
        return value

    def sub(m):
        name, fallback = m.group(1), m.group(2)
        if name in props:
            return resolve(props[name], props, depth + 1)
        return resolve(fallback, props, depth + 1) if fallback else m.group(0)

    return resolve(VAR_RE.sub(sub, value), props, depth + 1)


ROOT_SELECTORS = {":root", "html", ":host", "body"}


def _is_dark_context(ctx: Tuple[str, ...]) -> bool:
    return any(re.search(r"prefers-color-scheme\s*:\s*dark", c) for c in ctx)


def themes(css: str) -> Dict[str, Dict[str, str]]:
    """Return {theme label: resolved custom properties}.

    The base theme is custom properties on :root/html outside any dark media
    query. Every other block that sets token-like custom properties on a root-ish
    selector ([data-theme], .dark, :root:not(...)) becomes a variant layered on
    top of the base. Variants with identical values are merged.
    """
    base: Dict[str, str] = {}
    variants: Dict[str, Dict[str, str]] = {}
    for ctx, sel, body in iter_rules(css):
        decls = {k: v for k, v in parse_decls(body).items() if k.startswith("--")}
        if not decls:
            continue
        sel_norm = re.sub(r"\s+", " ", sel.strip())
        dark_ctx = _is_dark_context(ctx)
        if sel_norm in ROOT_SELECTORS and not dark_ctx and not any(c.startswith("@media") for c in ctx):
            base.update(decls)
            continue
        rootish = any(t in sel_norm for t in (":root", "html", "[data-theme", "[data-mode", ".dark", ".light", "body"))
        if not rootish:
            continue
        label = sel_norm + (" (prefers dark)" if dark_ctx else "")
        variants.setdefault(label, {}).update(decls)

    out: Dict[str, Dict[str, str]] = {}
    if base:
        out[":root"] = {k: resolve(v, base) for k, v in base.items()}
    seen = []
    for label, decls in variants.items():
        merged = dict(base)
        merged.update(decls)
        resolved = {k: resolve(v, merged) for k, v in merged.items()}
        fingerprint = tuple(sorted((k, resolved[k]) for k in decls))
        if fingerprint in seen:
            continue
        seen.append(fingerprint)
        out[label] = resolved
    return out


# Role pairs from the design-tokens skill: (foreground, background, minimum, guideline)
ROLE_PAIRS = [
    ("--text", "--bg", 4.5, 7.0),
    ("--text", "--surface", 4.5, 7.0),
    ("--muted", "--bg", 4.5, 4.5),
    ("--muted", "--surface", 4.5, 4.5),
    ("--on-accent", "--accent", 4.5, 4.5),
    ("--accent-ink", "--bg", 4.5, 4.5),
    ("--accent", "--bg", 3.0, 3.0),
]

ADVISORY = {("--accent", "--bg")}

# Common alternative token names, mapped onto roles.
ALIASES = {
    "--bg": ["--background", "--color-bg", "--color-background", "--bg-color", "--wp--preset--color--bg",
             "--wp--preset--color--base"],
    "--surface": ["--card", "--color-surface", "--surface-1", "--wp--preset--color--surface"],
    "--text": ["--foreground", "--fg", "--color-text", "--text-color", "--wp--preset--color--text",
               "--wp--preset--color--contrast"],
    "--muted": ["--muted-foreground", "--text-muted", "--color-muted", "--wp--preset--color--muted"],
    "--accent": ["--primary", "--brand", "--color-accent", "--color-primary", "--wp--preset--color--accent"],
    "--on-accent": ["--primary-foreground", "--accent-foreground", "--on-primary", "--color-on-accent"],
}


def _lookup(props: Dict[str, str], role: str) -> Optional[str]:
    if role in props:
        return props[role]
    for alt in ALIASES.get(role, []):
        if alt in props:
            return props[alt]
    return None


def check_token_pairs(props: Dict[str, str]) -> List[dict]:
    """Check the standard role pairs. Returns a list of result dicts."""
    results = []
    for fg_name, bg_name, minimum, guideline in ROLE_PAIRS:
        fg_raw, bg_raw = _lookup(props, fg_name), _lookup(props, bg_name)
        if fg_raw is None or bg_raw is None:
            continue
        fg, bg = color.try_parse(fg_raw), color.try_parse(bg_raw)
        if fg is None or bg is None:
            results.append({"pair": f"{fg_name} / {bg_name}", "fg": fg_raw, "bg": bg_raw,
                            "ratio": None, "status": "unparsed", "minimum": minimum})
            continue
        r = color.contrast(fg, bg)
        status = "pass" if r >= guideline else ("warn" if r >= minimum else "fail")
        if status == "fail" and (fg_name, bg_name) in ADVISORY:
            # A light brand used as a button fill is fine when its label passes;
            # it only fails when used for thin lines, icons or text on --bg.
            status = "warn"
        results.append({"pair": f"{fg_name} / {bg_name}", "fg": color.to_hex(fg), "bg": color.to_hex(bg),
                        "ratio": round(r, 2), "status": status, "minimum": minimum, "guideline": guideline})
    return results


def check_tokens_css(css: str) -> Dict[str, List[dict]]:
    return {label: check_token_pairs(props) for label, props in themes(css).items()}


COLOR_TOKEN_RE = re.compile(
    r"#[0-9a-fA-F]{3,8}\b|(?:rgba?|hsla?|oklch|oklab)\([^()]*\)", re.I)


def color_values(css: str) -> List[str]:
    """All literal color values in declarations that are not custom properties."""
    out = []
    for _, sel, body in iter_rules(css):
        for prop, val in parse_decls(body).items():
            if prop.startswith("--"):
                continue
            out.extend(m.group(0).lower() for m in COLOR_TOKEN_RE.finditer(val))
    return out


def declarations(css: str, prop: str) -> List[Tuple[str, str]]:
    """(selector, value) for every declaration of `prop`."""
    out = []
    for _, sel, body in iter_rules(css):
        decls = parse_decls(body)
        if prop in decls:
            out.append((sel, decls[prop]))
    return out


def font_faces(css: str) -> List[Dict[str, str]]:
    return [parse_decls(body) for _, sel, body in iter_rules(css) if sel.strip().lower() == "@font-face"]
