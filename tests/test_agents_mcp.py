import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from webcraft import agents, mcp, skills

ROOT = Path(__file__).resolve().parents[1]


class SkillTests(unittest.TestCase):
    def test_all_bundled_skills_valid(self):
        results = skills.validate()
        self.assertGreaterEqual(len(results), 9)
        for name, errors in results.items():
            self.assertEqual(errors, [], name)

    def test_read_file_cannot_escape(self):
        s = skills.get("scroll-motion")
        self.assertIn("Reveals", s.read_file("references/snippets.md"))
        with self.assertRaises(ValueError):
            s.read_file("../launch-qa/SKILL.md")


class InstallTests(unittest.TestCase):
    def test_native_skills_install_and_uninstall(self):
        with tempfile.TemporaryDirectory() as d:
            log = agents.install("claude", scope="project", project_dir=d)
            out = Path(d) / ".claude" / "skills"
            self.assertTrue((out / "design-tokens" / "SKILL.md").is_file())
            self.assertTrue((out / "design-tokens" / "scripts" / "contrast.py").is_file())
            self.assertTrue((out / "design-tokens" / agents.MARKER).is_file())
            n = len(skills.load_all())
            self.assertTrue(any(l.startswith(f"installed {n} skill(s)") for l in log), log)
            agents.uninstall("claude", scope="project", project_dir=d)
            self.assertEqual(list(out.iterdir()), [])

    def test_does_not_clobber_foreign_skill(self):
        with tempfile.TemporaryDirectory() as d:
            mine = Path(d) / ".agents" / "skills" / "hero-section"
            mine.mkdir(parents=True)
            (mine / "SKILL.md").write_text("my own", encoding="utf-8")
            log = agents.install("codex", scope="project", project_dir=d)
            self.assertEqual((mine / "SKILL.md").read_text(encoding="utf-8"), "my own")
            self.assertTrue(any(l.startswith("skip") for l in log))

    def test_cursor_rules_rewrite_paths(self):
        with tempfile.TemporaryDirectory() as d:
            agents.install("cursor", project_dir=d, only=["scroll-motion"])
            rule = (Path(d) / ".cursor" / "rules" / "webcraft-scroll-motion.mdc").read_text(encoding="utf-8")
            self.assertTrue(rule.startswith("---\ndescription: "))
            self.assertIn("alwaysApply: false", rule)
            self.assertIn(".webcraft/skills/scroll-motion/references/snippets.md", rule)
            self.assertTrue((Path(d) / ".webcraft/skills/scroll-motion/references/snippets.md").is_file())

    def test_agents_md_block_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            md = Path(d) / "AGENTS.md"
            md.write_text("# Project\n\nOwn notes.\n", encoding="utf-8")
            agents.install("agents-md", project_dir=d)
            agents.install("agents-md", project_dir=d)
            text = md.read_text(encoding="utf-8")
            self.assertEqual(text.count(agents.BLOCK_START), 1)
            self.assertIn("Own notes.", text)
            self.assertIn("`.agents/skills/launch-qa/SKILL.md`", text)
            agents.uninstall("agents-md", project_dir=d)
            self.assertEqual(md.read_text(encoding="utf-8"), "# Project\n\nOwn notes.\n")

    def test_mcp_config_snippets(self):
        for c in agents.MCP_CLIENTS:
            self.assertIn("mcp", agents.mcp_config(c))


class McpTests(unittest.TestCase):
    def rpc(self, server, method, params=None, mid=1):
        return server.handle({"jsonrpc": "2.0", "id": mid, "method": method, "params": params or {}})

    def test_handshake_and_lists(self):
        s = mcp.Server()
        init = self.rpc(s, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                          "clientInfo": {"name": "t", "version": "0"}})
        self.assertEqual(init["result"]["protocolVersion"], "2025-06-18")
        self.assertIsNone(s.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        tools = {t["name"] for t in self.rpc(s, "tools/list")["result"]["tools"]}
        self.assertTrue({"generate_tokens", "check_contrast", "audit_site", "get_skill"} <= tools)
        prompts = self.rpc(s, "prompts/list")["result"]["prompts"]
        self.assertTrue(any(p["name"] == "hero-section" for p in prompts))
        res = self.rpc(s, "resources/list")["result"]["resources"]
        self.assertTrue(any(r["uri"] == "webcraft://skills/scroll-motion/references/snippets.md" for r in res))

    def test_tool_calls(self):
        s = mcp.Server()
        r = self.rpc(s, "tools/call", {"name": "check_contrast", "arguments": {"foreground": "#000", "background": "#fff"}})
        self.assertIn("21.00:1", r["result"]["content"][0]["text"])
        r = self.rpc(s, "tools/call", {"name": "generate_tokens", "arguments": {"brand": "#e4572e", "format": "css"}})
        self.assertIn("--accent: #e4572e;", r["result"]["content"][0]["text"])
        r = self.rpc(s, "tools/call", {"name": "get_skill", "arguments": {"name": "nope"}})
        self.assertTrue(r["result"]["isError"])
        r = self.rpc(s, "tools/call", {"name": "audit_site", "arguments": {
            "target": str(ROOT / "examples" / "sample-site"), "format": "json"}})
        self.assertEqual(json.loads(r["result"]["content"][0]["text"])["verdict"], "Not ready")
        r = self.rpc(s, "prompts/get", {"name": "launch-qa", "arguments": {"task": "check my site"}})
        self.assertIn("Task: check my site", r["result"]["messages"][0]["content"]["text"])
        self.assertEqual(self.rpc(s, "nope/nope")["error"]["code"], -32601)

    def test_stdio_subprocess(self):
        msgs = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25",
                                                                           "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        ]
        data = "".join(json.dumps(m) + "\n" for m in msgs).encode()
        env = dict(__import__("os").environ, PYTHONPATH=str(ROOT / "src"))
        p = subprocess.run([sys.executable, "-m", "webcraft", "mcp"], input=data, capture_output=True, env=env, timeout=60)
        lines = [json.loads(l) for l in p.stdout.decode("utf-8").splitlines() if l.strip()]
        self.assertEqual([l["id"] for l in lines], [1, 2], p.stderr.decode())
        self.assertEqual(lines[0]["result"]["serverInfo"]["name"], "webcraft")


if __name__ == "__main__":
    unittest.main()
