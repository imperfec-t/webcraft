import json
import unittest

from webcraft import color, css, tokens


class ColorTests(unittest.TestCase):
    def test_contrast_known_pairs(self):
        self.assertAlmostEqual(color.contrast("#000", "#fff"), 21.0, places=2)
        self.assertAlmostEqual(color.contrast("#1b1b1f", "#f6f4ef"), 15.62, places=1)
        self.assertAlmostEqual(color.contrast("#777", "#fff"), 4.48, places=1)

    def test_parse_syntaxes(self):
        self.assertEqual(color.to_hex(color.parse("rgb(255 0 0)")), "#ff0000")
        self.assertEqual(color.to_hex(color.parse("rgba(0, 0, 255, 1)")), "#0000ff")
        self.assertEqual(color.to_hex(color.parse("hsl(0, 100%, 50%)")), "#ff0000")
        self.assertEqual(color.to_hex(color.parse("oklch(1 0 0)")), "#ffffff")
        self.assertEqual(color.to_hex(color.parse("color-mix(in srgb, #000 50%, #fff)")), "#808080")
        self.assertEqual(color.to_hex(color.parse("white")), "#ffffff")
        self.assertIsNone(color.try_parse("not-a-color"))

    def test_oklch_round_trip(self):
        for hexv in ("#e4572e", "#0a84ff", "#7b2cbf", "#00c2a8"):
            L, C, H = color.rgb_to_oklch(color.parse(hexv))
            self.assertEqual(color.to_hex(color.oklch(L, C, H)), hexv)

    def test_alpha_is_composited(self):
        # 50% black over white is mid grey, not black
        self.assertLess(color.contrast("rgb(0 0 0 / 50%)", "#fff"), 5)


class TokenTests(unittest.TestCase):
    BRANDS = ["#e4572e", "#ffd400", "#0a84ff", "#222222", "#00c2a8", "#7b2cbf", "#ff69b4",
              "#808080", "#c0ffee", "#003049", "#f77f00", "#2a9d8f", "#e9c46a", "#ffffff", "#000000"]

    def test_every_text_pair_passes_for_many_brands(self):
        for brand in self.BRANDS:
            for tone in tokens.TONES:
                t = tokens.generate(brand, tone=tone)
                for theme, rows in t["contrast"].items():
                    for r in rows:
                        self.assertNotEqual(r["status"], "fail", f"{brand} {tone} {theme} {r}")

    def test_css_round_trips_through_checker(self):
        t = tokens.generate("#e4572e", tone="editorial")
        out = css.check_tokens_css(tokens.render_css(t))
        self.assertIn(":root", out)
        self.assertIn('[data-theme="dark"]', out)
        self.assertEqual(len(out), 2, "the prefers-color-scheme copy should merge with [data-theme=dark]")
        for rows in out.values():
            self.assertTrue(rows)
            self.assertFalse([r for r in rows if r["status"] == "fail"])

    def test_dark_base(self):
        t = tokens.generate("#0a84ff", base="dark")
        text = tokens.render_css(t)
        self.assertIn("color-scheme: dark", text.split("}")[0])
        self.assertIn('[data-theme="light"]', text)

    def test_theme_json_and_dtcg_are_valid_json(self):
        t = tokens.generate("#2a9d8f", tone="technical")
        tj = json.loads(tokens.render_theme_json(t))
        self.assertEqual(tj["version"], 3)
        slugs = {p["slug"] for p in tj["settings"]["color"]["palette"]}
        self.assertTrue({"bg", "text", "accent", "on-accent"} <= slugs)
        d = json.loads(tokens.render_dtcg(t))
        self.assertEqual(d["color"]["light"]["bg"]["$type"], "color")

    def test_neutrals_are_tinted(self):
        t = tokens.generate("#e4572e")
        L, C, H = color.rgb_to_oklch(color.parse(t["themes"]["light"]["--bg"]))
        self.assertGreater(C, 0.002)

    def test_bad_input(self):
        with self.assertRaises(ValueError):
            tokens.generate("nope")
        with self.assertRaises(ValueError):
            tokens.generate("#fff", tone="grunge")


class CssTests(unittest.TestCase):
    def test_var_resolution_and_aliases(self):
        sheet = """
        :root { --brand: #1d4ed8; --background: #ffffff; --foreground: #111111;
                --primary: var(--brand); --primary-foreground: #fff; }
        @media (prefers-color-scheme: dark) { :root { --background: #0b0b0c; --foreground: #f4f4f5; } }
        """
        out = css.check_tokens_css(sheet)
        self.assertEqual(len(out), 2)
        base = {r["pair"]: r for r in out[":root"]}
        self.assertEqual(base["--on-accent / --accent"]["status"], "pass")
        self.assertEqual(base["--accent / --bg"]["fg"], "#1d4ed8")

    def test_failing_pair_detected(self):
        out = css.check_tokens_css(":root{--bg:#fff;--muted:#bbb}")
        self.assertEqual(out[":root"][0]["status"], "fail")


if __name__ == "__main__":
    unittest.main()
