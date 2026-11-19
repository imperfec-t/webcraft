"""Generate a design-token set from one brand color.

Implements the rules in skills/design-tokens: role-based colors, neutrals
tinted 2 to 6% toward the accent hue, dark mode that is designed rather than
inverted, a fluid type scale, spacing, one corner personality, and contrast
checked for every role pair.
"""
from __future__ import annotations

import json
from typing import Dict, Optional

from . import color
from .css import check_token_pairs

TONES = {
    "corporate": {
        "display": '"Inter Tight", "Inter", system-ui, sans-serif',
        "body": '"Inter", system-ui, -apple-system, "Segoe UI", sans-serif',
        "google": ["Inter+Tight:wght@600;700", "Inter:wght@400;500;600"],
        "radius": "soft", "pairing": "One family in two widths: tight display, regular body.",
    },
    "playful": {
        "display": '"Bricolage Grotesque", system-ui, sans-serif',
        "body": '"DM Sans", system-ui, -apple-system, "Segoe UI", sans-serif',
        "google": ["Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800", "DM+Sans:wght@400;500;700"],
        "radius": "pill", "pairing": "Characterful grotesque display with a friendly geometric body.",
    },
    "editorial": {
        "display": '"Fraunces", Georgia, "Times New Roman", serif',
        "body": '"Source Sans 3", system-ui, -apple-system, "Segoe UI", sans-serif',
        "google": ["Fraunces:opsz,wght@9..144,500;9..144,700", "Source+Sans+3:wght@400;600"],
        "radius": "sharp", "pairing": "Serif display with sans body: contrast of structure.",
    },
    "technical": {
        "display": '"Space Grotesk", system-ui, sans-serif',
        "body": '"IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif',
        "mono": '"IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace',
        "google": ["Space+Grotesk:wght@500;700", "IBM+Plex+Sans:wght@400;500;600", "IBM+Plex+Mono:wght@400"],
        "radius": "sharp", "pairing": "Squared grotesque display, neutral humanist body, mono for data.",
    },
}

RADII = {
    "sharp": {"--radius-sm": "2px", "--radius": "4px", "--radius-lg": "8px", "--radius-pill": "999px"},
    "soft": {"--radius-sm": "8px", "--radius": "16px", "--radius-lg": "28px", "--radius-pill": "999px"},
    "pill": {"--radius-sm": "12px", "--radius": "20px", "--radius-lg": "32px", "--radius-pill": "999px"},
}

TYPE_SCALE = {
    "--step--1": "clamp(0.83rem, 0.8rem + 0.15vw, 0.9rem)",
    "--step-0": "clamp(1rem, 0.95rem + 0.25vw, 1.125rem)",
    "--step-1": "clamp(1.25rem, 1.1rem + 0.6vw, 1.6rem)",
    "--step-2": "clamp(1.6rem, 1.3rem + 1.3vw, 2.4rem)",
    "--step-3": "clamp(2rem, 1.5rem + 2.6vw, 3.6rem)",
    "--step-4": "clamp(2.5rem, 1.6rem + 4.6vw, 5.5rem)",
    "--step-5": "clamp(3rem, 1.5rem + 7vw, 7.5rem)",
}

TYPE_RHYTHM = {
    "--leading-body": "1.6",
    "--leading-display": "1.02",
    "--tracking-display": "-0.03em",
    "--measure": "68ch",
}

SPACING = {
    "--space-1": "0.25rem", "--space-2": "0.5rem", "--space-3": "0.75rem", "--space-4": "1rem",
    "--space-6": "1.5rem", "--space-8": "2rem", "--space-12": "3rem", "--space-16": "4rem",
    "--section": "clamp(4rem, 3rem + 6vw, 9rem)",
    "--gutter": "clamp(1rem, 0.5rem + 3vw, 3rem)",
    "--container": "76rem",
}

USAGE = {
    "--bg": "Page background",
    "--surface": "Cards, inputs, raised panels",
    "--surface-2": "Hover and second elevation",
    "--text": "Body text and headings",
    "--muted": "Secondary text, captions, placeholders",
    "--border": "Hairlines, dividers, input borders",
    "--accent": "Buttons, highlights, focus ring (about 10% of the surface)",
    "--accent-ink": "Links and accent-colored text on --bg",
    "--on-accent": "Text and icons placed on --accent",
}


