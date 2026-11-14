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
if ! command -v kpackagetool6 >/dev/null 2>&1; then
    printf '%s\n' 'kpackagetool6 was not found. KRect requires KDE Plasma 6.' \
        'On Kubuntu with Plasma 6, install the kpackagetool6 package first.' >&2
    exit 1
fi

krect_root=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
krect_data="${XDG_DATA_HOME:-$HOME/.local/share}"
if [[ ! -f "$krect_root/package/contents/code/main.js" ]]; then
    printf '%s\n' 'Package is not built. Run python3 tools/build.py first.' >&2
    exit 1
fi
if [[ -f "$krect_data/kwin/scripts/krect/metadata.json" ]]; then
    kpackagetool6 --type=KWin/Script --upgrade "$krect_root/package"
else
    kpackagetool6 --type=KWin/Script --install "$krect_root/package"
fi

printf '%s\n' \
    'KRect package installed for this user.' \
    'Open System Settings → Window Management → KWin Scripts.' \
    'Enable KRect and click Apply. For an update, disable/apply, then enable/apply.' \
    'Change shortcuts in Keyboard → Shortcuts; search for KRect.'
