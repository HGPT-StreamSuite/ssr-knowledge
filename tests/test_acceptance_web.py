"""Static-page parity/packaging checks. No HTTP, DB, real data or installation."""
from __future__ import annotations

import copy
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from ssr_knowledge.contracts import _validate, validate

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "acceptance" / "dist"
NODE = shutil.which("node")


def data():
    text = (WEB / "data.js").read_text(encoding="utf-8")
    return json.loads(text.split("globalThis.KnowledgeAcceptanceData = ", 1)[1].removesuffix(";\n"))


class StaticAcceptanceTests(unittest.TestCase):
    def test_embedded_contracts_and_fixtures_match_repo_bytes(self):
        value = data()
        self.assertEqual(len(value["schemas"]), 8)
        for name, schema in value["schemas"].items():
            self.assertEqual(schema, json.loads((ROOT / "contracts" / name).read_text(encoding="utf-8")))
        for name, digest in value["source_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)

    def test_all_page_examples_pass_current_python_validator(self):
        value = data()
        for name, example in value["samples"].items():
            with self.subTest(schema=name):
                validate(example, name)
        self.assertFalse(value["samples"]["tool-config.schema.json"]["network_enabled"])

    @unittest.skipUnless(NODE, "existing Node required for browser/Python parity; do not install")
    def test_browser_rules_match_python_for_current_contract_cases(self):
        value = data()
        cases = []
        for name, sample in value["samples"].items():
            cases.append({"name": name, "value": sample})
            for key in value["schemas"][name]["required"]:
                missing = copy.deepcopy(sample); missing.pop(key)
                cases.append({"name": name, "value": missing})
            extra = copy.deepcopy(sample); extra["__proto__"] = {"polluted": True}
            cases.append({"name": name, "value": extra})
            for invalid in [None, False, [], "invalid"]:
                cases.append({"name": name, "value": invalid})
        wrong_record = copy.deepcopy(value["samples"]["record.schema.json"])
        wrong_record.update(kind="not_a_kind", tags=[False], source={"source_id": 1})
        cases.append({"name": "record.schema.json", "value": wrong_record})
        wrong_tools = copy.deepcopy(value["samples"]["tool-config.schema.json"])
        wrong_tools["network_enabled"] = True
        wrong_tools["tools"][0]["parameters"][0]["required"] = "false"
        cases.append({"name": "tool-config.schema.json", "value": wrong_tools})
        expected = [_validate(case["value"], value["schemas"][case["name"]], "$") for case in cases]
        program = "const fs=require('node:fs');require('./web/acceptance/dist/data.js');const api=require('./web/acceptance/dist/contract.js');const data=globalThis.KnowledgeAcceptanceData;const cases=JSON.parse(fs.readFileSync(0,'utf8'));console.log(JSON.stringify(cases.map(c=>api.validate(c.value,data.schemas[c.name]))));"
        result = subprocess.run([NODE, "-e", program], cwd=ROOT, input=json.dumps(cases, ensure_ascii=False),
                                capture_output=True, text=True, encoding="utf-8", check=True)
        self.assertEqual(json.loads(result.stdout), expected)

    def test_local_assets_and_document_links_exist_without_server(self):
        class Links(HTMLParser):
            def __init__(self):
                super().__init__(); self.links = []; self.ids = set(); self.external = []; self.native_text = ""; self.in_native = False
            def handle_starttag(self, tag, attrs):
                values = dict(attrs)
                if tag == "pre" and values.get("id") == "native-request": self.in_native = True
                if "id" in values: self.ids.add(values["id"])
                for key in ("src", "href"):
                    if key in values: self.links.append(values[key])
                if tag == "meta" and values.get("http-equiv") == "Content-Security-Policy":
                    self.csp = values["content"]
            def handle_endtag(self, tag):
                if tag == "pre": self.in_native = False
            def handle_data(self, text):
                if self.in_native: self.native_text += text
        html = (WEB / "index.html").read_text(encoding="utf-8")
        parser = Links(); parser.feed(html)
        self.assertIn("connect-src 'none'", parser.csp)
        self.assertTrue({"browser-gate", "criteria", "evidence", "not-applicable", "blocked"} <= parser.ids)
        self.assertIn("本輪網頁驗收：BLOCKED／未通過", html)
        self.assertIn("模擬 DOM 測試不能替代", html)
        self.assertIn("預設瀏覽器身分未知", html)
        self.assertIn("頁面 → native handler 未接通", html)
        self.assertEqual(json.loads(parser.native_text), json.loads((ROOT / "fixtures" / "acceptance-native.synthetic.json").read_text(encoding="utf-8")))
        for target in parser.links:
            with self.subTest(target=target):
                self.assertNotIn("://", target)
                if target.startswith("#"):
                    self.assertIn(target[1:], parser.ids)
                else:
                    self.assertTrue((WEB / target).resolve().is_file())


if __name__ == "__main__":
    unittest.main()
