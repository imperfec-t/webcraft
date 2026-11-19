import os
import tempfile
import unittest
from pathlib import Path

from webcraft import mcp, prompts


class BuiltinPromptTests(unittest.TestCase):
    def test_all_builtin_prompts_valid(self):
        results = prompts.validate_builtin()
        self.assertGreaterEqual(len(results), 12)
        for name, errors in results.items():
            self.assertEqual(errors, [], name)

    def test_search_and_categories(self):
        heroes = prompts.search("", "webcraft", "Hero")
        self.assertTrue(heroes)
        self.assertTrue(all(p.category == "Hero" for p in heroes))
        self.assertIn("webcraft/three-d-hero", [p.id for p in prompts.search("three.js")])
        self.assertIn("Dashboard", prompts.categories("webcraft"))

    def test_fill(self):
        p = prompts.get("webcraft/cinematic-video-hero")
        self.assertIn("BRAND NAME", p.placeholders)
        out = prompts.fill(p.body, {"brand name": "Northwind", "CTA LABEL": "  "})
        self.assertIn("Northwind", out)
        self.assertNotIn("[BRAND NAME]", out)
        self.assertIn("[CTA LABEL]", out, "blank values leave the placeholder visible")

    def test_unknown_prompt(self):
        with self.assertRaises(KeyError):
            prompts.get("webcraft/nope")


class PersonalLibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = os.environ.get("WEBCRAFT_DATA")
        os.environ["WEBCRAFT_DATA"] = self.tmp.name

    def tearDown(self):
        if self.old is None:
            os.environ.pop("WEBCRAFT_DATA", None)
        else:
            os.environ["WEBCRAFT_DATA"] = self.old
        self.tmp.cleanup()

    def test_save_list_get_edit_delete(self):
        self.assertEqual(prompts.load_all("mine"), [])
        p = prompts.save("Neon hero: v2", "Build a hero for [BRAND NAME] in [ACCENT COLOR].", category="Hero",
                         tags=["neon", " dark "], source='Bought from "a site"', source_url="https://example.test/p")
        self.assertEqual(p.id, "mine/neon-hero-v2")
        self.assertTrue(str(p.path).startswith(self.tmp.name))
        again = prompts.get("mine/neon-hero-v2")
        self.assertEqual(again.tags, ["neon", "dark"])
        self.assertEqual(again.source, 'Bought from "a site"')
        self.assertEqual(again.placeholders, ["BRAND NAME", "ACCENT COLOR"])
        dup = prompts.save("Neon hero: v2", "Another body text.")
        self.assertEqual(dup.id, "mine/neon-hero-v2-2", "same title never overwrites")
        edited = prompts.save("Neon hero: v2", "Edited [BRAND NAME].", slug="neon-hero-v2", overwrite=True)
        self.assertIn("Edited", prompts.get(edited.id).body)
        self.assertEqual(len(prompts.search("", "mine")), 2)
        self.assertIn("mine/neon-hero-v2", [x.id for x in prompts.search("neon")])
        prompts.delete("mine/neon-hero-v2")
        self.assertEqual(len(prompts.load_all("mine")), 1)

    def test_cannot_delete_builtin_or_escape(self):
        with self.assertRaises(ValueError):
            prompts.delete("webcraft/saas-landing-page")
        with self.assertRaises(ValueError):
            prompts.delete("mine/../../etc")
        with self.assertRaises(ValueError):
            prompts.save("", "text")
        with self.assertRaises(ValueError):
            prompts.save("Title", "   ")

    def test_mcp_tools(self):
        prompts.save("Private one", "Secret layout for [BRAND NAME].", category="Hero")
        s = mcp.Server()
        r = s.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                      "params": {"name": "list_prompts", "arguments": {"library": "mine"}}})
        self.assertIn("mine/private-one", r["result"]["content"][0]["text"])
        r = s.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                      "params": {"name": "get_prompt", "arguments": {"id": "mine/private-one",
                                                                     "values": {"BRAND NAME": "Acme"}}}})
        text = r["result"]["content"][0]["text"]
        self.assertIn("Secret layout for Acme.", text)
        self.assertIn("do not publish", text)


if __name__ == "__main__":
    unittest.main()
