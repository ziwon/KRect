# Packaging and releases

## Outputs

For version `0.1.0`, the release workflow produces:

- `krect_0.1.0-1ubuntu24.04_all.deb`: Plasma 5.27, `kpackagetool5`.
- `krect_0.1.0-1ubuntu26.04_all.deb`: Plasma 6, `kpackagetool6`.
- `krect-0.1.0.kwinscript` and `krect-0.1.0.zip`.
- `SHA256SUMS` covering those four files.

Both Debian packages are architecture-independent JavaScript/UI/data packages.
They install to `/usr/share/kwin/scripts/krect`. Their dependencies constrain
`kwin-common` and `plasma-workspace` to the target Plasma generation, including
Ubuntu's `4:` package-version epoch. An Ubuntu release upgrade may remove the
old KRect package to satisfy those constraints; install the matching package
after the upgrade. There is no APT repository or automatic KRect package update.

No maintainer scripts run inside user sessions, enable KRect, change shortcuts,
or modify home directories. Existing user packages shadow the global copy:
remove a user-scope KRect installation before using the Debian package. Toggle
KRect or log out/in after updating or removing a running script.

## Local builds

Use Python 3.9+ and `dpkg-deb` (provided by `dpkg`). No Node/Python runtime is
needed by the installed KWin script.

```bash
python3 tools/build.py
python3 tools/build_deb.py --ubuntu 24.04
python3 tools/build_deb.py --ubuntu 26.04
dpkg-deb --info dist/krect_0.1.0-1ubuntu24.04_all.deb
```

`SOURCE_DATE_EPOCH` controls package timestamps. Identical source, toolchain,
target, and epoch produce identical `.deb` bytes; CI uses the commit timestamp.
The payload is copied from `package/`, with its entry point taken directly from
`src/main.js` to avoid packaging stale generated JavaScript.

Run `node --test tests/*.test.cjs` and
`python3 -m unittest discover -s tests -p 'test_*.py' -v` before committing.
The Debian tests inspect actual archives and check repeat-build equality.

## GitHub Actions

[release.yml](../.github/workflows/release.yml) runs on main pushes, pull requests,
manual dispatch, and `v*` tag pushes. Ordinary builds upload Actions artifacts;
only a tag push publishes a GitHub Release.

1. The validation job checks matching versions, all automated tests, shell
   syntax, generated entry-point consistency, and builds the source distributions.
2. Separate `ubuntu:24.04` and `ubuntu:26.04` containers build `.deb` files,
   run Lintian (errors fail the job), install real runtime dependencies and the
   package, check global KPackage discovery and source equality, and remove it.
3. After all jobs pass for a version tag, the release job creates the release,
   generates checksums, and uploads the assets. Only this job receives
   `contents: write`. Reruns replace the same assets instead of creating duplicates.

Containers have no running Plasma desktop. Installation/KPackage checks do not
certify KWin behaviour, Qt settings persistence, or Wayland rendering. See
[VALIDATION.md](VALIDATION.md) for actual desktop coverage.

Actions are pinned to upstream commit SHAs. No repository secret is needed;
publication uses the workflow's `GITHUB_TOKEN`.

## Publish a version

Set the same numeric `major.minor.patch` version in `package/metadata.json` and
`package.json`. Rebuild and commit the generated entry point and release changes.
The tag must exactly match `v` plus that version; a mismatch fails validation.

```bash
git push origin main
git tag -a v0.1.0 -m 'KRect 0.1.0'
git push origin v0.1.0
```

Inspect the Actions run and the release assets before sharing the release.
The workflow does not create version tags automatically.
