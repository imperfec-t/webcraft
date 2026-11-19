"""DESIGN.md support: parse, check, convert, write, and a reference library.

DESIGN.md (introduced by Google Stitch) is a markdown design-system document:
optional YAML frontmatter with colors, typography, rounded, spacing and
components, followed by prose sections. This module:

- parses both the frontmatter form and the older prose-only form
- maps the palette onto webcraft's role tokens and checks contrast, including
  every component's declared background/text pair
- converts a DESIGN.md into tokens.css, and webcraft tokens into a DESIGN.md
- manages a local copy of VoltAgent/awesome-design-md (MIT), downloaded on
  request, as a searchable reference library
"""
from __future__ import annotations

import datetime as _dt
import io
import json
import os
import re
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import __version__, color, css

LIBRARY_REPO = "VoltAgent/awesome-design-md"
LIBRARY_ZIP = f"https://codeload.github.com/{LIBRARY_REPO}/zip/refs/heads/main"
LIBRARY_URL = f"https://github.com/{LIBRARY_REPO}"
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")

REFERENCE_NOTICE = (
    "<!-- From VoltAgent/awesome-design-md (MIT License), "
    "https://github.com/VoltAgent/awesome-design-md. This describes another company's visual language "
    "and is a reference only: do not use its name, logo, imagery or copy, and license or replace any "
    "proprietary fonts it names. -->"
)


# --- a small YAML subset (enough for DESIGN.md frontmatter) -----------------

def _scalar(v: str) -> Any:
    v = v.strip()
    if not v:
        return ""
    m = re.match(r"^(\"(?:[^\"\\]|\\.)*\"|'(?:[^']|'')*')\s*(?:#.*)?$", v)
    if m:  # quoted value, possibly followed by a comment
        v = m.group(1)
    if v[0] in "\"'" and v[-1:] == v[0] and len(v) >= 2:
        inner = v[1:-1]
        return inner.replace('\\"', '"') if v[0] == '"' else inner.replace("''", "'")
    v = re.split(r"\s+#", v, 1)[0].strip()
    if v.startswith("[") and v.endswith("]"):
        return [_scalar(x) for x in v[1:-1].split(",") if x.strip()]
    if v in ("true", "false"):
        return v == "true"
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d+\.\d+", v):
        return float(v)
    return v


def parse_yaml(text: str) -> Dict[str, Any]:
    """Parse nested mappings, scalars, flow/block lists and |/> block strings."""
    root: Dict[str, Any] = {}
    stack: List[Tuple[int, Any, Any, Any]] = [(-1, root, None, None)]  # (indent, container, parent, key)
    lines = text.replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(lines):
        raw = lines[i]
        i += 1
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        _, container, parent, key = stack[-1]
        if line.startswith("- ") or line == "-":
            item = _scalar(line[1:].strip())
            if isinstance(container, dict) and not container and parent is not None:
                container = []
                parent[key] = container
                stack[-1] = (stack[-1][0], container, parent, key)
            if isinstance(container, list):
                container.append(item)
            continue
        m = re.match(r"^(\"[^\"]*\"|'[^']*'|[^:#][^:]*?)\s*:(?:\s+(.*)|\s*)$", line)
        if not m or not isinstance(container, dict):
            continue
        k = _scalar(m.group(1))
        v = (m.group(2) or "").strip()
        if v in ("|", ">", "|-", ">-", "|+", ">+"):
            block = []
            while i < len(lines) and (not lines[i].strip() or len(lines[i]) - len(lines[i].lstrip(" ")) > indent):
                block.append(lines[i].strip())
                i += 1
            container[k] = ("\n" if v.startswith("|") else " ").join(block).strip()
        elif v == "":
            child: Dict[str, Any] = {}
            container[k] = child
            stack.append((indent, child, container, k))
        else:
            container[k] = _scalar(v)
    return root


def _yaml_quote(v: Any) -> str:
    s = str(v)
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return s
    if re.search(r"[:#{}\[\],&*!|>'\"%@`]|^\s|\s$|^$", s):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def dump_yaml(data: Dict[str, Any], indent: int = 0) -> str:
    out = []
    pad = "  " * indent
    for k, v in data.items():
        if isinstance(v, dict):
            out.append(f"{pad}{k}:")
            out.append(dump_yaml(v, indent + 1))
        else:
            out.append(f"{pad}{k}: {_yaml_quote(v)}")
    return "\n".join(x for x in out if x != "")


