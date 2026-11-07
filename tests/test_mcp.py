import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
HAS_MCP = importlib.util.find_spec("mcp") is not None


@unittest.skipUnless(HAS_MCP, "optional MCP SDK is not installed")
class MCPTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("build_graph.py", "graph_store.py", "graph_content.py"):
            shutil.copy2(REPO / name, self.root)
        subprocess.run([sys.executable, "-X", "utf8", str(self.root / "build_graph.py")], check=True, capture_output=True)

    async def connect_and_check(self, allow_write):
        import anyio
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        arguments = ["-X", "utf8", str(REPO / "graph_mcp.py"), "--root", str(self.root)]
        if allow_write:
            arguments.append("--allow-write")
        params = StdioServerParameters(command=sys.executable, args=arguments, env=dict(os.environ))
        with anyio.fail_after(30):
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    names = {tool.name for tool in tools.tools}
                    self.assertIn("graph_search", names)
                    self.assertIn("graph_health", names)
                    self.assertIn("graph_human_changes", names)
                    self.assertEqual("graph_apply" in names, allow_write)
                    bad = await session.call_tool("graph_search", {"query_text": "урон", "limit": -1})
                    self.assertTrue(bad.isError)
                    found = await session.call_tool("graph_search", {"query_text": "урон"})
                    self.assertFalse(found.isError)
                    self.assertIn("sys_damage_model", [n["id"] for n in json.loads(found.content[0].text)["nodes"]])
                    node = await session.call_tool("graph_node", {"node_id": "sys_damage_model"})
                    current = json.loads(node.content[0].text)["revision"]
                    if allow_write:
                        operation = {"op": "update-node", "id": "sys_damage_model", "fields": {"needs_review": True, "human": "Updated through MCP"}}
                        saved = await session.call_tool("graph_apply", {"operations": [operation], "expected_revision": current, "summary": "MCP test"})
                        self.assertFalse(saved.isError, saved.content)
                        self.assertTrue(json.loads(saved.content[0].text)["saved"])
                        updated = await session.call_tool("graph_node", {"node_id": "sys_damage_model"})
                        card = json.loads(updated.content[0].text)["nodes"][0]
                        self.assertEqual(card["summary"], "Updated through MCP")
                        self.assertTrue(card["needs_review"])
                        conflict = await session.call_tool("graph_apply", {"operations": [operation], "expected_revision": current})
                        self.assertTrue(conflict.isError)
                        from graph_store import load_document, revision, save_document
                        doc = load_document(self.root)
                        doc["NODES"]["sys_damage_model"]["note"] = "Human note"
                        save_document(self.root, doc, revision(self.root))
                        human = await session.call_tool("graph_human_changes", {"node_id": "sys_damage_model"})
                        human = json.loads(human.content[0].text)
                        next_operation = {**operation, "fields": {"human": "Further agent update"}}
                        refused = await session.call_tool("graph_apply", {"operations": [next_operation], "expected_revision": human["revision"]})
                        self.assertTrue(refused.isError)
                        ack = {"op": "acknowledge-node", "id": "sys_damage_model", "token": human["human_edit"]["token"], "note": "I read the human note and will preserve it"}
                        accepted = await session.call_tool("graph_apply", {"operations": [ack, next_operation], "expected_revision": human["revision"]})
                        self.assertFalse(accepted.isError, accepted.content)

    async def test_stdio_reads_and_writes_with_revision_checks(self):
        await self.connect_and_check(True)

    async def test_stdio_defaults_to_read_only(self):
        await self.connect_and_check(False)


if __name__ == "__main__":
    unittest.main()
