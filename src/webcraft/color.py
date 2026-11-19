"""Color parsing, OKLCH conversion and WCAG contrast.

Pure standard library. Colors are carried as RGBA tuples of floats in 0..1
(sRGB, gamma-encoded). Supported CSS syntaxes: hex (3, 4, 6, 8 digits),
rgb()/rgba(), hsl()/hsla(), oklch(), oklab(), color-mix() in srgb/oklab/oklch,
and a set of common named colors.
"""
from __future__ import annotations

import math
import re
from typing import Optional, Tuple

RGBA = Tuple[float, float, float, float]

NAMED = {
    "white": "#ffffff", "black": "#000000", "transparent": "#00000000",
    "red": "#ff0000", "green": "#008000", "blue": "#0000ff", "yellow": "#ffff00",
    "orange": "#ffa500", "purple": "#800080", "gray": "#808080", "grey": "#808080",
    "silver": "#c0c0c0", "navy": "#000080", "teal": "#008080", "maroon": "#800000",
    "olive": "#808000", "lime": "#00ff00", "aqua": "#00ffff", "cyan": "#00ffff",
    "fuchsia": "#ff00ff", "magenta": "#ff00ff", "pink": "#ffc0cb", "coral": "#ff7f50",
    "tomato": "#ff6347", "gold": "#ffd700", "indigo": "#4b0082", "crimson": "#dc143c",
    "whitesmoke": "#f5f5f5", "ivory": "#fffff0", "beige": "#f5f5dc", "linen": "#faf0e6",
    "slategray": "#708090", "darkslategray": "#2f4f4f", "dimgray": "#696969",
    "lightgray": "#d3d3d3", "gainsboro": "#dcdcdc", "rebeccapurple": "#663399",
}

_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?"


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def _split_args(inner: str):
    """Split 'a b c / d' or 'a, b, c, d' into components and alpha."""
    inner = inner.strip()
    alpha = None
    if "/" in inner:
        inner, a = inner.rsplit("/", 1)
        alpha = a.strip()
    parts = [p for p in re.split(r"[\s,]+", inner.strip()) if p]
    if alpha is None and len(parts) == 4:
        alpha = parts.pop()
    return parts, alpha


def _num(tok: str, pct_scale: float = 1.0) -> float:
    tok = tok.strip().lower()
    if tok == "none":
        return 0.0
    if tok.endswith("%"):
        return float(tok[:-1]) / 100.0 * pct_scale
    for unit in ("deg", "turn", "rad", "grad"):
        if tok.endswith(unit):
            v = float(tok[: -len(unit)])
            return {"deg": v, "turn": v * 360, "rad": math.degrees(v), "grad": v * 0.9}[unit]
    return float(tok)


def _alpha(tok: Optional[str]) -> float:
    if tok is None:
        return 1.0
    return _clamp(_num(tok, 1.0))


def parse_hex(value: str) -> RGBA:
    v = value.strip().lstrip("#")
    if len(v) in (3, 4):
        v = "".join(c * 2 for c in v)
    if len(v) not in (6, 8) or not re.fullmatch(r"[0-9a-fA-F]+", v):
        raise ValueError(f"not a hex color: {value!r}")
    r, g, b = (int(v[i:i + 2], 16) / 255 for i in (0, 2, 4))
    a = int(v[6:8], 16) / 255 if len(v) == 8 else 1.0
    return (r, g, b, a)


def _hsl_to_rgb(h: float, s: float, l: float) -> Tuple[float, float, float]:
    h = (h % 360) / 360

    def hue(p, q, t):
        t %= 1
        if t < 1 / 6:
            return p + (q - p) * 6 * t
        if t < 1 / 2:
            return q
        if t < 2 / 3:
            return p + (q - p) * (2 / 3 - t) * 6
        return p

    if s == 0:
        return (l, l, l)
    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q
    return (hue(p, q, h + 1 / 3), hue(p, q, h), hue(p, q, h - 1 / 3))