# --- parsing -----------------------------------------------------------------

def split_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    text = text.replace("\r\n", "\n")
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            return parse_yaml(text[4:end]), text[end + 4:].lstrip("-\n")
    return {}, text


def _kebab(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def sections(body: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    cur = None
    buf: List[str] = []
    for line in body.split("\n"):
        m = re.match(r"^##\s+(?:\d+\.\s*)?(.+?)\s*$", line)
        if m and not line.startswith("###"):
            if cur:
                out[cur] = "\n".join(buf).strip()
            cur, buf = m.group(1), []
        elif cur:
            buf.append(line)
    if cur:
        out[cur] = "\n".join(buf).strip()
    return out


def _prose_colors(secs: Dict[str, str]) -> Dict[str, Dict[str, str]]:
    """Colors from '- **Name** (`#hex`): role' lines in a color section."""
    text = next((v for k, v in secs.items() if re.search(r"colou?r", k, re.I)), "")
    found: Dict[str, Dict[str, str]] = {}
    for line in text.split("\n"):
        m = re.match(r"^\s*[-*]\s+\*\*(.+?)\*\*\s*\(?`?(#[0-9a-fA-F]{3,6})`?\)?\s*[:—–-]?\s*(.*)$", line)
        if not m:
            continue
        name = _kebab(m.group(1)) or f"color-{len(found) + 1}"
        if name in found:
            name = f"{name}-{len(found) + 1}"
        found[name] = {"value": m.group(2).lower(), "role": m.group(3).strip()}
    return found


def parse(text: str) -> Dict[str, Any]:
    fm, body = split_frontmatter(text)
    secs = sections(body)
    colors: Dict[str, str] = {}
    roles_text: Dict[str, str] = {}
    if isinstance(fm.get("colors"), dict):
        for k, v in fm["colors"].items():
            if isinstance(v, str) and color.try_parse(v):
                colors[str(k)] = v
    if not colors:
        for k, info in _prose_colors(secs).items():
            colors[k] = info["value"]
            roles_text[k] = info["role"]
    title = fm.get("name") or ""
    if not title:
        m = re.search(r"^#\s+(.+)$", body, re.M)
        title = m.group(1).strip() if m else ""
    desc = fm.get("description") or ""
    if not desc:
        first = next(iter(secs.values()), "")
        desc = re.sub(r"\s+", " ", first.split("\n\n")[0]).strip()
    return {
        "name": str(title),
        "description": str(desc),
        "has_frontmatter": bool(fm),
        "colors": colors,
        "color_roles": roles_text,
        "typography": fm.get("typography") if isinstance(fm.get("typography"), dict) else {},
        "rounded": fm.get("rounded") if isinstance(fm.get("rounded"), dict) else {},
        "spacing": fm.get("spacing") if isinstance(fm.get("spacing"), dict) else {},
        "components": fm.get("components") if isinstance(fm.get("components"), dict) else {},
        "sections": list(secs),
    }


# --- roles, contrast, tokens --------------------------------------------------

ROLE_RULES = [
    # role, preferred exact keys, keyword fallbacks, excluded words
    ("--bg", ["canvas", "background", "bg", "surface-0", "base", "page", "paper"],
     ["canvas", "background", "near-black", "page", "deepest"], ["inverse", "on-", "hover", "press", "overlay", "soft", "cream"]),
    ("--surface", ["surface-1", "surface", "card", "panel", "container", "canvas-soft", "surface-low"],
     ["surface", "card", "panel", "container", "elevated"], ["inverse", "on-", "hover", "press"]),
    ("--text", ["ink", "on-surface", "on-background", "text", "foreground", "fg", "on-canvas", "text-primary"],
     ["ink", "text", "foreground", "white", "primary text"], ["mute", "subtle", "secondary", "tertiary", "inverse", "on-primary", "disabled", "-2", "-3"]),
    ("--muted", ["ink-muted", "ink-mute", "ink-subtle", "muted", "text-secondary", "on-surface-variant", "ink-secondary", "secondary-text"],
     ["mute", "subtle", "secondary", "silver", "gray", "grey"], ["inverse", "on-primary", "hairline", "border", "surface", "bg", "background"]),
    ("--border", ["hairline", "border", "outline", "divider", "stroke", "rule"],
     ["hairline", "border", "outline", "divider", "stroke"], ["inverse", "focus", "input", "strong"]),
    ("--accent", ["primary", "accent", "brand", "cta", "action", "brand-primary"],
     ["primary", "accent", "brand", "cta"], ["on-", "hover", "press", "focus", "deep", "soft", "subdued", "bg", "disabled", "dark", "light", "text", "ink"]),
    ("--on-accent", ["on-primary", "on-accent", "on-brand", "primary-foreground", "on-cta"],
     ["on-primary", "on-accent", "on-brand"], []),
]


ROLE_TEXT_EXCLUDE = {"--bg": ("button", "cta", "badge", "promo", "link"), "--surface": ("button", "cta")}

# Prose palettes describe each color's job; score those descriptions.
PROSE_RULES = [
    ("--bg", [("page background", 6), ("page canvas", 6), ("body background", 6), ("dominant background", 6),
              ("deepest background", 5), ("background", 3), ("canvas", 3), ("primary surface", 3)]),
    ("--surface", [("card", 3), ("surface", 2), ("raised", 2), ("elevated", 2), ("container", 2), ("panel", 2)]),
    ("--text", [("primary text", 6), ("body text", 5), ("headline", 3), ("heading", 3), ("body", 2), ("text", 1)]),
    ("--muted", [("secondary text", 6), ("muted", 3), ("caption", 3), ("description", 2), ("secondary", 1)]),
    ("--border", [("border", 3), ("divider", 3), ("hairline", 3), ("outline", 2)]),
    ("--accent", [("primary cta", 6), ("brand accent", 5), ("cta", 3), ("accent", 3), ("primary action", 3),
                  ("button", 1), ("link", 1)]),
    ("--on-accent", [("button text", 4), ("text on", 3), ("on dark", 2)]),
]
PROSE_NEGATIVE = ("never as a ui color", "logo", "only in the brand", "opacity", "hover", "overlay",
                  "success", "error", "warning", "danger", "badge")


def _map_prose(colors: Dict[str, str], roles_text: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    out: Dict[str, str] = {}
    names: Dict[str, str] = {}
    used_values = set()
    for role, phrases in PROSE_RULES:
        best, best_score = None, 0
        for k, v in colors.items():
            c = color.try_parse(v)
            text = roles_text.get(k, "")
            if c is None or c[3] < 0.99 or v.lower() in used_values or any(n in text for n in PROSE_NEGATIVE):
                continue
            score = sum(w for p, w in phrases if p in text)
            if role == "--text" and "--bg" in out and color.contrast(c, color.parse(out["--bg"])) < 3:
                continue
            if score > best_score:
                best, best_score = k, score
        if best:
            out[role] = colors[best]
            names[role] = best
            used_values.add(colors[best].lower())
    return out, names


def map_roles(d: Dict[str, Any]) -> Dict[str, str]:
    colors = {k.lower(): v for k, v in d["colors"].items() if color.try_parse(v)}
    roles_text = {k.lower(): v.lower() for k, v in d.get("color_roles", {}).items()}
    if roles_text and not d.get("has_frontmatter"):
        out, names = _map_prose(colors, roles_text)
        return _finish_roles(d, out, names)
    out: Dict[str, str] = {}
    names: Dict[str, str] = {}
    used = set()
    for role, exact, words, exclude in ROLE_RULES:
        def ok(k):
            return k not in used and not any(x in k for x in exclude)
        cands: List[str] = [k for k in exact if k in colors and k not in used]
        cands += [k for k in colors if ok(k) and any(w in k for w in words)]
        bad_text = ROLE_TEXT_EXCLUDE.get(role, ())
        cands += [k for k in colors if ok(k) and any(w in roles_text.get(k, "") for w in words)
                  and not any(b in roles_text.get(k, "") for b in bad_text)]
        cands = list(dict.fromkeys(cands))
        if not cands:
            continue
        pick = cands[0]
        if role == "--text" and "--bg" in out and cands[0] not in exact:
            bg = color.parse(out["--bg"])
            pick = max(cands[:8], key=lambda k: color.contrast(color.parse(colors[k]), bg))
        out[role] = colors[pick]
        names[role] = pick
        used.add(pick)
    return _finish_roles(d, out, names)


def _finish_roles(d: Dict[str, Any], out: Dict[str, str], names: Dict[str, str]) -> Dict[str, str]:
    if "--surface" not in out and "--bg" in out:
        out["--surface"] = out["--bg"]
    if "--accent" in out and "--on-accent" not in out:
        acc = color.parse(out["--accent"])
        best = max(("#ffffff", "#000000"), key=lambda c: color.contrast(c, acc))
        out["--on-accent"] = best
        names["--on-accent"] = "(derived)"
    d["_role_names"] = names
    return out


def _resolve_ref(v: Any, d: Dict[str, Any]) -> Optional[str]:
    if not isinstance(v, str):
        return None
    m = re.fullmatch(r"\{colors\.([\w.-]+)\}", v.strip())
    if m:
        return d["colors"].get(m.group(1))
    return v if color.try_parse(v) else None


def check(d: Dict[str, Any]) -> Dict[str, Any]:
    roles = map_roles(d)
    role_results = css.check_token_pairs(roles)
    comp_results = []
    bg_default = roles.get("--bg")
    for name, spec in (d.get("components") or {}).items():
        # WCAG exempts disabled controls and placeholder text from contrast minimums.
        if not isinstance(spec, dict) or re.search(r"disabled|placeholder|decorative", str(name)):
            continue
        fg = _resolve_ref(spec.get("textColor"), d)
        bg = _resolve_ref(spec.get("backgroundColor"), d) or bg_default
        if not fg or not bg:
            continue
        fgc, bgc = color.try_parse(fg), color.try_parse(bg)
        if not fgc or not bgc:
            continue
        r = color.contrast(fgc, bgc)
        typo = spec.get("typography", "")
        large = bool(re.search(r"display|headline|hero|title-lg|h1|h2", str(typo)))
        need = 3.0 if large else 4.5
        comp_results.append({"component": name, "fg": color.to_hex(fgc), "bg": color.to_hex(bgc), "ratio": round(r, 2),
                             "minimum": need, "status": "pass" if r >= need else "fail"})
    bg = color.try_parse(roles.get("--bg", "")) if roles.get("--bg") else None
    theme = "unknown" if bg is None else ("dark" if color.luminance(bg) < 0.2 else "light")
    return {"roles": roles, "role_names": d.get("_role_names", {}), "theme": theme,
            "role_pairs": role_results, "components": comp_results,
            "fails": sum(r["status"] == "fail" for r in role_results + comp_results)}


def _px(v: Any) -> Optional[float]:
    m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)(px|rem)?\s*", str(v))
    if not m:
        return None
    n = float(m.group(1))
    return n * 16 if m.group(2) == "rem" else n


def _font(d: Dict[str, Any], words) -> Optional[str]:
    for k, spec in (d.get("typography") or {}).items():
        if isinstance(spec, dict) and any(w in k for w in words) and spec.get("fontFamily"):
            return str(spec["fontFamily"])
    return None


def _stack(family: Optional[str], fallback: str) -> str:
    if not family:
        return fallback
    if "," in family:
        return family
    fam = family.strip().strip("\"'")
    return f'"{fam}", {fallback}'


def to_tokens_css(d: Dict[str, Any], source_label: str = "") -> str:
    res = check(d)
    roles = res["roles"]
    lines = [f"/* tokens.css converted from DESIGN.md{(': ' + source_label) if source_label else ''} by webcraft {__version__}",
             f"   Theme: {res['theme']}. Role tokens map onto the design's own colors (kept below as --ds-*).",
             "   Fonts named here may be proprietary: license them or replace them with open alternatives. */", "", ":root {"]
    lines.append(f"  color-scheme: {'dark' if res['theme'] == 'dark' else 'light'};")
    lines.append("  /* roles (webcraft) */")
    for role in ("--bg", "--surface", "--text", "--muted", "--border", "--accent", "--on-accent"):
        if role in roles:
            src = res["role_names"].get(role, "")
            lines.append(f"  {role}: {roles[role]};" + (f"  /* {src} */" if src else ""))
    if "--accent" in roles and "--bg" in roles:
        acc = color.parse(roles["--accent"])
        bg = color.parse(roles["--bg"])
        L, C, H = color.rgb_to_oklch(acc)
        ink = color.solve_lightness(L, C, H, bg, 4.6, -1 if color.luminance(bg) > 0.2 else +1)
        lines.append(f"  --accent-ink: {color.to_hex(ink)};  /* accent adjusted to 4.5:1 on --bg */")
    lines.append("  /* design colors */")
    for k, v in d["colors"].items():
        lines.append(f"  --ds-{_kebab(k)}: {v};")
    display = _font(d, ("display", "headline", "heading", "h1", "title"))
    body = _font(d, ("body", "text", "paragraph"))
    mono = _font(d, ("mono", "code"))
    lines.append("  /* type */")
    body_fallback = 'system-ui, -apple-system, "Segoe UI", sans-serif'
    lines.append(f"  --font-display: {_stack(display, 'system-ui, sans-serif')};")
    lines.append(f"  --font-body: {_stack(body or display, body_fallback)};")
    if mono:
        lines.append(f"  --font-mono: {_stack(mono, 'ui-monospace, Menlo, monospace')};")
    for k, spec in (d.get("typography") or {}).items():
        if isinstance(spec, dict) and spec.get("fontSize"):
            lines.append(f"  --type-{_kebab(k)}: {spec['fontSize']};")
    rounded = d.get("rounded") or {}
    if rounded:
        lines.append("  /* shape */")
        for k, v in rounded.items():
            lines.append(f"  --radius-{_kebab(str(k))}: {v};")
        mid = rounded.get("md") or rounded.get("DEFAULT") or rounded.get("default")
        if mid:
            lines.append(f"  --radius: {mid};")
    spacing = d.get("spacing") or {}
    if spacing:
        lines.append("  /* space */")
        for k, v in spacing.items():
            lines.append(f"  --space-{_kebab(str(k))}: {v};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def from_tokens(t: Dict[str, Any], name: str = "my-site") -> str:
    """Write a DESIGN.md (Stitch format) from a webcraft tokens.generate() result."""
    primary = t["themes"][t["base"]]
    other = t["themes"]["dark" if t["base"] == "light" else "light"]

    def rem_px(v: str) -> str:
        m = re.findall(r"(\d+(?:\.\d+)?)rem", v)
        return f"{round(float(m[-1]) * 16)}px" if m else v

    fam = lambda s: s.split(",")[0].strip().strip('"')
    display, body = fam(t["fonts"]["--font-display"]), fam(t["fonts"]["--font-body"])
    steps = t["type"]
    typography = {
        "display-xl": {"fontFamily": display, "fontSize": rem_px(steps["--step-5"]), "fontWeight": 700, "lineHeight": 1.02, "letterSpacing": "-0.03em"},
        "display-lg": {"fontFamily": display, "fontSize": rem_px(steps["--step-4"]), "fontWeight": 700, "lineHeight": 1.04, "letterSpacing": "-0.03em"},
        "headline": {"fontFamily": display, "fontSize": rem_px(steps["--step-3"]), "fontWeight": 700, "lineHeight": 1.1, "letterSpacing": "-0.02em"},
        "title": {"fontFamily": display, "fontSize": rem_px(steps["--step-1"]), "fontWeight": 600, "lineHeight": 1.25, "letterSpacing": "-0.01em"},
        "body": {"fontFamily": body, "fontSize": rem_px(steps["--step-0"]), "fontWeight": 400, "lineHeight": 1.6, "letterSpacing": 0},
        "caption": {"fontFamily": body, "fontSize": rem_px(steps["--step--1"]), "fontWeight": 400, "lineHeight": 1.45, "letterSpacing": 0},
        "button": {"fontFamily": body, "fontSize": "15px", "fontWeight": 600, "lineHeight": 1.2, "letterSpacing": 0},
    }
    colors = {
        "primary": primary["--accent"], "on-primary": primary["--on-accent"], "primary-ink": primary["--accent-ink"],
        "canvas": primary["--bg"], "surface-1": primary["--surface"], "surface-2": primary["--surface-2"],
        "ink": primary["--text"], "ink-muted": primary["--muted"], "hairline": primary["--border"],
        f"{'dark' if t['base'] == 'light' else 'light'}-canvas": other["--bg"],
        f"{'dark' if t['base'] == 'light' else 'light'}-surface-1": other["--surface"],
        f"{'dark' if t['base'] == 'light' else 'light'}-ink": other["--text"],
        f"{'dark' if t['base'] == 'light' else 'light'}-primary": other["--accent"],
    }
    rounded = {k.replace("--radius-", "").replace("--radius", "md"): v for k, v in t["radius"].items()}
    spacing = {}
    for k, v in t["space"].items():
        if k.startswith("--space-"):
            spacing[k[8:]] = rem_px(v)
    spacing["section"] = rem_px(t["space"]["--section"])
    components = {
        "button-primary": {"backgroundColor": "{colors.primary}", "textColor": "{colors.on-primary}",
                           "typography": "{typography.button}", "rounded": "{rounded.pill}", "padding": "12px 24px"},
        "card": {"backgroundColor": "{colors.surface-1}", "textColor": "{colors.ink}", "rounded": "{rounded.md}", "padding": "24px"},
        "link": {"textColor": "{colors.primary-ink}", "typography": "{typography.body}"},
        "caption": {"textColor": "{colors.ink-muted}", "typography": "{typography.caption}"},
    }
    fm = {
        "version": "alpha",
        "name": name,
        "description": f"A {t['tone']} {t['base']} interface built on one {t['brand_hue']} accent ({primary['--accent']}) "
                       f"over tinted neutrals, {t['radius_personality']} corners, and {display} display type over {body} body. "
                       "Generated by webcraft; every text pair is contrast-checked.",
        "colors": colors, "typography": typography, "rounded": rounded, "spacing": spacing, "components": components,
    }
    contrast_lines = "\n".join(f"- `{r['pair']}` {r['ratio']}:1 ({r['status']})" for r in t["contrast"][t["base"]])
    body_md = f"""
# {name}

## Overview

{fm['description']} The page should read as calm and deliberate: one accent used on roughly a tenth of the surface, generous section spacing, and display type that does the visual work.

## Colors

- **Canvas** (`{colors['canvas']}`): page background, never pure white or black.
- **Surface** (`{colors['surface-1']}`, `{colors['surface-2']}`): cards, inputs, hover and second elevation.
- **Ink** (`{colors['ink']}`): body text and headings.
- **Ink muted** (`{colors['ink-muted']}`): captions and secondary text; passes 4.5:1 on canvas and surface.
- **Hairline** (`{colors['hairline']}`): dividers and input borders.
- **Primary** (`{colors['primary']}`): buttons, highlights, focus ring. Text on it uses **on-primary** (`{colors['on-primary']}`).
- **Primary ink** (`{colors['primary-ink']}`): links and accent-colored text on canvas.

Contrast on the {t['base']} theme:
{contrast_lines}

A {'dark' if t['base'] == 'light' else 'light'} theme is defined too (the `{'dark' if t['base'] == 'light' else 'light'}-*` colors): designed, not inverted, with surfaces rising in lightness.

## Typography

{t['pairing']} Body text at {typography['body']['fontSize']} with 1.6 line height and lines of 60 to 75 characters. Display sizes are fluid (`clamp()` in tokens.css); the pixel values above are the maximums. Display tracking tightens as size grows.

## Layout

Content width up to {t['space']['--container']}, side gutter `{t['space']['--gutter']}`, section padding `{t['space']['--section']}`. Space between sections is clearly larger than space inside them.

## Elevation & Depth

One soft shadow (`{primary['--shadow']}`) for raised cards; hairline borders do most of the separation.

## Shapes

{t['radius_personality'].capitalize()} corners: {', '.join(f'{k} {v}' for k, v in rounded.items())}. Hold one corner personality everywhere.

## Components

- **Primary button**: primary fill, on-primary label, pill radius, 12px 24px padding. One primary action per view.
- **Card**: surface fill, hairline border, md radius, 24px padding.
- **Link**: primary ink, underlined.

## Do's and Don'ts

- Do use the accent sparingly; if everything is accented, nothing is.
- Do keep two font families at most.
- Don't place muted text on the accent or on images without a scrim.
- Don't mix corner radii.
- Don't animate anything but transform and opacity; respect prefers-reduced-motion.
"""
    return "---\n" + dump_yaml(fm) + "\n---\n" + body_md.lstrip("\n")


# --- library -------------------------------------------------------------------

class LibraryMissing(Exception):
    pass


def cache_dir() -> Path:
    env = os.environ.get("WEBCRAFT_CACHE")
    if env:
        base = Path(env)
    elif os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        base = Path(os.environ["LOCALAPPDATA"]) / "webcraft"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "webcraft"
    return base / "design-md"


def library_status() -> Dict[str, Any]:
    meta = cache_dir() / "meta.json"
    if not meta.is_file():
        return {"synced": False, "path": str(cache_dir()), "source": LIBRARY_URL}
    info = json.loads(meta.read_text(encoding="utf-8"))
    info.update({"synced": True, "path": str(cache_dir())})
    return info


def _read_zip_bytes(source: Optional[str]) -> Tuple[bytes, str]:
    if source and Path(source).is_file():
        return Path(source).read_bytes(), str(source)
    if source and Path(source).is_dir():
        buf = io.BytesIO()
        root = Path(source)
        with zipfile.ZipFile(buf, "w") as z:
            for f in root.rglob("*"):
                if f.is_file() and ".git" not in f.parts:
                    z.write(f, "repo/" + f.relative_to(root).as_posix())
        return buf.getvalue(), str(source)
    from .source import USER_AGENT, _ssl_context
    req = urllib.request.Request(source or LIBRARY_ZIP, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60, context=_ssl_context()) as r:
        return r.read(40 * 1024 * 1024), source or LIBRARY_URL


def sync(source: Optional[str] = None) -> Dict[str, Any]:
    """Download (or import from a local zip/folder) the library into the cache."""
    data, label = _read_zip_bytes(source)
    z = zipfile.ZipFile(io.BytesIO(data))
    target = cache_dir()
    designs = target / "designs"
    staged = target.parent / (target.name + ".tmp")
    if staged.exists():
        _rmtree(staged)
    (staged / "designs").mkdir(parents=True)
    count = 0
    for info in z.infolist():
        parts = info.filename.split("/")
        if len(parts) == 4 and parts[1] == "design-md" and parts[3] == "DESIGN.md" and NAME_RE.match(parts[2]):
            out = staged / "designs" / parts[2]
            out.mkdir()
            (out / "DESIGN.md").write_bytes(z.read(info)[:2_000_000])
            count += 1
        elif len(parts) == 2 and parts[1] == "LICENSE":
            (staged / "LICENSE").write_bytes(z.read(info)[:100_000])
    if count == 0:
        _rmtree(staged)
        raise ValueError("no design-md/<name>/DESIGN.md files found in the download")
    commit = z.comment.decode("ascii", "ignore").strip() if z.comment else ""
    index = []
    for d in sorted((staged / "designs").iterdir()):
        try:
            p = parse((d / "DESIGN.md").read_text(encoding="utf-8", errors="replace"))
            chk = check(p)
        except Exception:
            continue
        index.append({"name": d.name, "title": p["name"], "description": p["description"][:400],
                      "theme": chk["theme"], "swatches": {k: v for k, v in chk["roles"].items()},
                      "fonts": [f for f in (_font(p, ("display", "headline", "heading")), _font(p, ("body",))) if f],
                      "frontmatter": p["has_frontmatter"], "fails": chk["fails"]})
    (staged / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    meta = {"source": label, "repo": LIBRARY_URL, "commit": commit, "count": count,
            "synced_at": _dt.datetime.now().isoformat(timespec="seconds"), "license": "MIT (VoltAgent)"}
    (staged / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    if target.exists():
        _rmtree(target)
    staged.rename(target)
    return meta


def _rmtree(p: Path) -> None:
    import shutil
    shutil.rmtree(p, ignore_errors=True)


def library_index() -> List[Dict[str, Any]]:
    f = cache_dir() / "index.json"
    if not f.is_file():
        raise LibraryMissing("the DESIGN.md library is not downloaded yet; run: webcraft design sync")
    return json.loads(f.read_text(encoding="utf-8"))


def search(query: str = "") -> List[Dict[str, Any]]:
    items = library_index()
    q = query.lower().strip()
    if not q:
        return items
    terms = q.split()
    themes = [t for t in terms if t in ("dark", "light")]
    words = [t for t in terms if t not in ("dark", "light")]
    return [i for i in items
            if all(i["theme"] == t for t in themes)
            and all(w in (i["name"] + " " + i["title"] + " " + i["description"]).lower() for w in words)]


def read(name_or_path: str) -> Tuple[str, str]:
    """Return (label, text) for a library name or a DESIGN.md path."""
    p = Path(name_or_path)
    if p.is_file():
        return p.name, p.read_text(encoding="utf-8", errors="replace")
    if not NAME_RE.match(name_or_path):
        raise KeyError(f"{name_or_path!r} is neither a file nor a library design name")
    f = cache_dir() / "designs" / name_or_path / "DESIGN.md"
    if not f.is_file():
        library_index()  # raises LibraryMissing if not synced
        close = [i["name"] for i in search(name_or_path.split(".")[0])][:5]
        raise KeyError(f"no design named {name_or_path!r}" + (f"; did you mean: {', '.join(close)}" if close else ""))
    return name_or_path, f.read_text(encoding="utf-8", errors="replace")


def with_notice(text: str) -> str:
    """Insert the reference notice after the frontmatter (frontmatter must stay first)."""
    if REFERENCE_NOTICE in text:
        return text
    t = text.replace("\r\n", "\n")
    if t.startswith("---\n"):
        end = t.find("\n---", 4)
        if end != -1:
            close = end + 4
            return t[:close] + "\n\n" + REFERENCE_NOTICE + "\n" + t[close:]
    return REFERENCE_NOTICE + "\n\n" + t


def use(name: str, project_dir: str = ".", tokens: bool = False, force: bool = False) -> List[str]:
    label, text = read(name)
    proj = Path(project_dir)
    proj.mkdir(parents=True, exist_ok=True)
    out = proj / "DESIGN.md"
    log = []
    if out.exists() and not force:
        raise FileExistsError(f"{out} already exists; pass --force to replace it")
    out.write_text(with_notice(text), encoding="utf-8")
    log.append(f"wrote {out}")
    if tokens:
        tf = proj / "tokens.css"
        if tf.exists() and not force:
            raise FileExistsError(f"{tf} already exists; pass --force to replace it")
        tf.write_text(to_tokens_css(parse(text), label), encoding="utf-8")
        log.append(f"wrote {tf}")
    return log


def render_check(label: str, d: Dict[str, Any], res: Dict[str, Any]) -> str:
    lines = [f"# DESIGN.md check: {label}", "",
             f"{d['name'] or label} · theme {res['theme']} · {len(d['colors'])} colors · "
             f"{'frontmatter' if d['has_frontmatter'] else 'prose only (colors read from the palette section)'}", ""]
    lines.append("Role mapping:")
    for role, val in res["roles"].items():
        lines.append(f"  {role:<12} {val}  <- {res['role_names'].get(role, '?')}")
    lines.append("")
    lines.append("Role pairs:")
    for r in res["role_pairs"]:
        lines.append(f"  {r['pair']:<24} {r['ratio']:>5}:1  {r['status']}")
    if res["components"]:
        lines.append("")
        lines.append("Components (declared background / text):")
        for r in res["components"]:
            lines.append(f"  {r['component']:<28} {r['fg']} on {r['bg']}  {r['ratio']:>5}:1  {r['status'] if r['status'] == 'pass' else 'FAIL'} (min {r['minimum']})")
    lines.append("")
    lines.append("All pairs pass." if not res["fails"] else f"{res['fails']} pair(s) below WCAG AA.")
    return "\n".join(lines)
