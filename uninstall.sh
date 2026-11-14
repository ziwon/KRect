#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "--help" ]]; then
    printf '%s\n' 'Usage: bash uninstall.sh' 'Disable and remove the current user KRect package.'
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
for krect_command in "$krect_package_tool" "$krect_config_tool"; do
    if ! command -v "$krect_command" >/dev/null 2>&1; then
        printf 'Missing required command: %s\n' "$krect_command" >&2
        exit 1
    fi
done

"$krect_config_tool" --file kwinrc --group Plugins --key krectEnabled false
krect_unloaded=false
for krect_dbus in "qdbus$krect_major" "/usr/lib/qt$krect_major/bin/qdbus" qdbus; do
    if command -v "$krect_dbus" >/dev/null 2>&1; then
        if "$krect_dbus" org.kde.KWin /Scripting org.kde.kwin.Scripting.unloadScript krect >/dev/null 2>&1; then
            krect_unloaded=true
            break
        fi
    fi
done
"$krect_package_tool" --type=KWin/Script --remove krect
/usr/bin/python3 "$krect_root/tools/install_app.py" --remove
printf '%s\n' 'KRect package removed. Saved settings and custom shortcuts are retained.'
if [[ "$krect_unloaded" == false ]]; then
    printf '%s\n' 'Log out and back in to stop the currently loaded script.'
fi