def parse(value: str) -> RGBA:
    """Parse a CSS color string. Raises ValueError when unsupported."""
    s = value.strip().lower()
    if not s:
        raise ValueError("empty color")
    if s in NAMED:
        return parse_hex(NAMED[s])
    if s.startswith("#"):
        return parse_hex(s)
    m = re.fullmatch(r"([a-z-]+)\((.*)\)", s, re.S)
    if not m:
        if re.fullmatch(r"[0-9a-f]{3,8}", s):
            return parse_hex(s)
        raise ValueError(f"unsupported color: {value!r}")
    fn, inner = m.group(1), m.group(2)
    if fn == "color-mix":
        return _parse_color_mix(inner)
    parts, a = _split_args(inner)
    if len(parts) != 3:
        raise ValueError(f"unsupported color: {value!r}")
    if fn in ("rgb", "rgba"):
        rgb = [_num(p, 255.0) / 255.0 for p in parts]
        return (_clamp(rgb[0]), _clamp(rgb[1]), _clamp(rgb[2]), _alpha(a))
    if fn in ("hsl", "hsla"):
        h = _num(parts[0])
        sat = _num(parts[1], 1.0) if parts[1].endswith("%") else _num(parts[1]) / 100
        lig = _num(parts[2], 1.0) if parts[2].endswith("%") else _num(parts[2]) / 100
        r, g, b = _hsl_to_rgb(h, sat, lig)
        return (r, g, b, _alpha(a))
    if fn == "oklch":
        L = _num(parts[0], 1.0)
        C = _num(parts[1], 0.4)
        H = _num(parts[2])
        r, g, b = oklch_to_rgb(L, C, H)
        return (_clamp(r), _clamp(g), _clamp(b), _alpha(a))
    if fn == "oklab":
        L = _num(parts[0], 1.0)
        A = _num(parts[1], 0.4)
        B = _num(parts[2], 0.4)
        r, g, b = oklab_to_rgb(L, A, B)
        return (_clamp(r), _clamp(g), _clamp(b), _alpha(a))
    raise ValueError(f"unsupported color function: {fn}()")


def _parse_color_mix(inner: str) -> RGBA:
    # color-mix(in <space>, <color> [p%], <color> [p%])
    pieces = _top_level_split(inner, ",")
    if len(pieces) != 3:
        raise ValueError("color-mix needs a color space and two colors")
    space = pieces[0].strip().replace("in ", "").strip()

    def color_and_pct(chunk):
        chunk = chunk.strip()
        m = re.search(r"\s(" + _NUM + r")%\s*$", chunk)
        pct = None
        if m:
            pct = float(m.group(1)) / 100
            chunk = chunk[: m.start()].strip()
        else:
            m = re.match(r"^(" + _NUM + r")%\s+", chunk)
            if m:
                pct = float(m.group(1)) / 100
                chunk = chunk[m.end():].strip()
        return parse(chunk), pct

    c1, p1 = color_and_pct(pieces[1])
    c2, p2 = color_and_pct(pieces[2])
    if p1 is None and p2 is None:
        p1 = 0.5
    elif p1 is None:
        p1 = 1 - p2
    w2 = 1 - p1
    if space.startswith("srgb"):
        mixed = tuple(c1[i] * p1 + c2[i] * w2 for i in range(3))
        return (mixed[0], mixed[1], mixed[2], c1[3] * p1 + c2[3] * w2)
    return mix(c1, c2, w2)


def _top_level_split(text: str, sep: str):
    out, depth, buf = [], 0, []
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == sep and depth == 0:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf))
    return out


def try_parse(value: str) -> Optional[RGBA]:
    try:
        return parse(value)
    except (ValueError, ZeroDivisionError):
        return None


def to_hex(c) -> str:
    r, g, b = (int(round(_clamp(x) * 255)) for x in c[:3])
    out = f"#{r:02x}{g:02x}{b:02x}"
    if len(c) == 4 and c[3] < 0.999:
        out += f"{int(round(_clamp(c[3]) * 255)):02x}"
    return out


# --- OKLab / OKLCH (Bjorn Ottosson) -----------------------------------------

def _to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _to_gamma(c: float) -> float:
    if c <= 0.0031308:
        return 12.92 * c
    return 1.055 * (abs(c) ** (1 / 2.4)) * (1 if c >= 0 else -1) - 0.055


def rgb_to_oklab(c) -> Tuple[float, float, float]:
    r, g, b = (_to_linear(x) for x in c[:3])
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    return (
        0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
        1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
        0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
    )


