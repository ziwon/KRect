import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def test_config_controls_match_schema(self):
        schema = ET.parse(ROOT / "package/contents/config/main.xml")
        ui = ET.parse(ROOT / "package/contents/ui/config.ui")
        entries = {item.attrib["name"] for item in schema.findall(".//{*}entry")}
        controls = {item.attrib["name"][5:] for item in ui.findall(".//widget")
                    if item.attrib.get("name", "").startswith("kcfg_")}
        self.assertEqual(entries, controls)

    def test_generated_entry_point_matches_source(self):
        self.assertEqual((ROOT / "src/main.js").read_bytes(),
                         (ROOT / "package/contents/code/main.js").read_bytes())


@unittest.skipIf(os.geteuid() == 0, "Installer intentionally refuses root")
class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="krect tests ")
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name)
        self.project = self.base / "project with spaces"
        shutil.copytree(ROOT / "package", self.project / "package")
        for name in ["install.sh", "uninstall.sh"]:
            shutil.copy(ROOT / name, self.project / name)
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.log = self.base / "calls.jsonl"
        for name in ["kpackagetool6", "kwriteconfig6", "qdbus6"]:
            tool = self.bin / name
            tool.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
with open(os.environ["KRECT_TEST_LOG"], "a") as log:
    log.write(json.dumps([name, *sys.argv[1:]]) + "\\n")
sys.exit(91 if os.environ.get("KRECT_FAIL_TOOL") == name else 0)
''')
            tool.chmod(0o755)
        self.data = self.base / "data home"
        self.env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}",
                        XDG_DATA_HOME=str(self.data), KRECT_TEST_LOG=str(self.log))

    def run_script(self, script, *args):
        return subprocess.run(["bash", str(self.project / script), *args],
                              env=self.env, text=True, capture_output=True)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_new_install_passes_path_as_one_argument_and_does_not_enable(self):
        result = self.run_script("install.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [["kpackagetool6", "--type=KWin/Script", "--install", str(self.project / "package")]])
        self.assertIn("Enable KRect", result.stdout)

    def test_existing_user_package_selects_upgrade(self):
        installed = self.data / "kwin/scripts/krect/metadata.json"
        installed.parent.mkdir(parents=True)
        installed.write_text("{}")
        result = self.run_script("install.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--upgrade", self.calls()[0])

    def test_install_failure_does_not_report_success(self):
        self.env["KRECT_FAIL_TOOL"] = "kpackagetool6"
        result = self.run_script("install.sh")
        self.assertEqual(result.returncode, 91)
        self.assertNotIn("package installed", result.stdout)

    def test_unbuilt_package_rejected(self):
        (self.project / "package/contents/code/main.js").unlink()
        result = self.run_script("install.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_unknown_argument_does_not_mutate(self):
        self.assertEqual(self.run_script("install.sh", "--surprise").returncode, 2)
        self.assertEqual(self.run_script("uninstall.sh", "--surprise").returncode, 2)
        self.assertEqual(self.calls(), [])

    def test_help_does_not_mutate(self):
        self.assertEqual(self.run_script("install.sh", "--help").returncode, 0)
        self.assertEqual(self.run_script("uninstall.sh", "--help").returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_uninstall_disables_and_unloads_only_krect_before_removing(self):
        result = self.run_script("uninstall.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [
            ["kwriteconfig6", "--file", "kwinrc", "--group", "Plugins", "--key", "krectEnabled", "false"],
            ["qdbus6", "org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.unloadScript", "krect"],
            ["kpackagetool6", "--type=KWin/Script", "--remove", "krect"],
        ])


if __name__ == "__main__":
    unittest.main()
