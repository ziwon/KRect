#!/usr/bin/env python3
"""Build architecture-independent Ubuntu packages without changing the desktop."""
import argparse
from datetime import datetime, timezone
from email.utils import format_datetime
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {"24.04": (5, "4:5.27", "4:6~"), "26.04": (6, "4:6.0", "4:7~")}


def build(ubuntu, output):
    major, minimum, maximum = TARGETS[ubuntu]
    metadata = json.loads((ROOT / "package/metadata.json").read_text())
    version = metadata["KPlugin"]["Version"]
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("Package version must be a numeric major.minor.patch")
    deb_version = f"{version}-1ubuntu{ubuntu}"
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "1794614400"))
    date = format_datetime(datetime.fromtimestamp(epoch, timezone.utc))
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"krect_{deb_version}_all.deb"
    with tempfile.TemporaryDirectory(prefix="krect deb ") as temporary:
        staging = Path(temporary) / "krect"
        plugin = staging / "usr/share/kwin/scripts/krect"
        shutil.copytree(ROOT / "package", plugin)
        shutil.copyfile(ROOT / "src/main.js", plugin / "contents/code/main.js")
        application = staging / "usr/share/krect"
        shutil.copytree(ROOT / "app", application, ignore=shutil.ignore_patterns("__pycache__", "*.desktop", "krect-launcher"))
        launcher = staging / "usr/bin/krect"
        launcher.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / "app/krect-launcher", launcher)
        desktop = staging / "usr/share/applications/org.krect.KRect.desktop"
        desktop.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / "app/org.krect.KRect.desktop", desktop)
        icon = staging / "usr/share/icons/hicolor/scalable/apps/org.krect.KRect.svg"
        icon.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / "app/assets/org.krect.KRect.svg", icon)
        docs = staging / "usr/share/doc/krect"
        docs.mkdir(parents=True)
        (docs / "copyright").write_text(
            "Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/\n"
            "Upstream-Name: KRect\nSource: https://github.com/ziwon/KRect\n\n"
            "Files: *\nCopyright: 2026 KRect contributors\nLicense: MIT\n"
            + "\n".join(" " + line if line else " ." for line in (ROOT / "LICENSE").read_text().splitlines()[4:])
            + "\n"
        )
        changelog = (
            f"krect ({deb_version}) noble; urgency=medium\n\n"
            f"  * Package KRect {version} for Ubuntu {ubuntu} / Plasma {major}.\n\n"
            f" -- KRect contributors <ziwon@users.noreply.github.com>  {date}\n"
        ).replace(") noble;", ") resolute;" if ubuntu == "26.04" else ") noble;")
        (docs / "changelog.Debian.gz").write_bytes(gzip.compress(changelog.encode(), mtime=0))
        manual = staging / "usr/share/man/man1"
        manual.mkdir(parents=True)
        (manual / "krect.1.gz").write_bytes(gzip.compress((ROOT / "docs/krect.1").read_bytes(), mtime=0))
        (docs / "README.Debian").write_text(
            f"KRect for Ubuntu {ubuntu} / Plasma {major}\n\n"
            "Open KRect from the application launcher and click Enable KRect.\n"
            "Installation does not enable scripts or change user shortcuts/settings.\n"
            "Remove an existing user-scope KRect package before using this global package;\n"
            "~/.local/share/kwin/scripts/krect overrides the system copy.\n"
            "After upgrading/removing the package, disable/re-enable KRect or log out\n"
            "and back in to reload/stop a script already running in KWin.\n"
        )
        control = staging / "DEBIAN"
        control.mkdir()
        size = sum(p.stat().st_size for p in staging.rglob("*") if p.is_file())
        svg_dependencies = "libqt5svg5" if major == 5 else "libqt6svg6, qt6-svg-plugins"
        (control / "control").write_text(
            "Package: krect\n"
            f"Version: {deb_version}\n"
            "Section: kde\nPriority: optional\nArchitecture: all\n"
            "Maintainer: KRect contributors <ziwon@users.noreply.github.com>\n"
            f"Installed-Size: {(size + 1023) // 1024}\n"
            f"Depends: python3, python3-dbus, python3-pyqt{major}, {svg_dependencies}, "
            f"kpackagetool{major}, libkf{major}config-bin, kde-cli-tools, kwin-common (>= {minimum}), "
            f"kwin-common (<< {maximum}), plasma-workspace (>= {minimum}), "
            f"plasma-workspace (<< {maximum})\n"
            "Homepage: https://github.com/ziwon/KRect\n"
            f"Description: Rectangle-style window placement for Plasma {major}\n"
            " Native desktop app, tray controls, layout preview, editable KDE shortcuts,\n"
            " and a KWin engine for halves, quarters, thirds, restore and display movement.\n"
        )
        for path in [staging, *staging.rglob("*")]:
            path.chmod(0o755 if path.is_dir() else 0o644)
            os.utime(path, (epoch, epoch))
        launcher.chmod(0o755)
        subprocess.run(
            ["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(staging), str(archive)],
            check=True, env=dict(os.environ, SOURCE_DATE_EPOCH=str(epoch)),
        )
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ubuntu", required=True, choices=TARGETS)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    print(build(args.ubuntu, args.output.resolve()))
