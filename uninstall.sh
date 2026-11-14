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
for krect_command in kpackagetool6 kwriteconfig6; do
    if ! command -v "$krect_command" >/dev/null 2>&1; then
        printf 'Missing required command: %s\n' "$krect_command" >&2
        exit 1
    fi
done

kwriteconfig6 --file kwinrc --group Plugins --key krectEnabled false
krect_unloaded=false
for krect_dbus in qdbus6 /usr/lib/qt6/bin/qdbus qdbus; do
    if command -v "$krect_dbus" >/dev/null 2>&1; then
        if "$krect_dbus" org.kde.KWin /Scripting org.kde.kwin.Scripting.unloadScript krect >/dev/null 2>&1; then
            krect_unloaded=true
            break
        fi
    fi
done
kpackagetool6 --type=KWin/Script --remove krect
printf '%s\n' 'KRect package removed. Saved settings and custom shortcuts are retained.'
if [[ "$krect_unloaded" == false ]]; then
    printf '%s\n' 'Log out and back in to stop the currently loaded script.'
fi