def oklab_to_rgb(L: float, A: float, B: float) -> Tuple[float, float, float]:
    l = (L + 0.3963377774 * A + 0.2158037573 * B) ** 3
    m = (L - 0.1055613458 * A - 0.0638541728 * B) ** 3
    s = (L - 0.0894841775 * A - 1.2914855480 * B) ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    b = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return (_to_gamma(r), _to_gamma(g), _to_gamma(b))


def rgb_to_oklch(c) -> Tuple[float, float, float]:
    L, A, B = rgb_to_oklab(c)
    C = math.hypot(A, B)
    H = math.degrees(math.atan2(B, A)) % 360
    return (L, C, H)


def oklch_to_rgb(L: float, C: float, H: float) -> Tuple[float, float, float]:
    h = math.radians(H)
    return oklab_to_rgb(L, C * math.cos(h), C * math.sin(h))


def in_gamut(rgb, eps: float = 1e-4) -> bool:
    return all(-eps <= x <= 1 + eps for x in rgb[:3])


def oklch(L: float, C: float, H: float) -> RGBA:
    """Build an sRGB color from OKLCH, reducing chroma until it fits the gamut."""
    L = _clamp(L)
    lo, hi = 0.0, max(C, 0.0)
    rgb = oklch_to_rgb(L, hi, H)
    if not in_gamut(rgb):
        for _ in range(24):
            mid = (lo + hi) / 2
            if in_gamut(oklch_to_rgb(L, mid, H)):
                lo = mid
            else:
                hi = mid
        rgb = oklch_to_rgb(L, lo, H)
    r, g, b = (_clamp(x) for x in rgb)
    return (r, g, b, 1.0)


def mix(a, b, t: float) -> RGBA:
    """Mix in OKLab: t=0 gives a, t=1 gives b."""
    la, lb = rgb_to_oklab(a), rgb_to_oklab(b)
    L, A, B = (la[i] + (lb[i] - la[i]) * t for i in range(3))
    r, g, bb = oklab_to_rgb(L, A, B)
    alpha = (a[3] if len(a) > 3 else 1.0) * (1 - t) + (b[3] if len(b) > 3 else 1.0) * t
    return (_clamp(r), _clamp(g), _clamp(bb), alpha)


# --- WCAG 2.x contrast ------------------------------------------------------

def composite(fg, bg) -> RGBA:
    a = fg[3] if len(fg) > 3 else 1.0
    if a >= 0.999:
        return fg
    return tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3)) + (1.0,)


def luminance(c) -> float:
    r, g, b = (_to_linear(x) for x in c[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg, bg) -> float:
    """Contrast ratio of fg over bg. Accepts strings or RGBA tuples."""
    if isinstance(fg, str):
        fg = parse(fg)
    if isinstance(bg, str):
        bg = parse(bg)
    fg = composite(fg, bg)
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def levels(r: float) -> dict:
    return {
        "AA normal text (4.5:1)": r >= 4.5,
        "AA large text / UI (3:1)": r >= 3.0,
        "AAA normal text (7:1)": r >= 7.0,
    }


def solve_lightness(L: float, C: float, H: float, against, target: float, direction: int) -> RGBA:
    """Move OKLCH lightness in `direction` (-1 darker, +1 lighter) until
    contrast against `against` reaches `target`. Returns the first passing color,
    or the extreme if none passes."""
    color = oklch(L, C, H)
    if contrast(color, against) >= target:
        return color
    step = 0.005
    while 0.0 <= L <= 1.0:
        L += step * direction
        color = oklch(L, C, H)
        if contrast(color, against) >= target:
            return color
    return oklch(_clamp(L), C, H)


def describe_hue(H: float, C: float) -> str:
    if C < 0.03:
        return "neutral"
    # Bucket edges in OKLCH hue degrees (red ~29, orange ~70, yellow ~110, green ~142,
    # cyan ~195, blue ~264, magenta ~328).
    names = [(15, "rose"), (36, "red"), (55, "red-orange"), (80, "orange"), (100, "amber"),
             (122, "yellow"), (150, "green"), (180, "emerald"), (205, "teal"), (240, "cyan"),
             (285, "blue"), (300, "indigo"), (320, "violet"), (345, "magenta")]
    for limit, name in names:
        if H < limit:
            return name
    return "rose"
