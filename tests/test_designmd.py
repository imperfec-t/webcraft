import io
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from webcraft import designmd as dm, tokens

FRONTMATTER = '''---
version: alpha
name: Sample-design-analysis
description: >
  A near-black developer canvas with one lavender accent
  and hairline borders.
colors:
  primary: "#5e6ad2"          # accent, CTAs
  on-primary: "#ffffff"
  ink: "#f7f8f8"
  ink-muted: "#8a8f98"
  canvas: "#010102"
  surface-1: "#0f1011"
  hairline: "#23252a"
  primary-hover: "#828fff"
typography:
  display-xl:
    fontFamily: Sample Display
    fontSize: 80px
    letterSpacing: -3.0px
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: 16px
rounded:
  sm: 6px
  md: 8px
  pill: 9999px
spacing:
  md: 16px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
  button-ghost-bad:
    backgroundColor: "{colors.surface-1}"
    textColor: "#2a2a2a"
  button-disabled:
    backgroundColor: "{colors.surface-1}"
    textColor: "#222222"
---

## Overview

A product-focused dark canvas.

## Colors

Lavender only on CTAs.
'''

PROSE = '''# Design System Inspired by Example

## 1. Visual Theme & Atmosphere

A dark music player.

## 2. Color Palette & Roles

### Primary Brand
- **Signal Green** (`#1ed760`): Primary CTA, brand accent, play buttons
- **Logo Red** (`#eb001b`): Used only in the brand logo, never as a UI color
- **Near Black** (`#121212`): Deepest background surface, the page background
- **Dark Surface** (`#181818`): Cards, containers, elevated surfaces

### Text
- **White** (`#ffffff`): Primary text
- **Silver** (`#b3b3b3`): Secondary text, muted labels
- **Border Gray** (`#4d4d4d`): Divider borders
'''


class ParseTests(unittest.TestCase):
    def test_yaml_subset(self):
        y = dm.parse_yaml('a: "x # not a comment"  # real comment\nb:\n  c: 1\n  d: [1, two]\ne: >\n  folded\n  text\nf:\n  - one\n  - two\n')
        self.assertEqual(y["a"], "x # not a comment")
        self.assertEqual(y["b"], {"c": 1, "d": [1, "two"]})
        self.assertEqual(y["e"], "folded text")
        self.assertEqual(y["f"], ["one", "two"])

    def test_frontmatter_design(self):
        d = dm.parse(FRONTMATTER)
        self.assertTrue(d["has_frontmatter"])
        self.assertEqual(d["colors"]["primary"], "#5e6ad2")
        self.assertIn("lavender accent and hairline", d["description"])
        self.assertEqual(d["sections"], ["Overview", "Colors"])
        res = dm.check(d)
        self.assertEqual(res["theme"], "dark")
        self.assertEqual(res["roles"]["--bg"], "#010102")
        self.assertEqual(res["roles"]["--accent"], "#5e6ad2")
        self.assertEqual(res["role_names"]["--muted"], "ink-muted")
        comps = {c["component"]: c for c in res["components"]}
        self.assertEqual(comps["button-primary"]["status"], "pass")
        self.assertEqual(comps["button-ghost-bad"]["status"], "fail")
        self.assertNotIn("button-disabled", comps, "disabled controls are exempt from WCAG contrast")

    def test_prose_design(self):
        d = dm.parse(PROSE)
        self.assertFalse(d["has_frontmatter"])
        roles = dm.check(d)["roles"]
        self.assertEqual(roles["--bg"], "#121212")
        self.assertEqual(roles["--text"], "#ffffff")
        self.assertEqual(roles["--muted"], "#b3b3b3")
        self.assertEqual(roles["--accent"], "#1ed760")
        self.assertNotIn("#eb001b", roles.values(), "logo-only colors must not become UI roles")

    def test_to_tokens_css(self):
        out = dm.to_tokens_css(dm.parse(FRONTMATTER), "sample")
        self.assertIn("--bg: #010102;", out)
        self.assertIn("--ds-primary-hover: #828fff;", out)
        self.assertIn('--font-display: "Sample Display"', out)
        self.assertIn("--radius: 8px;", out)
        self.assertIn("proprietary", out)

    def test_round_trip_from_tokens(self):
        t = tokens.generate("#e4572e", tone="editorial")
        text = dm.from_tokens(t, "northwind")
        d = dm.parse(text)
        self.assertEqual(d["name"], "northwind")
        res = dm.check(d)
        self.assertEqual(res["roles"]["--accent"], "#e4572e")
        self.assertEqual(res["fails"], 0, res)
        self.assertGreaterEqual(len(res["components"]), 3)

    def test_notice_keeps_frontmatter_first(self):
        out = dm.with_notice(FRONTMATTER)
        self.assertTrue(out.startswith("---\n"))
        self.assertIn(dm.REFERENCE_NOTICE, out)
        self.assertTrue(dm.parse(out)["has_frontmatter"])


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = os.environ.get("WEBCRAFT_CACHE")
        os.environ["WEBCRAFT_CACHE"] = str(Path(self.tmp.name) / "cache")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("awesome-design-md-main/LICENSE", "MIT License")
            z.writestr("awesome-design-md-main/design-md/sample/DESIGN.md", FRONTMATTER)
            z.writestr("awesome-design-md-main/design-md/musicco/DESIGN.md", PROSE)
            z.writestr("awesome-design-md-main/design-md/../evil/DESIGN.md", "nope")
            z.writestr("awesome-design-md-main/README.md", "readme")
        self.zip = Path(self.tmp.name) / "lib.zip"
        self.zip.write_bytes(buf.getvalue())

    def tearDown(self):
        if self.old is None:
            os.environ.pop("WEBCRAFT_CACHE", None)
        else:
            os.environ["WEBCRAFT_CACHE"] = self.old
        self.tmp.cleanup()

    def test_missing_library(self):
        with self.assertRaises(dm.LibraryMissing):
            dm.library_index()
        self.assertFalse(dm.library_status()["synced"])

    def test_sync_search_read_use(self):
        meta = dm.sync(str(self.zip))
        self.assertEqual(meta["count"], 2)
        self.assertFalse((dm.cache_dir().parent / "evil").exists())
        self.assertTrue((dm.cache_dir() / "LICENSE").is_file())
        self.assertEqual({i["name"] for i in dm.search("")}, {"sample", "musicco"})
        self.assertEqual([i["name"] for i in dm.search("dark lavender")], ["sample"])
        self.assertEqual(dm.search("light"), [])
        label, text = dm.read("musicco")
        self.assertIn("Signal Green", text)
        with self.assertRaises(KeyError):
            dm.read("nope")
        proj = Path(self.tmp.name) / "proj"
        log = dm.use("sample", str(proj), tokens=True)
        self.assertEqual(len(log), 2)
        written = (proj / "DESIGN.md").read_text(encoding="utf-8")
        self.assertTrue(written.startswith("---\n"))
        self.assertIn("awesome-design-md", written)
        self.assertIn("--bg: #010102;", (proj / "tokens.css").read_text(encoding="utf-8"))
        with self.assertRaises(FileExistsError):
            dm.use("sample", str(proj))


if __name__ == "__main__":
    unittest.main()
