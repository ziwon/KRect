#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
    printf '%s\n' 'Usage: bash install.sh' 'Install or update KRect for the current user; enable it in KDE System Settings.'
    exit 0
fi
if [[ $# -ne 0 ]]; then
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

printf '%s\n' \
    'KRect package installed for this user.' \
    'Open System Settings → Window Management → KWin Scripts.' \
    'Enable KRect and click Apply. For an update, disable/apply, then enable/apply.' \
    'Change shortcuts in Keyboard → Shortcuts; search for KRect.'
