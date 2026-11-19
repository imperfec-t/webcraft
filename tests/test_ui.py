import json
import re
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from webcraft import ui

ROOT = Path(__file__).resolve().parents[1]


class UiServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ui.make_server(port=0)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def request(self, path, body=None, token=True, host=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-Webcraft-Token"] = self.srv.secret
        if host:
            headers["Host"] = host
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, headers=headers, method="POST" if data else "GET")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.headers, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read().decode("utf-8")

    def api(self, name, body=None):
        status, _, text = self.request("/api/" + name, body or {})
        self.assertEqual(status, 200, text)
        return json.loads(text)

    def test_page_served_with_secret_and_nonce(self):
        status, headers, html = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(self.srv.secret, html)
        nonce = re.search(r"nonce-([\w-]+)", headers["Content-Security-Policy"]).group(1)
        self.assertIn(f'<script nonce="{nonce}">', html)
        self.assertNotIn("__WEBCRAFT_TOKEN__", html)

    def test_rejects_missing_token_and_foreign_host(self):
        status, _, _ = self.request("/api/meta", {}, token=False)
        self.assertEqual(status, 403)
        status, _, _ = self.request("/", host="evil.example")
        self.assertEqual(status, 403)
        status, _, _ = self.request("/api/meta", {}, host="evil.example:80")
        self.assertEqual(status, 403)

    def test_endpoints(self):
        meta = self.api("meta")["data"]
        self.assertIn("claude", [a["key"] for a in meta["agents"]])
        tk = self.api("tokens", {"brand": "#0a84ff", "tone": "technical"})["data"]
        self.assertIn("--accent: #0a84ff;", tk["css"])
        self.assertEqual(json.loads(tk["theme_json"])["version"], 3)
        ct = self.api("contrast", {"fg": "#000", "bg": "#fff"})["data"]
        self.assertEqual(ct["ratio"], 21.0)
        au = self.api("audit", {"target": str(ROOT / "examples" / "sample-site"), "offline": True})["data"]
        self.assertEqual(au["report"]["verdict"], "Not ready")
        td = self.api("teardown", {"target": str(ROOT / "examples" / "sample-site" / "index.html")})["data"]
        self.assertGreaterEqual(len(td["result"]["sections"]), 5)
        sk = self.api("skill", {"name": "scroll-motion", "file": "references/snippets.md"})["data"]
        self.assertIn("Reveals", sk["text"])

    def test_overview(self):
        o = self.api("overview")["data"]
        self.assertGreaterEqual(o["skills"], 10)
        self.assertGreaterEqual(o["prompts"]["builtin"], 12)
        self.assertIn("synced", o["designs"])
        self.assertTrue(o["mcp_command"].endswith("mcp"))
        for k in ("cwd", "prompts", "designs", "skills"):
            self.assertTrue(o["paths"][k])

    def test_page_has_every_view_and_help(self):
        _, _, html = self.request("/")
        for v in ("overview", "tokens", "designs", "prompts", "contrast", "audit", "detect", "teardown", "skills", "install"):
            self.assertIn(f'id="view-{v}"', html)
        self.assertEqual(html.count('class="help" data-help='), 9)
        self.assertIn('id="palette"', html)
        self.assertNotIn("onclick=", html, "inline handlers would be blocked by the CSP")

    def test_errors_are_reported_not_raised(self):
        r = self.api("tokens", {"brand": "not-a-color"})
        self.assertFalse(r["ok"])
        r = self.api("skill", {"name": "scroll-motion", "file": "../launch-qa/SKILL.md"})
        self.assertFalse(r["ok"])
        status, _, _ = self.request("/api/nope", {})
        self.assertEqual(status, 404)

    def test_prompts_endpoints(self):
        import os
        with tempfile.TemporaryDirectory() as d:
            old = os.environ.get("WEBCRAFT_DATA")
            os.environ["WEBCRAFT_DATA"] = d
            try:
                lst = self.api("prompts_list", {"library": "webcraft"})["data"]
                self.assertGreaterEqual(len(lst["items"]), 12)
                one = self.api("prompts_get", {"id": "webcraft/bento-features-section"})["data"]
                self.assertTrue(one["placeholders"])
                saved = self.api("prompts_save", {"title": "Mine A", "body": "Hello [BRAND NAME]", "tags": "a, b"})["data"]
                self.assertEqual(saved["id"], "mine/mine-a")
                edited = self.api("prompts_save", {"id": "mine/mine-a", "title": "Mine A", "body": "Edited"})["data"]
                self.assertEqual(edited["id"], "mine/mine-a")
                self.assertFalse(self.api("prompts_delete", {"id": "webcraft/bento-features-section"})["ok"])
                self.assertTrue(self.api("prompts_delete", {"id": "mine/mine-a"})["ok"])
            finally:
                if old is None:
                    os.environ.pop("WEBCRAFT_DATA", None)
                else:
                    os.environ["WEBCRAFT_DATA"] = old

    def test_install_preview_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.api("install", {"agents": ["claude", "cursor"], "scope": "project", "project": d, "dry_run": True})
            self.assertTrue(r["ok"])
            self.assertEqual(list(Path(d).iterdir()), [])
            r = self.api("install", {"agents": ["claude"], "scope": "project", "project": d, "dry_run": False})
            self.assertTrue((Path(d) / ".claude" / "skills" / "launch-qa" / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
