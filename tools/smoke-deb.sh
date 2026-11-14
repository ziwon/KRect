#!/usr/bin/env bash
# Run only in a disposable Ubuntu CI container: this installs/removes packages.
set -euo pipefail
if [[ $EUID -ne 0 || ! -f /.dockerenv ]]; then
    printf '%s\n' 'Run this check as root inside a disposable Docker container.' >&2
    exit 1
fi
if [[ $# -ne 2 || ! $2 =~ ^[56]$ ]]; then
    printf '%s\n' 'Usage: bash tools/smoke-deb.sh path/to/krect.deb plasma-major' >&2
    exit 2
fi
krect_deb=$(realpath "$1")
krect_major=$2
export DEBIAN_FRONTEND=noninteractive
apt-get install -y --no-install-recommends "$krect_deb"
test "$(dpkg-query -W -f='${db:Status-Status}' krect)" = installed
test -f /usr/share/kwin/scripts/krect/metadata.json
test ! -e /root/.local/share/kwin/scripts/krect
krect_listing=$(QT_QPA_PLATFORM=offscreen "kpackagetool$krect_major" --type=KWin/Script --list --global)
printf '%s\n' "$krect_listing"
[[ $krect_listing =~ (^|[[:space:]])krect($|[[:space:]]) ]]
cmp src/main.js /usr/share/kwin/scripts/krect/contents/code/main.js
desktop-file-validate /usr/share/applications/org.krect.KRect.desktop
krect --version
QT_QPA_PLATFORM=offscreen krect --smoke-test
dpkg --remove krect
test ! -e /usr/share/kwin/scripts/krect/metadata.json
test ! -e /usr/bin/krect
test ! -e /usr/share/applications/org.krect.KRect.desktop
test ! -e /usr/share/krect
printf 'Ubuntu package install, KPackage discovery, and removal passed for Plasma %s.\n' "$krect_major"