def _theme(brand, dark: bool) -> Dict[str, str]:
    L, C, H = color.rgb_to_oklch(brand)
    # Neutral tint: a small chroma toward the brand hue. Pure greys look unrelated.
    tint = 0.0 if C < 0.02 else min(max(C * 0.06, 0.005), 0.014)
    if not dark:
        bg = color.oklch(0.982, tint * 0.8, H)
        surface = color.oklch(0.955, tint, H)
        surface2 = color.oklch(0.93, tint * 1.1, H)
        text = color.solve_lightness(0.22, tint * 1.5, H, surface, 12.0, -1)
        muted = color.solve_lightness(0.56, tint * 2, H, surface, 4.6, -1)
        accent = color.oklch(L, C, H)
        accent_ink = color.solve_lightness(L, C, H, bg, 4.6, -1)
        shadow = "0 1px 2px rgb(0 0 0 / .04), 0 8px 24px rgb(0 0 0 / .06)"
    else:
        bg = color.oklch(0.17, tint, H)
        surface = color.oklch(0.21, tint * 1.1, H)
        surface2 = color.oklch(0.25, tint * 1.2, H)
        text = color.solve_lightness(0.93, tint * 0.8, H, surface, 12.0, +1)
        muted = color.solve_lightness(0.68, tint * 1.5, H, surface, 4.6, +1)
        # Slightly less chroma so the accent does not glow, lifted until it reads as UI on --bg.
        accent = color.solve_lightness(max(L, 0.6), C * 0.88, H, bg, 3.2, +1)
        accent_ink = color.solve_lightness(max(L, 0.68), C * 0.85, H, bg, 4.6, +1)
        shadow = "0 1px 2px rgb(0 0 0 / .3), 0 8px 24px rgb(0 0 0 / .35)"
    border = color.mix(bg, text, 0.13)
    on_accent = _best_on(accent, text, dark)
    return {
        "--bg": color.to_hex(bg),
        "--surface": color.to_hex(surface),
        "--surface-2": color.to_hex(surface2),
        "--text": color.to_hex(text),
        "--muted": color.to_hex(muted),
        "--border": color.to_hex(border),
        "--accent": color.to_hex(accent),
        "--accent-ink": color.to_hex(accent_ink),
        "--on-accent": color.to_hex(on_accent),
        "--shadow": shadow,
    }


def _best_on(accent, text, dark: bool):
    light = color.parse("#ffffff")
    near_dark = text if not dark else color.oklch(0.18, 0.01, color.rgb_to_oklch(accent)[2])
    candidates = [light, near_dark, color.parse("#000000")]
    best = max(candidates[:2], key=lambda c: color.contrast(c, accent))
    if color.contrast(best, accent) >= 4.5:
        return best
    return max(candidates, key=lambda c: color.contrast(c, accent))


def generate(brand: str, base: str = "light", tone: str = "corporate", radius: Optional[str] = None) -> dict:
    """Build the token set. Returns a dict with light/dark color themes, type,
    spacing, radius, contrast results and notes."""
    if tone not in TONES:
        raise ValueError(f"tone must be one of: {', '.join(TONES)}")
    if base not in ("light", "dark"):
        raise ValueError("base must be light or dark")
    brand_rgba = color.parse(brand)
    radius = radius or TONES[tone]["radius"]
    if radius not in RADII:
        raise ValueError(f"radius must be one of: {', '.join(RADII)}")
    light = _theme(brand_rgba, dark=False)
    dark = _theme(brand_rgba, dark=True)
    t = TONES[tone]
    fonts = {"--font-display": t["display"], "--font-body": t["body"]}
    if "mono" in t:
        fonts["--font-mono"] = t["mono"]
    google = "https://fonts.googleapis.com/css2?" + "&".join(f"family={f}" for f in t["google"]) + "&display=swap"

    notes = []
    L, C, H = color.rgb_to_oklch(brand_rgba)
    if color.contrast(light["--accent"], light["--bg"]) < 3.0:
        notes.append("The brand color is light: on the light theme use it as a fill with --on-accent text, "
                     "not for thin borders, icons or text. Links use --accent-ink, which is darkened to pass.")
    if light["--accent-ink"] != light["--accent"]:
        notes.append("--accent-ink is a darker step of the brand so links pass 4.5:1 on --bg.")
    if C < 0.02:
        notes.append("The brand color is nearly neutral, so neutrals are left untinted. Consider a second, "
                     "saturated accent only if a distinct meaning needs it.")

    return {
        "brand": color.to_hex(brand_rgba),
        "brand_hue": color.describe_hue(H, C),
        "base": base,
        "tone": tone,
        "radius_personality": radius,
        "pairing": t["pairing"],
        "google_fonts_url": google,
        "themes": {"light": light, "dark": dark},
        "fonts": fonts,
        "type": dict(TYPE_SCALE, **TYPE_RHYTHM),
        "space": SPACING,
        "radius": RADII[radius],
        "contrast": {"light": check_token_pairs(light), "dark": check_token_pairs(dark)},
        "notes": notes,
    }


