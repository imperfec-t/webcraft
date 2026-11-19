import tempfile
import unittest
from pathlib import Path

from webcraft import audit, detect, source, teardown

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples" / "sample-site"

CLEAN = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Northwind Studio: brand identity and websites for founders</title>
<meta name="description" content="Northwind is a small design studio building brand identities and fast marketing websites for founders and growing service businesses.">
<link rel="canonical" href="https://northwind.test/">
<link rel="icon" href="/favicon.svg">
<meta property="og:title" content="Northwind Studio"><meta property="og:description" content="Brand and web design">
<meta property="og:image" content="https://northwind.test/og.png">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization","name":"Northwind"}</script>
</head><body>
<header><nav><a href="/work/">Work</a></nav></header>
<main><section class="hero"><h1>Brands people remember</h1><p>We design identities and websites.</p>
<a class="btn" href="/contact/">Plan your project</a>
<img src="hero.avif" width="1200" height="800" alt="Studio desk"></section>
<section><h2>Services</h2><p>Identity, websites, campaigns.</p></section></main>
<footer><p>&copy; 2099 Northwind</p></footer>
</body></html>"""


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = audit.audit(str(SAMPLE), remote_checks=False)
        cls.ids = {f.id for f in cls.report.findings}

    def test_finds_planted_blockers(self):
        blockers = {f.id for f in self.report.findings if f.severity == "blocker"}
        self.assertTrue({"viewport", "noindex", "placeholder-content", "broken-local-links"} <= blockers, blockers)
        self.assertEqual(self.report.verdict, "Not ready")

    def test_finds_planted_should_fix(self):
        expected = {"img-alt", "img-dimensions", "lcp-lazy", "dead-links", "form-labels", "heading-skip", "lang",
                    "render-blocking-js", "font-display", "reduced-motion", "video-autoplay", "video-poster",
                    "token-contrast", "css-hidden-content", "accessible-name", "title-duplicate"}
        self.assertTrue(expected <= self.ids, expected - self.ids)

    def test_finds_planted_polish(self):
        expected = {"copyright-year", "tel-mismatch", "100vw", "100vh", "radius-sprawl", "font-families", "link-text"}
        self.assertTrue(expected <= self.ids, expected - self.ids)

    def test_not_checked_is_honest(self):
        text = audit.render(self.report)
        self.assertIn("## Not checked", text)
        self.assertIn("Form delivery", text)
        self.assertTrue(text.splitlines()[2].startswith("Verdict:"))

    def test_clean_page_has_no_blockers_or_should_fix(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "index.html"
            p.write_text(CLEAN, encoding="utf-8")
            (Path(d) / "hero.avif").write_bytes(b"")
            (Path(d) / "404.html").write_text("<h1>Not found</h1>", encoding="utf-8")
            rep = audit.audit(str(p), remote_checks=False)
            serious = [f for f in rep.findings if f.severity != "polish"]
            self.assertEqual(serious, [], [(f.id, f.problem) for f in serious])
            self.assertEqual(rep.verdict, "Ready")


class DetectTeardownTests(unittest.TestCase):
    def test_detect_versions_and_fonts(self):
        res = detect.detect(source.load(str(SAMPLE / "index.html")))
        motion = {t["name"]: t for t in res["technologies"]["motion"]}
        self.assertIn("GSAP", motion)
        self.assertEqual(motion["GSAP"].get("version"), "3.12.5")
        self.assertIn("AOS", motion)
        self.assertEqual(res["fonts"]["roles"].get("display"), "Playfair Display")
        self.assertEqual(res["palette"]["theme"], "light")

    def test_teardown_keeps_no_original_copy(self):
        res = teardown.teardown(str(SAMPLE / "index.html"))
        text = teardown.render(res)
        names = [s["name"] for s in res["sections"]]
        self.assertEqual(names[:4], ["Header / navigation", "Hero", "Proof strip (logos)", "Services"])
        self.assertIn("FAQ", names)
        self.assertEqual(names[-1], "Footer")
        for phrase in ("We build brands", "Lorem ipsum", "Brand identity", "hero.jpg", "Plan your project", "Studio"):
            self.assertNotIn(phrase, text)
        self.assertIn("[H1 headline, 5 words, 2 lines]", text)
        self.assertIn('data-aos="fade-up" x3', text)


if __name__ == "__main__":
    unittest.main()
