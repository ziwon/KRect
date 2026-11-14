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
        (self.project / "tools").mkdir()
        shutil.copy(ROOT / "tools/plasma-tools.sh", self.project / "tools/plasma-tools.sh")
        shutil.copy(ROOT / "tools/install_app.py", self.project / "tools/install_app.py")
        shutil.copytree(ROOT / "app", self.project / "app", ignore=shutil.ignore_patterns("__pycache__"))
        for name in ["install.sh", "uninstall.sh"]:
            shutil.copy(ROOT / name, self.project / name)
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.log = self.base / "calls.jsonl"
        for name in ["kpackagetool5", "kwriteconfig5", "qdbus5", "kpackagetool6", "kwriteconfig6", "qdbus6"]:
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
                        HOME=str(self.base / "home with spaces"), XDG_CONFIG_HOME=str(self.base / "config home"),
                        XDG_DATA_HOME=str(self.data), KRECT_TEST_LOG=str(self.log))
        self.plasma_version("6.4.0")

    def plasma_version(self, version):
        tool = self.bin / "plasmashell"
        tool.write_text(f"#!/bin/sh\nprintf '%s\\n' 'plasmashell {version}'\n")
        tool.chmod(0o755)

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
        desktop = self.data / "applications/org.krect.KRect.desktop"
        self.assertTrue(desktop.is_file())
        self.assertIn('Exec="', desktop.read_text())
        self.assertTrue((self.data / "krect/main.py").is_file())
        launcher = Path(self.env["HOME"]) / ".local/bin/krect"
        version = subprocess.check_output([str(launcher), "--version"], env=self.env, text=True)
        self.assertEqual(version.strip(), "KRect " + json.loads((ROOT / "package.json").read_text())["version"])

    def test_script_only_install_skips_desktop_app(self):
        result = self.run_script("install.sh", "--script-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.data / "applications/org.krect.KRect.desktop").exists())

    def test_existing_user_package_selects_upgrade(self):
        installed = self.data / "kwin/scripts/krect/metadata.json"
        installed.parent.mkdir(parents=True)
        installed.write_text("{}")
        result = self.run_script("install.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--upgrade", self.calls()[0])

    def test_plasma5_selects_matching_tools_even_when_plasma6_tools_exist(self):
        self.plasma_version("5.27.12")
        self.assertEqual(self.run_script("install.sh").returncode, 0)
        self.assertEqual(self.run_script("uninstall.sh").returncode, 0)
        self.assertEqual([call[0] for call in self.calls()],
                         ["kpackagetool5", "kwriteconfig5", "qdbus5", "kpackagetool5"])

    def test_unsupported_plasma_does_not_mutate(self):
        for version in ["5.26.5", "4.11.0", "7.0.0", "unknown"]:
            with self.subTest(version=version):
                self.plasma_version(version)
                self.assertNotEqual(self.run_script("install.sh").returncode, 0)
                self.assertNotEqual(self.run_script("uninstall.sh").returncode, 0)
                self.assertEqual(self.calls(), [])

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
        self.assertEqual(self.run_script("install.sh").returncode, 0)
        self.log.unlink()
        result = self.run_script("uninstall.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [
            ["kwriteconfig6", "--file", "kwinrc", "--group", "Plugins", "--key", "krectEnabled", "false"],
            ["qdbus6", "org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.unloadScript", "krect"],
            ["kpackagetool6", "--type=KWin/Script", "--remove", "krect"],
        ])
        self.assertFalse((self.data / "applications/org.krect.KRect.desktop").exists())
        self.assertFalse((self.data / "krect").exists())


if __name__ == "__main__":
    unittest.main()
