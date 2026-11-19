#!/usr/bin/env python3
"""WCAG 2.x contrast checker.

Usage:
  contrast.py "#1b1b1f" "#f6f4ef"       check one foreground/background pair
  contrast.py --tokens tokens.css        check standard role pairs in a CSS file

Exit code is 1 if any checked pair fails AA for normal text (4.5:1).
"""
import re
import sys

ROLE_PAIRS = [
    ("--text", "--bg"),
    ("--text", "--surface"),
    ("--muted", "--bg"),
    ("--muted", "--surface"),
    ("--on-accent", "--accent"),
    ("--accent", "--bg"),
]


def parse_hex(value):
    v = value.strip().lstrip("#")
    if len(v) in (3, 4):
        v = "".join(c * 2 for c in v)
    if len(v) not in (6, 8) or not re.fullmatch(r"[0-9a-fA-F]+", v):
        raise ValueError(f"not a hex color: {value!r}")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def luminance(rgb):
    def channel(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg, bg):
    a, b = luminance(parse_hex(fg)), luminance(parse_hex(bg))
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def levels(r):
    return {
        "AA normal": r >= 4.5,
        "AA large": r >= 3.0,
        "AAA normal": r >= 7.0,
    }


def report(label, fg, bg):
    r = ratio(fg, bg)
    marks = "  ".join(f"{k}: {'pass' if ok else 'FAIL'}" for k, ok in levels(r).items())
    print(f"{label:<28} {fg} on {bg}  {r:5.2f}:1  {marks}")
    return r >= 4.5


def read_tokens(path):
    text = open(path, encoding="utf-8").read()
    # Only the first :root block, so theme overrides do not shadow the base.
    m = re.search(r":root\s*\{(.*?)\}", text, re.S)
    block = m.group(1) if m else text
    return dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\b", block))


def main(argv):
    if len(argv) == 3 and argv[1] == "--tokens":
        tokens = read_tokens(argv[2])
        ok, checked = True, 0
        for fg, bg in ROLE_PAIRS:
            if fg in tokens and bg in tokens:
                checked += 1
                ok = report(f"{fg} / {bg}", tokens[fg], tokens[bg]) and ok
        if not checked:
            print("No role pairs found. Expected hex values for tokens such as --text and --bg in :root.")
            return 2
        return 0 if ok else 1
    if len(argv) == 3:
        return 0 if report("pair", argv[1], argv[2]) else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except (ValueError, OSError) as e:
        print(f"error: {e}")
        sys.exit(2)
