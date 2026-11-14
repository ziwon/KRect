#!/usr/bin/env python3
"""Build an installable .kwinscript and a complete source distribution using stdlib."""
import json
from pathlib import Path
import shutil
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "package"
metadata = json.loads((PACKAGE / "metadata.json").read_text())
version = metadata["KPlugin"]["Version"]
assert metadata["KPlugin"]["Id"] == "krect"
for path in [PACKAGE / "contents/config/main.xml", PACKAGE / "contents/ui/config.ui"]:
    ET.parse(path)
code = PACKAGE / "contents/code/main.js"
code.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(ROOT / "src/main.js", code)
dist = ROOT / "dist"
dist.mkdir(exist_ok=True)


def add(archive, path, name):
    # Fixed timestamps make builds reproducible from identical inputs.
    info = zipfile.ZipInfo(name, (2026, 11, 14, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (0o100755 if path.suffix == ".sh" else 0o100644) << 16
    archive.writestr(info, path.read_bytes())


plugin = dist / f"krect-{version}.kwinscript"
with zipfile.ZipFile(plugin, "w") as archive:
    for path in sorted(PACKAGE.rglob("*")):
        if path.is_file():
            add(archive, path, path.relative_to(PACKAGE).as_posix())
    add(archive, ROOT / "LICENSE", "LICENSE")

bundle = dist / f"krect-{version}.zip"
with zipfile.ZipFile(bundle, "w") as archive:
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in {"dist", ".git", "__pycache__"} for part in path.relative_to(ROOT).parts):
            continue
        add(archive, path, f"krect/{path.relative_to(ROOT).as_posix()}")
    add(archive, plugin, f"krect/dist/{plugin.name}")
print(plugin)
print(bundle)
