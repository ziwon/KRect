#!/usr/bin/env python3
"""Install/remove only KRect's per-user app and desktop integration."""
import argparse
import os
from pathlib import Path
import shlex
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remove", action="store_true")
    args = parser.parse_args()
    data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    binary = Path.home() / ".local/bin/krect"
    desktop = data / "applications/org.krect.KRect.desktop"
    icon = data / "icons/hicolor/scalable/apps/org.krect.KRect.svg"
    target = data / "krect"
    if args.remove:
        for path in [binary, desktop, icon, Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "autostart/org.krect.KRect.desktop"]:
            path.unlink(missing_ok=True)
        if target.is_dir():
            shutil.rmtree(target)
        return
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "app/main.py", target / "main.py")
    shutil.copytree(ROOT / "app/krect", target / "krect", dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "app/assets", target / "assets", dirs_exist_ok=True)
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text("#!/bin/sh\nexec /usr/bin/python3 -B " + shlex.quote(str(target / "main.py")) + ' "$@"\n')
    binary.chmod(0o755)
    desktop.parent.mkdir(parents=True, exist_ok=True)
    # Quoting follows the Desktop Entry specification; paths can contain spaces.
    command = str(binary).replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$").replace("%", "%%")
    desktop.write_text((ROOT / "app/org.krect.KRect.desktop").read_text().replace("Exec=krect", f'Exec="{command}"'))
    icon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "app/assets/org.krect.KRect.svg", icon)
    print(f"Desktop app installed: {binary}")


if __name__ == "__main__":
    main()