def _block(selector: str, groups, indent: str = "  ") -> str:
    lines = [f"{selector} {{"]
    for title, values in groups:
        if title:
            lines.append(f"{indent}/* {title} */")
        for k, v in values.items():
            lines.append(f"{indent}{k}: {v};")
    lines.append("}")
    return "\n".join(lines)


def render_css(t: dict, auto_dark: bool = True, base_styles: bool = False) -> str:
    primary, secondary = ("light", "dark") if t["base"] == "light" else ("dark", "light")
    colors_primary = dict(t["themes"][primary])
    colors_secondary = dict(t["themes"][secondary])
    header = [
        f"/* tokens.css, generated by webcraft tokens",
        f"   brand {t['brand']} ({t['brand_hue']}), tone {t['tone']}, base {t['base']}, "
        f"corners {t['radius_personality']}",
        f"   Fonts: {t['google_fonts_url']}",
        "   (preload the one or two files used above the fold)",
        "",
        "   Token        Used for",
    ]
    for k, v in USAGE.items():
        header.append(f"   {k:<13}{v}")
    header.append("*/")

    out = ["\n".join(header), ""]
    out.append(_block(":root", [
        (None, {"color-scheme": primary}),
        ("color", {k: v for k, v in colors_primary.items() if k != "--shadow"}),
        ("type", dict(t["fonts"], **t["type"])),
        ("space", t["space"]),
        ("shape", dict(t["radius"], **{"--shadow": colors_primary["--shadow"]})),
    ]))
    out.append("")
    alt = {"color-scheme": secondary}
    alt.update(colors_secondary)
    out.append(_block(f'[data-theme="{secondary}"]', [(None, alt)]))
    if auto_dark and primary == "light":
        out.append("")
        inner = _block(':root:not([data-theme="light"])', [(None, alt)], indent="    ")
        inner = "\n".join("  " + line for line in inner.splitlines())
        out.append("@media (prefers-color-scheme: dark) {\n" + inner + "\n}")
    if base_styles:
        out.append("")
        out.append(BASE_STYLES.strip())
    return "\n".join(out) + "\n"


BASE_STYLES = """
/* base: optional starter styles that consume the tokens */
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: var(--step-0) / var(--leading-body) var(--font-body);
  -webkit-font-smoothing: antialiased;
}
h1, h2, h3 { font-family: var(--font-display); line-height: var(--leading-display); letter-spacing: var(--tracking-display); }
h1 { font-size: var(--step-5); }
h2 { font-size: var(--step-3); }
h3 { font-size: var(--step-1); letter-spacing: -0.01em; }
p { max-width: var(--measure); }
a { color: var(--accent-ink); }
small, .muted { color: var(--muted); }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
.button {
  display: inline-flex; align-items: center; gap: var(--space-2);
  padding: var(--space-3) var(--space-6); border-radius: var(--radius-pill);
  background: var(--accent); color: var(--on-accent); text-decoration: none; font-weight: 600;
}
.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow); }
"""


