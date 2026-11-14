#!/usr/bin/env bash
# Sourced by install.sh and uninstall.sh; match tools to the desktop generation.
krect_version=$(plasmashell --version 2>/dev/null) || {
    printf '%s\n' 'plasmashell was not found. KRect requires Plasma 5.27 or Plasma 6.' >&2
    return 1
}
if [[ ! $krect_version =~ ([0-9]+)\.([0-9]+) ]]; then
    printf 'Cannot identify Plasma version: %s\n' "$krect_version" >&2
    return 1
fi
krect_major=${BASH_REMATCH[1]}
krect_minor=${BASH_REMATCH[2]}
if [[ $krect_major != 6 && ! ( $krect_major == 5 && $krect_minor -ge 27 ) ]]; then
    printf 'Unsupported Plasma version: %s. Use Plasma 5.27 or Plasma 6.\n' "$krect_version" >&2
    return 1
fi
krect_package_tool="kpackagetool$krect_major"
krect_config_tool="kwriteconfig$krect_major"

