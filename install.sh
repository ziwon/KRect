#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
    printf '%s\n' 'Usage: bash install.sh [--script-only]' 'Install the desktop app and KWin engine for the current user.'
    exit 0
fi
if [[ $# -gt 1 || ( $# -eq 1 && $1 != --script-only ) ]]; then
    printf '%s\n' 'Unknown argument. Use --help.' >&2
    exit 2
fi
if [[ $EUID -eq 0 ]]; then
    printf '%s\n' 'Run this as your desktop user, without sudo.' >&2
    exit 1
fi
krect_root=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$krect_root/tools/plasma-tools.sh"
if ! command -v "$krect_package_tool" >/dev/null 2>&1; then
    printf 'Missing required command for Plasma %s: %s\n' "$krect_major" "$krect_package_tool" >&2
    exit 1
fi

krect_data="${XDG_DATA_HOME:-$HOME/.local/share}"
if [[ ! -f "$krect_root/package/contents/code/main.js" ]]; then
    printf '%s\n' 'Package is not built. Run python3 tools/build.py first.' >&2
    exit 1
fi
if [[ -f "$krect_data/kwin/scripts/krect/metadata.json" ]]; then
    "$krect_package_tool" --type=KWin/Script --upgrade "$krect_root/package"
else
    "$krect_package_tool" --type=KWin/Script --install "$krect_root/package"
fi

if [[ ${1:-} != --script-only ]]; then
    /usr/bin/python3 "$krect_root/tools/install_app.py"
    if command -v kbuildsycoca"$krect_major" >/dev/null 2>&1; then
        kbuildsycoca"$krect_major" --noincremental >/dev/null 2>&1 || true
    fi
fi

printf '%s\n' \
    'KRect package installed for this user.' \
    'Open KRect from the application launcher and click Enable KRect.' \
    'The script can also be enabled in System Settings → Window Management → KWin Scripts.' \
    'Change shortcuts in Keyboard → Shortcuts; search for KRect.'