def render_theme_json(t: dict) -> str:
    """A WordPress theme.json (version 3) carrying the same tokens."""
    light = t["themes"]["light"] if t["base"] == "light" else t["themes"]["dark"]
    names = {"--bg": "Background", "--surface": "Surface", "--surface-2": "Surface 2", "--text": "Text",
             "--muted": "Muted", "--border": "Border", "--accent": "Accent", "--accent-ink": "Accent ink",
             "--on-accent": "On accent"}
    palette = [{"slug": k[2:], "name": names[k], "color": light[k]} for k in names]
    sizes = [{"slug": k[2:].replace("--", "minus-"), "name": k[2:], "size": v}
             for k, v in TYPE_SCALE.items()]
    spacing = [{"slug": k[8:], "name": k[2:], "size": v} for k, v in SPACING.items() if k.startswith("--space-")]

    def family(stack, slug, name):
        return {"slug": slug, "name": name, "fontFamily": stack}

    families = [family(t["fonts"]["--font-display"], "display", "Display"),
                family(t["fonts"]["--font-body"], "body", "Body")]
    doc = {
        "$schema": "https://schemas.wp.org/trunk/theme.json",
        "version": 3,
        "settings": {
            "appearanceTools": True,
            "color": {"defaultPalette": False, "defaultGradients": False, "palette": palette},
            "typography": {"defaultFontSizes": False, "fluid": True, "fontFamilies": families, "fontSizes": sizes},
            "spacing": {"defaultSpacingSizes": False, "spacingSizes": spacing, "units": ["px", "rem", "%", "vw", "svh"]},
            "layout": {"contentSize": "44rem", "wideSize": SPACING["--container"]},
            "custom": {"radius": {k[2:]: v for k, v in t["radius"].items()},
                       "section": SPACING["--section"], "gutter": SPACING["--gutter"]},
        },
        "styles": {
            "color": {"background": "var(--wp--preset--color--bg)", "text": "var(--wp--preset--color--text)"},
            "typography": {"fontFamily": "var(--wp--preset--font-family--body)",
                           "fontSize": "var(--wp--preset--font-size--step-0)", "lineHeight": TYPE_RHYTHM["--leading-body"]},
            "elements": {
                "link": {"color": {"text": "var(--wp--preset--color--accent-ink)"}},
                "heading": {"typography": {"fontFamily": "var(--wp--preset--font-family--display)",
                                           "lineHeight": TYPE_RHYTHM["--leading-display"],
                                           "letterSpacing": TYPE_RHYTHM["--tracking-display"]}},
                "button": {"color": {"background": "var(--wp--preset--color--accent)",
                                     "text": "var(--wp--preset--color--on-accent)"},
                           "border": {"radius": t["radius"]["--radius-pill"]}},
            },
        },
    }
    return json.dumps(doc, indent=2) + "\n"


def render_dtcg(t: dict) -> str:
    """W3C Design Tokens Community Group format (for Figma Tokens, Style Dictionary)."""
    def colors(theme):
        return {k[2:]: {"$type": "color", "$value": v} for k, v in theme.items() if k != "--shadow"}

    doc = {
        "color": {"light": colors(t["themes"]["light"]), "dark": colors(t["themes"]["dark"])},
        "font": {k[7:]: {"$type": "fontFamily", "$value": v} for k, v in t["fonts"].items()},
        "size": {k[2:]: {"$type": "dimension", "$value": v} for k, v in TYPE_SCALE.items()},
        "space": {k[2:]: {"$type": "dimension", "$value": v} for k, v in SPACING.items()},
        "radius": {k[2:]: {"$type": "dimension", "$value": v} for k, v in t["radius"].items()},
    }
    return json.dumps(doc, indent=2) + "\n"


def render_report(t: dict) -> str:
    lines = [f"Brand {t['brand']} ({t['brand_hue']}), tone {t['tone']}, corners {t['radius_personality']}.",
             f"Pairing: {t['pairing']}", "", "Contrast:"]
    for theme, results in t["contrast"].items():
        for r in results:
            mark = {"pass": "pass", "warn": "below guideline", "fail": "FAIL"}.get(r["status"], r["status"])
            lines.append(f"  {theme:<6} {r['pair']:<24} {r['fg']} on {r['bg']}  {r['ratio']:>5}:1  {mark}")
    for n in t["notes"]:
        lines.append(f"Note: {n}")
    return "\n".join(lines)
