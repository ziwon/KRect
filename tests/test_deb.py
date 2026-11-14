import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_deb", ROOT / "tools/build_deb.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


@unittest.skipUnless(shutil.which("dpkg-deb"), "dpkg-deb required")
class DebianTests(unittest.TestCase):
    def test_packages_have_matching_dependencies_and_global_payload(self):
        with tempfile.TemporaryDirectory(prefix="krect deb tests ") as temporary:
            for ubuntu, major in [("24.04", 5), ("26.04", 6)]:
                with self.subTest(ubuntu=ubuntu):
                    deb = builder.build(ubuntu, Path(temporary))
                    info = subprocess.check_output(["dpkg-deb", "-f", str(deb)], text=True)
                    self.assertIn("Architecture: all", info)
                    self.assertIn(f"kpackagetool{major}", info)
                    self.assertNotIn(f"kpackagetool{11 - major}", info)
                    self.assertIn(f"-1ubuntu{ubuntu}", info)
                    unpacked = Path(temporary) / ubuntu
                    subprocess.run(["dpkg-deb", "--raw-extract", str(deb), str(unpacked)], check=True)
                    plugin = unpacked / "usr/share/kwin/scripts/krect"
                    self.assertEqual((plugin / "contents/code/main.js").read_bytes(),
                                     (ROOT / "src/main.js").read_bytes())
                    self.assertTrue((plugin / "contents/ui/config.ui").is_file())
                    self.assertTrue((unpacked / "usr/share/doc/krect/copyright").is_file())
                    self.assertEqual([p.name for p in (unpacked / "DEBIAN").iterdir()], ["control"])
                    for path in unpacked.rglob("*"):
                        self.assertEqual(path.stat().st_mode & 0o777, 0o755 if path.is_dir() else 0o644)

    def test_build_is_reproducible(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            first = builder.build("24.04", output).read_bytes()
            self.assertEqual(builder.build("24.04", output).read_bytes(), first)


if __name__ == "__main__":
    unittest.main()
